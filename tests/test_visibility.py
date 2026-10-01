"""M3.2 透干引擎测试：四个天干位置全覆盖 + 月令/日主相关性 + 距离。"""

from __future__ import annotations

import datetime as dt

from tianze.analysis.visibility import analyze_visibility
from tianze.domain.models import BirthInfo
from tianze.ganzhi.tables import HIDDEN_STEMS
from tianze.pipeline import build_chart

POS4 = ["year", "month", "day", "hour"]


def test_year_stem_transparency():
    """藏干透出于年干：己未月藏己，年干己 → month_related=True。"""
    rs = analyze_visibility(["己", "甲", "丙", "庚"], ["卯", "未", "子", "酉"], POS4, "丙")
    hits = [r for r in rs if r.visible_stem == "己" and r.source_branch == "未"]
    assert len(hits) == 1
    r = hits[0]
    assert r.position == "year" and r.source_position == "month"
    assert r.source_role.value == "本气"
    assert r.month_related is True and r.day_master_related is False
    assert r.distance == 1
    assert "月令透干" in r.statement


def test_month_stem_transparency():
    """透出于月干：卯藏乙，月干乙。"""
    rs = analyze_visibility(["己", "乙", "丙", "庚"], ["未", "卯", "子", "酉"], POS4, "丙")
    hits = [r for r in rs if r.visible_stem == "乙"]
    assert len(hits) == 2  # 卯（本气）与未（余气）各一条
    by_source = {r.source_branch: r for r in hits}
    assert by_source["卯"].source_role.value == "本气" and by_source["卯"].month_related is True
    assert by_source["未"].source_role.value == "余气" and by_source["未"].month_related is False
    assert all(r.position == "month" for r in hits)
    assert {r.distance for r in hits} == {0, 1}  # 卯在月支位距0，未在年支位距1


def test_day_stem_transparency_and_day_master_flag():
    """透出于日干且藏干即日主：戌藏丁，日干丁。"""
    rs = analyze_visibility(["己", "乙", "丁", "庚"], ["未", "卯", "戌", "酉"], POS4, "丁")
    hits = [r for r in rs if r.visible_stem == "丁" and r.source_branch == "戌"]
    assert len(hits) == 1
    r = hits[0]
    assert r.position == "day" and r.day_master_related is True
    assert r.source_role.value == "余气"
    assert "藏干即日主" in r.statement


def test_hour_stem_transparency_and_distance():
    """透出于时干，距来源支 2 位（月支→时支）。"""
    rs = analyze_visibility(["己", "甲", "丙", "戊"], ["未", "寅", "子", "酉"], POS4, "丙")
    hits = [r for r in rs if r.visible_stem == "戊" and r.source_branch == "寅"]
    assert len(hits) == 1
    r = hits[0]
    assert r.position == "hour" and r.source_position == "month"
    assert r.distance == 2 and r.month_related is True


def test_exhaustive_consistency_with_hidden_table():
    """穷举一致性：任意组合下，产出的透干记录集合 == 表格推导集合。"""
    stems = ["甲", "己", "丁", "庚"]
    branches = ["寅", "丑", "戌", "亥"]
    got = {(r.source_branch, r.hidden_stem, r.position) for r in
           analyze_visibility(stems, branches, POS4, "丁")}
    expected = set()
    for bi, b in enumerate(branches):
        for hidden, _role in HIDDEN_STEMS[b]:
            for si, s in enumerate(stems):
                if s == hidden:
                    expected.add((b, hidden, POS4[si]))
    assert got == expected


def test_no_transparency_returns_empty():
    """全无透出（藏干字都不在天干）。"""
    rs = analyze_visibility(["庚", "辛", "壬", "癸"], ["子", "申", "酉", "亥"], POS4, "壬")
    # 子癸、申庚壬戊、酉辛、亥壬甲：壬（申/亥藏）透出在时干壬 → 不为空；改用完全无透组合
    rs2 = analyze_visibility(["丙", "丁", "丙", "丁"], ["酉", "酉", "丑", "丑"], POS4, "丁")
    assert rs2 == [], "丙丁不在酉丑藏干中，应无透出"


def test_female_1983_visibility_counts():
    """癸亥 甲寅 甲戌 甲戌：亥→甲×3、寅→甲×3，共 6 条；月令透干 3 条；全部 day_master_related。"""
    chart = build_chart(BirthInfo(date=dt.date(1983, 2, 15), time=dt.time(20, 0), gender="female"))
    vs = chart.visibility
    assert len(vs) == 6
    assert all(v.day_master_related for v in vs)  # 藏干甲即日主
    month_hits = [v for v in vs if v.month_related]
    assert len(month_hits) == 3
    assert {v.position for v in month_hits} == {"month", "day", "hour"}
    assert {v.distance for v in vs} == {0, 1, 2, 3}
