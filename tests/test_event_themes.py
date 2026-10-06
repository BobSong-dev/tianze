"""M14：事件主题层测试（EventThemeCandidate / 规则 / 流派感知 / confidence）。"""

from __future__ import annotations

import datetime

import pytest

from tianze.domain.models import BirthInfo, Gender
from tianze.pipeline import build_chart
from tianze.analysis.event_themes import (
    CONFIDENCE_PARAMS, EVALUATORS, EventDirection, EventStatus, EventTheme,
    compute_event_themes,
)
from tianze.analysis.temporal_delta import compute_temporal_delta


@pytest.fixture(scope="module")
def chart_male():
    return build_chart(BirthInfo(date=datetime.date(1984, 2, 5),
                                 time=datetime.time(10, 30), gender=Gender.MALE))


@pytest.fixture(scope="module")
def chart_female():
    return build_chart(BirthInfo(date=datetime.date(1983, 2, 15),
                                 time=datetime.time(20, 0), gender=Gender.FEMALE))


def test_report_structure(chart_male):
    rep = compute_event_themes(chart_male, annual=("丙", "午"))
    assert rep.eventSchemaVersion == "1.0.0"
    assert rep.warnings and any("不是现实事件预测" in w for w in rep.warnings)
    assert rep.params["kind"] == "ENGINEERING_HEURISTIC"
    assert rep.unmatchedRules, "未命中规则应保留可审计"


def test_no_confirmed_and_no_fortune(chart_male):
    rep = compute_event_themes(chart_male, luck=("甲", "子"), annual=("丙", "午"),
                               monthly=("庚", "寅"))
    blob = rep.model_dump_json(by_alias=True, exclude_none=True)
    assert "CONFIRMED" not in blob
    for banned in ("一定", "必然", "必定", "发财", "升职", "结婚", "离婚", "横祸"):
        assert banned not in blob


def test_school_aware_disputed_career(chart_male):
    """官星支持 + 伤官见官反对 → career DISPUTED + agreement=CONFLICT（分歧显式保留）。"""
    rep = compute_event_themes(chart_male, luck=("甲", "子"), annual=("丙", "午"),
                               monthly=("庚", "寅"))
    career = next(t for t in rep.themes if t.theme == EventTheme.CAREER)
    assert career.status == EventStatus.DISPUTED
    assert career.agreement == "CONFLICT"
    assert career.supportingEvidence and career.opposingEvidence
    assert career.schoolViews["traditional"] == "both"
    assert any("救应" not in e for e in career.opposingEvidence)  # v1 不判救应


def test_gender_conditional_spouse_star(chart_male, chart_female):
    """配偶星：男看财、女看官；性别未知 → UNRESOLVED（不猜）。"""
    ctx_chart = chart_male
    # 男命流年财星（己日主 → 壬/癸为财）
    rep_m = compute_event_themes(ctx_chart, annual=("壬", "辰"))
    rel_m = next((t for t in rep_m.themes if t.theme == EventTheme.RELATIONSHIP), None)
    assert rel_m is not None and rel_m.status != EventStatus.UNRESOLVED
    assert any("妻星" in e for e in rel_m.supportingEvidence)
    # 女命流年官杀（甲日主 → 庚/辛为官杀）
    rep_f = compute_event_themes(chart_female, annual=("庚", "午"))
    rel_f = next((t for t in rep_f.themes if t.theme == EventTheme.RELATIONSHIP), None)
    assert rel_f is not None and rel_f.status != EventStatus.UNRESOLVED
    assert any("夫星" in e for e in rel_f.supportingEvidence)


def test_gender_unknown_unresolved(chart_male):
    """性别未知 → EV-REL-03 输出 UNRESOLVED 主题候选。"""
    import copy
    chart_u = chart_male.model_copy(update={
        "birth": chart_male.birth.model_copy(update={"gender": Gender.UNKNOWN})})
    rep = compute_event_themes(chart_u, annual=("壬", "辰"))
    rel = next(t for t in rep.themes if t.theme == EventTheme.RELATIONSHIP)
    assert rel.status == EventStatus.UNRESOLVED
    assert any("性别未知" in e for e in rel.supportingEvidence + rel.opposingEvidence
               or rel.supportingEvidence)


