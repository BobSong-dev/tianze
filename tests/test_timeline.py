"""M12 扩展：Timeline / TenGodThemeDelta / 流月流日干支。"""

from __future__ import annotations

from tianze.analysis.temporal_extended import (
    TimelineNode, TenGodThemeDelta, TimelineResult,
    build_timeline, month_pillar_for_year, day_pillar_for_jdn, gregorian_to_jdn,
)


def test_month_pillar_wuhu():
    """五虎遁：甲年寅月=丙寅。"""
    assert month_pillar_for_year(0, 1) == ("丙", "寅")  # 甲年
    assert month_pillar_for_year(5, 1) == ("丙", "寅")  # 己年(己=stem_index 5)
    assert month_pillar_for_year(1, 1) == ("戊", "寅")  # 乙年


def test_day_pillar_jdn():
    """日柱 JDN 公式：1949-10-01=甲子。"""
    jdn = gregorian_to_jdn(1949, 10, 1)
    assert day_pillar_for_jdn(jdn) == ("甲", "子")


def test_day_pillar_2000():
    """2000-01-01=戊午。"""
    jdn = gregorian_to_jdn(2000, 1, 1)
    assert day_pillar_for_jdn(jdn) == ("戊", "午")


def test_timeline_basic():
    da_yun = [
        {"ganZhi": "庚申", "startYear": 2006, "endYear": 2016},
        {"ganZhi": "己未", "startYear": 2016, "endYear": 2026},
    ]
    tl = build_timeline(
        natal_stems=["癸", "庚", "癸", "己"],
        natal_branches=["未", "申", "亥", "未"],
        day_master="癸", birth_year=2003, da_yun=da_yun,
        target_years=[2020, 2021, 2022, 2023, 2024, 2025],
    )
    assert tl.totalNodes == 8  # 2 luck + 6 annual
    # 检查大运节点
    luck_nodes = [n for n in tl.nodes if n.level == "luck"]
    assert len(luck_nodes) == 2
    # 检查流年节点
    annual_nodes = [n for n in tl.nodes if n.level == "annual"]
    assert len(annual_nodes) == 6
    # structuralChangeScore 非负
    for n in tl.nodes:
        assert n.structuralChangeScore >= 0


def test_timeline_ten_god_deltas():
    da_yun = [{"ganZhi": "庚申", "startYear": 2006, "endYear": 2016}]
    tl = build_timeline(
        natal_stems=["癸", "庚", "癸", "己"],
        natal_branches=["未", "申", "亥", "未"],
        day_master="癸", birth_year=2003, da_yun=da_yun,
        target_years=[2010],
    )
    assert len(tl.tenGodDeltas) > 0
    for d in tl.tenGodDeltas:
        assert d.direction in ("increased", "decreased", "unchanged", "new", "removed")


def test_timeline_relations_have_source():
    """所有 temporal 节点的 relations 都带来源标记。"""
    da_yun = [{"ganZhi": "丙寅", "startYear": 2006, "endYear": 2016}]
    tl = build_timeline(
        natal_stems=["癸", "庚", "癸", "己"],
        natal_branches=["未", "申", "亥", "未"],
        day_master="癸", birth_year=2003, da_yun=da_yun,
        target_years=[2010],
    )
    for n in tl.nodes:
        for rel in n.relations:
            assert "sources" in rel


def test_timeline_evidence_present():
    da_yun = [{"ganZhi": "丙寅", "startYear": 2006, "endYear": 2016}]
    tl = build_timeline(
        natal_stems=["癸", "庚", "癸", "己"],
        natal_branches=["未", "申", "亥", "未"],
        day_master="癸", birth_year=2003, da_yun=da_yun,
        target_years=[2010],
    )
    luck_node = next(n for n in tl.nodes if n.level == "luck")
    assert len(luck_node.evidence) > 0


def test_timeline_no_fortune_output():
    da_yun = [{"ganZhi": "丙寅", "startYear": 2006, "endYear": 2016}]
    tl = build_timeline(
        natal_stems=["癸", "庚", "癸", "己"],
        natal_branches=["未", "申", "亥", "未"],
        day_master="癸", birth_year=2003, da_yun=da_yun,
        target_years=[2010],
    )
    blob = tl.model_dump_json()
    for banned in ("发财", "大凶", "必有灾", "升职", "结婚", "离婚"):
        assert banned not in blob
