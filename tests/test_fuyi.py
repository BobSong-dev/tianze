"""M4.2 fuyi 分析器测试：R21 级联九规则全路径 + UNCERTAIN 弃权 + 冲突注记。"""

from __future__ import annotations

import datetime as dt

from tianze.analysis.month_command import compute_month_command
from tianze.analysis.roots import collect_roots
from tianze.analysis.strength import StrengthFacts, default_run, run_strength
from tianze.analysis.strength.methods.fuyi import FuyiStrengthAnalyzer
from tianze.analysis.strength.methods.weighted import WeightedStrengthAnalyzer
from tianze.domain.models import BirthInfo, RuleLevel
from tianze.ganzhi.tables import STEM_ELEMENT
from tianze.pipeline import build_chart

POS4 = ["year", "month", "day", "hour"]


def make_facts(pillars: list[tuple[str, str | None, str | None]], day_master: str = "甲") -> StrengthFacts:
    stems = [p[1] for p in pillars]
    branches = [p[2] for p in pillars]
    month_branch = next(p[2] for p in pillars if p[0] == "month")
    mc = compute_month_command(month_branch, day_master, stems)
    roots = collect_roots(stems, branches, POS4, day_master)
    return StrengthFacts(
        day_master=day_master,
        day_master_element=STEM_ELEMENT[day_master],
        month_command=mc,
        day_master_roots=tuple(r for r in roots if r.is_day_master),
        other_stems=tuple((s, p[0]) for s, p in zip(stems, pillars) if s and p[0] != "day"),
        pillar_units=tuple(pillars),
    )


def fuyi_of(pillars, day_master="甲"):
    return FuyiStrengthAnalyzer().analyze(make_facts(pillars, day_master))


def test_r21_1_extreme_strong():
    """得令 + 多根 + 多印比 → 极强（high）。1983 盘。"""
    r = fuyi_of([("year", "癸", "亥"), ("month", "甲", "寅"), ("day", "甲", "戌"), ("hour", "甲", "戌")])
    assert r.verdict == "极强" and r.confidence == "high"
    assert r.evidence[0].startswith("命中规则 R21-1")
    assert any("得令" in e for e in r.support_evidence)
    assert any("多根" in e for e in r.support_evidence)


def test_r21_2_extreme_weak_high():
    """失令(死) + 无根 + 无印比 + 月令克日 → 极弱（high）。"""
    r = fuyi_of([("year", "庚", "酉"), ("month", "丙", "戌"), ("day", "甲", "酉"), ("hour", "辛", "戌")])
    assert r.verdict == "极弱" and r.confidence == "high"
    assert r.evidence[0].startswith("命中规则 R21-2")
    assert any("月令克日主" in e for e in r.drain_evidence)
    assert any("无根" in e for e in r.drain_evidence)


def test_r21_3_extreme_weak_medium():
    """失令(相，不克日) + 无根 + 无印比 → 极弱（medium）。"""
    r = fuyi_of([("year", "庚", "子"), ("month", "丙", "子"), ("day", "甲", "戌"), ("hour", "辛", "丑")])
    assert r.verdict == "极弱" and r.confidence == "medium"
    assert r.evidence[0].startswith("命中规则 R21-3")


def test_r21_4_uncertain_on_conflict():
    """得令但仅月令单根 + 无印比 + 克泄耗 3 透 → UNCERTAIN（信号对冲，不强判）。"""
    r = fuyi_of([("year", "庚", "酉"), ("month", "丙", "寅"), ("day", "甲", "戌"), ("hour", "辛", "丑")])
    assert r.verdict == "UNCERTAIN" and r.confidence == "high"
    assert any("信号冲突" in x for x in r.evidence)
    assert "UNCERTAIN" in r.note


def test_r21_5_strong_medium():
    """相月 + 双根 + 双印比 → 支持票 5 vs 克泄票 1 → 偏强（medium）。"""
    r = fuyi_of([("year", "壬", "子"), ("month", "丁", "亥"), ("day", "甲", "戌"), ("hour", "乙", "卯")])
    assert r.verdict == "偏强" and r.confidence == "medium"
    assert r.evidence[0].startswith("命中规则 R21-5")


