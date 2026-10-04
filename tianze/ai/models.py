"""M11 · AI Interpretation Layer models and types.

M11 产品闭环新增：
- ClaimType / Claim / Structured Claim Reference
- GroundingSeverity（WARNING/ERROR/FATAL）
- InterpretationSection.claims
- InterpretationMetadata.attempt_count
- ContextBuilder 输出 claim_refs（模型只能引用提供的 refId）
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from tianze.domain.models import CamelizeModel
from pydantic import BaseModel, ConfigDict

# ---- Schema versions ----
INTERPRETATION_SCHEMA_VERSION = "1.1.0"  # 1.1.0: +claims +severity +attemptCount
PROMPT_VERSION = "1.1.0"                  # 1.1.0: +claim refs +data isolation


class ClaimType(str, Enum):
    FACT = "FACT"
    STRENGTH = "STRENGTH"
    PATTERN = "PATTERN"
    TIAOHOU = "TIAOHOU"
    SPECIAL_PATTERN = "SPECIAL_PATTERN"
    TRANSFORMATION = "TRANSFORMATION"
    BINGYAO = "BINGYAO"
    TONGGUAN = "TONGGUAN"
    SOURCE = "SOURCE"
    VERIFICATION = "VERIFICATION"


class GroundingSeverity(str, Enum):
    WARNING = "WARNING"   # 缺少可选引用
    ERROR = "ERROR"       # 引用不存在的 ID
    FATAL = "FATAL"       # 发明格局/古籍 / UNRESOLVED→确定 / MACHINE→人工


class GroundingIssueType(str, Enum):
    UNKNOWN_EVIDENCE_ID = "UNKNOWN_EVIDENCE_ID"
    UNKNOWN_SOURCE_ID = "UNKNOWN_SOURCE_ID"
    UNSUPPORTED_PATTERN = "UNSUPPORTED_PATTERN"
    UNSUPPORTED_STRENGTH_CLAIM = "UNSUPPORTED_STRENGTH_CLAIM"
    FABRICATED_CLASSICAL_SOURCE = "FABRICATED_CLASSICAL_SOURCE"
    VERIFICATION_MISREPRESENTATION = "VERIFICATION_MISREPRESENTATION"
    UNRESOLVED_ASSERTED = "UNRESOLVED_ASSERTED"
    UNKNOWN_CLAIM_REF = "UNKNOWN_CLAIM_REF"
    STRENGTH_MISMATCH = "STRENGTH_MISMATCH"
    TIAOHOU_STEM_MISMATCH = "TIAOHOU_STEM_MISMATCH"
    CONG_TYPE_MISMATCH = "CONG_TYPE_MISMATCH"
    ZHUANWANG_TYPE_MISMATCH = "ZHUANWANG_TYPE_MISMATCH"
    TRANSFORMATION_MISMATCH = "TRANSFORMATION_MISMATCH"


class GroundingIssue(CamelizeModel):
    type: GroundingIssueType
    severity: GroundingSeverity = GroundingSeverity.ERROR
    detail: str
    claimed: str | None = None
    actual: str | None = None


class Claim(CamelizeModel):
    """AI section 内的结构化引用。"""

    type: ClaimType
    ref_id: str
    value: str | None = None


class FactType(str, Enum):
    FACT = "FACT"
    DERIVED_FACT = "DERIVED_FACT"
    METHOD_RESULT = "METHOD_RESULT"
    CANDIDATE = "CANDIDATE"


class ContextFact(CamelizeModel):
    category: str
    fact_type: FactType
    statement: str
    key: str
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
    source_kind: str = "CLASSICAL_TEXT"
    verification_status: str = "MACHINE_CURATED"
    quality: str | None = None
    commentator: str | None = None


class InterpretationContext(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    """从 AnalyzeResult 提取的解释所需最小上下文。"""

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
    claim_refs: list[str] = []  # 模型可引用的全部 refId（deterministic 生成）


class InterpretationSection(BaseModel):
    model_config = ConfigDict(populate_by_name=True, validate_assignment=True)
    type: str
    title: str
    content: str
    claims: list[Claim] = []
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
    grounding_fatal: bool = False


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
    attempt_count: int = 1
