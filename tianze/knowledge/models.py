"""K0 · 古籍知识库 Schema（Classical Knowledge Integration）。

设计原则（docs/knowledge/01-KNOWLEDGE-ARCHITECTURE.md）：
- 原文 ≠ 评注 ≠ 现代整理 ≠ 开源项目经验 ≠ Tianze 推导——五级来源不可混用；
- 两层规则：RuleCandidate（文献整理出的候选，不保证可执行）与
  ExecutableRule（经规范化/验证/测试后引擎可执行），禁止"看到一句古籍立即变 if"；
- 机器化保留转换痕迹：conditions/effects/normalizationNotes/source 全程携带；
- OCR 错字照录：Quote.rawText 不可变，修订只能写 correctedText + correction 理由；
- 数据质量等级（A/B/C/D）进入运行时 provenance。
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator

from tianze.domain.models import (  # noqa: F401
    CamelizeModel,
    KnowledgeSource,
    ProvenanceRef,
    SourceKind,
)

# KnowledgeSource / SourceKind 定义于 domain.models（核心契约），此处再导出以保持
# knowledge 层单一入口；二者是同一类型（身份相同，schema 校验一致）。


# SourceKind：定义于 domain.models（核心契约），此处经 __init__ 再导出。

class ContentNature(str, Enum):
    """知识库自带的五类内容性质（与 `00-索引与方法论.md` 对齐）。"""

    CLASSICAL_ORIGINAL = "古籍原文"
    XU_COMMENTARY = "徐乐吾对古籍的解释"
    XU_VIEWPOINT = "徐乐吾明确观点"
    COMPILER_NOTE = "整理归纳"
    CASE_RECORD = "书中命例"


class QualityGrade(str, Enum):
    """数据质量等级（K0）：进入运行时 provenance。

    A 古籍原文+明确版本+页码+已人工核对
    B 原文+页码，OCR 未完全人工复核
    C 现代注家/评注/开源项目整理
    D 来源不完整或仅工程经验
    """

    A = "A"
    B = "B"
    C = "C"
    D = "D"


class VerificationStatus(str, Enum):
    """验证状态（M6.1）：机器不得产生 HUMAN_*；只有真人逐条核验后才可升级。"""

    UNREVIEWED = "UNREVIEWED"
    MACHINE_EXTRACTED = "MACHINE_EXTRACTED"      # 程序解析，未整理
    MACHINE_CURATED = "MACHINE_CURATED"          # 程序/AI 整理（含本仓库此前的 curation）
    SOURCE_ALIGNED = "SOURCE_ALIGNED"            # 已与来源文本逐字对齐（尚未判定解释正确性）
    HUMAN_VERIFIED = "HUMAN_VERIFIED"            # 真人逐条核验（verifiedBy 必须为人名）
    HUMAN_VERIFIED_PRIMARY_SOURCE = "HUMAN_VERIFIED_PRIMARY_SOURCE"  # 真人对照一手扫描件核验


class VerificationMethod(str, Enum):
    REGEX_EXTRACTION = "regex_extraction"
    HEURISTIC_DRAFT = "heuristic_draft"
    AI_CURATION = "ai_curation"                  # 本仓库 M6 的 curation 实为此类（诚实降级）
    SOURCE_ALIGNMENT = "source_alignment"
    ENGINE_TEST = "engine_test"
    HUMAN_REVIEW = "human_review"


class VerificationRecord(CamelizeModel):
    """统一验证记录：Quote/RuleCandidate/ExecutableRule/Commentary/CaseReference 通用。"""

    status: VerificationStatus = VerificationStatus.UNREVIEWED
    verified_by: str | None = None       # 机器流程固定 "tianze-pipeline:{tool}"；人工才可为人名
    verified_at: str | None = None
    method: VerificationMethod | None = None
    source_checked: bool = False
    notes: str | None = None

    def model_validate(cls, value):  # noqa: N805（classmethod 语义）
        return super().model_validate(value)

    @model_validator(mode="after")
    def _no_fake_human(self) -> "VerificationRecord":
        if self.status.name.startswith("HUMAN") and self.verified_by and self.verified_by.startswith("tianze-pipeline:"):
            raise ValueError("机器不得伪造人工核验：HUMAN_* 状态要求真人署名")
        return self


class AccuracyMatrix(CamelizeModel):
    """四个独立概念分别建模，禁止混淆（M6.1）。"""

    traceability: Literal["PASS", "FAIL", "UNVERIFIED"] = "UNVERIFIED"      # 能否找到出处
    text_accuracy: Literal["VERIFIED", "OCR_RISK", "UNVERIFIED"] = "UNVERIFIED"  # OCR 与 PDF 是否一致
    interpretation_accuracy: VerificationStatus = VerificationStatus.UNREVIEWED  # 结构化是否准确表达原文
    engine_accuracy: Literal["TESTED", "UNTESTED"] = "UNTESTED"              # 引擎语义是否被测试覆盖


class ConflictKind(str, Enum):
    """冲突分类（M6.1 扩展）：全部可查询，禁止 last-rule-wins。"""

    TEXT_CONFLICT = "TEXT_CONFLICT"
    COMMENTARY_CONFLICT = "COMMENTARY_CONFLICT"
    RULE_CONFLICT = "RULE_CONFLICT"
    CONDITION_OVERLAP = "CONDITION_OVERLAP"
    SCHOOL_DIFFERENCE = "SCHOOL_DIFFERENCE"
    OCR_AMBIGUITY = "OCR_AMBIGUITY"


class CaseIdentity(CamelizeModel):
    """命例同一性键：四柱（有序）+ 姓名/称谓 + 来源书籍。不做文本 hash。"""

    pillars: list[str]                 # [年,月,日,时] 干支
    name: str | None = None
    book: str | None = None



# Schema 版本（M6.1）：字段变更必须走 migration，禁止静默改 JSON 导致旧数据失效
KNOWLEDGE_SCHEMA_VERSION = "1.1.0"     # 1.1.0: +verification/accuracyMatrix；conflicts.json +kind
CASE_SCHEMA_VERSION = "1.0.0"




class Correction(CamelizeModel):
    status: Literal["none", "proposed", "verified"]
    reason: str | None = None


class Quote(CamelizeModel):
    """原文引用：rawText 照录不可变；OCR 修订只写 correctedText + correction。"""

    raw_text: str
    corrected_text: str | None = None
    correction: Correction | None = None

    @property
    def display_text(self) -> str:
        return self.corrected_text or self.raw_text


class Commentary(CamelizeModel):
    """评注/解释层：与原文严格分离。"""

    author: str                        # 如 "徐乐吾" / "孙正治" / "整理者"
    text: str
    source: KnowledgeSource | None = None
    nature: ContentNature = ContentNature.COMPILER_NOTE


class RuleCondition(CamelizeModel):
    """ExecutableRule 条件：field 为命局事实字段名，operator 受限。"""

    field: str                         # dayMaster / monthBranch / hasStem / state ...
    operator: Literal["eq", "ne", "in", "not_in", "exists", "not_exists"]
    value: Any = None


class RuleEffect(CamelizeModel):
    """ExecutableRule 效果：保留具体天干（specificStem），五行是派生。"""

    kind: Literal["needStem", "avoidStem", "note"]
    target_stem: str | None = None     # specificStem 优先
    element: str | None = None         # 派生字段（由 stem 推得，不入原文）
    priority: Literal["primary", "secondary", "tertiary"] | None = None
    condition_note: str | None = None  # 如 "先癸后丁：癸优先，乏癸用丁"
    text: str | None = None            # note 型效果原文


class RuleCandidate(BaseModel):
    """第一层：从文献整理出的规则候选（尚未保证可执行）。"""

    id: str                            # 沿用知识库原始 ID（QBT-甲-01 等，全局唯一）
    book: str                          # QBT/DTZ/SPZY/...（书籍代码）
    source_file: str                   # 来源 md（相对 knowledge/raw）
    title: str | None = None
    topic: str | None = None           # 主题
    core_text: str | None = None       # 核心规则
    applicable_condition: str | None = None  # 适用条件（原文描述）
    observation: str | None = None     # 需要观察
    reasoning: str | None = None       # 推理逻辑
    exceptions: str | None = None      # 例外情况
    original_quote: Quote | None = None      # 原文
    commentaries: list[Commentary] = []      # 评注/解释层
    source: KnowledgeSource
    content_nature: list[ContentNature] = []
    tags: list[str] = []
    quality: QualityGrade = QualityGrade.B
    ocr_risk: bool = False             # 含【OCR识别待核】等标记


class ExecutableRule(CamelizeModel):
    """第二层：经规范化/验证/测试后可由引擎执行的规则。

    id 规范（K0-RuleID）：`{DOMAIN}-{来源ID}`，如 `TH-QBT-甲-01`；
    来源 ID（QBT-甲-01）全局唯一且进入 released 后不可改。
    """

    id: str
    candidate_id: str                  # 指回 RuleCandidate.id（引用完整性受检）
    domain: Literal["tiaohou", "generic"]
    conditions: list[RuleCondition]
    effects: list[RuleEffect]
    exceptions: list[RuleCondition] = []
    modifiers: list[RuleCondition] = []
    normalization_notes: str | None = None  # 机器化过程增加了解释？为什么这样拆？
    conflict_note: str | None = None        # 与其他规则的条件重叠/两说并存说明（不静默覆盖）
    verification: VerificationRecord = VerificationRecord(status=VerificationStatus.MACHINE_EXTRACTED)
    accuracy_matrix: AccuracyMatrix = AccuracyMatrix()
    source: KnowledgeSource
    provenance: list[ProvenanceRef] = []
    quality: QualityGrade = QualityGrade.B
    status: Literal["draft", "active"] = "draft"


class RuleConflict(CamelizeModel):
    """规则冲突：同条件多规则时不静默覆盖——全部保留并登记。"""

    rule_ids: list[str]
    condition_overlap: dict[str, Any]  # 重叠条件（如 {"dayMaster":"甲","monthBranch":"未"}）
    description: str
    resolution: Literal["all-retained", "specific-over-general", "manual"] = "all-retained"


class CaseReference(CamelizeModel):
    """命例：仅作 evaluation/reference，不是 ground truth（K0 纪律）。"""

    case_id: str
    pillars: dict[str, str]            # {"year":"癸未","month":"庚申","day":"癸亥","hour":"己未"}
    source: KnowledgeSource
    quote: str | None = None           # 原书断语（照录）
    related_rules: list[str] = []
    note: str | None = None


class KnowledgeStats(CamelizeModel):
    """K1 统计报告（tools/validate_knowledge.py 输出）。"""

    files: int = 0
    rules_total: int = 0
    quotes_total: int = 0
    commentaries_total: int = 0
    candidates_total: int = 0
    executable_total: int = 0
    classical_explicit_total: int = 0
    project_reference_total: int = 0
    unverified_total: int = 0
    ocr_risk_total: int = 0
    tiaohou_coverage: dict[str, int] = {}   # {"covered": n, "unresolved": m, "total": 120}
    conflicts_total: int = 0
    duplicate_ids: list[str] = []
    missing_source: list[str] = []