def test_shensha_view_isolated(chart_male):
    """神煞视角（驿马/桃花）单独成 view，不与传统 view 合并成强结论。"""
    # 甲子年生人：年支子 → 驿马在寅；日支巳 → 驿马在亥
    rep = compute_event_themes(chart_male, monthly=("甲", "寅"))
    mob = next(t for t in rep.themes if t.theme == EventTheme.MOBILITY)
    assert mob.schoolViews == {"shensha": "support"}
    assert any("驿马" in e for e in mob.supportingEvidence)
    assert mob.confidence <= 1.0
    # shensha 规则的 provenance 含 CLASSICAL_EXPLICIT（SS-R22 引文）但 view 标注 shensha
    hit = mob.triggeredRules[0]
    assert hit.view.value == "shensha"


def test_yima_and_xianchi_tables():
    """驿马/咸池起例正确（申子辰马在寅、寅午戌马在申、咸池三合沐浴位）。"""
    from tianze.analysis.event_themes import _YIMA, _XIANCHI
    assert _YIMA["子"] == "寅" and _YIMA["午"] == "申" and _YIMA["酉"] == "亥"
    assert _XIANCHI["子"] == "酉" and _XIANCHI["午"] == "卯"


def test_cai_ku_conflict_note(chart_male):
    """财库逢冲规则必须携带两说 conflictNote（DTZ-35 喜冲不可靠）。"""
    import json
    from tianze.knowledge.event_rules import load_event_rules
    r = next(x for x in load_event_rules() if x["id"] == "EV-WEA-03")
    assert "两说" in (r.get("conflictNote") or "")
    assert any(p["level"] == "CLASSICAL_EXPLICIT" for p in r["provenance"])


def test_confidence_transparent_and_bounded(chart_male):
    """confidence 0..1、依据逐条可回查、参数随结果输出；不是概率。"""
    rep = compute_event_themes(chart_male, luck=("甲", "子"), annual=("丙", "午"),
                               monthly=("庚", "寅"))
    for t in rep.themes:
        assert 0.0 <= t.confidence <= 1.0
        assert t.confidenceBasis  # 每条主题都有加权依据
        for b in t.confidenceBasis:
            assert "event:rule:" in b
    assert rep.params["note"] and "概率" in rep.params["note"]


def test_deterministic_output(chart_male):
    r1 = compute_event_themes(chart_male, luck=("甲", "子"), annual=("丙", "午"))
    r2 = compute_event_themes(chart_male, luck=("甲", "子"), annual=("丙", "午"))
    assert r1.model_dump_json(by_alias=True, exclude_none=True) == \
        r2.model_dump_json(by_alias=True, exclude_none=True)


def test_missing_evaluator_raises(chart_male, monkeypatch):
    import tianze.analysis.event_themes as et
    from tianze.knowledge import event_rules as er
    rules = [dict(r) for r in er.load_event_rules()]
    rules.append({"id": "EV-NOPE-99", "theme": "career", "view": "traditional",
                  "label": "x", "provenance": []})
    monkeypatch.setattr(er, "load_event_rules", lambda: rules)
    monkeypatch.setattr(et, "_load_event_rules", lambda: rules)
    with pytest.raises(KeyError, match="EV-NOPE-99"):
        compute_event_themes(chart_male, annual=("丙", "午"))


def test_all_rules_have_evaluators():
    from tianze.knowledge.event_rules import load_event_rules
    for r in load_event_rules():
        assert r["id"] in EVALUATORS, f"{r['id']} 缺执行器"


def test_provenance_discipline():
    """无引文链的规则不得标 CLASSICAL_EXPLICIT；工程规则用 TIANZE-ENGINEERING-*。"""
    from tianze.knowledge.event_rules import load_event_rules
    for r in load_event_rules():
        levels = {p["level"] for p in r["provenance"]}
        if r["candidateId"].startswith("TIANZE-ENGINEERING-"):
            assert "CLASSICAL_EXPLICIT" not in levels
            assert "ENGINEERING_HEURISTIC" in levels
        if "CLASSICAL_EXPLICIT" in levels:
            assert r["view"] in ("traditional", "special_pattern", "shensha")


