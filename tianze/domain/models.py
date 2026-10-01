"""领域模型（L2 契约）：Pydantic v2，JSON 输出 camelCase。"""

from __future__ import annotations

import datetime as dt
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator
from pydantic.alias_generators import to_camel

from tianze.ganzhi.tables import Element, TenGod, YinYang  # noqa: F401 (re-export)

Position = Literal["year", "month", "day", "hour"]


class CamelizeModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid", frozen=True)


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


class TimeAlgorithm(str, Enum):
    CLOCK = "clock"
    TRUE_SOLAR = "true_solar"
    MEAN_SOLAR = "mean_solar"


class HiddenStemRole(str, Enum):
    BEN = "本气"
    ZHONG = "中气"
    YU = "余气"


class BirthInfo(CamelizeModel):
    date: dt.date
    time: dt.time | None = None
    time_known: bool = True
    gender: Gender = Gender.UNKNOWN
    place: str | None = None
    longitude: float | None = None
    tz_offset_hours: float = 8.0
    calendar: Literal["solar"] = "solar"
    sect: Literal[1, 2] = 2          # R1 晚子时流派
    time_alg: TimeAlgorithm = TimeAlgorithm.CLOCK  # R2

    @model_validator(mode="after")
    def _sync_time_known(self) -> "BirthInfo":
        if self.time is None:
            object.__setattr__(self, "time_known", False)
        elif not self.time_known:
            object.__setattr__(self, "time", None)
            object.__setattr__(self, "time_known", False)
        return self


class TimeResolution(CamelizeModel):
    """R3 双轨道时间与全链路溯源（jiwenxu BirthTimeResolution 思想的自研实现）。"""

    local_clock: dt.datetime            # 用户输入的钟表时间
    pillar_dt: dt.datetime              # 日/时柱轨道（标准时，DST 校正后）
    birth_instant_utc: dt.datetime      # 真实瞬间
    beijing_dt: dt.datetime             # 年/月柱轨道（绝对时刻的北京时间）
    dst_applied: bool = False
    effective_mode: Literal["clock", "true_solar", "mean_solar"] = "clock"
    equation_of_time_minutes: float | None = None   # M3 启用
    longitude_correction_minutes: float | None = None  # M3 启用


class HiddenStem(CamelizeModel):
    stem: str
    role: HiddenStemRole
    element: Element
    yin_yang: YinYang
    ten_god: TenGod


class Pillar(CamelizeModel):
    position: Position
    stem: str
    branch: str
    stem_element: Element
    stem_yin_yang: YinYang
    branch_element: Element
    branch_yin_yang: YinYang
    hidden_stems: list[HiddenStem]
    ten_god: TenGod | None = None       # 日柱为 None（展示层渲染"日主"）
    na_yin: str
    chang_sheng: str | None = None      # 十二长生（R5），未知时辰的时柱为 None
    xun_kong: str | None = None


class Pillars(CamelizeModel):
    year: Pillar
    month: Pillar
    day: Pillar
    hour: Pillar | None = None


class DayMasterInfo(CamelizeModel):
    stem: str
    element: Element
    yin_yang: YinYang


class SpecialPoints(CamelizeModel):
    tai_yuan: str
    ming_gong: str | None = None   # 未知时辰缺席（R11）
    shen_gong: str | None = None


class DaYunEntry(CamelizeModel):
    index: int
    start_year: int
    end_year: int
    start_age: int
    end_age: int
    gan_zhi: str  # index=0（未起运段）为空串


class LuckInfo(CamelizeModel):
    forward: bool
    start_years: int
    start_months: int
    start_days: int
    start_hours: int
    da_yun: list[DaYunEntry]


class LunarDateInfo(CamelizeModel):
    year: int
    month_cn: str
    day_cn: str
    is_leap_month: bool


class Adjacency(str, Enum):
    ADJACENT = "ADJACENT"    # 贴邻
    SEPARATED = "SEPARATED"  # 隔柱


class RelationKind(str, Enum):
    STEM_COMBINATION = "stem_combination"    # 天干五合（R13 只报化气候选）
    STEM_OPPOSITION = "stem_opposition"      # 天干四冲（R14）
    SIX_COMBINATION = "six_combination"      # 地支六合
    CLASH = "clash"                          # 六冲
    HARM = "harm"                            # 六害
    BREAK = "break"                          # 六破
    PUNISHMENT_TRIO = "punishment_trio"      # 三刑全（寅巳申/丑戌未）
    PUNISHMENT_PAIR = "punishment_pair"      # 三刑部分对
    SELF_PUNISHMENT = "self_punishment"      # 自刑
    PUNISHMENT_ZIMAO = "punishment_zimao"    # 子卯无礼之刑
    THREE_HARMONY = "three_harmony"          # 三合局（三支全）
    THREE_HARMONY_HALF = "three_harmony_half"  # 半三合（R10：须含中神）
    THREE_MEETING = "three_meeting"          # 三会方


class Interaction(CamelizeModel):
    kind: RelationKind
    label: str
    members: list[str]                  # 参与的天干或地支（canonical 序）
    positions: list[Position]
    adjacency: Adjacency | None = None  # 成对关系才有
    month_involved: bool = False
    transform_candidate: Element | None = None  # R13：只是候选，不判成立
    sub_type: str | None = None         # 刑：无恩之刑/恃势之刑/无礼之刑
    note: str | None = None
    convention_id: str = "R9"


