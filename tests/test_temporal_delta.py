"""M13：完整 Temporal Delta 引擎测试。"""

from __future__ import annotations

import datetime

import pytest

from tianze.domain.models import BirthInfo, Gender
from tianze.pipeline import build_chart
from tianze.analysis.temporal_delta import (
    DeltaKind, compute_temporal_delta, DELTA_SCHEMA_VERSION,
)
from tianze.analysis.temporal import AnalysisSupport


@pytest.fixture(scope="module")
def chart():
    bi = BirthInfo(date=datetime.date(1984, 2, 5), time=datetime.time(10, 30), gender=Gender.MALE)
    return build_chart(bi)


def _kinds(rep, analysis=None):
    return [(i.analysis, i.kind) for i in rep.items
            if analysis is None or i.analysis == analysis]


def test_delta_schema_and_warnings(chart):
    rep = compute_temporal_delta(chart, luck=("甲", "子"), annual=("丙", "午"))
    assert rep.deltaSchemaVersion == DELTA_SCHEMA_VERSION
    assert rep.warnings  # 边界声明
    assert any("不构成任何吉凶" in w for w in rep.warnings)


def test_delta_strength_experimental(chart):
    """旺衰 delta：EXPERIMENTAL 标记 + verdict/score/agreement 比较。"""
    rep = compute_temporal_delta(chart, luck=("丁", "巳"), annual=("丁", "巳"))
    s_items = [i for i in rep.items if i.analysis == "strength"]
    for i in s_items:
        assert i.supportLevel == AnalysisSupport.EXPERIMENTAL
        assert i.refId and i.refId.startswith("temporal:strength:")
        assert i.trigger  # 触发来源非空


def test_delta_pattern_month_command_untouched(chart):
    """格局候选不随岁运变：必须出现 unsupported 说明；pattern 项为 SUPPORTED。"""
    rep = compute_temporal_delta(chart, annual=("庚", "申"))
    assert any("月令" in n for n in rep.unsupportedNotes)
    p_items = [i for i in rep.items if i.analysis == "pattern"]
    for i in p_items:
        assert i.supportLevel == AnalysisSupport.SUPPORTED
        assert i.refId.startswith("temporal:pattern:")


def test_delta_tiaohou_arrival(chart):
    """调候用神岁运到位 → UNBLOCKED/STRENGTHENED 事件，refId 确定性。"""
    rep = compute_temporal_delta(chart, annual=("丙", "午"))
    t_items = [i for i in rep.items if i.analysis == "tiaohou"]
    # 1984-02-05 己土生寅月：调候用神为 丙/癸/甲 类；丙 到位或重见必有事件
    assert t_items, "调候 delta 不应为空"
    for i in t_items:
        assert i.kind in (DeltaKind.UNBLOCKED, DeltaKind.STRENGTHENED)
        assert i.refId.startswith("temporal:tiaohou:")
        assert i.supportLevel == AnalysisSupport.SUPPORTED


def test_delta_candidate_blocked_not_confirmed(chart):
    """从格候选状态迁移只能是 CANDIDATE/LIKELY/BLOCKED 等级变化，绝无 CONFIRMED。"""
    rep = compute_temporal_delta(chart, luck=("辛", "酉"), annual=("辛", "酉"),
                                 monthly=("辛", "酉"))
    s_items = [i for i in rep.items if i.analysis == "special"]
    for i in s_items:
        assert i.supportLevel == AnalysisSupport.EXPERIMENTAL
        for v in (i.natalValue, i.temporalValue):
            if isinstance(v, str) and v in ("CONFIRMED",):
                pytest.fail("特殊格局不得输出 CONFIRMED")


def test_delta_tengod_additive_only(chart):
    """十神主题只增不减：不允许 WEAKENED/REMOVED。"""
    rep = compute_temporal_delta(chart, luck=("甲", "子"), annual=("庚", "午"))
    g_items = [i for i in rep.items if i.analysis == "tenGodTheme"]
    for i in g_items:
        assert i.kind in (DeltaKind.ADDED, DeltaKind.STRENGTHENED)


def test_delta_no_layers_empty(chart):
    """无岁运 → 无 items，不出空壳结论。"""
    rep = compute_temporal_delta(chart)
    assert rep.items == []


def test_delta_refids_deterministic(chart):
    """相同输入 → 相同 refId 集合（确定性）。"""
    r1 = compute_temporal_delta(chart, annual=("丙", "午"))
    r2 = compute_temporal_delta(chart, annual=("丙", "午"))
    ids1 = sorted(i.refId for i in r1.items if i.refId)
    ids2 = sorted(i.refId for i in r2.items if i.refId)
    assert ids1 == ids2


def test_delta_no_fortune_language(chart):
    rep = compute_temporal_delta(chart, luck=("甲", "子"), annual=("丙", "午"))
    blob = rep.model_dump_json()
    for banned in ("发财", "大凶", "必有灾", "升职", "结婚", "离婚", "横死"):
        assert banned not in blob


def test_delta_monthly_daily_layers(chart):
    """流月/流日层参与 delta：trigger 与证据标注流月/流日。"""
    rep = compute_temporal_delta(chart, monthly=("庚", "寅"), daily=("乙", "卯"))
    assert rep.context.monthly_stem == "庚" and rep.context.daily_branch == "卯"
    # 至少月/日层出现在 trigger 文本中
    if rep.items:
        assert any("流月" in (i.trigger or "") or "流日" in (i.trigger or "") for i in rep.items)


def test_delta_temporal_relations_monthly_source():
    """流月支与原局支的冲合带 monthly 来源。"""
    from tianze.analysis.temporal import analyze_temporal
    r = analyze_temporal(
        natal_stems=["癸", "庚", "癸", "己"],
        natal_branches=["未", "申", "亥", "未"],
        day_master="癸",
        monthly_stem="丁", monthly_branch="巳",
    )
    assert r.context.monthly_stem == "丁"
    srcs = [s.value for rel in r.relations for s in rel.sources]
    assert "monthly" in srcs


def test_delta_three_harmony_completed_by_monthly():
    """流月补齐三合：原局 2 支 + 流月第 3 支。"""
    from tianze.analysis.temporal import analyze_temporal
    r = analyze_temporal(
        natal_stems=["甲", "丙", "戊", "庚"],
        natal_branches=["子", "辰", "午", "卯"],
        day_master="戊",
        monthly_stem="甲", monthly_branch="申",   # 申子辰三合补申
    )
    completed = [rel for rel in r.relations if rel.kind == "three_harmony_completed"]
    assert completed, "流月申应补齐申子辰"
    assert any("monthly" in c.positions for c in completed) and any("流月" in (c.note or "") for c in completed)
