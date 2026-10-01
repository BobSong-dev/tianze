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
    癸正印+甲比肩×2 → 印比透干 3 处得势。M4.2 后三方法并列。"""
    chart = build_chart(BirthInfo(date=dt.date(1983, 2, 15), time=dt.time(20, 0), gender="female"))
    report = chart.strength
    assert report is not None and len(report.methods) == 3
    names = [m.name for m in report.methods]
    assert names == ["dimension", "weighted", "fuyi"]
    dim = report.methods[0]
    assert dim.verdict is None, "M4.1 定性三维不输出强弱 verdict"
    ev = dim.strength_evidence
    assert ev.de_ling.result is True
    assert any("得令" in r for r in ev.de_ling.reason)
    assert ev.de_di.result is True
    assert any("寅" in r for r in ev.de_di.reason) and any("亥" in r for r in ev.de_di.reason)
    assert ev.de_shi.result is True
    assert any("3 处" in r for r in ev.de_shi.reason)
    assert dim.note and "不评分" in dim.note
    # weighted：逐字加权 ratio（手算 6.5/11 ≈ 0.5909 → 偏强）
    weighted = report.methods[1]
    assert weighted.name == "weighted" and weighted.score is not None
    assert weighted.verdict == "偏强"
    assert weighted.params["monthMultiplier"] == 1.5
    assert len(weighted.contributions) == 14  # 3 干(除日主) + 11 藏干
    # fuyi：R21-1 命中 → 极强
    fuyi = report.methods[2]
    assert fuyi.verdict == "极强" and fuyi.confidence == "high"
    assert fuyi.support_evidence and fuyi.drain_evidence is not None
    # agreement：偏强与极强相邻 → PARTIAL（R22）；dimension 无 verdict 不参与
    assert report.agreement == "PARTIAL"
    assert "R22" in report.note or "R19" in report.note


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
    """JSON 形状与任务书一致：三方法并列，agreement=PARTIAL（R22）。"""
    chart = build_chart(BirthInfo(date=dt.date(1983, 2, 15), time=dt.time(20, 0), gender="female"))
    data = chart.to_json_dict()
    s = data["strength"]
    assert [m["name"] for m in s["methods"]] == ["dimension", "weighted", "fuyi"]
    se = s["methods"][0]["strengthEvidence"]
    assert se["deLing"]["result"] is True and isinstance(se["deLing"]["reason"], list)
    assert se["deDi"]["result"] is True
    assert se["deShi"]["result"] is True
    assert s["agreement"] == "PARTIAL"
    weighted = s["methods"][1]
    assert weighted["analyzerId"] == "weighted-v1" and "score" in weighted and "params" in weighted
    assert weighted["contributions"] and "provenance" in weighted
    assert data["conventions"]["strengthFramework"] == "R19"


def test_dimensional_analyzer_protocol_conformance():
    a = DimensionalStrengthAnalyzer()
    assert a.analyzer_id and a.name
    assert callable(a.analyze)
