"""M12/M13：Timeline 树 / TenGodThemeDelta / 流月流日干支 / 聚焦分析。"""

from __future__ import annotations

from tianze.analysis.temporal_extended import (
    TimelineNode, TenGodThemeDelta, TimelineResult,
    build_timeline, month_pillar_for_year, day_pillar_for_jdn, gregorian_to_jdn,
    month_windows_for_year, build_focused_temporal,
)


def _flatten(nodes: list[TimelineNode]) -> list[TimelineNode]:
    out: list[TimelineNode] = []
    for n in nodes:
        out.append(n)
        out.extend(_flatten(n.children))
    return out


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


def test_month_windows_for_year():
    """流年 2026（丙午）：寅月=庚寅（五虎遁），窗口从立春到次年立春前。"""
    mws = month_windows_for_year(2026)
    assert len(mws) == 12
    assert mws[0]["stem"] == "庚" and mws[0]["branch"] == "寅"   # 丙年正月庚寅
    assert mws[0]["jieName"] == "立春"
    assert mws[11]["branch"] == "丑"
    # 相邻窗口衔接：上一窗 end == 下一窗 start
    for a, b in zip(mws, mws[1:]):
        assert a["end"] == b["start"]


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
    assert tl.totalNodes == 8  # 2 luck + 6 annual（树形计数）
    luck_nodes = [n for n in tl.nodes if n.level == "luck"]
    assert len(luck_nodes) == 2
    annual_nodes = [n for n in _flatten(tl.nodes) if n.level == "annual"]
    assert len(annual_nodes) == 6
    for n in _flatten(tl.nodes):
        assert n.structuralChangeScore >= 0
    # 树形：流年挂在大运 children 下（两运合计 6 个流年）
    assert sum(len(n.children) for n in luck_nodes) == 6


def test_timeline_focus_year_months():
    """focus_year 展开该流年的 12 个流月节点。"""
    da_yun = [{"ganZhi": "己未", "startYear": 2016, "endYear": 2026}]
    tl = build_timeline(
        natal_stems=["癸", "庚", "癸", "己"],
        natal_branches=["未", "申", "亥", "未"],
        day_master="癸", birth_year=2003, da_yun=da_yun,
        target_years=[2020], focus_year=2020,
    )
    flat = _flatten(tl.nodes)
    month_nodes = [n for n in flat if n.level == "monthly"]
    assert len(month_nodes) == 12
    assert month_nodes[0].month == 1
    assert month_nodes[0].monthWindow and "立春" in month_nodes[0].monthWindow


def test_timeline_focus_month_days():
    """focus_month 展开流日节点；日柱与 JDN 公式一致。"""
    da_yun = [{"ganZhi": "己未", "startYear": 2016, "endYear": 2026}]
    tl = build_timeline(
        natal_stems=["癸", "庚", "癸", "己"],
        natal_branches=["未", "申", "亥", "未"],
        day_master="癸", birth_year=2003, da_yun=da_yun,
        target_years=[2020], focus_year=2020, focus_month=1,
    )
    flat = _flatten(tl.nodes)
    day_nodes = [n for n in flat if n.level == "daily"]
    # 寅月约 29~31 天
    assert 28 <= len(day_nodes) <= 32
    for dn in day_nodes[:3]:
        jdn = gregorian_to_jdn(dn.year, dn.month, dn.day)
        assert dn.ganzhi == "".join(day_pillar_for_jdn(jdn))


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


def test_ten_god_excludes_day_master():
    """十神主题计数：日主本人不计入（分类主体不是主题单元）。"""
    from tianze.analysis.temporal_extended import _count_ten_gods
    counts = _count_ten_gods(["癸", "庚", "癸", "己"], "癸")
    # 两个癸（日主+年干）：日主不计；年干癸=比肩 计 1
    assert counts.get("比肩", 0) == 1
    assert sum(counts.values()) == 3  # 庚(正印) 癸(比肩) 己(七杀)


def test_timeline_relations_have_source():
    """所有 temporal 节点的 relations 都带来源标记。"""
    da_yun = [{"ganZhi": "丙寅", "startYear": 2006, "endYear": 2016}]
    tl = build_timeline(
        natal_stems=["癸", "庚", "癸", "己"],
        natal_branches=["未", "申", "亥", "未"],
        day_master="癸", birth_year=2003, da_yun=da_yun,
        target_years=[2010],
    )
    for n in _flatten(tl.nodes):
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
        target_years=[2010], focus_year=2010, focus_month=1,
    )
    blob = tl.model_dump_json()
    for banned in ("发财", "大凶", "必有灾", "升职", "结婚", "离婚"):
        assert banned not in blob


def test_focused_temporal_month_daily():
    """聚焦分析：流月/流日干支进入 TemporalContext。"""
    import datetime
    from tianze.domain.models import BirthInfo, Gender
    from tianze.pipeline import build_chart
    bi = BirthInfo(date=datetime.date(1984, 2, 5), time=datetime.time(10, 30), gender=Gender.MALE)
    chart = build_chart(bi)
    ta, mw_info = build_focused_temporal(
        chart, luck_index=1, year=2026, month_number=1,
        day=(2026, 3, 1),
    )
    ctx = ta.context
    assert ctx.annual_stem == "丙" and ctx.annual_branch == "午"   # 2026
    assert ctx.monthly_stem == "庚" and ctx.monthly_branch == "寅"  # 丙年寅月
    # 流日 2026-03-01 由 JDN 公式决定
    jdn = gregorian_to_jdn(2026, 3, 1)
    assert (ctx.daily_stem, ctx.daily_branch) == day_pillar_for_jdn(jdn)
    assert mw_info and mw_info["stem"] == "庚"
