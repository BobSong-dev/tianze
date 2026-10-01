"""干支事实层测试：与 lunar-python 表对账（藏干逐支、十神 10×10 全矩阵）。"""

from __future__ import annotations

import pytest
from lunar_python.util.LunarUtil import LunarUtil

from tianze.ganzhi.tables import (
    BRANCHES,
    BRANCH_ELEMENT,
    HIDDEN_STEMS,
    STEMS,
    STEM_ELEMENT,
    YANG_CHANGSHENG_START,
    branch_index,
    branch_yin_yang,
    stem_index,
    stem_yin_yang,
    ten_god,
)


def test_stem_branch_counts_and_elements():
    assert len(STEMS) == 10 and len(BRANCHES) == 12
    for s in ("甲", "丙", "戊", "庚", "壬"):
        assert STEM_ELEMENT[s].value in {"WOOD", "FIRE", "EARTH", "METAL", "WATER"}
    # 阴阳 = 序数奇偶
    for i, s in enumerate(STEMS):
        assert (stem_yin_yang(s).value == "YANG") == (i % 2 == 0)
    for i, b in enumerate(BRANCHES):
        assert (branch_yin_yang(b).value == "YANG") == (i % 2 == 0)
    # 地支五行固定（R8）
    assert BRANCH_ELEMENT["子"].value == "WATER" and BRANCH_ELEMENT["巳"].value == "FIRE"
    assert BRANCH_ELEMENT["戌"].value == "EARTH" and BRANCH_ELEMENT["申"].value == "METAL"


def test_hidden_stems_match_lunar_table():
    """R8：Tianze 藏干表与 lunar-python ZHI_HIDE_GAN 逐支对账。"""
    assert set(LunarUtil.ZHI_HIDE_GAN.keys()) == set(BRANCHES)
    for branch, expected in LunarUtil.ZHI_HIDE_GAN.items():
        ours = [stem for stem, _role in HIDDEN_STEMS[branch]]
        assert ours == list(expected), f"藏干不一致: {branch}: {ours} != {expected}"


def test_hidden_stem_roles():
    assert [r for _s, r in HIDDEN_STEMS["子"]] == ["本气"]
    assert [r for _s, r in HIDDEN_STEMS["寅"]] == ["本气", "中气", "余气"]
    assert [r for _s, r in HIDDEN_STEMS["午"]] == ["本气", "中气"]


def test_ten_god_full_matrix_matches_lunar():
    """十神推导 vs lunar-python 100 条硬编码表（SHI_SHEN 键 = 日干+他干）。"""
    for dm in STEMS:
        for other in STEMS:
            expected = LunarUtil.SHI_SHEN[dm + other]
            got = ten_god(dm, other).value
            assert got == expected, f"十神不一致: {dm}见{other}: {got} != {expected}"


def test_ten_god_key_cases():
    assert ten_god("甲", "甲").value == "比肩"
    assert ten_god("甲", "乙").value == "劫财"
    assert ten_god("甲", "丙").value == "食神"
    assert ten_god("甲", "丁").value == "伤官"
    assert ten_god("甲", "戊").value == "偏财"
    assert ten_god("甲", "己").value == "正财"
    assert ten_god("甲", "庚").value == "七杀"
    assert ten_god("甲", "辛").value == "正官"
    assert ten_god("甲", "壬").value == "偏印"
    assert ten_god("甲", "癸").value == "正印"
    assert ten_god("癸", "己").value == "七杀"
    assert ten_god("癸", "戊").value == "正官"


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        stem_index("啊")
    with pytest.raises(ValueError):
        branch_index("啊")
    with pytest.raises(ValueError):
        ten_god("甲", "啊")


def test_yang_changsheng_starts_are_traditional():
    """阳干长生位（甲亥/丙寅/戊寅/庚巳/壬申）——三合守恒律测试的基础数据。"""
    assert YANG_CHANGSHENG_START["甲"] == "亥"
    assert YANG_CHANGSHENG_START["丙"] == "寅"
    assert YANG_CHANGSHENG_START["庚"] == "巳"
    assert YANG_CHANGSHENG_START["壬"] == "申"
    assert branch_index("子") == 0 and branch_index("亥") == 11
