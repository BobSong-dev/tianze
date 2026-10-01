"""M3.3 月令引擎（R6/R17）。

输出：季节（三会口径）、月支五行阴阳、藏干优先级（本气→中气→余气，含透出标记）、
对日主的旺相休囚死关系（含土旺四季特判），全部附证据语句。
得令严格 = 旺（R17）；"相"（月令生日主）不是得令，但在证据中注明。
"""

from __future__ import annotations

from typing import Sequence

from tianze.domain.models import (
    DayMasterRelation,
    Element,
    HiddenStemPriorityItem,
    MonthCommand,
    Season,
    SeasonState,
    YinYang,
)
from tianze.ganzhi.tables import (
    BRANCHES,
    BRANCH_ELEMENT,
    HIDDEN_STEMS,
    STEM_ELEMENT,
    branch_yin_yang,
)

SEASON_BY_BRANCH: dict[str, Season] = {
    "寅": Season.SPRING, "卯": Season.SPRING, "辰": Season.SPRING,
    "巳": Season.SUMMER, "午": Season.SUMMER, "未": Season.SUMMER,
    "申": Season.AUTUMN, "酉": Season.AUTUMN, "戌": Season.AUTUMN,
    "亥": Season.WINTER, "子": Season.WINTER, "丑": Season.WINTER,
}

# 旺相休囚死（R6/R17 通行口径）：按**月支本气五行**判定——
# 当令者旺、我生者相、生我者休、克我者囚、我克者死；
# 四库月（辰戌丑未）本气为土 → 土日主自动得令（"土旺四季"由此成立，非额外特判）。

EARTH_STORES: frozenset[str] = frozenset({"辰", "戌", "丑", "未"})

ELEM_CN: dict[Element, str] = {
    Element.WOOD: "木", Element.FIRE: "火", Element.EARTH: "土",
    Element.METAL: "金", Element.WATER: "水",
}
SEASON_CN: dict[Season, str] = {
    Season.SPRING: "春", Season.SUMMER: "夏", Season.AUTUMN: "秋", Season.WINTER: "冬",
}
SEASON_TRIO: dict[Season, str] = {
    Season.SPRING: "寅卯辰", Season.SUMMER: "巳午未",
    Season.AUTUMN: "申酉戌", Season.WINTER: "亥子丑",
}
_STATE_CN: dict[SeasonState, str] = {
    SeasonState.WANG: "得令（旺）", SeasonState.XIANG: "相（月令所生，不得令但受生）",
    SeasonState.XIU: "休（生月令，泄）", SeasonState.QIN: "囚（克月令，反受制）",
    SeasonState.SI: "死（为月令所克）",
}

R6_RULE = "当令者旺、我生者相、生我者休、克我者囚、我克者死（按月支本气五行，R6/R17）"

_GEN: dict[Element, Element] = {
    Element.WOOD: Element.FIRE, Element.FIRE: Element.EARTH,
    Element.EARTH: Element.METAL, Element.METAL: Element.WATER,
    Element.WATER: Element.WOOD,
}
_CTL: dict[Element, Element] = {
    Element.WOOD: Element.EARTH, Element.EARTH: Element.WATER,
    Element.WATER: Element.FIRE, Element.FIRE: Element.METAL,
    Element.METAL: Element.WOOD,
}


def season_state_for(day_element: Element, month_branch: str) -> tuple[SeasonState, str]:
    """返回（状态, 判定依据说明）。按月支本气五行判定（R6/R17）。"""
    month_elem = BRANCH_ELEMENT[month_branch]
    if day_element == month_elem:
        return SeasonState.WANG, (
            f"日主与月支{month_branch}本气（{ELEM_CN[month_elem]}）同气 → 当令者旺"
            + ("（土旺四季）" if month_branch in EARTH_STORES else "")
        )
    if _GEN[month_elem] == day_element:
        return SeasonState.XIANG, f"月令{ELEM_CN[month_elem]}生日主 → 相"
    if _GEN[day_element] == month_elem:
        return SeasonState.XIU, f"日主生月令{ELEM_CN[month_elem]} → 休"
    if _CTL[day_element] == month_elem:
        return SeasonState.QIN, f"日主克月令{ELEM_CN[month_elem]} → 囚"
    if _CTL[month_elem] == day_element:
        return SeasonState.SI, f"月令{ELEM_CN[month_elem]}克日主 → 死"
    raise AssertionError("五行关系不完备")  # pragma: no cover


def compute_month_command(
    month_branch: str,
    day_master: str,
    stems: Sequence[str | None],
    day_master_element: Element | None = None,
) -> MonthCommand:
    if month_branch not in BRANCHES:
        raise ValueError(f"非法月支: {month_branch!r}")
    dm_elem = day_master_element or STEM_ELEMENT[day_master]
    season = SEASON_BY_BRANCH[month_branch]
    month_elem = BRANCH_ELEMENT[month_branch]

    visible_chars = {s for s in stems if s}
    priority = [
        HiddenStemPriorityItem(
            stem=hidden,
            role=role,
            transparent=hidden in visible_chars,
        )
        for hidden, role in HIDDEN_STEMS[month_branch]
    ]

    state, rule = season_state_for(dm_elem, month_branch)
    relation = DayMasterRelation(
        state=state,
        in_command=state == SeasonState.WANG,
        rule=rule,
    )

    evidence: list[str] = [
        f"日主{day_master}（{ELEM_CN[dm_elem]}）生于{month_branch}月",
        f"{month_branch}月属{SEASON_CN[season]}季（{SEASON_TRIO[season]}），"
        f"月支本气五行为{ELEM_CN[month_elem]}（{month_elem.value}）",
        f"旺相休囚死判定：{relation.rule}（R6/R17）",
        f"日主{ELEM_CN[dm_elem]}处【{state.value}】→ {_STATE_CN[state]}",
    ]
    priority_desc = "、".join(f"{item.stem}（{item.role.value}{'，已透出' if item.transparent else ''}）" for item in priority)
    evidence.append(f"{month_branch}藏干优先级（本气→中气→余气）：{priority_desc}")
    return MonthCommand(
        month_branch=month_branch,
        season=season,
        element=month_elem,
        yin_yang=branch_yin_yang(month_branch),
        hidden_stem_priority=priority,
        day_master=day_master,
        relation_to_day_master=relation,
        evidence=evidence,
    )
