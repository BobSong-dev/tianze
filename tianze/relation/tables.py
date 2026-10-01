"""L4 关系表（R9/R10/R13/R14）——传统公版内容，逐对可溯源。

多重关系并存不裁决（R9）：如 寅亥既六合又相破、巳申既六合又相破又是三刑成员。
"""

from __future__ import annotations

from tianze.ganzhi.tables import Element

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
