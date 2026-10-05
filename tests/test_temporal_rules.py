"""M13：岁运知识规则（ExecutableRule domain=temporal → TemporalEvidence）。"""

from __future__ import annotations

import json
import os

import pytest

from tianze.analysis.temporal import analyze_temporal
from tianze.knowledge.temporal_rules import (
    TEMPORAL_RULES_PATH, load_temporal_rules, evaluate_temporal_rules,
)


@pytest.fixture(scope="module")
def rules():
    assert os.path.exists(TEMPORAL_RULES_PATH), "先运行 tools/build_temporal_rules.py"
    return load_temporal_rules()


def test_rules_load(rules):
    assert len(rules) == 10
    ids = [r["id"] for r in rules]
    assert len(ids) == len(set(ids))
    for r in rules:
        assert r["domain"] == "temporal"
        assert r["candidateId"]
        assert r["verification"]["status"] == "MACHINE_CURATED"   # 诚实降级
        assert r["accuracyMatrix"]["traceability"] == "PASS"


def test_provenance_discipline(rules):
    """有引文的规则必须带 CLASSICAL_EXPLICIT；无引文的只能是 PROJECT_REFERENCE/ENGINEERING_HEURISTIC。"""
    by_id = {r["id"]: r for r in rules}
    for rid in ("TR-SS-R09", "TR-SS-R10A", "TR-SS-R10B", "TR-DTZ-35", "TR-DTZ-09", "TR-SPZY-28"):
        levels = {p["level"] for p in by_id[rid]["provenance"]}
        assert "CLASSICAL_EXPLICIT" in levels, f"{rid} 有原文链必须标 CLASSICAL_EXPLICIT"
    for rid in ("TR-FUYIN-01", "TR-FANYIN-01", "TR-BINGLIN-01", "TR-TIANKEDI-01"):
        levels = {p["level"] for p in by_id[rid]["provenance"]}
        assert "CLASSICAL_EXPLICIT" not in levels   # 无引文链，不得冒充古籍明文
        assert levels & {"PROJECT_REFERENCE", "ENGINEERING_HEURISTIC"}


def test_suijun_trigger_and_rescue():
    """TR-SS-R09：日主克流年干 → 日犯岁君；救应神可见 → 有救观察。"""
    ta = analyze_temporal(
        natal_stems=["庚", "丙", "甲", "甲"],
        natal_branches=["子", "寅", "戌", "卯"],
        day_master="甲", annual_stem="戊", annual_branch="辰",
    )
    ev = next(t for t in ta.ruleTriggers if t.ruleId == "TR-SS-R09")
    assert ev.matched and ev.refId == "temporal:rule:TR-SS-R09"
    assert any("日犯岁君" in o for o in ev.observations)
    assert any("已见" in o and "庚" in o for o in ev.observations)  # 救神庚辛（制甲者）已见


def test_suijun_no_rescue():
    """救应之神原局大运均未见 → 无救观察。"""
    # 庚日主犯岁君（甲），救神=丙丁：原局与大运均无丙丁 → 无救
    ta = analyze_temporal(
        natal_stems=["庚", "戊", "庚", "庚"],
        natal_branches=["子", "寅", "戌", "辰"],
        day_master="庚", annual_stem="甲", annual_branch="辰",
    )
    ev = next(t for t in ta.ruleTriggers if t.ruleId == "TR-SS-R09")
    assert ev.matched
    assert any("未见" in o for o in ev.observations)


def test_suijun_negative():
    """流年干非日主所克 → 不触发。"""
    ta = analyze_temporal(
        natal_stems=["庚", "丙", "甲", "甲"],
        natal_branches=["子", "寅", "戌", "卯"],
        day_master="甲", annual_stem="壬", annual_branch="申",  # 壬水生甲木，非克
    )
    ev = next(t for t in ta.ruleTriggers if t.ruleId == "TR-SS-R09")
    assert not ev.matched


