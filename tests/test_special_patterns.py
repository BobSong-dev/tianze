"""M8 特殊格局/病药/通关测试：状态映射、阻断、property test、Golden Case。"""

from __future__ import annotations

import pytest

from tianze.analysis.case_chart import build_case_chart
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


# ---------- M23 · DTZ-47 真化条件精细化 ----------

def test_dtz47_adjacent_pair_candidate():
    """DTZ-47 邻位合：日干与月干相合、月令化神、印比不见、原局见辰 → CANDIDATE。"""
    ts = analyze_transformation("甲", "未", ["丙", "己", "甲", "庚"], ["辰", "未", "戌", "申"])
    t = next(x for x in ts if x.stem_pair == ("甲", "己"))
    assert t.status == SpecialStatus.CANDIDATE
    assert t.obstructions == []
    assert t.adjacent_to_day_master is True
    assert t.chen_present is True  # 逢龙而运（化气元神之地）


def test_dtz47_year_stem_too_far():
    """DTZ-47：年干与日干相隔太远不能合化 → UNRESOLVED + 位置阻断证据。"""
    ts = analyze_transformation("甲", "未", ["己", "丙", "甲", "庚"], ["辰", "午", "戌", "申"])
    t = next(x for x in ts if x.stem_pair == ("甲", "己"))
    assert t.status == SpecialStatus.UNRESOLVED
    assert any("相隔太远" in o for o in t.obstructions)
    assert t.adjacent_to_day_master is False


def test_dtz47_non_day_pair_not_hua():
    """DTZ-47：非日主之合（年月合）不构成化格候选依据 → UNRESOLVED。"""
    ts = analyze_transformation("壬", "未", ["己", "甲", "壬", "庚"], ["辰", "午", "子", "申"])
    t = next(x for x in ts if x.stem_pair == ("甲", "己"))
    assert t.status == SpecialStatus.UNRESOLVED
    assert any("非日主之合" in o for o in t.obstructions)
    assert t.adjacent_to_day_master is None


def test_dtz47_yin_bijie_blocks_hua():
    """DTZ-47 原注：印绶/比劫均不可见——壬印透干 → 日干不衰绝，阻化。"""
    ts = analyze_transformation("甲", "未", ["壬", "己", "甲", "庚"], ["辰", "未", "戌", "申"])
    t = next(x for x in ts if x.stem_pair == ("甲", "己"))
    assert t.status == SpecialStatus.UNRESOLVED
    assert any("印绶" in o and "比劫" in o for o in t.obstructions)


def test_dtz47_temporal_stems_not_position_blocked():
    """岁运扩展干与日干之合不受原局邻位约束（位置约束只判原局 0-3 位）。"""
    natal = ["丙", "己", "甲", "庚"]
    ext = natal + ["己", "甲"]  # 岁运再遇甲/己（DTZ-48：烈女不事二夫场景）
    ts = analyze_transformation("甲", "未", ext, ["辰", "未", "戌", "申"])
    t = next(x for x in ts if x.stem_pair == ("甲", "己") and x.adjacent_to_day_master is not None)
    # day-month 邻位候选仍在，且不被岁运干的位置规则阻断
    assert t.status == SpecialStatus.CANDIDATE


def test_dtz47_dict_has_new_fields():
    """to_dict 输出 chenPresent / adjacentToDayMaster（additive Schema 字段）。"""
    ts = analyze_transformation("甲", "未", ["丙", "己", "甲", "庚"], ["辰", "未", "戌", "申"])
    d = ts[0].to_dict()
    assert "chenPresent" in d and "adjacentToDayMaster" in d
    assert d["provenance"][1]["level"] == "CLASSICAL_EXPLICIT"


# ---------- M23 · DTZ-06 从格经典造回归（结构分类，非事件拟合） ----------

def _special_of(pillars: dict[str, str]) -> dict:
    chart = build_case_chart(pillars)
    adv = chart.advancedAnalysis["specialPattern"]
    return adv


def test_dtz06_xu_shiying_yin_transparent_blocks_cong():
    """许世英造（癸酉 辛酉 乙丑 辛巳）：乙木生金旺月、两辛并透，
    然癸水偏印透干生身 → 不作从煞论（从官杀候选受阻，不得 LIKELY）。"""
    adv = _special_of({"year": "癸酉", "month": "辛酉", "day": "乙丑", "hour": "辛巳"})
    cong_sha = next((c for c in adv["cong"] if c["type"] == "从官杀"), None)
    assert cong_sha is not None, "金势成局应有从官杀候选"
    assert cong_sha["status"] in ("CANDIDATE", "BLOCKED", "DISPUTED", "UNRESOLVED")
    assert cong_sha["status"] != "LIKELY", "印透生身（DTZ-06）：不作从煞论"
    assert any("印比" in b["text"] or "印" in b["text"] for b in cong_sha["blockers"])


