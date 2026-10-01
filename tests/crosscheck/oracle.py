"""独立算法路径的排盘 oracle（差分对拍用）——与主引擎不同的实现。

独立性说明（学 bazi-atlas crosscheck 并声明共享面）：
- 与主引擎**共享**的数据：中国 DST 窗口表（公共事实，见 docs/ERRATA-05）与干支字符常量。
- 与主引擎**不同**的实现路径：
  * 日柱 = 儒略日整数公式 `(JDN - 2433191) % 60`；
    锚点 1949-10-01 = 甲子（真实 JDN=2433191；Erfix 的 2433180 有 +11 天 bug，
    见 docs/ERRATA-06）。外部锚点自检：1949-10-01=甲子 / 2000-01-01=戊午 / 2024-01-01=甲子。
  * 年柱 = Meeus Ch.25 太阳黄经区间 + 序数公式（不用任何历法库的节气表）。
  * 月柱 = 黄经区间定月序 + 五虎遁（独立于 lunar 的实现）。
  * 时柱 = 五鼠遁（独立实现；23 点档时干基准=次日日干，R1）。
- 黄经用 Meeus《Astronomical Algorithms》Ch.25 低阶级数（~±6 分钟量级），
  因此 oracle 只承诺在距节气交界 >12 分钟的出生时刻上与主引擎一致；
  差分测试对交界 ±12 分钟内的样本跳过并记录（规则写入 test_crosscheck.py）。
"""

from __future__ import annotations

import datetime as dt
import math

from tianze.calendar.dst import cn_dst_shift_hours
from tianze.domain.models import BirthInfo

STEMS = "甲乙丙丁戊己庚辛壬癸"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"

_ANCHOR_JDN = 2433191  # 1949-10-01 = 甲子日（外部事实锚点）

# 五虎遁：年干 → 寅月天干序（甲己→丙2, 乙庚→戊4, 丙辛→庚6, 丁壬→壬8, 戊癸→甲0）
_WU_HU = (2, 4, 6, 8, 0)


# ---------- 儒略日 ----------

def jdn(year: int, month: int, day: int) -> int:
    """格里历儒略日数（正午起算的 JDN）。"""
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045


def jd_from_utc(moment_utc: dt.datetime) -> float:
    j0 = jdn(moment_utc.year, moment_utc.month, moment_utc.day)
    frac = (moment_utc.hour + moment_utc.minute / 60 + moment_utc.second / 3600) / 24.0
    return j0 - 0.5 + frac


# ---------- Meeus Ch.25 太阳视黄经（低阶级数，仅年/月柱域使用） ----------

def sun_longitude(jd_ut: float) -> float:
    t = (jd_ut - 2451545.0) / 36525.0
    mean_lon = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
    mean_anom = math.radians(357.52911 + 35999.05029 * t - 0.0001537 * t * t)
    center = (
        (1.914602 - 0.004817 * t - 0.000014 * t * t) * math.sin(mean_anom)
        + (0.019993 - 0.000101 * t) * math.sin(2 * mean_anom)
        + 0.000289 * math.sin(3 * mean_anom)
    )
    omega = math.radians(125.04 - 1934.136 * t)
    return (mean_lon + center - 0.00569 - 0.00478 * math.sin(omega)) % 360.0


# ---------- 独立时间合成（与主引擎同一 DST 数据表，不同代码路径） ----------

def _resolve(birth: BirthInfo) -> tuple[dt.datetime, dt.datetime, dt.datetime]:
    """返回 (pillar_dt, utc, beijing_dt)。oracle_four_pillars 之外的调用方（测试）可用。"""
    local = dt.datetime.combine(birth.date, birth.time or dt.time(12, 0))
    dst = cn_dst_shift_hours(local) if birth.tz_offset_hours == 8.0 else 0
    pillar_dt = local - dt.timedelta(hours=dst)
    utc = local - dt.timedelta(hours=birth.tz_offset_hours + dst)
    beijing = utc + dt.timedelta(hours=8)
    return pillar_dt, utc, beijing