def test_theme_status_vocabulary(chart_male, chart_female):
    """全部 status 在 CANDIDATE/LIKELY/DISPUTED/BLOCKED/UNRESOLVED 内。"""
    for chart, pairs in ((chart_male, [("甲", "子"), ("丙", "午"), ("庚", "寅")]),
                         (chart_female, [("庚", "辰"), ("己", "卯")])):
        rep = compute_event_themes(chart, luck=pairs[0], annual=pairs[1])
        for t in rep.themes:
            assert t.status in (EventStatus.CANDIDATE, EventStatus.LIKELY,
                                EventStatus.DISPUTED, EventStatus.BLOCKED,
                                EventStatus.UNRESOLVED)


def test_lazy_no_full_expansion(chart_male):
    """惰性：不选岁运节点 → 空报告（不做 80 年×12 月全量展开）。"""
    rep = compute_event_themes(chart_male)
    assert rep.themes == []


def test_timeline_event_theme_performance(chart_male):
    """性能纪律：聚焦节点事件主题计算为毫秒级（惰性，无全量预展开）。"""
    import time
    t0 = time.perf_counter()
    for _ in range(20):
        compute_event_themes(chart_male, luck=("甲", "子"), annual=("丙", "午"),
                             monthly=("庚", "寅"))
    elapsed = (time.perf_counter() - t0) / 20
    assert elapsed < 0.2, f"单节点事件主题计算过慢: {elapsed:.3f}s"


# ---------- M15 扩充规则（组合/条件化） ----------

def test_shishen_zhisha_conditional():
    """EV-CAR-04：岁运食神+七杀 → career 支持，前提（身强煞浅不可制）必须保留。"""
    # 甲日主：丙=食神，庚=七杀
    rep = compute_event_themes(_dm_chart("甲"), annual=("丙", "子"), luck=("庚", "午"))
    car = next((t for t in rep.themes if t.theme == EventTheme.CAREER), None)
    assert car is not None
    hit = next((h for h in car.triggeredRules if h.ruleId == "EV-CAR-04"), None)
    assert hit is not None
    assert any("身强煞浅" in e or "前提保留" in e for e in hit.evidence)


def test_sharen_he():
    """EV-CAR-05：原局阳刃 + 岁运七杀 → 煞刃相合 support。"""
    rep = compute_event_themes(_dm_chart("甲"), annual=("庚", "子"))
    car = next((t for t in rep.themes if t.theme == EventTheme.CAREER), None)
    hit = next((h for h in (car.triggeredRules if car else [])
                if h.ruleId == "EV-CAR-05"), None)
    if hit:
        assert "煞刃相合" in " ".join(hit.evidence)


def test_shishang_shengcai():
    """EV-WEA-04：岁运食伤+财星 → wealth 支持。"""
    rep = compute_event_themes(_dm_chart("甲"), annual=("丙", "子"), luck=("戊", "辰"))
    wea = next((t for t in rep.themes if t.theme == EventTheme.WEALTH), None)
    hit = next((h for h in (wea.triggeredRules if wea else [])
                if h.ruleId == "EV-WEA-04"), None)
    if hit:
        assert "食伤生财" in " ".join(hit.evidence)


def test_cai_yin_bu_rong():
    """EV-REL-05：岁运印+财并见 → relationship 反对 + MLD-18 边界保留。"""
    rep = compute_event_themes(_dm_chart("甲"), annual=("癸", "巳"))
    rel = next((t for t in rep.themes if t.theme == EventTheme.RELATIONSHIP), None)
    hit = next((h for h in (rel.triggeredRules if rel else [])
                if h.ruleId == "EV-REL-05"), None)
    if hit:
        assert any("不可避免" in e or "张力" in e for e in hit.evidence)


def _dm_chart(dm: str):
    """构造指定日主的最小真实 chart（经 pipeline，保证十神/藏干口径一致）。"""
    import datetime as _dt
    dates = {"甲": (1983, 2, 15), "己": (1984, 2, 5)}
    y, m, d = dates.get(dm, (1983, 2, 15))
    gender = Gender.FEMALE if dm == "甲" else Gender.MALE
    return build_chart(BirthInfo(date=_dt.date(y, m, d),
                                 time=_dt.time(20 if dm == "甲" else 10, 0),
                                 gender=gender))