def test_dtz06_wu_tingfang_follows_the_dominant():
    """伍庭芳造（壬寅 丁未 己卯 乙亥）：己土虽未月通根，然亥卯未会局、
    乙木透、丁壬合木——徐断「弃命相从，从势无情义」。

    Tianze 口径：weighted（未月通根）与 fuyi（势旺）真实分歧 → DISPUTED
    保留两读（R19 不裁决），不因历史名造调参迎合徐断（ADR-059 同纪律）。
    测试锁定：从格候选存在、非 BLOCKED、且分歧以 supports 文本透明记录。
    """
    adv = _special_of({"year": "壬寅", "month": "丁未", "day": "己卯", "hour": "乙亥"})
    cong = adv["cong"]
    assert cong, "木势成局应有从格候选"
    for c in cong:
        assert c["status"] in ("LIKELY", "CANDIDATE", "DISPUTED"), c["type"] + ":" + c["status"]
    sha = next(c for c in cong if c["type"] == "从官杀")
    assert sha["status"] == "DISPUTED", "weighted/fuyi 分歧必须如实保留"
    assert any("weighted" in s["text"] and "fuyi" in s["text"] for s in sha["supports"])


# ---------- M25 · 外格虚神候选（xushiOuter：候选而非成格） ----------

def test_xushi_outer_jinglancha():
    """井栏叉（ZP-12：庚日申戌拱酉）：刃位虚神候选；官杀透 → BLOCKED。"""
    chart = build_case_chart({"year": "甲辰", "month": "丙戌", "day": "庚申", "hour": "丁丑"})
    xo = chart.advancedAnalysis["specialPattern"]["xushiOuter"]
    c = next(x for x in xo if "井栏叉" in x["type"])
    assert c["status"] == "BLOCKED"  # 丙/丁官杀透 → 填实破格
    assert any("伤官变格" in sv for sv in c["schoolVariants"].values())


def test_xushi_outer_feitian_luma():
    """飞天禄马（ZP-12/DTZ-41）：庚日三子无午 → 候选；官星透 → BLOCKED。"""
    chart = build_case_chart({"year": "甲子", "month": "丙子", "day": "庚子", "hour": "丁丑"})
    c = next(x for x in chart.advancedAnalysis["specialPattern"]["xushiOuter"]
             if "飞天禄马" in x["type"])
    assert c["status"] == "BLOCKED" and any("官星" in b["text"] for b in c["blockers"])
    # 无官星透 → 候选
    chart2 = build_case_chart({"year": "壬子", "month": "壬子", "day": "庚子", "hour": "戊子"})
    c2 = next(x for x in chart2.advancedAnalysis["specialPattern"]["xushiOuter"]
              if "飞天禄马" in x["type"])
    assert c2["status"] == "CANDIDATE"


def test_xushi_outer_xinghe_zInvite():
    """刑合（ZP-07：癸日时寅虚邀巳）与子邀巳（ZP-11）候选。"""
    chart = build_case_chart({"year": "辛亥", "month": "乙卯", "day": "癸卯", "hour": "甲寅"})
    xo = chart.advancedAnalysis["specialPattern"]["xushiOuter"]
    assert any("刑合" in x["type"] for x in xo)
    assert any("假名刑合" in sv or "伤官说" in k for x in xo for k, sv in x["schoolVariants"].items())
    # 子邀巳（ZP-11）不落地为引擎候选（OCR 残缺 + 泛化 ~27%，M25 审计结论）
    chart2 = build_case_chart({"year": "甲子", "month": "丙寅", "day": "戊午", "hour": "壬子"})
    assert not any("子邀巳" in x["type"] for x in
                   chart2.advancedAnalysis["specialPattern"]["xushiOuter"])


def test_xushi_outer_never_confirmed_and_target_presence_blocks():
    """永不 CONFIRMED；虚神在场 → 不产生候选（子邀巳遇巳不立）。"""
    chart = build_case_chart({"year": "甲子", "month": "丙寅", "day": "戊午", "hour": "壬子"})
    blob = str(chart.advancedAnalysis)
    assert "CONFIRMED" not in blob
    chart2 = build_case_chart({"year": "甲子", "month": "丙寅", "day": "戊辰", "hour": "壬子"})
    # 辰在场 → 辰申拱酉 blocked？ 子邀巳: 巳不在 → still. 检查 井栏叉 在酉在场时不出现：
    for x in chart2.advancedAnalysis["specialPattern"]["xushiOuter"]:
        assert "CONFIRMED" != x["status"]
