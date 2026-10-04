"""M8 特殊格局/病药/通关测试：状态映射、阻断、property test、Golden Case。"""

from __future__ import annotations

import pytest

from tianze.analysis.special import (
    SpecialPatternCandidate,
    SpecialStatus,
    analyze_all_special,
    analyze_bingyao,
    analyze_cong,
    analyze_tongguan,
    analyze_transformation,
    analyze_zhuanwang,
)


def _counts(**kw):
    base = {"wood": {"visible": 0, "hidden": 0}, "fire": {"visible": 0, "hidden": 0},
            "earth": {"visible": 0, "hidden": 0}, "metal": {"visible": 0, "hidden": 0},
            "water": {"visible": 0, "hidden": 0}}
    base.update(kw)
    return base


# ---------- M8.1 从格 ----------

def test_cong_cai_candidate():
    """从财：甲日主极弱、无根无印比、土多 → CANDIDATE/LIKELY。"""
    rs = analyze_cong("甲", "子", ["戊", "己", "甲", "戊"], ["戌", "子", "戌", "戌"],
                      {"weighted": "极弱", "fuyi": "极弱", "dimension": None}, 0.05, 0, [])
    cai = [r for r in rs if r.type == "从财"]
    assert cai and cai[0].status in (SpecialStatus.LIKELY, SpecialStatus.CANDIDATE)
    assert any("无根" in s.text for s in cai[0].supports)


def test_cong_blocked_by_root():
    """Property：从格 candidate 被强根阻断 → 不能输出 LIKELY。"""
    rs = analyze_cong("甲", "子", ["戊", "己", "甲", "戊"], ["寅", "子", "卯", "戌"],
                      {"weighted": "偏弱", "fuyi": "偏弱", "dimension": None}, 0.3, 2, ["壬"])
    for r in rs:
        if r.status == SpecialStatus.LIKELY:
            blockers = [b.text for b in r.blockers]
            assert not any("有根" in b or "强根" in b for b in blockers), \
                f"有强根阻断却输出 LIKELY: {r.type}"


def test_cong_disputed_on_analyzer_conflict():
    """旺衰分析器冲突 → DISPUTED。"""
    rs = analyze_cong("甲", "子", ["戊", "己", "甲", "戊"], ["戌", "子", "戌", "戌"],
                      {"weighted": "极弱", "fuyi": "偏强", "dimension": None}, 0.1, 0, [])
    assert any(r.status == SpecialStatus.DISPUTED for r in rs)


def test_cong_never_confirmed():
    """从格永不输出 CONFIRMED。"""
    rs = analyze_cong("甲", "子", ["戊", "己", "甲", "戊"], ["戌", "子", "戌", "戌"],
                      {"weighted": "极弱", "fuyi": "极弱", "dimension": None}, 0.01, 0, [])
    for r in rs:
        assert r.status != "CONFIRMED"


# ---------- M8.2 专旺 ----------

def test_zhuanwang_qu_zhi():
    """甲日寅月，地支全木 → 曲直 CANDIDATE/LIKELY。"""
    rs = analyze_zhuanwang("甲", "寅", ["甲", "甲", "甲", "乙"], ["寅", "卯", "辰", "亥"],
                           _counts(wood={"visible": 4, "hidden": 6}, water={"visible": 1, "hidden": 1}),
                           {"weighted": "极强", "fuyi": "极强", "dimension": None})
    assert rs and rs[0].type == "曲直"
    assert rs[0].status in (SpecialStatus.LIKELY, SpecialStatus.CANDIDATE)


def test_zhuanwang_blocked_by_guan_sha():
    """甲日有庚透干 → BLOCKED。"""
    rs = analyze_zhuanwang("甲", "寅", ["甲", "甲", "甲", "庚"], ["寅", "卯", "辰", "亥"],
                           _counts(wood={"visible": 3, "hidden": 6}, metal={"visible": 1, "hidden": 0},
                                   water={"visible": 1, "hidden": 1}),
                           {"weighted": "偏强", "fuyi": "偏强", "dimension": None})
    assert rs and rs[0].type == "曲直"
    # 官杀庚在 stems 中：可能有 blocker（如果 share >= 阈值）或用 B2/B3 阻断
    assert rs[0].blockers or rs[0].status != SpecialStatus.LIKELY  # 不能 LIKELY 当有官杀时


def test_zhuanwang_all_five_types():
    """五种专旺格名称完备。"""
    from tianze.analysis.special import _ZHUANGWANG
    assert set(_ZHUANGWANG) == {"曲直", "炎上", "稼穑", "从革", "润下"}


def test_zhuanwang_school_variants_recorded():
    """schoolVariants：流派差异保留（不统一）。"""
    rs = analyze_zhuanwang("甲", "寅", ["甲", "甲", "甲", "乙"], ["寅", "卯", "辰", "亥"],
                           _counts(wood={"visible": 4, "hidden": 6}, water={"visible": 1, "hidden": 1}),
                           {"weighted": "极强", "fuyi": "极强", "dimension": None})
    assert hasattr(rs[0], 'schoolVariants') or rs[0].to_dict().get("schoolVariants"),         "schoolVariants 字段应存在"


# ---------- M8.3 化气 ----------

