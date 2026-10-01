"""M3.1 通根引擎测试：10 干 × 12 支穷举不变式 + 金测盘。"""

from __future__ import annotations

import datetime as dt

from tianze.analysis.roots import collect_roots, day_master_roots
from tianze.domain.models import BirthInfo, Position, RootDepth
from tianze.ganzhi.tables import BRANCHES, HIDDEN_STEMS, STEMS
from tianze.pipeline import build_chart

POS4: list[Position] = ["year", "month", "day", "hour"]


def test_root_table_exhaustive_10x12():
    """对每个（天干, 地支）组合：有藏干同字 ⟺ 产出根，且类型/深度映射正确。"""
    for stem in STEMS:
        for branch in BRANCHES:
            expected_types = {role for s, role in HIDDEN_STEMS[branch] if s == stem}
            got = collect_roots([stem], [branch], ["year"], stem)
            got_types = {r.root_type.value for r in got}
            assert got_types == expected_types, f"{stem}在{branch}: {got_types} != {expected_types}"
            if got:
                r = got[0]
                assert r.hidden_stem == stem and r.branch == branch
                assert r.position == "year" and r.is_month_root is False
                expected_depth = {"本气": "strong", "中气": "medium", "余气": "weak"}[r.root_type.value]
                assert r.depth.value == expected_depth


def test_root_depth_mapping_is_qualitative_only():
    """R15：本气/中气/余气 → strong/medium/weak 是定性映射，无任何数值。"""
    for role, depth in (("本气", "strong"), ("中气", "medium"), ("余气", "weak")):
        for branch, hiddens in HIDDEN_STEMS.items():
            for s, r in hiddens:
                if r == role:
                    got = collect_roots([s], [branch], ["month"], s)
                    assert got[0].depth.value == depth


def test_all_ten_stems_have_at_least_one_root_branch():
    """十干皆有根支（传统事实完整性）。"""
    for stem in STEMS:
        branches_with_root = [b for b in BRANCHES if any(s == stem for s, _ in HIDDEN_STEMS[b])]
        assert branches_with_root, f"{stem} 无任何根支"
        got = collect_roots([stem], branches_with_root, ["year"] * len(branches_with_root), stem)
        assert len(got) == len(branches_with_root)


def test_known_root_tables_spot_checks():
    # 甲：寅本气、亥中气（辰未藏乙非甲）
    jia = {(r.branch, r.root_type.value) for r in collect_roots(["甲"], BRANCHES, ["year"] * 12, "甲")}
    assert {("寅", "本气"), ("亥", "中气")} <= jia
    assert ("辰", "中气") not in jia
    # 戊：辰戌本气、寅巳申余气
    wu = {(r.branch, r.root_type.value) for r in collect_roots(["戊"], BRANCHES, ["year"] * 12, "戊")}
    assert {("辰", "本气"), ("戌", "本气"), ("寅", "余气"), ("巳", "余气"), ("申", "余气")} <= wu
    # 癸：子本气、丑中气、辰余气
    gui = {(r.branch, r.root_type.value) for r in collect_roots(["癸"], BRANCHES, ["year"] * 12, "癸")}
    assert {("子", "本气"), ("丑", "中气"), ("辰", "余气")} == gui


def test_plan_example_2003_roots():
    """2003-08-18（癸未 庚申 癸亥 己未）：庚通根月支申（本气）、己通根两未（本气）、癸无根。"""
    chart = build_chart(BirthInfo(date=dt.date(2003, 8, 18), time=dt.time(14, 30), gender="male"))
    roots = chart.roots
    gui = [r for r in roots if r.stem == "癸"]
    assert gui == [], "癸在未申亥未中无根"
    geng = [r for r in roots if r.stem == "庚"]
    assert len(geng) == 1
    assert geng[0].branch == "申" and geng[0].root_type.value == "本气"
    assert geng[0].is_month_root is True and geng[0].depth == RootDepth.STRONG
    ji = [r for r in roots if r.stem == "己"]
    assert {r.position for r in ji} == {"year", "hour"}
    assert all(r.root_type.value == "本气" for r in ji)
    assert all(not r.is_day_master for r in roots)  # 日主癸无根


def test_female_1983_day_master_roots():
    """癸亥 甲寅 甲戌 甲戌：甲通根月支寅（本气/月令）+ 年支亥（中气）。"""
    chart = build_chart(BirthInfo(date=dt.date(1983, 2, 15), time=dt.time(20, 0), gender="female"))
    dm = day_master_roots(chart.roots)
    assert all(r.stem == "甲" and r.is_day_master for r in dm)
    by_pos = {r.position: r for r in dm}
    assert set(by_pos) == {"month", "year"}
    assert by_pos["month"].branch == "寅" and by_pos["month"].root_type.value == "本气"
    assert by_pos["month"].is_month_root is True
    assert by_pos["year"].branch == "亥" and by_pos["year"].root_type.value == "中气"
    assert "月令通根" in by_pos["month"].statement


def test_unknown_time_three_branch_roots():
    chart = build_chart(BirthInfo(date=dt.date(2003, 8, 18)))
    for r in chart.roots:
        assert r.position in ("year", "month", "day")
