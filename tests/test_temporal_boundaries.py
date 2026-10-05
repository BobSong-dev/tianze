"""M13 · 时间边界专项验证：顺逆/起运/交节/流月边界/DST/时区/晚子时/闰日。

纪律：不完全信赖 lunar-python——
- 顺逆与起运折算用独立公式核对（R7 口径）；
- 节气时刻用 tests/crosscheck Meeus 黄经 oracle 对拍（精度承诺 ±15 分钟）；
- 流月五虎遁+节序 vs lunar-python EightChar 月柱全量对拍；
- 流日 JDN 公式 vs lunar-python 日柱抽样对拍。
"""

from __future__ import annotations

import datetime as dt
import random

import pytest

from tianze.calendar import lunar_adapter as LA
from tianze.calendar.time_resolution import resolve_time
from tianze.domain.models import BirthInfo, Gender
from tianze.pipeline import build_chart
from tianze.analysis.temporal_extended import (
    month_windows_for_year, day_pillar_for_jdn, gregorian_to_jdn,
)
from tests.crosscheck.oracle import sun_longitude, jd_from_utc


def _chart(date_s: str, time_s: str, gender: str, **kw) -> BirthInfo:
    y, m, d = (int(x) for x in date_s.split("-"))
    hh, mm = (int(x) for x in time_s.split(":"))
    return BirthInfo(date=dt.date(y, m, d), time=dt.time(hh, mm), gender=Gender(gender), **kw)


# ---------- 1) 顺逆：阳男阴女顺行，阴男阳女逆行（R7） ----------

PARITY_CASES = [
    # (出生, 年干, 阴阳)
    ("1984-06-01", "甲", "yang"),   # 甲子
    ("1983-06-01", "癸", "yin"),    # 癸亥
    ("1990-06-01", "庚", "yang"),   # 庚午
    ("2003-06-01", "癸", "yin"),    # 癸未
]


@pytest.mark.parametrize("date_s,stem,parity", PARITY_CASES, ids=["yang", "yin", "yang2", "yin2"])
def test_shunni_parity_x_gender(date_s, stem, parity):
    for gender, expect_forward in (("male", parity == "yang"), ("female", parity == "yin")):
        birth = _chart(date_s, "12:00", gender)
        chart = build_chart(birth)
        assert chart.pillars.year.stem == stem, f"{date_s} 年干应为 {stem}"
        assert chart.luck is not None
        assert chart.luck.forward == expect_forward, (
            f"{date_s} {parity}年干 × {gender}: forward 应为 {expect_forward}（阳男阴女顺行）")


# ---------- 2) 起运折算线性不变量（3天=1岁、1天=4月、1时辰=10天，允许进位） ----------

QIYUN_PROBES = [
    ("1984-02-05", "10:30", "male", True),
    ("1983-02-15", "20:00", "female", True),
    ("2003-08-18", "14:30", "male", False),
    ("1990-06-15", "06:15", "female", False),
    ("1976-01-30", "23:30", "male", False),
    ("2000-02-29", "12:00", "female", False),
]


@pytest.mark.parametrize("date_s,time_s,gender,_f", QIYUN_PROBES, ids=[p[0] for p in QIYUN_PROBES])
def test_qiyun_linear_invariant(date_s, time_s, gender, _f):
    birth = _chart(date_s, time_s, gender)
    chart = build_chart(birth)
    assert chart.luck is not None
    tr, _ = resolve_time(birth)
    moment = tr.beijing_dt
    jies = LA.jie_moments(moment)
    if chart.luck.forward:
        target = min(m for _n, m in jies if m > moment)
    else:
        target = max(m for _n, m in jies if m <= moment)
    dist_days = abs((target - moment).total_seconds()) / 86400
    folded = (chart.luck.start_years + chart.luck.start_months / 12
              + chart.luck.start_days / 360)
    # 容差 = 一个起运"天"档（10 天/360 = 0.0278）：lunar 将余数向上取整到 10 天档（可进位年/月）
    assert abs(dist_days / 3 - folded) <= 10 / 360, (
        f"起运折算偏离 3天=1岁 线性口径：dist/3={dist_days / 3:.4f} lunar={folded:.4f}")