class Season(str, Enum):
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


class SeasonState(str, Enum):
    """旺相休囚死（R6/R17）。"""

    WANG = "旺"
    XIANG = "相"
    XIU = "休"
    QIN = "囚"
    SI = "死"


class RootDepth(str, Enum):
    """通根深度的定性分级（R15）：本气→strong / 中气→medium / 余气→weak。非分数。"""

    STRONG = "strong"
    MEDIUM = "medium"
    WEAK = "weak"


class RootEvidence(CamelizeModel):
    """M3.1 通根事实：某天干在某地支藏干中有根（R15：只答"有没有根"，不给分）。"""

    stem: str                          # 被通根的天干（命局四干之一）
    branch: str                        # 根所在的地支
    hidden_stem: str                   # 对应的藏干字（与 stem 同字）
    root_type: HiddenStemRole          # 本气/中气/余气
    depth: RootDepth                   # 定性深度（R15 映射，非权重）
    position: Position                 # 根所在支的位置（year/month/day/hour）
    is_month_root: bool                # 是否月令通根
    is_day_master: bool                # 被通根者是否日主
    statement: str                     # 证据语句


class StemVisibility(CamelizeModel):
    """M3.2 透干事实：地支藏干同字透出于天干（R18：只记录，不判吉凶）。"""

    hidden_stem: str
    visible_stem: str
    position: Position                 # 透出所在的天干位置
    source_branch: str                 # 来源地支
    source_role: HiddenStemRole        # 藏干类型
    source_position: Position          # 来源地支位置
    distance: int                      # |支位置序 - 干位置序|（0-3，R18）
    month_related: bool                # 来源支为月支（月令透干）
    day_master_related: bool           # 透出天干即日主
    statement: str


class HiddenStemPriorityItem(CamelizeModel):
    stem: str
    role: HiddenStemRole
    transparent: bool                  # 该藏干是否透出（M3.2）


class DayMasterRelation(CamelizeModel):
    """月令对日主的旺相休囚死关系（R6/R17：土旺四季特判）。"""

    state: SeasonState
    in_command: bool                   # 得令（R17：严格 = 旺）
    rule: str


class MonthCommand(CamelizeModel):
    """M3.3 月令：季节/五行/藏干优先级/对日主关系，全部带证据（R6/R17）。"""

    month_branch: str
    season: Season
    element: Element
    yin_yang: YinYang
    hidden_stem_priority: list[HiddenStemPriorityItem]   # 本气→中气→余气
    day_master: str
    relation_to_day_master: DayMasterRelation
    evidence: list[str]


class ElementCountView(CamelizeModel):
    visible: int
    hidden: int


class ElementCounts(CamelizeModel):
    """M3.4 五行基础统计（R16：两个独立视图，不加权，不给分）。"""

    elements: dict[str, ElementCountView]   # key 为小写五行名（wood/fire/earth/metal/water）
    stems: dict[str, int]                   # 天干五行计数
    branches: dict[str, int]                # 地支主气五行计数
    hidden_stems: dict[str, int]            # 全部藏干五行计数
    missing: list[str]                      # 两视图皆 0 的五行


class DimensionResult(CamelizeModel):
    """单维度定性结论（M4.1）：只有 result 与 reason，无分数（R17/ADR-017）。"""

    result: bool
    reason: list[str] = []


class DimensionalEvidence(CamelizeModel):
    de_ling: DimensionResult   # 得令
    de_di: DimensionResult     # 得地
    de_shi: DimensionResult    # 得势


class StrengthMethodResult(CamelizeModel):
    """单个旺衰分析方法的输出（M4.2：多方法并列，Tianze 不裁决，R19）。"""

    analyzer_id: str
    name: str
    verdict: str | None = None              # 计分制方法才有；dimensional 为 None
    strength_evidence: DimensionalEvidence | None = None
    evidence: list[str] = []
    note: str | None = None


class StrengthReport(CamelizeModel):
    methods: list[StrengthMethodResult]
    agreement: str | None = None            # 仅当 ≥2 个给出 verdict 的方法并存时才有意义
    note: str


class ChartMeta(CamelizeModel):
    engine_version: str
    engine_stage: str
    lunar_python_version: str
    warnings: list[str] = []
    fallbacks: list[str] = []


class BaziChart(CamelizeModel):
    birth: BirthInfo
    time: TimeResolution
    lunar_date: LunarDateInfo
    pillars: Pillars
    day_master: DayMasterInfo
    special_points: SpecialPoints | None = None
    luck: LuckInfo | None = None
    relations: list[Interaction] = []
    roots: list[RootEvidence] = []               # M3.1
    visibility: list[StemVisibility] = []        # M3.2
    month_command: MonthCommand | None = None    # M3.3
    element_counts: ElementCounts | None = None  # M3.4
    strength: StrengthReport | None = None       # M4
    conventions: dict[str, str] = {}
    meta: ChartMeta

    def to_json_dict(self) -> dict[str, Any]:
        """统一 JSON（camelCase，缺省字段剔除）。"""
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)
