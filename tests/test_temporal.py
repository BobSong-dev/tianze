"""M12 岁运分析测试：时间结构 / 关系变化 / 三合补齐 / 伏吟反吟 / 来源标记。"""

from __future__ import annotations

import pytest

from tianze.analysis.temporal import (
    AnalysisSupport,
    TemporalSource,
    analyze_temporal,
)


def test_temporal_relations_with_sources():
    """岁运关系必须标记来源位置。"""
    r = analyze_temporal(
        natal_stems=["癸", "庚", "癸", "己"],
        natal_branches=["未", "申", "亥", "未"],
        day_master="癸",
        luck_stem="丙", luck_branch="寅",
    )
    # 丙寅大运与原局申 → 寅申冲
    clash = next(r for r in r.relations if r.kind == "clash")
    assert "寅" in clash.members and "申" in clash.members
    assert TemporalSource.NATAL in clash.sources
    assert TemporalSource.LUCK in clash.sources
    assert clash.is_new is True
    assert any("natal:month" in p for p in clash.positions)
    assert any("luck" in p for p in clash.positions)


def test_three_harmony_completed():
    """原局寅午 + 流年戌 → 三合火局补齐。"""
    r = analyze_temporal(
        natal_stems=["甲", "丙", "甲", "丁"],
        natal_branches=["寅", "午", "午", "午"],
        day_master="甲",
        annual_stem="戊", annual_branch="戌",
    )
    completed = [r for r in r.relations if r.kind == "three_harmony_completed"]
    assert completed
    assert completed[0].completes_harmony is True
    assert "寅午戌三合补齐" in completed[0].label
    assert any("流年" in e and "戌" in e for e in r.evidence)


def test_stem_combination_new():
    """岁运干与原局干五合 → is_new=True。"""
    r = analyze_temporal(
        natal_stems=["甲", "庚", "甲", "丁"],
        natal_branches=["子", "申", "子", "卯"],
        day_master="甲",
        luck_stem="己", luck_branch="丑",
    )
    combo = [r for r in r.relations if r.kind == "stem_combination"]
    assert combo and combo[0].is_new is True
    assert "甲" in combo[0].members and "己" in combo[0].members


def test_fuyin_detection():
    """大运与原局某柱完全相同 → 伏吟。"""
    r = analyze_temporal(
        natal_stems=["甲", "丙", "甲", "甲"],
        natal_branches=["戌", "寅", "戌", "戌"],
        day_master="甲",
        luck_stem="甲", luck_branch="戌",
    )
    fuyin = [s for s in r.structures if s.type == "fuyin"]
    assert fuyin


def test_fanyin_detection():
    """大运地支与原局地支相冲 → 反吟。"""
    r = analyze_temporal(
        natal_stems=["癸", "庚", "癸", "己"],
        natal_branches=["未", "申", "亥", "未"],
        day_master="癸",
        luck_stem="丙", luck_branch="寅",
    )
    fanyin = [s for s in r.structures if s.type == "fanyin"]
    assert fanyin, "寅申冲应检出反吟"


def test_binglin_detection():
    """岁运并临。"""
    r = analyze_temporal(
        natal_stems=["甲", "丙", "甲", "丁"],
        natal_branches=["子", "申", "子", "卯"],
        day_master="甲",
        luck_stem="壬", luck_branch="子",
        annual_stem="壬", annual_branch="子",
    )
    binglin = [s for s in r.structures if s.type == "binglin"]
    assert binglin
    assert "岁运并临" in binglin[0].label


def test_tiankedi_detection():
    """天克地冲。"""
    r = analyze_temporal(
        natal_stems=["甲", "丙", "甲", "丁"],
        natal_branches=["子", "申", "子", "卯"],
        day_master="甲",
        luck_stem="庚", luck_branch="午",
        annual_stem="甲", annual_branch="子",
    )
    tkd = [s for s in r.structures if s.type == "tiankedi"]
    assert tkd, "庚金克甲木 + 午子冲 → 天克地冲"


def test_no_luck_no_annual():
    """无大运无流年 → 只返回结构现象（无岁运关系）。"""
    r = analyze_temporal(
        natal_stems=["癸", "庚", "癸", "己"],
        natal_branches=["未", "申", "亥", "未"],
        day_master="癸",
    )
    assert r.relations == []
    assert r.evidence == []


def test_no_fortune_output():
    """岁运分析不输出吉凶。"""
    r = analyze_temporal(
        natal_stems=["癸", "庚", "癸", "己"],
        natal_branches=["未", "申", "亥", "未"],
        day_master="癸",
        luck_stem="丙", luck_branch="寅",
        annual_stem="甲", annual_branch="辰",
    )
    blob = r.model_dump_json()
    for banned in ("发财", "大凶", "必有灾", "升职", "结婚"):
        assert banned not in blob


def test_warnings_present():
    r = analyze_temporal(
        natal_stems=["癸", "庚", "癸", "己"],
        natal_branches=["未", "申", "亥", "未"],
        day_master="癸",
        luck_stem="丙", luck_branch="寅",
    )
    assert any("不构成" in w for w in r.warnings)
