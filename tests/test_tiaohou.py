"""M6 调候引擎测试 + K1 规则质量测试（Schema/Reference/Quote/ID/Coverage/Conflict）。"""

from __future__ import annotations

import datetime as dt
from collections import Counter

import pytest

from tianze.analysis.tiaohou import analyze_tiaohou
from tianze.domain.models import BirthInfo
from tianze.knowledge.loader import load_tiaohou_conflicts, load_tiaohou_rules
from tianze.knowledge.models import ExecutableRule
from tianze.pipeline import build_chart

STEMS = "甲乙丙丁戊己庚辛壬癸"
MONTHS = "寅卯辰巳午未申酉戌亥子丑"
POS4 = ["year", "month", "day", "hour"]


def stems_map(stems: list[str | None]) -> dict:
    return dict(zip(POS4, stems))


# ---------- 覆盖与质量（K1 Rule Quality Tests） ----------

def test_coverage_120():
    """Coverage Test：10 日主 × 12 月支全部有规则（本知识库为穷通宝鉴全本）。"""
    cells = set()
    for r in load_tiaohou_rules():
        dm = next(c.value for c in r.conditions if c.field == "dayMaster")
        mb = next(c.value for c in r.conditions if c.field == "monthBranch")
        cells.add((dm, mb))
    assert len(cells) == 120
    assert set(cells) == {(d, m) for d in STEMS for m in MONTHS}


def test_rule_id_uniqueness_and_format():
    """Rule ID Test：全局唯一；TH- 前缀 + 候选 ID 可反查。"""
    ids = [r.id for r in load_tiaohou_rules()]
    assert len(ids) == len(set(ids))
    for rid in ids:
        assert rid.startswith("TH-"), rid


def test_candidate_reference_integrity():
    """Reference Test：每条 ExecutableRule 的 candidateId 必须在候选库中存在。"""
    candidates = set()
    for book in ("QBT", "ZHY"):
        data = __import__("json").loads(
            (__import__("pathlib").Path("knowledge/normalized") / book / "rules.json")
            .read_text(encoding="utf-8"))["rules"]
        candidates |= {r["id"] for r in data}
    for r in load_tiaohou_rules():
        assert r.candidate_id in candidates, f"{r.id} 引用了不存在的候选 {r.candidate_id}"


def test_schema_all_rules_valid():
    """Schema Test：全部规则通过 Pydantic 校验（loader 内已验证，此处显式断言）。"""
    rules = load_tiaohou_rules()
    assert len(rules) == 182
    assert all(isinstance(r, ExecutableRule) for r in rules)


def test_classical_explicit_requires_quote():
    """Quote Test：声明 CLASSICAL_EXPLICIT 的规则必须携带原文引文（provenance.note）。"""
    for r in load_tiaohou_rules():
        for p in r.provenance:
            if p.level == "CLASSICAL_EXPLICIT":
                assert p.note, f"{r.id} 声明古籍原文但无引文"


def test_conflicts_registered_not_silent():
    """Conflict Test：条件重叠（甲-未、己-申）登记在案且带处理策略。"""
    conflicts = load_tiaohou_conflicts()
    overlaps = {tuple(c["conditionOverlap"].values()) for c in conflicts}
    assert ("甲", "未") in overlaps and ("己", "申") in overlaps
    assert all(c["resolution"] == "specific-over-general" for c in conflicts)


def test_no_uncited_classical_claims():
    """禁止伪造古籍出处：quality A 级（已人工核对）当前必须为零——知识库 OCR 未全核。"""
    for r in load_tiaohou_rules():
        assert r.quality in ("B", "C"), f"{r.id} 质量等级越权：{r.quality}"


# ---------- 分析器行为 ----------

def test_analyzer_desired_vs_present_separated():
    """1983 盘（甲寅月）：desired=丙/癸，命局四干癸甲甲甲——丙未见、癸已见（年干）。"""
    chart = build_chart(BirthInfo(date=dt.date(1983, 2, 15), time=dt.time(20, 0), gender="female"))
    t = chart.tiaohou
    assert t is not None and t.resolved is True
    by_stem = {r.target_stem: r for r in t.recommendations}
    assert by_stem["丙"].priority == "primary"
    assert by_stem["丙"].present is False and by_stem["丙"].positions == []
    assert by_stem["癸"].present is True
    assert by_stem["癸"].positions == ["year"]
    # 反查链：recommendation → rule id → 候选 ID → 出处页码
    rec = by_stem["丙"]
    assert rec.rule_ids and rec.rule_ids[0] == "TH-QBT-甲-01-寅"
    assert rec.source is not None and rec.source.book == "穷通宝鉴评注"
    assert rec.source.pages and rec.source.pages[0] == 34
    assert rec.quote and "春月之木" in rec.quote


def test_analyzer_month_targets_match_knowledge():
    """抽核经典调候口径：甲酉→丁先、庚申→丁庚、乙亥→丙尊壬多戊、癸午→比肩癸。"""
    def primary(dm, month):
        r = analyze_tiaohou(dm, month, stems_map([dm, None, dm, None]))
        ps = [x for x in r.recommendations if x.priority == "primary"]
        return ps[0].target_stem if ps else None

    assert primary("甲", "酉") == "丁"
    assert primary("庚", "申") == "丁"
    assert primary("乙", "亥") == "丙"
    assert primary("癸", "午") == "癸"  # 五月癸水须比肩


def test_condition_dormant_rule_recorded():
    """丁午（建禄）条件：seasonPhase 未提供时规则休眠并在 conditions/证据中留痕。"""
    r = analyze_tiaohou("丁", "午", stems_map(["丁", "丙", "甲", "丁"]))
    assert any(c.get("field") == "state" for c in r.conditions)
    assert any("休眠" in e or "条件未满足" in e for e in r.evidence)


def test_exception_and_avoid_stem():
    """乙子：专用丙火、忌癸出干——命局见癸时例外命中并写入证据。"""
    r = analyze_tiaohou("乙", "子", stems_map(["癸", "乙", "乙", "乙"]))
    by_stem = {x.target_stem: x for x in r.recommendations}
    assert "丙" in by_stem and by_stem["丙"].priority == "primary"
    assert any("忌 癸" in e or "癸" in e for e in r.evidence)
    assert r.exceptions and r.exceptions[0]["value"] == "癸"


def test_unresolved_cell_never_fabricated():
    """若知识库缺格（当前无），分析器必须输出 UNRESOLVED 而非编造——用错误月支验证。"""
    r = analyze_tiaohou("甲", "在天", stems_map(["甲", None, None, None]))
    assert r.resolved is False and r.recommendations == []


def test_no_fortune_telling_output():
    """M6 边界：输出结构中不得出现吉凶断语字段。"""
    r = analyze_tiaohou("甲", "寅", stems_map(["丙", "甲", "甲", "癸"]))
    blob = r.model_dump_json()
    for banned in ("富贵", "大贵", "吉凶", "婚姻", "财运"):
        assert banned not in blob


def test_specific_over_general_on_jia_wei():
    """甲未：六月专论（先丁后庚）覆盖五六月合论（先癸后丁）——specific-over-general。"""
    r = analyze_tiaohou("甲", "未", stems_map(["甲", "甲", "甲", "甲"]))
    primary = [x for x in r.recommendations if x.priority == "primary"]
    assert primary and primary[0].target_stem == "丁"  # 而非合论的 癸
    assert any("specific-over-general" in c or "专论" in c for c in r.conflicts)
