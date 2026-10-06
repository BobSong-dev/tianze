"""M11 AI 层测试：InterpretationContext / PromptBuilder / Grounding Validator / Mock Provider。"""

from __future__ import annotations

import asyncio
import json

import pytest

from tianze.ai import (
    MockInterpretationProvider,
    build_interpretation_context,
    interpret,
    validate_grounding,
)
from tianze.ai.context_builder import build_interpretation_context as _bic
from tianze.ai.models import (
    GroundingIssueType,
    InterpretationContext,
    InterpretationResult,
    InterpretationSection,
    ContextSource,
    ContextFact,
    ContextMethodResult,
    FactType,
)
from tianze.ai.prompt_builder import build_prompts
from tianze.sdk import AnalysisOptions, SimplifiedBirthInfo, analyze
from tianze.ai.models import INTERPRETATION_SCHEMA_VERSION, PROMPT_VERSION
from tianze.ai.models import INTERPRETATION_SCHEMA_VERSION, PROMPT_VERSION


def _make_result(**kw) -> dict:
    r = analyze(SimplifiedBirthInfo(date="2003-08-18", time="14:30", gender="male"))
    return r.model_dump()


def _make_ctx(**kw) -> InterpretationContext:
    return build_interpretation_context(_make_result(), **kw)


# ---- Context Builder ----

def test_context_builder_chart_facts():
    ctx = _make_ctx()
    assert len(ctx.chart_facts) >= 5  # dayMaster + 4 pillars
    assert any(f.fact_type == FactType.FACT for f in ctx.chart_facts)
    dm = next(f for f in ctx.chart_facts if f.key == "dayMaster")
    assert "癸" in dm.statement


def test_context_builder_strength_methods():
    ctx = _make_ctx()
    assert len(ctx.strength_methods) == 3
    methods = {m.method for m in ctx.strength_methods}
    assert methods == {"dimension", "weighted", "fuyi"}
    # dimension has no verdict (qualitative)
    dim = next(m for m in ctx.strength_methods if m.method == "dimension")
    assert dim.verdict is None


def test_context_builder_pattern():
    ctx = _make_ctx()
    assert len(ctx.pattern_candidates) >= 1
    assert ctx.pattern_candidates[0].get("name")  # 正印格 for 2003 example


def test_context_builder_tiaohou_sources():
    ctx = _make_ctx()
    assert ctx.tiaohou is not None and ctx.tiaohou.get("recommendations")
    assert len(ctx.sources) >= 1
    for s in ctx.sources:
        assert s.book  # 书名非空
        assert s.verification_status == "MACHINE_CURATED"


def test_context_builder_preserves_fact_vs_method_distinction():
    """事实和方法结论分层。"""
    ctx = _make_ctx()
    assert all(f.fact_type == FactType.FACT for f in ctx.chart_facts)
    assert all(f.fact_type == FactType.DERIVED_FACT for f in ctx.relations)
    assert len(ctx.strength_methods) > 0  # 方法结论单独建模


# ---- Prompt Builder ----

def test_prompt_builder_contains_key_sections():
    ctx = _make_ctx()
    sys_p, user_p = build_prompts(ctx)
    assert "不得自行排四柱" in sys_p
    assert "UNRESOLVED" in sys_p or "不确定" in sys_p
    assert "FACTS" in user_p
    assert "ANALYSIS" in user_p
    assert "untrusted-reference-data" in user_p  # source data isolation
    assert "癸" in user_p  # 日主事实出现


def test_prompt_builder_mentions_agreement():
    ctx = _make_ctx()
    sys_p, user_p = build_prompts(ctx)
    assert "分歧" in sys_p or "DISPUTED" in sys_p


# ---- Grounding Validator ----

def test_grounding_pass_clean_result():
    ctx = _make_ctx()
    result = InterpretationResult(
        summary="测试",
        sections=[InterpretationSection(type="strength", title="旺衰", content="多方法分析。")],
    )
    issues = validate_grounding(result, ctx)
    assert issues == []


def test_grounding_detects_unknown_source():
    ctx = _make_ctx()
    result = InterpretationResult(
        summary="",
        sections=[InterpretationSection(type="tiaohou", title="调候", content="参考《三命通会》。",
                                        source_ids=["nonexistent"])]
    )
    issues = validate_grounding(result, ctx)
    assert any(i.type == GroundingIssueType.FABRICATED_CLASSICAL_SOURCE for i in issues)
    assert any(i.type == GroundingIssueType.UNKNOWN_SOURCE_ID for i in issues)


def test_grounding_detects_wrong_pattern():
    ctx = _make_ctx()
    result = InterpretationResult(
        summary="",
        sections=[InterpretationSection(type="pattern", title="格局",
                                        content="此命为正官格。")]  # 正印格才是候选
    )
    issues = validate_grounding(result, ctx)
    assert any(i.type == GroundingIssueType.UNSUPPORTED_PATTERN for i in issues)


def test_grounding_detects_verification_misrepresentation():
    ctx = _make_ctx()
    result = InterpretationResult(
        summary="",
        sections=[InterpretationSection(type="tiaohou", title="调候",
                                        content="此规则经过专家核验。")]
    )
    issues = validate_grounding(result, ctx)
    assert any(i.type == GroundingIssueType.VERIFICATION_MISREPRESENTATION for i in issues)


def test_grounding_detects_unresolved_asserted():
    ctx = _make_ctx()
    ctx.unresolved = ["化气 [甲己] 证据不足"]
    result = InterpretationResult(
        summary="",
        sections=[InterpretationSection(type="advanced", title="化气",
                                        content="化气确定为土。")]
    )
    issues = validate_grounding(result, ctx)
    assert any(i.type == GroundingIssueType.UNRESOLVED_ASSERTED for i in issues)


