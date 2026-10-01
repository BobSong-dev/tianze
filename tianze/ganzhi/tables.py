"""干支事实层：天干地支、五行、阴阳、藏干、十神（R8）。

十神按五行生克+阴阳同异推导（不查表），测试与 lunar-python 的 100 条
硬编码表逐项对账（tests/test_ganzhi.py）。
"""

from __future__ import annotations

from enum import Enum


class Element(str, Enum):
    WOOD = "WOOD"
    FIRE = "FIRE"
    EARTH = "EARTH"
    METAL = "METAL"
    WATER = "WATER"


class YinYang(str, Enum):
    YANG = "YANG"
    YIN = "YIN"


class TenGod(str, Enum):
    BI_JIAN = "比肩"
    JIE_CAI = "劫财"
    SHI_SHEN = "食神"
    SHANG_GUAN = "伤官"
    PIAN_CAI = "偏财"
    ZHENG_CAI = "正财"
    QI_SHA = "七杀"
    ZHENG_GUAN = "正官"
    PIAN_YIN = "偏印"
    ZHENG_YIN = "正印"


STEMS: tuple[str, ...] = ("甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸")
BRANCHES: tuple[str, ...] = ("子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥")

STEM_ELEMENT: dict[str, Element] = {
    "甲": Element.WOOD, "乙": Element.WOOD,
    "丙": Element.FIRE, "丁": Element.FIRE,
    "戊": Element.EARTH, "己": Element.EARTH,
    "庚": Element.METAL, "辛": Element.METAL,
    "壬": Element.WATER, "癸": Element.WATER,
}
BRANCH_ELEMENT: dict[str, Element] = {
    "子": Element.WATER, "丑": Element.EARTH,
    "寅": Element.WOOD, "卯": Element.WOOD,
    "辰": Element.EARTH, "巳": Element.FIRE,
    "午": Element.FIRE, "未": Element.EARTH,
    "申": Element.METAL, "酉": Element.METAL,
    "戌": Element.EARTH, "亥": Element.WATER,
}


def stem_index(stem: str) -> int:
    try:
        return STEMS.index(stem)
    except ValueError as e:
        raise ValueError(f"非法天干: {stem!r}") from e


def branch_index(branch: str) -> int:
    try:
        return BRANCHES.index(branch)
    except ValueError as e:
        raise ValueError(f"非法地支: {branch!r}") from e


def stem_yin_yang(stem: str) -> YinYang:
    return YinYang.YANG if stem_index(stem) % 2 == 0 else YinYang.YIN


def branch_yin_yang(branch: str) -> YinYang:
    return YinYang.YANG if branch_index(branch) % 2 == 0 else YinYang.YIN


# R8：通行子平藏干表（本气 → 中气 → 余气）。
HIDDEN_STEMS: dict[str, tuple[tuple[str, str], ...]] = {
    "子": (("癸", "本气"),),
    "丑": (("己", "本气"), ("癸", "中气"), ("辛", "余气")),
    "寅": (("甲", "本气"), ("丙", "中气"), ("戊", "余气")),
    "卯": (("乙", "本气"),),
    "辰": (("戊", "本气"), ("乙", "中气"), ("癸", "余气")),
    "巳": (("丙", "本气"), ("庚", "中气"), ("戊", "余气")),
    "午": (("丁", "本气"), ("己", "中气")),
    "未": (("己", "本气"), ("丁", "中气"), ("乙", "余气")),
    "申": (("庚", "本气"), ("壬", "中气"), ("戊", "余气")),
    "酉": (("辛", "本气"),),
    "戌": (("戊", "本气"), ("辛", "中气"), ("丁", "余气")),
    "亥": (("壬", "本气"), ("甲", "中气")),
}

_GENERATES: dict[Element, Element] = {
    Element.WOOD: Element.FIRE, Element.FIRE: Element.EARTH,
    Element.EARTH: Element.METAL, Element.METAL: Element.WATER,
    Element.WATER: Element.WOOD,
}
_CONTROLS: dict[Element, Element] = {
    Element.WOOD: Element.EARTH, Element.EARTH: Element.WATER,
    Element.WATER: Element.FIRE, Element.FIRE: Element.METAL,
    Element.METAL: Element.WOOD,
}


def ten_god(day_master: str, other: str) -> TenGod:
    """日主对某天干的十神（R8 推导口径，与 lunar-python SHI_SHEN 表对账）。"""
    if day_master not in STEM_ELEMENT:
        raise ValueError(f"非法日主: {day_master!r}")
    if other not in STEM_ELEMENT:
        raise ValueError(f"非法天干: {other!r}")
    e1 = STEM_ELEMENT[day_master]
    e2 = STEM_ELEMENT[other]
    same = stem_index(day_master) % 2 == stem_index(other) % 2
    if e1 == e2:
        return TenGod.BI_JIAN if same else TenGod.JIE_CAI
    if _GENERATES[e1] == e2:
        return TenGod.SHI_SHEN if same else TenGod.SHANG_GUAN
    if _CONTROLS[e1] == e2:
        return TenGod.PIAN_CAI if same else TenGod.ZHENG_CAI
    if _CONTROLS[e2] == e1:
        return TenGod.QI_SHA if same else TenGod.ZHENG_GUAN
    if _GENERATES[e2] == e1:
        return TenGod.PIAN_YIN if same else TenGod.ZHENG_YIN
    raise AssertionError("五行关系不完备")  # pragma: no cover


# 五行阳气起点（十二长生）：用于三合局守恒律测试（长生/帝旺/墓 = 三合三支）。
YANG_CHANGSHENG_START: dict[str, str] = {
    "甲": "亥", "丙": "寅", "戊": "寅", "庚": "巳", "壬": "申",
}