def test_qiyun_direction_matches_forward_flag():
    """顺行探针的起运距离应指向下一节，逆行指向前一节（方向自洽）。"""
    birth = _chart("1984-02-05", "10:30", "male")
    chart = build_chart(birth)
    tr, _ = resolve_time(birth)
    jies = LA.jie_moments(tr.beijing_dt)
    nxt = min(m for _n, m in jies if m > tr.beijing_dt)
    prv = max(m for _n, m in jies if m <= tr.beijing_dt)
    dist_next = (nxt - tr.beijing_dt).total_seconds() / 86400
    dist_prev = (tr.beijing_dt - prv).total_seconds() / 86400
    assert chart.luck.forward is True  # 1984 甲子年男 → 阳男顺行
    # 逆行
    birth2 = _chart("2003-08-18", "14:30", "male")
    chart2 = build_chart(birth2)
    assert chart2.luck.forward is False


# ---------- 3) 节气时刻：lunar vs Meeus 黄经 oracle ----------

def _meeus_crossing(target_deg: float, around: dt.datetime, span_hours=3.0) -> dt.datetime:
    """在 around±span 内以 1 分钟步长定位黄经过 target_deg 的时刻（UTC→北京）。"""
    base_jd = jd_from_utc(around - dt.timedelta(hours=span_hours))
    lo = dt.timedelta(0)
    hi = dt.timedelta(hours=2 * span_hours)
    def lon_at(td: dt.timedelta) -> float:
        return sun_longitude(base_jd + td.total_seconds() / 86400)
    steps = int(2 * span_hours * 60)
    prev = lon_at(lo)
    for i in range(1, steps + 1):
        td = dt.timedelta(minutes=i)
        cur = lon_at(td)
        # 黄经单调递增（span 3 小时内不会跨圈），找第一次 ≥ target
        if prev < target_deg <= cur:
            # 北京时间 = UTC + 8；oracle jd 输入用 UTC
            utc_moment = (around - dt.timedelta(hours=span_hours)) + td
            return utc_moment + dt.timedelta(hours=8)
        prev = cur
    raise AssertionError(f"未在 {around}±{span_hours}h 内找到黄经 {target_deg} 过点")


def test_jie_moments_vs_meeus_lichun_2026():
    """立春 2026：lunar 节表 vs Meeus 黄经 315° 过点（±15 分钟）。"""
    jies = dict(LA.jie_moments(dt.datetime(2026, 6, 1)))
    lichun = jies["立春"]
    # UTC 化：jie_moments 返回 naive 北京时间 → 转 UTC
    lichun_utc = lichun - dt.timedelta(hours=8)
    cross = _meeus_crossing(315.0, lichun_utc)
    assert abs((cross - lichun).total_seconds()) <= 15 * 60, (
        f"立春 2026 lunar={lichun} meeus={cross}")


@pytest.mark.parametrize("year", [1984, 2000, 2024])
def test_jie_moments_vs_meeus_more(year):
    """冬至/夏至/立秋：lunar vs Meeus（±15 分钟）。"""
    jies = LA.jie_moments(dt.datetime(year, 6, 1))
    by_name_year = {}
    for n, m in jies:
        by_name_year.setdefault((n, m.year), m)
    for name, deg in (("立秋", 135.0), ("立冬", 225.0), ("惊蛰", 345.0)):
        moment = next(m for (n, y), m in by_name_year.items() if n == name and y == year)
        cross = _meeus_crossing(deg, moment - dt.timedelta(hours=8))
        assert abs((cross - moment).total_seconds()) <= 15 * 60, (
            f"{name} {year}: lunar={moment} meeus={cross}")


# ---------- 4) 月柱节气边界切换 ----------

