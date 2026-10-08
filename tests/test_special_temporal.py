"""M15：从格/专旺/化气岁运专题测试。"""

from __future__ import annotations

import datetime

import pytest

from tianze.domain.models import BirthInfo, Gender
from tianze.pipeline import build_chart
from tianze.analysis.special_temporal import (
    SPECIAL_TEMPORAL_SCHEMA_VERSION, _merged_candidates, _sp_cong_break,
    _sp_hua, _sp_zw, _transitions, analyze_special_temporal,
)
from tianze.analysis.temporal_delta import compute_temporal_delta


@pytest.fixture(scope="module")
def chart_1983():
    """甲日主（阳），原局曲直候选（1983-02-15 20:00 女）。"""
    return build_chart(BirthInfo(date=datetime.date(1983, 2, 15),
                                 time=datetime.time(20, 0), gender=Gender.FEMALE))


def test_structure_and_version(chart_1983):
    rep = compute_temporal_delta(chart_1983, annual=("壬", "子"))
    for f in rep.specialFindings:
        assert f["group"] in ("cong", "zhuanwang", "transformation")
        assert f["transition"] in ("unchanged", "appeared", "disappeared",
                                   "blocked", "unblocked", "regraded")
        assert f["refId"].startswith("temporal:special:")
        assert f["provenanceLevels"]
        assert f["status"] == "CANDIDATE"  # 永远候选级


def test_zhuanwang_support_and_regraded(chart_1983):
    """曲直候选 + 流年壬（印）生扶 → 生扶观察 + 状态 regraded（CANDIDATE→UNRESOLVED 由 delta 记录）。"""
    rep = compute_temporal_delta(chart_1983, annual=("壬", "子"))
    f = next(x for x in rep.specialFindings if x["candidateType"] == "曲直")
    assert "生扶" in f["evidence"][0]
    assert "DTZ-25" in f["evidence"][0]
    assert f["transition"] == "regraded"  # delta 中 CANDIDATE→UNRESOLVED
    assert f["temporalStatus"] == "UNRESOLVED"


def test_cong_shunshi_for_temporal_only_candidate():
    """己日主 + 流年壬（正财）→ 岁运新增从财候选的顺势观察（阴干从势）。"""
    chart = build_chart(BirthInfo(date=datetime.date(1984, 2, 5),
                                  time=datetime.time(10, 30), gender=Gender.MALE))
    rep = compute_temporal_delta(chart, annual=("壬", "子"))
    f = next(x for x in rep.specialFindings if x["candidateType"] == "从财")
    assert "顺势之神" in f["evidence"][0]
    assert "岁运上下文新增候选" in f["evidence"][0]
    assert "阴干" in f["evidence"][0]  # 己为阴干 → 顺势说（DTZ-04）


def test_yang_yin_school_split():
    """TR-SP-02：同一印比岁运下，阳干破格说权重更高、阴干顺势说权重更高（上下文相关流派）。"""
    yang_split = _sp_cong_break(_FakeChart("甲"), _FakeChart("甲"),
                                {("cong", "从财"): {"status": "CANDIDATE", "temporal_only": False}})
    yin_split = _sp_cong_break(_FakeChart("己"), _FakeChart("己"),
                               {("cong", "从财"): {"status": "CANDIDATE", "temporal_only": False}})
    assert list(yang_split[0][6].keys())[0].startswith("破格说")
    assert list(yin_split[0][6].keys())[0].startswith("顺势说")
    # 双方都保留对方，不裁决
    assert len(yang_split[0][6]) == 2 and len(yin_split[0][6]) == 2


class _FakeChart:
    """最小 chart 替身：只暴露 day_master/temporal units 需要的接口。"""

    def __init__(self, dm: str):
        from types import SimpleNamespace
        self.day_master = SimpleNamespace(stem=dm)
        # 岁运干：印 + 比劫各一（甲印=壬/癸；己印=丙/丁）
        stem = "壬" if dm == "甲" else "丙"
        stem2 = "甲" if dm == "甲" else "己"
        self._units = [("annual", stem, "子"), ("luck", stem2, "子")]

    @property
    def advancedAnalysis(self):
        return {"specialPattern": {"cong": [], "zhuanwang": [], "transformation": []}}

    def temporal_units(self):  # 与 TemporalContext 接口一致（evaluator 经 ctx 调用）
        return self._units