def test_r21_6_weak_medium():
    """休月 + 无根 + 仅 1 印 + 克泄 2 透 → 克泄票领先 3 → 偏弱（medium）。"""
    r = fuyi_of([("year", "庚", "午"), ("month", "丙", "午"), ("day", "甲", "子"), ("hour", "癸", "酉")])
    assert r.verdict == "偏弱" and r.confidence == "medium"
    assert r.evidence[0].startswith("命中规则 R21-6")


def test_r21_7_strong_low():
    """相月 + 单根 + 单印比 → 支持票 3 vs 2 → 偏强（low）。"""
    r = fuyi_of([("year", "壬", "子"), ("month", "庚", "子"), ("day", "甲", "亥"), ("hour", "辛", "丑")])
    assert r.verdict == "偏强" and r.confidence == "low"
    assert r.evidence[0].startswith("命中规则 R21-7")


def test_r21_8_weak_low():
    """休月 + 单根 + 单印比 + 克泄 2 透 → 差 -1 → 偏弱（low）。"""
    r = fuyi_of([("year", "庚", "午"), ("month", "丙", "午"), ("day", "甲", "亥"), ("hour", "壬", "子")])
    assert r.verdict == "偏弱" and r.confidence == "low"
    assert r.evidence[0].startswith("命中规则 R21-8")


def test_r21_9_neutral():
    """休月 + 双根（亥中气+寅本气）+ 单印比 → 票数均衡 3:3 → 中和（low）。"""
    r = fuyi_of([("year", "壬", "亥"), ("month", "丁", "午"), ("day", "甲", "寅"), ("hour", "庚", "卯")])
    assert r.verdict == "中和" and r.confidence == "low"
    assert r.evidence[0].startswith("命中规则 R21-9")


def test_uncertain_abstains_from_agreement():
    """R22：UNCERTAIN 视为弃权——weighted 有 verdict 而 fuyi 弃权 → 无 agreement。"""
    facts = make_facts([("year", "庚", "酉"), ("month", "丙", "寅"), ("day", "甲", "戌"), ("hour", "辛", "丑")])
    report = run_strength([WeightedStrengthAnalyzer(), FuyiStrengthAnalyzer()], facts)
    fuyi = report.methods[1]
    assert fuyi.verdict == "UNCERTAIN"
    assert report.agreement is None


def test_disputed_when_far_apart():
    """极强 vs 偏弱（相隔 2 档）→ DISPUTED。"""
    facts = make_facts([("year", "癸", "亥"), ("month", "甲", "寅"), ("day", "甲", "戌"), ("hour", "甲", "戌")])

    class Fixed:
        analyzer_id = "fixed"
        name = "fixed"

        def __init__(self, verdict):
            self._v = verdict

        def analyze(self, facts):
            from tianze.domain.models import StrengthMethodResult
            return StrengthMethodResult(analyzer_id="fixed", name="fixed", verdict=self._v)

    report = run_strength([Fixed("极强"), Fixed("偏弱")], facts)
    assert report.agreement == "DISPUTED"
    report2 = run_strength([Fixed("极强"), Fixed("偏强")], facts)
    assert report2.agreement == "PARTIAL"


def test_provenance_and_real_chart():
    """fuyi 在真实排盘中可用；来源分级诚实标注。"""
    chart = build_chart(BirthInfo(date=dt.date(2003, 8, 18), time=dt.time(14, 30), gender="male"))
    fuyi = next(m for m in chart.strength.methods if m.name == "fuyi")
    assert fuyi.verdict in {"极强", "偏强", "中和", "偏弱", "极弱", "UNCERTAIN"}
    levels = {p.level for p in fuyi.provenance}
    assert RuleLevel.ENGINEERING_HEURISTIC in levels
    assert RuleLevel.PROJECT_REFERENCE in levels
    # 无伪造古籍出处
    assert not any(p.level == RuleLevel.CLASSICAL_EXPLICIT for p in fuyi.provenance)


def test_all_nine_rules_covered_by_cascade_table():
    """级联表完整：9 条规则、顺序固定、verdict 五级+UNCERTAIN。"""
    rules = FuyiStrengthAnalyzer.RULES
    assert [r[0] for r in rules] == [f"R21-{i}" for i in range(1, 10)]
    assert rules[-1][1] == "中和"  # 兜底规则
    assert all(v in {"极强", "偏强", "中和", "偏弱", "极弱", "UNCERTAIN"} for _, v, _ in rules)
