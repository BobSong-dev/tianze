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
    conventions: dict[str, str] = {}
    meta: ChartMeta

    def to_json_dict(self) -> dict[str, Any]:
        """统一 JSON（camelCase，缺省字段剔除）。"""
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)
