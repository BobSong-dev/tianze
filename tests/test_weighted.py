"""M4.2 weighted 分析器测试：参数化、贡献明细可复现总分、防重复计分、参数敏感性。"""

from __future__ import annotations

import datetime as dt

from tianze.analysis.month_command import compute_month_command
from tianze.analysis.roots import collect_roots
from tianze.analysis.strength import StrengthFacts, default_run
from tianze.analysis.strength.methods.weighted import WeightedStrengthAnalyzer, WeightedStrengthParams
from tianze.domain.models import BirthInfo, Position, RuleLevel
from tianze.ganzhi.tables import STEM_ELEMENT
from tianze.pipeline import build_chart

POS4: list[Position] = ["year", "month", "day", "hour"]


def make_facts(pillars: list[tuple[str, str | None, str | None]], day_master: str = "甲"):
    """pillars: (position, stem, branch)。month_command 需要真实月支。"""
    stems = [p[1] for p in pillars]
    branches = [p[2] for p in pillars]
    month_branch = next(p[2] for p in pillars if p[0] == "month")
    mc = compute_month_command(month_branch, day_master, stems)
    roots = collect_roots(stems, branches, [p[0] for p in pillars], day_master)
    return StrengthFacts(
        day_master=day_master,
        day_master_element=STEM_ELEMENT[day_master],
        month_command=mc,
        day_master_roots=tuple(r for r in roots if r.is_day_master),
        other_stems=tuple((s, p[0]) for s, p in zip(stems, pillars) if s and p[0] != "day"),
        pillar_units=tuple(pillars),
    )


def test_pure_strong_extreme():
    """全帮扶盘：ratio=1.0 → 极强。"""
    facts = make_facts([("year", "壬", "子"), ("month", "甲", "亥"), ("day", "甲", "卯"), ("hour", "癸", "亥")])
    result = WeightedStrengthAnalyzer().analyze(facts)
    assert result.score == 1.0 and result.verdict == "极强"
    assert all(c.effect == "support" for c in result.contributions)


def test_pure_weak_extreme():
    """全克泄耗盘：ratio=0.0 → 极弱（甲日主见金火土）。"""
    facts = make_facts([("year", "庚", "酉"), ("month", "丙", "戌"), ("day", "甲", "酉"), ("hour", "辛", "戌")])
    result = WeightedStrengthAnalyzer().analyze(facts)
    assert result.score == 0.0 and result.verdict == "极弱"
    assert all(c.effect == "drain" for c in result.contributions)


def test_drain_heavy_extreme_weak():
    """克泄耗远重：ratio=3/9.25≈0.324 ≤ 0.35 → 极弱。"""
    facts = make_facts([("year", "甲", "子"), ("month", "庚", "午"), ("day", "甲", "子"), ("hour", "丙", "午")])
    result = WeightedStrengthAnalyzer().analyze(facts)
    # support = 年甲1.0 + 子癸1.0×2 = 3.0
    # drain = 月庚1.5 + 时丙1.0 + 午(丁1.5+己0.75) + 午(丁1.0+己0.5) = 6.25
    assert result.score == round(3.0 / 9.25, 4)
    assert result.verdict == "极弱"


def test_score_exactly_at_weak_threshold():
    """边界：month_multiplier=1、权重全 1 的对称盘 score=0.4 恰等于 weak_threshold → 偏弱。"""
    params = WeightedStrengthParams(
        visible_stem_weight=1.0, main_qi_weight=1.0, middle_qi_weight=1.0,
        residual_qi_weight=1.0, month_multiplier=1.0,
    )
    facts = make_facts([("year", "甲", "子"), ("month", "庚", "午"), ("day", "甲", "子"), ("hour", "乙", "戌")])
    result = WeightedStrengthAnalyzer(params).analyze(facts)
    # 日主(日干甲)不计；support = 年甲+时乙+子癸×2 = 4.0
    # drain = 月庚 + 午(丁+己) + 戌(戊+辛+丁) = 6.0 → 0.4
    assert result.score == 0.4
    assert result.verdict == "偏弱"
    # 阈值敏感性：weak 阈值下调到 0.39 → 同一盘变中和
    looser = WeightedStrengthAnalyzer(WeightedStrengthParams(
        visible_stem_weight=1.0, main_qi_weight=1.0, middle_qi_weight=1.0,
        residual_qi_weight=1.0, month_multiplier=1.0, weak_threshold=0.39,
    ))
    assert looser.analyze(facts).verdict == "中和"