# ---------- 干支推导 ----------

def bazi_year(beijing_dt: dt.datetime, lam: float) -> int:
    """年支年（立春分界）。立春恒在 2 月上旬，故 1 月必属前一年、2 月按黄经判。"""
    year = beijing_dt.year
    if beijing_dt.month == 1:
        return year - 1
    if beijing_dt.month == 2 and lam < 315.0:
        return year - 1
    return year


def month_ordinal(lam: float) -> int:
    """0=寅月 … 11=丑月（立春 λ=315°，每 30° 一节）。"""
    return int(((lam - 315.0) % 360.0) // 30.0)


def day_ganzhi_index(pillar_dt: dt.datetime, sect: int) -> int:
    j = jdn(pillar_dt.year, pillar_dt.month, pillar_dt.day)
    if sect == 1 and pillar_dt.hour == 23:
        j += 1  # R1 流派 1：晚子时日柱进次日
    return (j - _ANCHOR_JDN) % 60


def hour_ganzhi(pillar_dt: dt.datetime, day_index: int, sect: int) -> str:
    hour = pillar_dt.hour
    branch = ((hour + 1) // 2) % 12
    # R1：两派时柱日干基准均为次日日干（sect=1 的日柱已进位，不再 +1）
    base = day_index if sect == 1 else (day_index + (1 if hour == 23 else 0))
    stem = ((base % 5) * 2 + branch) % 10
    return STEMS[stem] + BRANCHES[branch]


def oracle_four_pillars(birth: BirthInfo) -> dict[str, str | None]:
    local = dt.datetime.combine(birth.date, birth.time or dt.time(12, 0))
    dst = cn_dst_shift_hours(local) if birth.tz_offset_hours == 8.0 else 0
    pillar_dt = local - dt.timedelta(hours=dst)
    utc = local - dt.timedelta(hours=birth.tz_offset_hours + dst)
    beijing_dt = utc + dt.timedelta(hours=8)

    lam = sun_longitude(jd_from_utc(utc))

    year = bazi_year(beijing_dt, lam)
    y_stem, y_branch = (year - 4) % 10, (year - 4) % 12
    mo = month_ordinal(lam)
    m_branch = (2 + mo) % 12
    m_stem = (_WU_HU[y_stem % 5] + mo) % 10

    d_idx = day_ganzhi_index(pillar_dt, birth.sect)
    hour = hour_ganzhi(pillar_dt, d_idx, birth.sect) if birth.time_known else None

    return {
        "year": STEMS[y_stem] + BRANCHES[y_branch],
        "month": STEMS[m_stem] + BRANCHES[m_branch],
        "day": STEMS[d_idx % 10] + BRANCHES[d_idx % 12],
        "hour": hour,
    }


# ---------- 外部锚点自检（导入即验证，失败直接抛错） ----------

def _self_check() -> None:
    def day_of(y: int, m: int, d: int) -> str:
        idx = (jdn(y, m, d) - _ANCHOR_JDN) % 60
        return STEMS[idx % 10] + BRANCHES[idx % 12]

    assert day_of(1949, 10, 1) == "甲子", "日柱锚点失效：1949-10-01 应为甲子"
    assert day_of(2000, 1, 1) == "戊午", "日柱锚点失效：2000-01-01 应为戊午"
    assert day_of(2024, 1, 1) == "甲子", "日柱锚点失效：2024-01-01 应为甲子"
    # 黄经域抽检：2024 立春前后 λ 跨 315°（时刻约 02-04 16:27 北京 = 08:27 UTC）
    lam_before = sun_longitude(jd_from_utc(dt.datetime(2024, 2, 4, 8, 0)))
    lam_after = sun_longitude(jd_from_utc(dt.datetime(2024, 2, 4, 9, 0)))
    assert lam_before < 315.0 <= lam_after, "黄经锚点失效：2024 立春（08:26:53 UTC）前后未跨 315°"


_self_check()


def four_pillars_str(result: dict[str, str | None]) -> str:
    return " ".join(result[k] or "?" for k in ("year", "month", "day", "hour"))
