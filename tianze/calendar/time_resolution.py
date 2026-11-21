"""R3 双轨道时间合成（自研实现，问题定义来自 bazi-atlas / jiwenxu）。

- pillar_dt：日/时柱轨道 = 钟表时间 − 中国夏令时校正（R12）。
- birth_instant_utc：真实瞬间 = 钟表 −（标准时区偏移 + DST）。
- beijing_dt：年/月柱轨道 = UTC + 8（节气是全球同一瞬间，R3/R4）。
"""

from __future__ import annotations

import datetime as dt

from tianze.calendar.dst import cn_dst_shift_hours
from tianze.domain.models import BirthInfo, TimeResolution


def resolve_time(birth: BirthInfo) -> tuple[TimeResolution, list[str]]:
    warnings: list[str] = []
    local = dt.datetime.combine(birth.date, birth.time or dt.time(12, 0))

    dst = 0
    if birth.tz_offset_hours == 8.0:
        dst = cn_dst_shift_hours(local)
        if dst:
            warnings.append("出生时刻处于中国夏令时窗口：日/时柱轨道已按标准时 −1h 校正（R12，窗口表待核 ERRATA-05）")

    pillar_dt = local - dt.timedelta(hours=dst)
    if birth.time_alg.value != "clock":
        warnings.append("本次使用钟表时排柱，所请求的太阳时校正尚未启用。")
    birth_instant_utc = local - dt.timedelta(hours=birth.tz_offset_hours + dst)
    beijing_dt = birth_instant_utc + dt.timedelta(hours=8)

    if not birth.time_known:
        warnings.append("时辰未知：时柱/命宫/身宫/大运缺席，日柱按正午代算仅用于农历与节气回显（R11）")
    if birth.tz_offset_hours != 8.0:
        warnings.append(
            f"非东八区（tz={birth.tz_offset_hours:+g}）：年/月柱按绝对时刻北京时间轨道判定，"
            "日/时柱按当地标准时钟判定（R3）；非中国夏令时需调用方自行换算标准偏移"
        )

    tr = TimeResolution(
        local_clock=local,
        pillar_dt=pillar_dt,
        birth_instant_utc=birth_instant_utc,
        beijing_dt=beijing_dt,
        dst_applied=bool(dst),
        effective_mode="clock",
    )
    return tr, warnings