def test_contributions_reproduce_score():
    """'为什么得出这个分数'：score 必须等于 contributions 按方向加和的比值。"""
    chart = build_chart(BirthInfo(date=dt.date(2003, 8, 18), time=dt.time(14, 30), gender="male"))
    weighted = next(m for m in chart.strength.methods if m.name == "weighted")
    s = sum(c.value for c in weighted.contributions if c.effect == "support")
    d = sum(c.value for c in weighted.contributions if c.effect == "drain")
    assert weighted.score == round(s / (s + d), 4)
    assert weighted.params["strongThreshold"] == 0.55
    assert any(p.level == RuleLevel.PROJECT_REFERENCE for p in weighted.provenance)
    assert any(p.level == RuleLevel.ENGINEERING_HEURISTIC for p in weighted.provenance)


def test_month_multiplier_effect():
    """月令影响：把同一个帮扶单位从年柱挪到月柱，score 必须上升（×1.5）。"""
    year_side = make_facts([("year", "癸", "酉"), ("month", "庚", "申"), ("day", "甲", "申"), ("hour", "庚", "申")])
    r_year = WeightedStrengthAnalyzer().analyze(year_side).score
    month_side = make_facts([("year", "庚", "申"), ("month", "癸", "申"), ("day", "甲", "申"), ("hour", "庚", "申")])
    r_month = WeightedStrengthAnalyzer().analyze(month_side).score
    assert r_year is not None and r_month is not None and r_month > r_year


def test_no_double_counting_roots():
    """ADR-022：同一命局，伪造不同的'根'输入不得改变 weighted 结果——
    根事实已含在藏干单位里，禁止二次计分。"""
    pillars = [("year", "癸", "亥"), ("month", "甲", "寅"), ("day", "甲", "戌"), ("hour", "甲", "戌")]
    facts_a = make_facts(pillars)  # 真实根（寅亥）
    facts_b = StrengthFacts(  # 伪造：根列表清空/夸大都应不影响 weighted
        day_master=facts_a.day_master,
        day_master_element=facts_a.day_master_element,
        month_command=facts_a.month_command,
        day_master_roots=(),
        other_stems=facts_a.other_stems,
        pillar_units=facts_a.pillar_units,
    )
    ra = WeightedStrengthAnalyzer().analyze(facts_a)
    rb = WeightedStrengthAnalyzer().analyze(facts_b)
    assert ra.score == rb.score and ra.contributions == rb.contributions


def test_parameter_sensitivity_thresholds():
    """参数敏感性：同一命局（1983 盘 ratio≈0.5843），阈值变化 → verdict 按预期移动。"""
    facts = make_facts([("year", "癸", "亥"), ("month", "甲", "寅"), ("day", "甲", "戌"), ("hour", "甲", "戌")])
    baseline = WeightedStrengthAnalyzer().analyze(facts)
    assert baseline.score == 0.5843 and baseline.verdict == "偏强"  # 手算 6.5/11.125
    strict = WeightedStrengthAnalyzer(WeightedStrengthParams(strong_threshold=0.70, extreme_strong_threshold=0.80))
    r_strict = strict.analyze(facts)
    assert r_strict.verdict == "中和"
    assert r_strict.params["strongThreshold"] == 0.70  # 参数随结果输出
    loose = WeightedStrengthAnalyzer(WeightedStrengthParams(strong_threshold=0.50, extreme_strong_threshold=0.55))
    assert loose.analyze(facts).verdict == "极强"


def test_invalid_params_rejected():
    import pytest
    with pytest.raises(ValueError):
        WeightedStrengthParams(strong_threshold=0.45, weak_threshold=0.55)
    with pytest.raises(ValueError):
        WeightedStrengthParams(extreme_weak_threshold=0.5, weak_threshold=0.45, strong_threshold=0.55)


def test_weighted_in_default_run():
    """默认注册表含 weighted；2003 盘 score 手算复核。"""
    chart = build_chart(BirthInfo(date=dt.date(2003, 8, 18), time=dt.time(14, 30), gender="male"))
    weighted = next(m for m in chart.strength.methods if m.name == "weighted")
    # 手算：support = 年癸1.0 + 月庚1.5 + 申(庚1.5+壬0.75) + 亥(壬1.0) = 5.75
    #        drain  = 时己1.0 + 未(己1.0+丁0.5+乙0.25)×2 + 申戊0.375 + 亥甲0.5 = 5.375
    assert weighted.score == round(5.75 / 11.125, 4)
    assert weighted.verdict == "中和"  # 0.5169 ∈ (0.45, 0.55)
