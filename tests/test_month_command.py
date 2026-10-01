"""M3.3 月令测试：12 月支 × 10 日主全组合（120）+ 金标 + 证据链。"""

from __future__ import annotations

import datetime as dt

from tianze.analysis.month_command import (
    SEASON_BY_BRANCH,
    compute_month_command,
    season_state_for,
)
from tianze.ganzhi.tables import BRANCHES, BRANCH_ELEMENT, HIDDEN_STEMS, Element, STEMS, STEM_ELEMENT
from tianze.domain.models import BirthInfo
from tianze.pipeline import build_chart
# 独立复刻的生克环（不 import 引擎逻辑，作为交叉真值）
_GEN = {"WOOD": "FIRE", "FIRE": "EARTH", "EARTH": "METAL", "METAL": "WATER", "WATER": "WOOD"}
_CTL = {"WOOD": "EARTH", "EARTH": "WATER", "WATER": "FIRE", "FIRE": "METAL", "METAL": "WOOD"}
_STORES = {"辰", "戌", "丑", "未"}


def expected_state(day_stem: str, month_branch: str) -> str:
    """独立推导期望旺相休囚死：当令旺 / 月令我生相 / 我生月令休 / 我克月令囚 / 月令克我死；土旺四季特判。"""
    d = STEM_ELEMENT[day_stem].value
    if d == "EARTH" and month_branch in _STORES:
        return "旺"
    m = BRANCH_ELEMENT[month_branch].value
    if d == m:
        return "旺"
    if _GEN[m] == d:
        return "相"
    if _GEN[d] == m:
        return "休"
    if _CTL[d] == m:
        return "囚"
    return "死"


def test_all_120_daymaster_month_combinations():
    """12 月支 × 10 日主 = 120 组：状态与独立推导一致，得令标记 = 状态为旺。"""
    checked = 0
    for branch in BRANCHES:
        for day in STEMS:
            mc = compute_month_command(branch, day, [day])
            assert mc.relation_to_day_master.state.value == expected_state(day, branch), (
                f"{day}日主 {branch}月: {mc.relation_to_day_master.state.value} "
                f"!= {expected_state(day, branch)}"
            )
            assert mc.relation_to_day_master.in_command == (mc.relation_to_day_master.state.value == "旺")
            assert mc.season == SEASON_BY_BRANCH[branch]
            assert mc.element == BRANCH_ELEMENT[branch]
            assert len(mc.hidden_stem_priority) == len(HIDDEN_STEMS[branch])
            checked += 1
    assert checked == 120


def test_golden_states():
    cases = [
        ("甲", "寅", "旺", True),    # 木日主寅月：得令
        ("癸", "申", "相", False),   # 金生水：相，不得令
        ("甲", "亥", "相", False),   # 水生木
        ("甲", "子", "相", False),
        ("壬", "申", "相", False),   # 金生水
        ("甲", "未", "囚", False),   # 木克土：囚
        ("甲", "酉", "死", False),   # 金克木：死
        ("丙", "寅", "相", False),   # 木生火
        ("壬", "丑", "死", False),   # 土克水：丑月本气土，克水
        ("丙", "戌", "休", False),   # 火生土：休（戌月土，火生土）
        ("丁", "午", "旺", True),    # 火日主午月：得令
        ("壬", "子", "旺", True),    # 水日主子月：得令
        ("戊", "辰", "旺", True),    # 土旺四季特判（虽春季土死，四库月按旺）
        ("己", "戌", "旺", True),
        ("戊", "寅", "死", False),   # 春土非库月 → 死
    ]
    for day, branch, state, in_command in cases:
        mc = compute_month_command(branch, day, [day])
        assert mc.relation_to_day_master.state.value == state, f"{day}/{branch}: 期望{state}"
        assert mc.relation_to_day_master.in_command is in_command


def test_earth_store_override_flagged_in_evidence():
    mc = compute_month_command("辰", "戊", ["戊"])
    assert any("土旺四季" in e for e in mc.evidence)
    assert "土旺四季" in mc.relation_to_day_master.rule


def test_hidden_stem_priority_order_and_transparency():
    """寅藏甲丙戊，本气→中气→余气；天干见甲则甲 transparent。"""
    mc = compute_month_command("寅", "甲", ["甲", "丙", "戊", "甲"])
    assert [(i.stem, i.role.value) for i in mc.hidden_stem_priority] == [
        ("甲", "本气"), ("丙", "中气"), ("戊", "余气"),
    ]
    assert [i.transparent for i in mc.hidden_stem_priority] == [True, True, True]
    mc2 = compute_month_command("寅", "甲", ["庚", "辛", "甲", "癸"])
    assert [i.transparent for i in mc2.hidden_stem_priority] == [True, False, False]


def test_evidence_chain():
    """任务书示例：甲木日主寅月 → 证据含"得令"。"""
    mc = compute_month_command("寅", "甲", ["甲"])
    joined = "\n".join(mc.evidence)
    assert "日主甲（木）生于寅月" in joined
    assert "寅月属春季（寅卯辰）" in joined
    assert "得令（旺）" in joined
    assert "甲（本气" in joined
    assert len(mc.evidence) >= 4


def test_season_state_for_direct():
    state, rule = season_state_for(Element.EARTH, "丑")
    assert state.value == "旺" and "同气" in rule and "土旺四季" in rule
    state2, rule2 = season_state_for(Element.WOOD, "酉")
    assert state2.value == "死" and "克" in rule2
    state3, rule3 = season_state_for(Element.WATER, "丑")
    assert state3.value == "死" and "死" in rule3  # 丑月本气土克水（非季节表的水旺）


def test_month_command_in_real_chart():
    """2003-08-18：癸日主申月 → 相；藏干庚壬戊，庚透出（月干）。"""
    chart = build_chart(BirthInfo(date=dt.date(2003, 8, 18), time=dt.time(14, 30), gender="male"))
    mc = chart.month_command
    assert mc is not None
    assert mc.month_branch == "申" and mc.season.value == "autumn"
    assert mc.element.value == "METAL" and mc.yin_yang.value == "YANG"
    assert mc.relation_to_day_master.state.value == "相"
    assert mc.relation_to_day_master.in_command is False
    assert [(i.stem, i.transparent) for i in mc.hidden_stem_priority] == [("庚", True), ("壬", False), ("戊", False)]