def test_transitions_and_merge():
    """delta 状态迁移 → transition 映射（added→appeared 等）。"""
    from tianze.analysis.event_themes import EventRuleHit, EventDirection, EventTheme, SchoolView
    from tianze.analysis.temporal_delta import DeltaItem, DeltaKind
    items = [DeltaItem(analysis="special", kind=DeltaKind.BLOCKED, subject="从格候选·从财",
                       natalValue="LIKELY", temporalValue="BLOCKED", trigger="大运丙")]
    shim = type("S", (), {"items": items, "context": None})()
    trans = _transitions(shim)
    assert trans[("cong", "从财")]["kind"] == "blocked"
    # 非新增（blocked）且原局无此候选 → 不进 merged（merged 只收 natal + added）
    assert ("cong", "从财") not in _merged_candidates(_FakeChart("甲"), trans)
    # added 才进 merged
    trans_added = {("cong", "从财"): {"kind": "added", "natal": None,
                                      "temporal": "CANDIDATE", "trigger": "流年壬"}}
    merged = _merged_candidates(_FakeChart("甲"), trans_added)
    assert merged[("cong", "从财")] == {"status": None, "temporal_only": True}


def test_hua_never_confirmed(chart_1983):
    """化气候选 + 合神再现 → 引化候选，带 DTZ-18 合≠化 警示，status 恒为 CANDIDATE。"""
    rep = compute_temporal_delta(chart_1983, annual=("甲", "子"))
    hua = [x for x in rep.specialFindings if x["group"] == "transformation"]
    for f in hua:
        assert "合≠化" in f["evidence"][0] or "不升级" in f["evidence"][0]
        assert f["status"] == "CANDIDATE"
    # 直接评估器验证（原局可能无化气候选）
    from types import SimpleNamespace
    ctx_shim = SimpleNamespace(temporal_units=lambda: [("annual", "丁", "子")])
    out = _sp_hua(chart_1983, ctx_shim, {("transformation", "丁壬"): {"status": "CANDIDATE",
                                                                      "temporal_only": False}})
    if out:
        assert "不升级" in out[0][5]


def test_missing_evaluator_raises(chart_1983, monkeypatch):
    import tianze.analysis.special_temporal as st_mod
    monkeypatch.setattr(st_mod, "_load_special_rules",
                        lambda: [{"id": "TR-SP-NOPE", "category": "special-pattern",
                                  "provenance": []}])
    shim = type("S", (), {"items": [], "context": None})()
    with pytest.raises(KeyError, match="TR-SP-NOPE"):
        analyze_special_temporal(chart_1983, shim)


def test_no_fortune_language(chart_1983):
    rep = compute_temporal_delta(chart_1983, annual=("壬", "子"))
    blob = rep.model_dump_json(by_alias=True, exclude_none=True)
    for banned in ("发财", "大凶", "必定", "一定"):
        assert banned not in blob


def test_schema_version_export():
    assert SPECIAL_TEMPORAL_SCHEMA_VERSION == "1.0.0"


# ---------- M22：TR-SP-05 化神所忌 / TR-SP-07 从格所从受克 ----------

_chart83 = None


def _c83():
    """1983-02-15 女命（甲日主）chart，模块级惰性构建。"""
    global _chart83
    if _chart83 is None:
        import datetime
        from tianze.domain.models import BirthInfo, Gender
        from tianze.pipeline import build_chart
        _chart83 = build_chart(BirthInfo(date=datetime.date(1983, 2, 15),
                                         time=datetime.time(20, 0), gender=Gender.FEMALE))
    return _chart83


def test_sp05_hua_taboo_per_pair():
    """DTZ-48 逐干所忌：丁壬候选 + 岁运庚 → 受阻观察；岁运辛 → 不触发（引文只忌庚）。"""
    from types import SimpleNamespace
    ctx = SimpleNamespace(temporal_units=lambda: [("annual", "庚", "子")])
    cands = {("transformation", "丁壬"): {"status": "CANDIDATE", "temporal_only": False}}
    out = _sp_hua_taboo(_c83(), ctx, cands)
    assert out and "化神所忌" in out[0][5] and "庚" in out[0][5]
    ctx2 = SimpleNamespace(temporal_units=lambda: [("annual", "辛", "丑")])
    assert _sp_hua_taboo(_c83(), ctx2, cands) == []   # 辛不在丁壬所忌


