"""M9 · Tianze 稳定 SDK / Facade。

公开 API：
    >>> from tianze import analyze
    >>> result = analyze(BirthInfo(date=..., time=...), AnalysisOptions())

- Facade 不复制分析逻辑——纯委托给 pipeline 内部引擎。
- AnalyzeResult 输出统一 camelCase JSON。
- Partial Result：未知时辰不会导致整个 analyze() 失败。
- Deterministic：同输入 + 同版本 → 同输出。
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, model_validator
from pydantic.alias_generators import to_camel

from tianze.domain.models import CamelizeModel

__all__ = [
    "TianzeError", "InvalidBirthInfo", "AnalysisOptions", "SimplifiedBirthInfo",
    "AnalyzeResult", "AnalysisSchemaVersion", "analyze",
]


class AnalysisSchemaVersion(str, Enum):
    """ANALYSIS_SCHEMA_VERSION=1.0.0：外部稳定 Schema 改动必须 version bump。"""
    V1 = "1.0.0"


# ---- 错误模型 ----

class TianzeError(Exception):
    """Tianze 统一错误基类。"""

    def __init__(self, code: str, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code}] {message}")


class InvalidBirthInfo(TianzeError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__("INVALID_BIRTH_INFO", message, details)


class UnsupportedConvention(TianzeError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__("UNSUPPORTED_CONVENTION", message, details)


class KnowledgeDataError(TianzeError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__("KNOWLEDGE_DATA_ERROR", message, details)


class AnalysisUnavailable(TianzeError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__("ANALYSIS_UNAVAILABLE", message, details)


# ---- 输入模型 ----

class SimplifiedBirthInfo(BaseModel):
    """SDK 输入：简化版 BirthInfo（内部自动转换为完整 BirthInfo）。"""

    model_config = ConfigDict(populate_by_name=True, extra="forbid", alias_generator=to_camel)

    date: str                                    # "2003-08-18"
    time: Optional[str] = None                   # "14:30"；None=未知时辰
    gender: Optional[Literal["male", "female"]] = None
    timezone_offset: float = 8.0                 # 标准时区偏移（东八区=8）
    longitude: Optional[float] = None
    sect: Literal[1, 2] = 2                      # R1 晚子时流派
    time_alg: Literal["clock", "true_solar", "mean_solar"] = "clock"  # R2
    place: Optional[str] = None                  # 地名（展示用）

    @model_validator(mode="after")
    def _validate_date(self) -> "SimplifiedBirthInfo":
        import datetime
        try:
            datetime.date.fromisoformat(self.date)
        except ValueError:
            raise InvalidBirthInfo(f"日期格式无效: {self.date!r}") from None
        if self.time:
            try:
                parts = self.time.split(":")
                h, m = int(parts[0]), int(parts[1])
                if not (0 <= h < 24 and 0 <= m < 60):
                    raise ValueError
            except (ValueError, IndexError):
                raise InvalidBirthInfo(f"时间格式无效: {self.time!r}") from None
        return self


class AnalysisOptions(BaseModel):
    """分析选项：只暴露已实现的功能。"""

    model_config = ConfigDict(populate_by_name=True, extra="forbid", alias_generator=to_camel)

    include_strength: bool = True
    include_pattern: bool = True
    include_tiaohou: bool = True
    include_special_patterns: bool = True
    include_relations: bool = True
    include_element_counts: bool = True
    strength_methods: list[Literal["dimension", "weighted", "fuyi"]] = ["dimension", "weighted", "fuyi"]
    include_temporal: bool = False
    target_luck_index: int | None = None
    target_year: int | None = None
    target_month: int | None = None       # M13：流月序（1=寅月，节气窗口）
    target_day: str | None = None         # M13：流日（"YYYY-MM-DD"，公历）
    include_temporal_delta: bool = False  # M13：完整 Temporal Delta（strength/pattern/tiaohou/special/...）
    include_event_themes: bool = False    # M14：事件主题候选（career/wealth/...，非事件预测）
    include_explanations: bool = False    # M17：全链路解释链（theme → rule → rescue → source）


# ---- 输出模型 ----

class AnalysisMeta(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    engine_version: str
    engine_stage: str
    knowledge_schema_version: str
    case_schema_version: str
    analysis_schema_version: str
    lunar_python_version: str


class SimplifiedResult(BaseModel):
    """AnalyzeResult 的精简形态（非完整内部对象——由 facade 裁剪）。"""

    model_config = ConfigDict(populate_by_name=True)

    meta: dict
    pillars: dict
    dayMaster: dict
    relations: list = []
    blockedRelations: list = []
    roots: list = []
    visibility: list = []
    monthCommand: dict | None = None
    elementCounts: dict | None = None
    strength: dict | None = None
    pattern: dict | None = None
    tiaohou: dict | None = None
    advancedAnalysis: dict | None = None
    specialPoints: dict | None = None
    luck: dict | None = None
    conventions: dict = {}
    warnings: list[str] = []
    fallbacks: list[str] = []
    missingCapabilities: list[str] = []
    temporal: dict | None = None


# ---- Facade ----

def analyze(
    birth_info: SimplifiedBirthInfo | dict,
    options: AnalysisOptions | None = None,
) -> SimplifiedResult:
    """Tianze 稳定分析入口。

    Parameters
    ----------
    birth_info : SimplifiedBirthInfo or dict
        出生信息（JSON dict 自动校验转换）。
    options : AnalysisOptions, optional
        分析开关（默认全部开启）。

    Returns
    -------
    SimplifiedResult
        稳定输出（camelCase JSON，含 meta 版本信息）。

    Raises
    ------
    InvalidBirthInfo
        出生信息格式错误。
    AnalysisUnavailable
        引擎内部错误（不太可能，但以防万一）。

    Examples
    --------
    >>> from tianze import analyze, SimplifiedBirthInfo
    >>> result = analyze(SimplifiedBirthInfo(date="2003-08-18", time="14:30", gender="male"))
    >>> result.pillars["day"]["stem"]
    '癸'
    """
    import datetime as dt

    from tianze import __version__
    from tianze.knowledge.models import CASE_SCHEMA_VERSION, KNOWLEDGE_SCHEMA_VERSION
    from importlib.metadata import version as _v

    if options is None:
        options = AnalysisOptions()

    # 输入校验与转换
    if isinstance(birth_info, dict):
        try:
            birth_info = SimplifiedBirthInfo.model_validate(birth_info)
        except Exception as e:
            raise InvalidBirthInfo(str(e), {"input": birth_info}) from e

    try:
        birth_date = dt.date.fromisoformat(birth_info.date)
    except ValueError:
        raise InvalidBirthInfo(f"日期无效: {birth_info.date}") from None

    birth_time = None
    if birth_info.time:
        try:
            parts = birth_info.time.split(":")
            birth_time = dt.time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            raise InvalidBirthInfo(f"时间无效: {birth_info.time}") from None

    from tianze.domain.models import BirthInfo as _BI, Gender
    bi = _BI(
        date=birth_date,
        time=birth_time,
        gender=Gender(birth_info.gender) if birth_info.gender else Gender.UNKNOWN,
        tz_offset_hours=birth_info.timezone_offset,
        longitude=birth_info.longitude,
        sect=birth_info.sect,
        time_alg=birth_info.time_alg,
        place=birth_info.place,
    )

    # 调用内部 pipeline
    try:
        from tianze.pipeline import build_chart
        chart = build_chart(bi)
    except TianzeError:
        raise
    except Exception as e:
        raise AnalysisUnavailable(f"引擎内部错误: {e}") from e

    # 构建 Partial Result（根据 options 裁剪）
    d = chart.to_json_dict()
    warnings = list(d.get("meta", {}).get("warnings") or [])
    fallbacks = list(d.get("meta", {}).get("fallbacks") or [])
    missing = list(d.get("meta", {}).get("fallbacks") or [])  # 缺失能力

    # M12/M13: Temporal analysis (optional)
    temporal = None
    if options.include_temporal and chart.luck:
        from tianze.analysis.temporal_extended import (
            build_focused_temporal, build_timeline, month_windows_for_year,
        )
        from tianze.analysis.temporal_delta import compute_temporal_delta

        # 解析 target_day
        target_day_tuple = None
        if options.target_day:
            try:
                yd, md, dd = (int(x) for x in options.target_day.split("-"))
                target_day_tuple = (yd, md, dd)
            except ValueError:
                raise InvalidBirthInfo(f"target_day 格式无效: {options.target_day!r}（应为 YYYY-MM-DD）") from None

        temporal_result, mw_info = build_focused_temporal(
            chart,
            luck_index=options.target_luck_index,
            year=options.target_year,
            month_number=options.target_month,
            day=target_day_tuple,
        )
        temporal = temporal_result.model_dump(by_alias=True, exclude_none=True)
        if mw_info:
            temporal["monthWindow"] = mw_info

        # M13/M14: 完整 Delta（所选岁运层级 vs 原局）——事件主题需要 Delta 作为证据源
        if options.include_temporal_delta or options.include_event_themes:
            luck_pair = None
            if temporal.get("context", {}).get("luckStem"):
                luck_pair = (temporal["context"]["luckStem"], temporal["context"].get("luckBranch"))
            annual_pair = None
            if temporal.get("context", {}).get("annualStem"):
                annual_pair = (temporal["context"]["annualStem"], temporal["context"].get("annualBranch"))
            monthly_pair = None
            if temporal.get("context", {}).get("monthlyStem"):
                monthly_pair = (temporal["context"]["monthlyStem"], temporal["context"].get("monthlyBranch"))
            daily_pair = None
            if temporal.get("context", {}).get("dailyStem"):
                daily_pair = (temporal["context"]["dailyStem"], temporal["context"].get("dailyBranch"))
            delta_report = compute_temporal_delta(
                chart, luck=luck_pair, annual=annual_pair,
                monthly=monthly_pair, daily=daily_pair,
                luck_index=options.target_luck_index, annual_year=options.target_year,
            )
            temporal["delta"] = delta_report.model_dump(by_alias=True, exclude_none=True)

        # M14: 事件主题候选（惰性：只在选中岁运节点计算，依赖 Delta 证据源）
        if options.include_event_themes:
            from tianze.analysis.event_themes import compute_event_themes
            event_report = compute_event_themes(
                chart, luck=luck_pair, annual=annual_pair,
                monthly=monthly_pair, daily=daily_pair,
                delta_report=delta_report,
                with_explanations=options.include_explanations,
            )
            temporal["eventThemes"] = event_report.model_dump(by_alias=True, exclude_none=True)

        # M12/M13: Timeline（大运→流年；focus_year/focus_month 展开流月/流日）
        if chart.luck and chart.luck.da_yun:
            dy_dicts = [dy.model_dump(by_alias=True, exclude_none=True) for dy in chart.luck.da_yun]
            birth_year = birth_date.year
            natal_stems_tl = [chart.pillars.year.stem, chart.pillars.month.stem,
                              chart.pillars.day.stem]
            if chart.pillars.hour:
                natal_stems_tl.append(chart.pillars.hour.stem)
            natal_branches_tl = [chart.pillars.year.branch, chart.pillars.month.branch,
                                 chart.pillars.day.branch]
            if chart.pillars.hour:
                natal_branches_tl.append(chart.pillars.hour.branch)
            timeline = build_timeline(
                natal_stems=natal_stems_tl, natal_branches=natal_branches_tl,
                day_master=chart.day_master.stem, birth_year=birth_year,
                da_yun=dy_dicts,
                focus_year=options.target_year,
                focus_month=options.target_month,
            )
            temporal["timeline"] = timeline.model_dump(by_alias=True, exclude_none=True)

    result = SimplifiedResult(
        meta={
            "engineVersion": __version__,
            "engineStage": d.get("meta", {}).get("engineStage", ""),
            "knowledgeSchemaVersion": KNOWLEDGE_SCHEMA_VERSION,
            "caseSchemaVersion": CASE_SCHEMA_VERSION,
            "analysisSchemaVersion": AnalysisSchemaVersion.V1.value,
            "lunarPythonVersion": d.get("meta", {}).get("lunarPythonVersion", ""),
        },
        pillars=d.get("pillars") or {},
        dayMaster=d.get("dayMaster") or {},
        relations=d.get("relations") or [] if options.include_relations else [],
        blockedRelations=(d.get("blockedRelations") or []) if options.include_relations else [],
        roots=d.get("roots") or [] if options.include_element_counts else [],
        visibility=d.get("visibility") or [],
        monthCommand=d.get("monthCommand") if options.include_strength else None,
        elementCounts=d.get("elementCounts") if options.include_element_counts else None,
        strength=d.get("strength") if options.include_strength else None,
        pattern=d.get("pattern") if options.include_pattern else None,
        tiaohou=d.get("tiaohou") if options.include_tiaohou else None,
        advancedAnalysis=d.get("advancedAnalysis") if options.include_special_patterns else None,
        specialPoints=d.get("specialPoints"),
        luck=d.get("luck"),
        conventions=d.get("conventions") or {},
        warnings=warnings,
        fallbacks=fallbacks,
        missingCapabilities=missing,
    temporal=temporal,
    )
    return result
