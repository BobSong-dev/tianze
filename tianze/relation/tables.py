"""L4 关系表（R9/R10/R13/R14）——传统公版内容，逐对可溯源。

多重关系并存不裁决（R9）：如 寅亥既六合又相破、巳申既六合又相破又是三刑成员。
"""

from __future__ import annotations

from tianze.ganzhi.tables import BRANCHES, Element

FS = frozenset

# 天干五合（R13：化气只作候选）
STEM_COMBINATIONS: dict[FS[str], Element] = {
    FS({"甲", "己"}): Element.EARTH,
    FS({"乙", "庚"}): Element.METAL,
    FS({"丙", "辛"}): Element.WATER,
    FS({"丁", "壬"}): Element.WOOD,
    FS({"戊", "癸"}): Element.FIRE,
}

# 天干四冲（R14：戊己土居中不冲）
STEM_OPPOSITIONS: set[FS[str]] = {
    FS({"甲", "庚"}), FS({"乙", "辛"}), FS({"丙", "壬"}), FS({"丁", "癸"}),
}

# 地支六合（R13：午未化气默认土，火说/日月说分歧 → 输出 note）
SIX_COMBINATIONS: dict[FS[str], Element] = {
    FS({"子", "丑"}): Element.EARTH,
    FS({"寅", "亥"}): Element.WOOD,
    FS({"卯", "戌"}): Element.FIRE,
    FS({"辰", "酉"}): Element.METAL,
    FS({"巳", "申"}): Element.WATER,
    FS({"午", "未"}): Element.EARTH,
}

SIX_CLASHES: set[FS[str]] = {
    FS({"子", "午"}), FS({"丑", "未"}), FS({"寅", "申"}),
    FS({"卯", "酉"}), FS({"辰", "戌"}), FS({"巳", "亥"}),
}

SIX_HARMS: set[FS[str]] = {
    FS({"子", "未"}), FS({"丑", "午"}), FS({"寅", "巳"}),
    FS({"卯", "辰"}), FS({"申", "亥"}), FS({"酉", "戌"}),
}

SIX_BREAKS: set[FS[str]] = {
    FS({"子", "酉"}), FS({"丑", "辰"}), FS({"寅", "亥"}),
    FS({"卯", "午"}), FS({"巳", "申"}), FS({"未", "戌"}),
}

# 三合局（R10：半合须含中神）
THREE_HARMONIES: dict[FS[str], Element] = {
    FS({"申", "子", "辰"}): Element.WATER,
    FS({"亥", "卯", "未"}): Element.WOOD,
    FS({"寅", "午", "戌"}): Element.FIRE,
    FS({"巳", "酉", "丑"}): Element.METAL,
}
HARMONY_CENTERS: frozenset[str] = frozenset({"子", "卯", "午", "酉"})
# 传统表述顺序（长生支-中神-墓支）
THREE_HARMONIES_ORDER: dict[FS[str], tuple[str, str, str]] = {
    FS({"申", "子", "辰"}): ("申", "子", "辰"),
    FS({"亥", "卯", "未"}): ("亥", "卯", "未"),
    FS({"寅", "午", "戌"}): ("寅", "午", "戌"),
    FS({"巳", "酉", "丑"}): ("巳", "酉", "丑"),
}

# 三会方
THREE_MEETINGS: dict[FS[str], tuple[str, Element]] = {
    FS({"寅", "卯", "辰"}): ("东方木", Element.WOOD),
    FS({"巳", "午", "未"}): ("南方火", Element.FIRE),
    FS({"申", "酉", "戌"}): ("西方金", Element.METAL),
    FS({"亥", "子", "丑"}): ("北方水", Element.WATER),
}
THREE_MEETINGS_ORDER: dict[FS[str], tuple[str, str, str]] = {
    FS({"寅", "卯", "辰"}): ("寅", "卯", "辰"),
    FS({"巳", "午", "未"}): ("巳", "午", "未"),
    FS({"申", "酉", "戌"}): ("申", "酉", "戌"),
    FS({"亥", "子", "丑"}): ("亥", "子", "丑"),
}