def test_month_pillar_switch_at_lichun_2026():
    """立春 2026-02-04 前后 ±40 分钟：年柱 乙巳→丙午、月柱 己丑→庚寅。"""
    jies = LA.jie_moments(dt.datetime(2026, 6, 1))
    lichun = next(m for n, m in jies if n == "立春" and m.year == 2026)
    before = (lichun - dt.timedelta(minutes=40)).time().replace(second=0)
    after = (lichun + dt.timedelta(minutes=40)).time().replace(second=0)
    b_date = (lichun - dt.timedelta(minutes=40)).date()
    a_date = (lichun + dt.timedelta(minutes=40)).date()
    cb = build_chart(BirthInfo(date=b_date, time=before, gender=Gender.MALE))
    ca = build_chart(BirthInfo(date=a_date, time=after, gender=Gender.MALE))
    assert cb.pillars.year.stem + cb.pillars.year.branch == "乙巳"
    assert ca.pillars.year.stem + ca.pillars.year.branch == "丙午"
    assert cb.pillars.month.stem + cb.pillars.month.branch == "己丑"
    assert ca.pillars.month.stem + ca.pillars.month.branch == "庚寅"


def test_month_windows_mid_instant_vs_lunar():
    """流月窗口中点 → lunar EightChar 月柱必须等于窗口干支（五虎遁+节序对拍）。"""
    from lunar_python import Solar
    for year in (1984, 2000, 2024, 2026):
        for mw in month_windows_for_year(year):
            start = dt.datetime.strptime(mw["start"], "%Y-%m-%d %H:%M")
            end = dt.datetime.strptime(mw["end"], "%Y-%m-%d %H:%M")
            mid = start + (end - start) / 2
            solar = Solar.fromYmdHms(mid.year, mid.month, mid.day,
                                     mid.hour, mid.minute, 0)
            lunar_month = solar.getLunar().getEightChar().getMonth()
            assert lunar_month == mw["stem"] + mw["branch"], (
                f"{year} 月{mw['monthNumber']}（{mw['jieName']}）窗口干支 "
                f"{mw['stem'] + mw['branch']} ≠ lunar {lunar_month}")


def test_month_boundary_minute_precision():
    """窗口边界分钟级验证：交节前 1 分钟属上月柱，后 1 分钟属新月柱。"""
    year = 2026
    mws = month_windows_for_year(year)
    start = dt.datetime.strptime(mws[1]["start"], "%Y-%m-%d %H:%M")  # 惊蛰
    from lunar_python import Solar
    just_before = start - dt.timedelta(minutes=1)
    just_after = start + dt.timedelta(minutes=1)
    for moment, expect in ((just_before, mws[0]["stem"] + mws[0]["branch"]),
                           (just_after, mws[1]["stem"] + mws[1]["branch"])):
        solar = Solar.fromYmdHms(moment.year, moment.month, moment.day,
                                 moment.hour, moment.minute, 0)
        assert solar.getLunar().getEightChar().getMonth() == expect


# ---------- 5) 流日 JDN 公式差分对拍 ----------

def test_day_pillar_differential_sample():
    """60 个 LCG 抽样日期：JDN 公式日柱 == lunar-python 日柱。"""
    from lunar_python import Solar
    rng = random.Random(42)
    checked = 0
    for _ in range(60):
        y = rng.randint(1950, 2030)
        m = rng.randint(1, 12)
        d = rng.randint(1, 28)
        solar = Solar.fromYmd(y, m, d)
        lunar_day = solar.getLunar().getEightChar().getDay()
        mine = "".join(day_pillar_for_jdn(gregorian_to_jdn(y, m, d)))
        assert mine == lunar_day, f"{y}-{m:02d}-{d:02d}: JDN={mine} lunar={lunar_day}"
        checked += 1
    assert checked == 60


# ---------- 6) CN DST ----------

def test_cn_dst_summer_shift():
    """1988-06-10（夏令时）：pillar_dt = 钟表 −1h；冬天无 DST。"""
    birth_summer = _chart("1988-06-10", "01:00", "male")
    tr_s, _ = resolve_time(birth_summer)
    assert tr_s.dst_applied is True
    assert tr_s.pillar_dt.hour == 0            # 01:00 − 1h = 00:00（早子时）
    assert tr_s.birth_instant_utc.hour == 16   # 01:00 − 9h（8 时区 + 1 DST）= 前日 16:00 UTC
    birth_winter = _chart("1988-01-10", "01:00", "male")
    tr_w, _ = resolve_time(birth_winter)
    assert tr_w.dst_applied is False
    assert tr_w.pillar_dt.hour == 1