def test_ren_tou_cai_lu_tou_cai():
    """TR-SS-R10A/B：甲日主 流年己卯（刃头财）/ 甲日主 流年己寅？ 禄头财=甲禄寅+财干。"""
    # 刃头财：甲日主阳刃卯，流年干己（正财）
    ta = analyze_temporal(
        natal_stems=["庚", "丙", "甲", "甲"],
        natal_branches=["子", "寅", "戌", "子"],
        day_master="甲", annual_stem="己", annual_branch="卯",
    )
    a = next(t for t in ta.ruleTriggers if t.ruleId == "TR-SS-R10A")
    assert a.matched and "刃头财" in " ".join(a.observations)
    # 禄头财：甲禄在寅，流年干戊（偏财）
    ta2 = analyze_temporal(
        natal_stems=["庚", "丙", "甲", "甲"],
        natal_branches=["子", "寅", "戌", "子"],
        day_master="甲", annual_stem="戊", annual_branch="寅",
    )
    b = next(t for t in ta2.ruleTriggers if t.ruleId == "TR-SS-R10B")
    assert b.matched and "禄头财" in " ".join(b.observations)


def test_ren_tou_cai_negative():
    """流年支非阳刃或干非财 → 不触发。"""
    ta = analyze_temporal(
        natal_stems=["庚", "丙", "甲", "甲"],
        natal_branches=["子", "寅", "戌", "子"],
        day_master="甲", annual_stem="庚", annual_branch="卯",  # 庚=七杀非财
    )
    a = next(t for t in ta.ruleTriggers if t.ruleId == "TR-SS-R10A")
    assert not a.matched


def test_fuyin_binglin_tiankedi_triggers():
    """结构类规则从 structures 派生，单一检测源。"""
    # 原局：甲子 丙寅 甲戌 庚辰（无 庚午 柱）
    ta = analyze_temporal(
        natal_stems=["甲", "丙", "甲", "庚"],
        natal_branches=["子", "寅", "戌", "辰"],
        day_master="甲", luck_stem="庚", luck_branch="午",
        annual_stem="庚", annual_branch="午",
    )
    kinds = {t.ruleId: t.matched for t in ta.ruleTriggers}
    assert kinds["TR-BINGLIN-01"] is True     # 大运=流年 庚午
    assert kinds["TR-FUYIN-01"] is False      # 原局无 庚午 柱
    assert kinds["TR-FANYIN-01"] is True      # 午 冲 子（年柱）
    # 伏吟：流年 = 原局年柱 甲子
    ta2 = analyze_temporal(
        natal_stems=["甲", "丙", "甲", "庚"],
        natal_branches=["子", "寅", "戌", "午"],
        day_master="甲", annual_stem="甲", annual_branch="子",
    )
    f = next(t for t in ta2.ruleTriggers if t.ruleId == "TR-FUYIN-01")
    assert f.matched


def test_month_branch_never_temporal():
    """TR-DTZ-35/DTZ-09 的月支永远取原局（TemporalContext.month_branch 语义）。"""
    from tianze.analysis.temporal import TemporalContext
    ctx = TemporalContext(natal_stems=["甲", "丙", "甲", "庚"],
                          natal_branches=["子", "辰", "戌", "午"], day_master="甲",
                          luck_stem="壬", luck_branch="子")
    assert ctx.month_branch() == "辰"   # 原局月支，不受岁运影响


def test_missing_evaluator_raises(rules, monkeypatch):
    """JSON 中出现无执行器的规则 → 引擎必须报错（不静默跳过）。"""
    broken = [dict(r) for r in rules] + [
        {"id": "TR-NOPE-99", "domain": "temporal", "category": "x", "label": "x",
         "provenance": []},
    ]
    import tianze.knowledge.temporal_rules as tr
    monkeypatch.setattr(tr, "load_temporal_rules", lambda: broken)
    with pytest.raises(KeyError, match="TR-NOPE-99"):
        evaluate_temporal_rules(
            tr.TemporalContext(natal_stems=["甲", "丙", "甲", "庚"],
                               natal_branches=["子", "寅", "戌", "午"], day_master="甲"),
            [], [],
        )


def test_rule_triggers_in_analyze_temporal():
    """analyze_temporal 输出包含全部规则（未触发 matched=False 保留可审计）。"""
    ta = analyze_temporal(
        natal_stems=["庚", "丙", "甲", "甲"],
        natal_branches=["子", "寅", "戌", "卯"],
        day_master="甲", annual_stem="戊", annual_branch="辰",
    )
    assert len(ta.ruleTriggers) == 10
    blob = ta.model_dump_json(by_alias=True, exclude_none=True)
    # 观察项/结论层不得出现吉凶断语；古籍引文仅允许存在于 provenance 引文注记中
    for t_ in ta.ruleTriggers:
        for banned in ("发财", "大凶", "必有灾", "灾殃"):
            assert banned not in t_.label + " ".join(t_.observations)
    assert "灾殃" in blob  # 原书引文（provenance 注记）保留原貌，属 source 数据