def test_sp07_cong_ke_shen():
    """DTZ-48 克抑不能用：从财候选 + 岁运比劫 → 破格说/顺势说两说并存。"""
    from types import SimpleNamespace
    ctx = SimpleNamespace(temporal_units=lambda: [("annual", "甲", "辰")])
    cands = {("cong", "从财"): {"status": "CANDIDATE", "temporal_only": False}}
    out = st_mod._sp_cong_ke(_c83(), ctx, cands)
    assert out and "克所从之财" in out[0][5]
    assert set(out[0][6]) == {"破格说", "顺势说（保留）"}


def test_sp05_07_in_gate_rules():
    from tianze.knowledge.temporal_rules import load_temporal_rules
    ids = {r["id"] for r in load_temporal_rules()}
    assert {"TR-SP-05", "TR-SP-07"} <= ids
    # 均有 CLASSICAL 引文
    for r in load_temporal_rules():
        if r["id"] in ("TR-SP-05", "TR-SP-07"):
            assert any(p["level"] == "CLASSICAL_EXPLICIT" for p in r["provenance"])


import tianze.analysis.special_temporal as st_mod  # noqa: E402
from tianze.analysis.special_temporal import _sp_hua_taboo  # noqa: E402


# ---------- M27 · TR-SP-08 假从/假化岁运敏感（DTZ-49 行运之别） ----------

def test_trsp08_jiacong_sensitivity(chart_1983):
    """假从候选 + 岁运印比/根气 → 假从岁运敏感两说；无岁运不触发。"""
    from tianze.analysis.temporal_delta import compute_temporal_delta
    # 找一个带 SP-CG-E2 假从说的盘
    chart = None
    import datetime as _dt
    d0 = _dt.date(1980, 1, 1)
    for i in range(400):
        c = build_chart(BirthInfo(date=d0 + _dt.timedelta(days=i),
                                  time=_dt.time(10, 0), gender=Gender.MALE))
        for x in (c.advancedAnalysis or {}).get("specialPattern", {}).get("cong", []):
            if any("假从说" in (e.get("text") or "") for e in x.get("exceptions", [])):
                chart = c
                break
        if chart:
            break
    assert chart is not None, "样本窗口内应存在带假从说的从格候选"
    rep = compute_temporal_delta(chart, annual=("甲", "子"))
    f = next((x for x in rep.specialFindings
              if x["ruleId"] == "TR-SP-08" and x["group"] == "cong"), None)
    assert f is not None
    assert "假从" in f["evidence"][0]
    assert "逆旺气" in f["schoolSplit"]["逆旺气破格说（权重更高）"]
    assert f["status"] == "CANDIDATE"


def test_trsp08_jiahua_drain():
    """化气候选 + 岁运泄气之干 → 假化敏感（DTZ-49：化神见克泄便是假化）。"""
    from tianze.analysis.temporal_delta import compute_temporal_delta
    from tianze.analysis.special import analyze_transformation
    # 构造：甲日主 己邻位合（化土候选）+ 流年庚（土之泄？土生金→庚=泄）
    ts = analyze_transformation("甲", "未", ["丙", "己", "甲", "庚"], ["辰", "未", "戌", "申"])
    assert any(t.status.value == "CANDIDATE" for t in ts)
    chart = build_chart(BirthInfo(date=datetime.date(1990, 1, 15),
                                  time=datetime.time(10, 0), gender=Gender.MALE))
    rep = compute_temporal_delta(chart, annual=("庚", "辰"))
    jh = [x for x in rep.specialFindings if x["ruleId"] == "TR-SP-08"
          and x["group"] == "transformation"]
    if jh:  # 该盘若有化气候选则必须带假化敏感两说
        assert "假化" in jh[0]["label"] or "假化" in jh[0]["evidence"][0]


def test_trsp08_weakened_root_constrained():
    """微根受制：假从要件微根被岁运刑冲 → 条件变化两说（不升级候选）。"""
    import datetime as dt
    chart = build_chart(BirthInfo(date=dt.date(1980, 1, 3),
                                  time=dt.time(10, 0), gender=Gender.MALE))
    rep = compute_temporal_delta(chart, annual=("甲", "丑"))  # 丑冲微根所在支未
    hits = [x for x in rep.specialFindings if x["ruleId"] == "TR-SP-08"
            and x["label"] == "微根受制"]
    assert hits, [x["evidence"][0][:50] for x in rep.specialFindings if x["ruleId"] == "TR-SP-08"]
    assert "条件变化说" in hits[0]["schoolSplit"]
    assert "保守说" in hits[0]["schoolSplit"]
    assert all(x["status"] == "CANDIDATE" for x in hits)  # 永不升级