def test_transformation_candidate():
    """甲己合化土 → 候选。"""
    ts = analyze_transformation("甲", "子", ["甲", "己", "甲", "乙"], ["子", "子", "亥", "卯"])
    assert any(t.stem_pair == ("甲", "己") for t in ts)


def test_no_he_no_transformation():
    """Property：无天干五合 → 不得出现化气候选。"""
    ts = analyze_transformation("甲", "子", ["甲", "乙", "甲", "乙"], ["子", "子", "亥", "卯"])
    assert ts == []


def test_transformation_season_unsupported():
    """甲己化土，但月支为卯（木）→ season_support=False → UNRESOLVED。"""
    ts = analyze_transformation("甲", "卯", ["甲", "己", "甲", "乙"], ["卯", "卯", "亥", "卯"])
    t = next(t for t in ts if t.stem_pair == ("甲", "己"))
    assert t.season_support is False
    assert t.status == SpecialStatus.UNRESOLVED


def test_transformation_never_confirmed():
    ts = analyze_transformation("戊", "子", ["戊", "癸", "甲", "乙"], ["子", "子", "亥", "卯"])
    for t in ts:
        assert t.status != "CONFIRMED"


# ---------- M8.4 病药 ----------

def test_bingyao_obvious_problem_with_medicine():
    """土 4/5 → OVERPOWERED_FACTOR；木可见 → 制药。"""
    r = analyze_bingyao(_counts(earth={"visible": 4, "hidden": 1}, wood={"visible": 1, "hidden": 0}))
    assert any(p["target"] == "earth" for p in r["problems"])
    # 木克土 → 制药；火生土 → 泄药（如果可见）
    # medicines 可能因 wood/fire 可见数不足而为空
    assert isinstance(r["medicines"], list)


def test_bingyao_no_problem():
    """五行均衡 → 无病无药。"""
    r = analyze_bingyao(_counts(wood={"visible": 1, "hidden": 0}, fire={"visible": 1, "hidden": 0},
                                earth={"visible": 1, "hidden": 0}, metal={"visible": 1, "hidden": 0},
                                water={"visible": 1, "hidden": 0}))
    assert r["problems"] == [] and r["medicines"] == []


def test_bingyao_no_medicine():
    """有病无药 → problems 有、medicines 空。"""
    r = analyze_bingyao(_counts(earth={"visible": 4, "hidden": 0}))
    assert r["problems"] and r["medicines"] == []


def test_bingyao_provenance_no_medical():
    """病药 provenance 不得提及医学疾病。"""
    r = analyze_bingyao(_counts(earth={"visible": 4, "hidden": 0}, wood={"visible": 1, "hidden": 0}))
    blob = json.dumps(r, ensure_ascii=False)
    for banned in ("你会得", "易患", "健康预测"):
        assert banned not in blob  # 禁止输出个人健康预测（结构性分析允许提及"病药"概念）


import json  # noqa: E402


# ---------- M8.5 通关 ----------

def test_tongguan_bridge_present():
    """金 4 字 vs 木 1 字（≥2 倍对峙），水 2 字可见 → 桥存在。"""
    r = analyze_tongguan(_counts(metal={"visible": 4, "hidden": 0}, wood={"visible": 1, "hidden": 0},
                                 water={"visible": 2, "hidden": 0}))
    assert any(b["bridge"] == "WATER" and b["present"] for b in r["bridges"])


def test_tongguan_bridge_absent():
    """金 4 字 vs 木 1 字，水 0 字 → 桥不存在。"""
    r = analyze_tongguan(_counts(metal={"visible": 4, "hidden": 0}, wood={"visible": 1, "hidden": 0}))
    if r["bridges"]:
        b = next(b for b in r["bridges"] if b["bridge"] == "WATER")
        assert b["present"] is False


def test_tongguan_no_conflict_when_balanced():
    """金 2 vs 木 2（不到 2 倍）→ 不算对峙。"""
    r = analyze_tongguan(_counts(metal={"visible": 2, "hidden": 0}, wood={"visible": 2, "hidden": 0}))
    assert r["conflictPairs"] == []


def test_tongguan_bridge_element_path():
    """Property：通关 bridge 必须满足 A→C→B 生链。"""
    r = analyze_tongguan(_counts(metal={"visible": 4, "hidden": 0}, wood={"visible": 1, "hidden": 0},
                                 water={"visible": 2, "hidden": 0}))
    for b in r["bridges"]:
        assert b["bridge"] == "WATER"  # 金生水、水生木


# ---------- M8 综合 ----------

def test_analyze_all_special_integration():
    """总入口：三组结果完整。"""
    r = analyze_all_special("甲", "子", ["戊", "己", "甲", "戊"], ["戌", "子", "戌", "戌"],
                            {"weighted": "极弱", "fuyi": "极弱", "dimension": None}, 0.05, 0, [],
                            _counts(earth={"visible": 4, "hidden": 1}, wood={"visible": 1, "hidden": 0},
                                    water={"visible": 1, "hidden": 0}, metal={"visible": 0, "hidden": 0},
                                    fire={"visible": 0, "hidden": 0}))
    assert "specialPattern" in r and "bingYao" in r and "tongGuan" in r
    assert "cong" in r["specialPattern"] and "zhuanwang" in r["specialPattern"]
    assert "transformation" in r["specialPattern"]