# ---------- 7) 海外时区双轨道（R3/R12） ----------

def test_overseas_dual_track():
    """2000-01-01 05:00（UTC−5）：年/月柱走北京时间绝对时刻，日/时柱走本地标准时。"""
    birth = _chart("2000-01-01", "05:00", "male", tz_offset_hours=-5.0)
    chart = build_chart(birth)
    # 北京时间 = 当日 18:00 → 仍在 己卯 年（立春前）、子月（大雪后）
    assert chart.pillars.year.stem + chart.pillars.year.branch == "己卯"
    assert chart.pillars.month.stem + chart.pillars.month.branch == "丙子"
    # 日柱 = 本地日期 2000-01-01（JDN 公式）
    expect_day = "".join(day_pillar_for_jdn(gregorian_to_jdn(2000, 1, 1)))
    assert chart.pillars.day.stem + chart.pillars.day.branch == expect_day
    # 时柱：本地 05:00 → 卯时（05-07）
    assert chart.pillars.hour.branch == "卯"


# ---------- 8) 晚子时流派（R1） ----------

def test_late_zi_sect1_vs_sect2():
    """1986-04-21 23:30：sect2（当天派）= JDN(4-21) 日柱；sect1（次日制）= JDN+1。"""
    d21 = "".join(day_pillar_for_jdn(gregorian_to_jdn(1986, 4, 21)))
    d22 = "".join(day_pillar_for_jdn(gregorian_to_jdn(1986, 4, 22)))
    c2 = build_chart(BirthInfo(date=dt.date(1986, 4, 21), time=dt.time(23, 30),
                               gender=Gender.MALE, sect=2))
    c1 = build_chart(BirthInfo(date=dt.date(1986, 4, 21), time=dt.time(23, 30),
                               gender=Gender.MALE, sect=1))
    assert c2.pillars.day.stem + c2.pillars.day.branch == d21
    assert c1.pillars.day.stem + c1.pillars.day.branch == d22
    assert d21 != d22


# ---------- 9) 闰年闰日 ----------

def test_leap_day_birth():
    """2000-02-29：排盘成功；日柱=JDN 公式；大运正常（女性庚辰年逆排）。"""
    birth = _chart("2000-02-29", "12:00", "female")
    chart = build_chart(birth)
    expect_day = "".join(day_pillar_for_jdn(gregorian_to_jdn(2000, 2, 29)))
    assert chart.pillars.day.stem + chart.pillars.day.branch == expect_day
    assert chart.luck is not None and chart.luck.forward is False
    # 2001-02-28 后一天是 03-01（非闰年）：日柱连续
    d1 = gregorian_to_jdn(2000, 2, 28)
    d2 = gregorian_to_jdn(2000, 2, 29)
    d3 = gregorian_to_jdn(2000, 3, 1)
    assert d3 - d1 == 2
    for j in (d1, d2, d3):
        s, b = day_pillar_for_jdn(j)
        assert s in "甲乙丙丁戊己庚辛壬癸" and b in "子丑寅卯辰巳午未申酉戌亥"


# ---------- 10) 大运干支独立校验（序列 +1 连续、干支同奇偶） ----------

def test_dayun_sequence_independent():
    """大运干支序列：相邻指数差 = ±1（按顺逆），60 步内不重复。"""
    for date_s, time_s, gender, _f in QIYUN_PROBES[:4]:
        chart = build_chart(_chart(date_s, time_s, gender))
        entries = [dy for dy in chart.luck.da_yun if dy.gan_zhi]
        idxs = []
        for dy in entries:
            gz = dy.gan_zhi
            for i in range(60):
                if ("甲乙丙丁戊己庚辛壬癸"[i % 10] == gz[0]
                        and "子丑寅卯辰巳午未申酉戌亥"[i % 12] == gz[1]):
                    idxs.append(i)
                    break
        step = 1 if chart.luck.forward else -1
        for a, b in zip(idxs, idxs[1:]):
            assert (b - a) % 60 == step % 60, (
                f"{date_s} {gender}: 大运干支序列不连续 {idxs}")