# 三刑（R9：命名取通行口径，义理派互换 → 输出 note）。ORDER 为传统表述顺序。
PUNISHMENT_TRIOS: dict[FS[str], str] = {
    FS({"寅", "巳", "申"}): "无恩之刑",
    FS({"丑", "戌", "未"}): "恃势之刑",
}
PUNISHMENT_TRIO_ORDER: dict[FS[str], tuple[str, str, str]] = {
    FS({"寅", "巳", "申"}): ("寅", "巳", "申"),
    FS({"丑", "戌", "未"}): ("丑", "戌", "未"),
}
PUNISHMENT_ZIMAO: FS[str] = FS({"子", "卯"})
ZIMAO_NAME = "无礼之刑"
SELF_PUNISHMENT: frozenset[str] = frozenset({"辰", "午", "酉", "亥"})


# ---- M24 · 暗合（SPZY-34 逐对引文）----
# 「干与干相遇为明合，地支所藏人元之用相遇为暗合——两支毗连、各取其禄旺之气」；
# 值 = 参与暗合的藏干对（evidence 用）；「凡命造之佳者必多合，非以化论也」——
# 暗合永远不产生化气候选（transform_candidate 恒为 None）。
HIDDEN_COMBINATIONS: dict[FS[str], list[tuple[str, str]]] = {
    FS({"子", "巳"}): [("癸", "戊")],                 # 子中癸水得禄、巳中戊土得禄——戊癸合
    FS({"寅", "丑"}): [("甲", "己")],
    FS({"寅", "未"}): [("甲", "己")],
    FS({"卯", "申"}): [("乙", "庚")],
    FS({"辰", "子"}): [("戊", "癸")],
    FS({"戌", "子"}): [("戊", "癸")],
    FS({"巳", "丑"}): [("丙", "辛"), ("戊", "癸")],   # 原注：巳酉会局不以合论
    FS({"午", "亥"}): [("丁", "壬"), ("甲", "己")],
}
# 巳丑的会局例外：原局见酉时以 note 保留两读（不删关系、不判化）
HIDDEN_COMBO_EXCEPTIONS: dict[FS[str], tuple[str, str]] = {
    FS({"巳", "丑"}): ("酉", "巳酉会局不以合论（SPZY-34 原注）"),
}


# 天乙贵人（SS-R17 阳贵阴贵起例并集；歌诀「甲戊庚牛羊，乙己鼠猴乡。丙丁猪鸡位，
# 壬癸兔蛇藏。六辛逢马虎，此是贵人方」逐字）。值 = 该日主的天乙贵人支集合
# （阳贵/阴贵各一，SS-R17 逐日推演）。用途限定：拱贵 sub_type（ZP-05）与六乙鼠贵
# 候选（ZP-06）——SS-R16 三要件（见合/交互得/生旺无冲破）意味着裸贵人临命本身
# 不构成可执行结论（「若干支无合又不交互，乃庸常者流」），故不输出独立神煞事实。
TIAN_YI_NOBLE: dict[str, frozenset[str]] = {
    "甲": frozenset({"丑", "未"}), "戊": frozenset({"丑", "未"}), "庚": frozenset({"丑", "未"}),
    "乙": frozenset({"子", "申"}), "己": frozenset({"子", "申"}),
    "丙": frozenset({"亥", "酉"}), "丁": frozenset({"亥", "酉"}),
    "壬": frozenset({"卯", "巳"}), "癸": frozenset({"巳", "卯"}),
    "辛": frozenset({"午", "寅"}),
}


def arch_target(a: str, b: str) -> str | None:
    """拱夹定位（DTZ-10/ZP-05）：两支在地支环上恰隔一支 → 返回被拱之支。

    寅↔辰 拱卯、亥↔丑 拱子（跨年界）。同支、不相隔或相隔 >2 → None。
    结构注记：三合局成员相隔四位（长生-中神-墓），隔二缺一的拱对不可能
    同属一个三合局——拱只可能指向三会方中支、日主禄位或泛夹位。
    """
    if a not in BRANCHES or b not in BRANCHES or a == b:
        return None
    ia, ib = BRANCHES.index(a), BRANCHES.index(b)
    if (ib - ia) % 12 == 2:
        return BRANCHES[(ia + 1) % 12]
    if (ia - ib) % 12 == 2:
        return BRANCHES[(ib + 1) % 12]
    return None
