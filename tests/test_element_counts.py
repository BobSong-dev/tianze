"""M3.4 五行基础统计测试（R16：两独立视图，不加权）。"""

from __future__ import annotations

import datetime as dt

from tianze.analysis.element_counts import count_elements
from tianze.domain.models import BirthInfo
from tianze.pipeline import build_chart


def test_synthetic_counts_two_views():
    counts = count_elements(["庚", "辛", "戊", "丙"], ["子", "申", "酉", "戌"])
    # visible = 4 干 + 4 支主气
    assert counts.elements["metal"].visible == 4  # 庚辛 + 申酉
    assert counts.elements["water"].visible == 1  # 子
    assert counts.elements["earth"].visible == 2  # 戊 + 戌
    assert counts.elements["fire"].visible == 1   # 丙
    assert counts.elements["wood"].visible == 0
    # hidden = 全部藏干：子癸 / 申庚壬戊 / 酉辛 / 戌戊辛丁
    assert counts.hidden_stems == {"wood": 0, "fire": 1, "earth": 2, "metal": 3, "water": 2}
    assert counts.elements["wood"].visible == 0 and counts.elements["wood"].hidden == 0
    assert counts.missing == ["wood"]
    # 明细视图
    assert counts.stems == {"wood": 0, "fire": 1, "earth": 1, "metal": 2, "water": 0}
    assert counts.branches == {"wood": 0, "fire": 0, "earth": 1, "metal": 2, "water": 1}


def test_sum_invariants():
    stems = ["癸", "庚", "癸", "己"]
    branches = ["未", "申", "亥", "未"]
    counts = count_elements(stems, branches)
    assert sum(counts.stems.values()) == 4
    assert sum(counts.branches.values()) == 4
    assert sum(counts.hidden_stems.values()) == 11  # 未(3)+申(3)+亥(2)+未(3)
    for key, view in counts.elements.items():
        assert view.visible == counts.stems[key] + counts.branches[key]


def test_plan_example_2003_counts():
    """癸未 庚申 癸亥 己未：手工核算。"""
    counts = count_elements(["癸", "庚", "癸", "己"], ["未", "申", "亥", "未"])
    assert counts.stems == {"wood": 0, "fire": 0, "earth": 1, "metal": 1, "water": 2}
    assert counts.branches == {"wood": 0, "fire": 0, "earth": 2, "metal": 1, "water": 1}
    assert counts.hidden_stems == {"wood": 3, "fire": 2, "earth": 3, "metal": 1, "water": 2}
    assert (counts.elements["wood"].visible, counts.elements["wood"].hidden) == (0, 3)
    assert (counts.elements["fire"].visible, counts.elements["fire"].hidden) == (0, 2)
    assert (counts.elements["earth"].visible, counts.elements["earth"].hidden) == (3, 3)
    assert (counts.elements["metal"].visible, counts.elements["metal"].hidden) == (2, 1)
    assert (counts.elements["water"].visible, counts.elements["water"].hidden) == (3, 2)
    assert counts.missing == []  # 木火虽显性为 0，但藏干中有 → 非缺


def test_missing_requires_both_views_zero():
    counts = count_elements(["丙", "丁", "丙", "丁"], ["酉", "酉", "丑", "丑"])
    # hidden: 酉辛×2 + 丑己癸辛×2 → 金3、土2、水2；无木火
    assert counts.missing == ["wood"]
    assert (counts.elements["metal"].visible, counts.elements["metal"].hidden) == (2, 4)


def test_unknown_time_three_pillars():
    counts = count_elements(["癸", "庚", "癸"], ["未", "申", "亥"])
    assert sum(counts.stems.values()) == 3
    assert sum(counts.branches.values()) == 3


def test_counts_in_chart_json():
    chart = build_chart(BirthInfo(date=dt.date(2003, 8, 18), time=dt.time(14, 30), gender="male"))
    data = chart.to_json_dict()
    ec = data["elementCounts"]
    assert ec["elements"]["water"]["visible"] == 3
    assert ec["elements"]["wood"] == {"visible": 0, "hidden": 3}
    assert ec["missing"] == []
    assert set(data["roots"][0].keys()) >= {"stem", "branch", "rootType", "depth", "position", "isMonthRoot"}
    assert data["monthCommand"]["relationToDayMaster"]["state"] == "相"
    assert data["monthCommand"]["hiddenStemPriority"][0] == {"stem": "庚", "role": "本气", "transparent": True}
