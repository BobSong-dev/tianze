"""M11 · AI Interpretation Layer models and types.

结构：
- InterpretationContext: 从 AnalyzeResult 提取的解释所需最小上下文
- InterpretationResult: 模型返回的结构化解释
- GroundingIssue: 程序化检查发现的幻觉/越界
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from tianze.domain.models import CamelizeModel
from pydantic import BaseModel, ConfigDict


# ---- Schema versions ----
INTERPRETATION_SCHEMA_VERSION = "1.0.0"
PROMPT_VERSION = "1.0.0"


class GroundingIssueType(str, Enum):
    UNKNOWN_EVIDENCE_ID = "UNKNOWN_EVIDENCE_ID"
    UNKNOWN_SOURCE_ID = "UNKNOWN_SOURCE_ID"
    UNSUPPORTED_PATTERN = "UNSUPPORTED_PATTERN"
    UNSUPPORTED_STRENGTH_CLAIM = "UNSUPPORTED_STRENGTH_CLAIM"
    FABRICATED_CLASSICAL_SOURCE = "FABRICATED_CLASSICAL_SOURCE"
    VERIFICATION_MISREPRESENTATION = "VERIFICATION_MISREPRESENTATION"
    UNRESOLVED_ASSERTED = "UNRESOLVED_ASSERTED"


class GroundingIssue(CamelizeModel):
    type: GroundingIssueType
    detail: str
    claimed: str | None = None
    actual: str | None = None


class FactType(str, Enum):
    FACT = "FACT"                    # 原书事实（四柱等）
    DERIVED_FACT = "DERIVED_FACT"    # 派生事实（通根/关系等）
    METHOD_RESULT = "METHOD_RESULT"  # 某分析方法的结论
    CANDIDATE = "CANDIDATE"          # 高阶候选（特殊格局）


class ContextFact(CamelizeModel):
    category: str                    # chart / relation / root / visibility / monthCommand / …
    fact_type: FactType
    statement: str
    key: str                         # 唯一标识 key，供模型引用
    data: dict[str, Any] = {}


class ContextMethodResult(CamelizeModel):
    analyzer_id: str
    method: str
    verdict: str | None = None
    score: float | None = None
    confidence: str | None = None
    agreement: str | None = None
    evidence: list[str] = []
    note: str | None = None


class ContextSource(CamelizeModel):
    source_id: str
    book: str
    chapter: str | None = None
    pages: list[int] = []
    quote: str | None = None
    source_kind: str = "CLASSICAL_TEXT"     # SourceKind.value
    verification_status: str = "MACHINE_CURATED"
    quality: str | None = None
    commentator: str | None = None


class InterpretationContext(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    """从 AnalyzeResult 提取的解释所需最小上下文（不含完整内部 JSON）。"""

    meta: dict[str, Any] = {}
    chart_facts: list[ContextFact] = []
    relations: list[ContextFact] = []
    structure: list[ContextFact] = []
    strength_methods: list[ContextMethodResult] = []
    strength_agreement: str | None = None
    pattern_candidates: list[dict[str, Any]] = []
    pattern_evaluation: dict[str, Any] | None = None
    tiaohou: dict[str, Any] | None = None
    advanced: dict[str, Any] | None = None
    evidence: list[dict[str, Any]] = []
    sources: list[ContextSource] = []
    warnings: list[str] = []
    unresolved: list[str] = []
    disagreements: list[str] = []
    all_rule_ids: list[str] = []


class InterpretationSection(CamelizeModel):
    type: str                         # summary / strength / pattern / tiaohou / advanced / bingyao / tongguan / disagreements / uncertainties
    title: str
    content: str
    evidence_ids: list[str] = []
    source_ids: list[str] = []


class InterpretationResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True, validate_assignment=True)
    summary: str = ""
    sections: list[InterpretationSection] = []
    disagreements: list[str] = []
    uncertainties: list[str] = []
    source_references: list[str] = []
    grounding_issues: list[GroundingIssue] = []
    grounding_passed: bool = True


class InterpretationMetadata(CamelizeModel):
    provider: str
    model: str
    prompt_version: str
    interpretation_schema_version: str
    engine_version: str
    knowledge_schema_version: str
    analysis_schema_version: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
