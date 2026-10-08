"""Tianze 天泽 —— 可验证、可溯源的四柱八字结构化分析引擎。"""

__version__ = "0.4.0.dev0"  # 开发线；已发布的 v0.3.0 tag 固定指向 5821c84，不随 HEAD 移动
ENGINE_STAGE = "M4"  # 里程碑标记：M3 结构事实 / M4 旺衰框架（dimension） / M5 格局

from tianze.sdk import (  # noqa: F401
    analyze, AnalysisOptions, SimplifiedBirthInfo, TianzeError,
    InvalidBirthInfo, UnsupportedConvention, KnowledgeDataError, AnalysisUnavailable,
)
