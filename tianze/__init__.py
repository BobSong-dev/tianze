"""Tianze 天泽 —— 可验证、可溯源的四柱八字结构化分析引擎。"""

__version__ = "0.2.0"
ENGINE_STAGE = "M4"  # 里程碑标记：M3 结构事实 / M4 旺衰框架（dimension） / M5 格局

from tianze.sdk import (  # noqa: F401
    analyze, AnalysisOptions, SimplifiedBirthInfo, TianzeError,
    InvalidBirthInfo, UnsupportedConvention, KnowledgeDataError, AnalysisUnavailable,
)
