"""M7 · 命例数据模型（CaseReference 体系）。

三层数据严格分离：
- CaseFact          四柱/性别/出生原文（原书明确记载的命例事实）
- AuthorInterpretation  作者判断（AUTHOR_INTERPRETATION，如"此造官印相生"）
- HistoricalClaim   人生事件（HISTORICAL_CLAIM，如"某年登科"——不是已验证真事）

sourceAnalysis（原书分析）与 tianzeAnalysis（引擎分析）永久分离；
命例用途 = reference / rule usage study / cross-check / regression candidate，
**不是监督学习标签**。Schema 版本 CASE_SCHEMA_VERSION=1.0.0。
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from tianze.domain.models import CamelizeModel, KnowledgeSource
from tianze.knowledge.models import (
    CASE_SCHEMA_VERSION,
    CaseIdentity,
    QualityGrade,
    VerificationRecord,
    VerificationStatus,
)

__all__ = [
    "CASE_SCHEMA_VERSION", "AnalysisClaimType", "RuleCaseRelation", "CaseStatement",
    "CaseFact", "SourceAnalysis", "TianzeAnalysis", "CaseComparison", "CaseReference",
]


class AnalysisClaimType(str, Enum):
    AUTHOR_INTERPRETATION = "AUTHOR_INTERPRETATION"   # 作者判断
    HISTORICAL_CLAIM = "HISTORICAL_CLAIM"             # 人生事件记载（非已验证真事）
    COMPILER_NOTE = "COMPILER_NOTE"                   # 整理者说明


class RuleCaseRelation(str, Enum):
    """Rule↔Case 关系三态：不可把 ENGINE_TRIGGERED 冒充"古人明确用了这条规则"。"""

    EXPLICITLY_CITED = "EXPLICITLY_CITED"   # 命例块"涉及规则"明确引用
    INFERRED_MATCH = "INFERRED_MATCH"       # 由四柱结构推断相关（非原书引用）
    ENGINE_TRIGGERED = "ENGINE_TRIGGERED"   # Tianze 引擎对该四柱触发


class CaseStatement(CamelizeModel):
    """命例中的一句话，带分层标记。"""

    text: str
    claim_type: AnalysisClaimType
    speaker: str | None = None          # 徐乐吾 / 原书 / 整理者


class CaseFact(CamelizeModel):
    pillars: dict[str, str]             # {"year":"癸未",...}；OCR 照录
    gender: Literal["male", "female", "unknown"] | None = None
    birth_text: str | None = None       # 原文生时记载（如"光绪十六年正月二十三日寅时"）
    name: str | None = None             # 姓名/称谓（无名氏/孝廉等）
    unresolved: bool = False            # 四柱 OCR 不确定/无法解析 → UNRESOLVED


class SourceAnalysis(CamelizeModel):
    """原书/作者分析层（永远不与引擎输出混合）。"""

    verdict: str | None = None          # 作者最终判断（照录）
    steps: list[CaseStatement] = []     # 分析步骤/断语（分层标记）
    events: list[CaseStatement] = []    # 实际事件（全部 HISTORICAL_CLAIM）
    purpose: str | None = None          # 该命例主要用于说明
    dayun: str | None = None            # 大运/流年原文（照录）


class TianzeAnalysis(CamelizeModel):
    """Tianze 引擎对该命例四柱的分析（可重算、与原书无关）。"""

    computed: bool = False
    strength_verdicts: dict[str, str | None] = {}   # 方法名 → verdict
    pattern_candidate: str | None = None
    pattern_status: str | None = None
    tiaohou_targets: list[str] = []                 # primary/secondary 目标干
    tiaohou_primary_present: bool | None = None
    engine_rule_ids: list[str] = []                 # ENGINE_TRIGGERED 的规则
    note: str | None = None


class CaseComparison(CamelizeModel):
    """对比：只记录差异与一致，不裁决谁对。"""

    case_id: str
    source_claims: list[str] = []
    engine_results: list[str] = []
    agreements: list[str] = []
    differences: list[str] = []
    unresolved: list[str] = []


class CaseReference(CamelizeModel):
    case_id: str
    source: KnowledgeSource
    fact: CaseFact
    source_analysis: SourceAnalysis
    tianze_analysis: TianzeAnalysis = TianzeAnalysis()
    rule_references: list[dict] = []    # [{ruleId, relation: RuleCaseRelation}]
    identity: CaseIdentity | None = None
    possible_duplicates: list[str] = []  # 不自动合并，只登记候选重复
    verification: VerificationRecord = VerificationRecord(status=VerificationStatus.MACHINE_EXTRACTED)
    quality: QualityGrade = QualityGrade.B
    raw_block_id: str | None = None     # 源文件中的原始块 ID（QBTM-甲-01 等）
    source_file: str | None = None
