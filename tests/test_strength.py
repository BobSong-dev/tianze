"""M4 旺衰框架测试：多算法架构 + dimension 定性三维（不评分）。"""

from __future__ import annotations

import datetime as dt

from tianze.analysis.strength import StrengthFacts, default_run, run_strength
from tianze.analysis.strength.methods.dimensional import DimensionalStrengthAnalyzer, DE_SHI_THRESHOLD
from tianze.domain.models import BirthInfo
from tianze.ganzhi.tables import STEM_ELEMENT
from tianze.pipeline import build_chart


def test_female_1983_all_three_true():
    """癸亥 甲寅 甲戌 甲戌：甲木寅月得令；通根寅(本气)+亥(中气)得地；
    癸正印+甲比肩×2 → 印比透干 3 处得势。"""
    chart = build_chart(BirthInfo(date=dt.date(1983, 2, 15), time=dt.time(20, 0), gender="female"))
    report = chart.strength
    assert report is not None and len(report.methods) == 1
    m = report.methods[0]
    assert m.analyzer_id == "dimensional_v1" and m.name == "dimension"
    assert m.verdict is None, "M4.1 定性三维不输出强弱 verdict"
    ev = m.strength_evidence
    assert ev.de_ling.result is True
    assert any("得令" in r for r in ev.de_ling.reason)
    assert ev.de_di.result is True
    assert any("寅" in r for r in ev.de_di.reason) and any("亥" in r for r in ev.de_di.reason)
    assert ev.de_shi.result is True
    assert any("3 处" in r for r in ev.de_shi.reason)
    assert m.note and "不评分" in m.note
    assert report.agreement is None
    assert "不输出 agreement" in report.note


def test_plan_2003_de_shi_counts_peer_bijian():
    """癸日主（癸未 庚申 癸亥 己未）：申月相→不得令；四支无癸根→不得地；
    年干癸是**比肩**（别柱同干必须计入）+ 月干庚正印 = 印比 2 处 → 得势（R17 阈值恰达）。"""
    chart = build_chart(BirthInfo(date=dt.date(2003, 8, 18), time=dt.time(14, 30), gender="male"))
    ev = chart.strength.methods[0].strength_evidence
    assert ev.de_ling.result is False
    assert any("相" in r for r in ev.de_ling.reason) and any("不得令" in r for r in ev.de_ling.reason)
    assert ev.de_di.result is False
    assert any("无任何同字之根" in r for r in ev.de_di.reason)
    assert ev.de_shi.result is True
    assert any("比肩" in r for r in ev.de_shi.reason) and any("正印" in r for r in ev.de_shi.reason)
    assert any("2 处" in r for r in ev.de_shi.reason)


def test_de_shi_threshold_boundary_synthetic():
    """阈值边界：印比恰 2 处 → 得势；1 处 → 不得势（构造 facts 直接测）。"""
    def make(other_stems):
        from tianze.analysis.month_command import compute_month_command
        mc = compute_month_command("申", "甲", ["甲"])
        return StrengthFacts(
            day_master="甲",
            day_master_element=STEM_ELEMENT["甲"],
            month_command=mc,
            day_master_roots=(),
            other_stems=tuple(other_stems),
        )

    two = default_run(make((("甲", "year"), ("乙", "month"))))
    ev2 = two.methods[0].strength_evidence
    assert ev2.de_shi.result is True  # 比肩+劫财 = 2

    one = default_run(make((("癸", "year"), ("庚", "month"), ("丙", "hour"))))
    ev1 = one.methods[0].strength_evidence
    assert ev1.de_shi.result is False  # 仅癸正印 1 处（庚七杀/丙食神不帮身）

    zero = default_run(make((("庚", "year"), ("丙", "month"))))
    assert zero.methods[0].strength_evidence.de_shi.result is False

    assert DE_SHI_THRESHOLD == 2  # 阈值显式常量，公开可查


def test_multi_method_agreement_semantics():
    """≥2 个带 verdict 的方法 → agreement；分歧 → DISPUTED；Tianze 不裁决。"""
    from tianze.analysis.month_command import compute_month_command
    f = StrengthFacts(
        day_master="甲",
        day_master_element=STEM_ELEMENT["甲"],
        month_command=compute_month_command("寅", "甲", ["甲"]),
        day_master_roots=(),
        other_stems=(("甲", "year"),),
    )

    class FakeA:
        analyzer_id = "fake_a"
        name = "fake_a"

        def analyze(self, facts):
            from tianze.domain.models import StrengthMethodResult
            return StrengthMethodResult(analyzer_id="fake_a", name="fake_a", verdict="偏强")

    class FakeB:
        analyzer_id = "fake_b"
        name = "fake_b"

        def analyze(self, facts):
            from tianze.domain.models import StrengthMethodResult
            return StrengthMethodResult(analyzer_id="fake_b", name="fake_b", verdict="偏弱")

    same = run_strength([FakeA(), FakeA()], f)
    assert same.agreement == "HIGH"
    disputed = run_strength([FakeA(), FakeB()], f)
    assert disputed.agreement == "DISPUTED"
    assert "不裁判" in disputed.note


def test_strength_json_shape():
    """JSON 形状与任务书一致：strength.methods[].strengthEvidence.deLing{result,reason}。"""
    chart = build_chart(BirthInfo(date=dt.date(1983, 2, 15), time=dt.time(20, 0), gender="female"))
    data = chart.to_json_dict()
    s = data["strength"]
    assert s["methods"][0]["name"] == "dimension"
    se = s["methods"][0]["strengthEvidence"]
    assert se["deLing"]["result"] is True and isinstance(se["deLing"]["reason"], list)
    assert se["deDi"]["result"] is True
    assert se["deShi"]["result"] is True
    assert "agreement" not in s  # 单方法时 agreement=None 被 exclude_none 剔除（既有契约）
    assert "不输出 agreement" in s["note"]
    assert data["conventions"]["strengthFramework"] == "R19"


def test_dimensional_analyzer_protocol_conformance():
    a = DimensionalStrengthAnalyzer()
    assert a.analyzer_id and a.name
    assert callable(a.analyze)
