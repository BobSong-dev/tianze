"""M13 · TemporalCaseReference：原书岁运信息的三层分离 Schema。

对齐 CASE_SCHEMA 的分层纪律（M7）：
    sourceTemporalAnalysis  —— 原书/原文提到的大运、流年、流月与岁运分析（OCR 可能有噪声）
    tianzeTemporalAnalysis  —— Tianze 引擎对同一命例的岁运计算结果（独立，绝不覆盖前者）
    historicalClaims        —— 原书历史断言（升学/死亡/就任……），只是 claim，不是 truth

原则：
- 历史事件不是 truth；本 Schema 只做"记录 + 干支一致性校验 + 引擎对账"，不评判吉凶
- 大运干支校验 = 序列内部一致性（相邻运干支指数 +1 mod 60、年龄差 +10），
  不依赖出生时间（命例多缺性别/真太阳时，无法重算起运）
- 不为了迎合古籍案例调整引擎规则（引擎差异如实记录为 mismatch）
"""

from __future__ import annotations

from typing import Literal

from tianze.domain.models import CamelizeModel

__all__ = [
    "SourceDayunEntry", "TemporalMention", "SourceTemporalAnalysis",
    "TianzeTemporalAnalysis", "HistoricalClaim", "TemporalCaseReference",
    "TEMPORAL_CASE_SCHEMA_VERSION",
]

TEMPORAL_CASE_SCHEMA_VERSION = "1.0.0"


class SourceDayunEntry(CamelizeModel):
    """原书大运序列中的一项（age 为原书标注起运岁数）。"""
    age: int | None = None
    gan_zhi: str
    raw_text: str                    # 原文片段（可回查）


class TemporalMention(CamelizeModel):
    """原书分析文本中对岁运的显式提及。"""
    kind: Literal["luck", "annual", "monthly", "suijun", "taisui", "generic"]
    gan_zhi: str | None = None       # 完整干支（两字）
    partial_gz: str | None = None    # 单干/单支提及（如「午运」「已运」OCR 噪声）
    raw_text: str                    # 命中片段
    context: str                     # 所在句子（截断）
    claim_type: Literal["AUTHOR_INTERPRETATION", "HISTORICAL_CLAIM", "COMPILER_NOTE"]


class SourceTemporalAnalysis(CamelizeModel):
    """第一层：原书岁运分析（原样保留，含噪声）。"""
    dayun: list[SourceDayunEntry] = []
    unparsed_dayun_text: str | None = None   # 未能结构化的大运字段原文（诚实保留）
    dayun_sequence_consistent: bool | None = None  # 相邻运干支同向 ±1、年龄差 +10 的内部一致性
    dayun_direction: Literal["forward", "backward"] | None = None  # 顺行/逆行（原书序列方向）
    mentions: list[TemporalMention] = []


class TianzeTemporalAnalysis(CamelizeModel):
    """第二层：Tianze 引擎对同一命例的岁运计算（独立分析，缺输入时显式 not_computed）。"""
    computed: bool = False
    not_computed_reason: str | None = None   # 如 "命例缺出生日期/性别，无法重算起运"
    dayun: list[dict] = []                   # Tianze DaYunEntry dict（可计算时）
    comparison_note: str | None = None


class HistoricalClaim(CamelizeModel):
    """第三层：原书历史断言——只是 claim，不是 truth。"""
    text: str
    claim_type: Literal["AUTHOR_INTERPRETATION", "HISTORICAL_CLAIM", "COMPILER_NOTE"] = "HISTORICAL_CLAIM"
    temporal_gz: str | None = None   # 与该 claim 关联的岁运干支（可空）


class TemporalCaseReference(CamelizeModel):
    """单命例的 TemporalCaseReference。"""
    case_id: str
    book: str
    schema_version: str = TEMPORAL_CASE_SCHEMA_VERSION
    source_temporal: SourceTemporalAnalysis
    tianze_temporal: TianzeTemporalAnalysis
    historical_claims: list[HistoricalClaim] = []
    notes: str | None = None