# ---- Mock Provider End-to-End ----

def test_mock_provider_interpret_passes_grounding():
    ctx = _make_ctx(engine_version="0.2.0")
    result, meta = asyncio.run(interpret(ctx, MockInterpretationProvider()))
    assert result.grounding_passed
    assert meta.provider == "mock"
    assert meta.prompt_version


def test_mock_provider_e2e():
    ctx = _make_ctx()
    result, meta = asyncio.run(interpret(ctx, MockInterpretationProvider(), engine_version="test"))
    assert meta.interpretation_schema_version == INTERPRETATION_SCHEMA_VERSION
    assert meta.prompt_version == PROMPT_VERSION
    assert result.summary  # 非空


import asyncio  # noqa: E402


# ---- M13 Temporal AI ----

def _make_temporal_result() -> dict:
    r = analyze(
        SimplifiedBirthInfo(date="2003-08-18", time="14:30", gender="male"),
        AnalysisOptions(include_temporal=True, target_year=2026, include_temporal_delta=True),
    )
    return r.model_dump()


def test_context_builder_temporal():
    ctx = build_interpretation_context(_make_temporal_result())
    assert ctx.temporal is not None
    assert "大运" in ctx.temporal["chain"] and "流年" in ctx.temporal["chain"]
    assert any(t["ruleId"] == "TR-SPZY-28" for t in ctx.temporal["matchedRules"])
    temporal_refs = [r for r in ctx.claim_refs if r.startswith("temporal:")]
    assert temporal_refs, "必须有 temporal claim refs"
    assert "temporal:rule:TR-SPZY-28" in ctx.claim_refs


def test_prompt_contains_temporal_section():
    ctx = build_interpretation_context(_make_temporal_result())
    system_prompt, user_prompt = build_prompts(ctx)
    assert "## TEMPORAL" in user_prompt
    assert "岁运链" in user_prompt
    assert "不得输出任何具体人生事件预测" in system_prompt
    assert "EXPERIMENTAL" in system_prompt


def test_prompt_no_temporal_section_without_temporal():
    ctx = build_interpretation_context(_make_result())
    _, user_prompt = build_prompts(ctx)
    assert "## TEMPORAL" not in user_prompt


def test_grounding_temporal_prediction_blocked():
    """岁运 section 出现具体事件预测语言 → TEMPORAL_PREDICTION issue。"""
    ctx = build_interpretation_context(_make_temporal_result())
    result = InterpretationResult(
        summary="岁运概要",
        sections=[InterpretationSection(
            type="temporal", title="岁运", content="此大运中您一定会发财，事业必定腾飞。",
            claims=[],
        )],
    )
    issues = validate_grounding(result, ctx)
    assert any(i.type == GroundingIssueType.TEMPORAL_PREDICTION for i in issues)


def test_grounding_temporal_structural_passes():
    """结构化岁运描述（含 EXPERIMENTAL 说明）不触发 TEMPORAL_PREDICTION。"""
    ctx = build_interpretation_context(_make_temporal_result())
    result = InterpretationResult(
        summary="岁运概要",
        sections=[InterpretationSection(
            type="temporal", title="岁运",
            content="流年丙午与原局形成天干关系（TR-SPZY-28 流年即太岁，术语框架）。"
                    "Delta 中旺衰加权条目标记为 EXPERIMENTAL，说明岁运参与计分存在流派分歧，"
                    "本描述仅为结构状态迁移。",
            claims=[],
        )],
    )
    issues = validate_grounding(result, ctx)
    temporal_issues = [i for i in issues if i.type == GroundingIssueType.TEMPORAL_PREDICTION]
    assert not temporal_issues


# ---- M14 Event Theme AI ----

def _make_event_result() -> dict:
    r = analyze(
        SimplifiedBirthInfo(date="1984-02-05", time="10:30", gender="male"),
        AnalysisOptions(include_temporal=True, target_year=2026,
                        include_temporal_delta=True, include_event_themes=True),
    )
    return r.model_dump()


def test_context_builder_event_themes():
    ctx = build_interpretation_context(_make_event_result())
    assert ctx.event_themes is not None
    assert ctx.event_themes["themes"], "1984 盘 + 岁运应有事件主题"
    event_refs = [r for r in ctx.claim_refs if r.startswith("event:")]
    assert event_refs
    assert any(r.startswith("event:rule:EV-") for r in event_refs)


def test_prompt_contains_event_themes():
    ctx = build_interpretation_context(_make_event_result())
    system_prompt, user_prompt = build_prompts(ctx)
    assert "## EVENT THEMES" in user_prompt
    assert "禁止写成概率" in system_prompt


def test_grounding_event_prediction_blocked():
    ctx = build_interpretation_context(_make_event_result())
    result = InterpretationResult(
        summary="事件主题",
        sections=[InterpretationSection(
            type="event_themes", title="事件主题",
            content="此年您一定会发财，结婚概率为 80%。",
            claims=[],
        )],
    )
    issues = validate_grounding(result, ctx)
    assert any(i.type == GroundingIssueType.EVENT_PREDICTION for i in issues)


def test_grounding_event_structural_passes():
    ctx = build_interpretation_context(_make_event_result())
    result = InterpretationResult(
        summary="事件主题",
        sections=[InterpretationSection(
            type="event_themes", title="事件主题",
            content="事业主题为 DISPUTED：官星透出支持，伤官见官反对，两说并存不做裁决。"
                    "confidence 为透明加权值（非概率）。",
            claims=[],
        )],
    )
    issues = validate_grounding(result, ctx)
    assert not [i for i in issues if i.type == GroundingIssueType.EVENT_PREDICTION]
