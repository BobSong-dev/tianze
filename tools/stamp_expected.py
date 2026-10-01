"""生成 tests/fixtures/charts.json —— expected 由独立路径 oracle 盖章（bazi-atlas 模式）。

每次运行：对全部用例执行 主引擎 vs oracle 对拍，任何不一致直接失败（不允许静默入库）。
动态边界用例（立春/交节 ±33 分钟）由 lunar 节气表现场计算生成。
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tianze.calendar import lunar_adapter as LA  # noqa: E402
from tianze.domain.models import BirthInfo  # noqa: E402
from tianze.pipeline import build_chart  # noqa: E402
from tests.crosscheck.oracle import four_pillars_str, oracle_four_pillars  # noqa: E402

VERIFIED_BY = "独立算法路径对拍（JDN 日柱公式 + 五鼠遁/五虎遁 + Meeus Ch.25 黄经区间），与主引擎实现路径不同"


def case(name: str, y: int, mo: int, d: int, h: int | None = None, mi: int | None = None, *,
         tz: float = 8.0, lon: float | None = None, sect: int = 2, gender: str = "male",
         known: bool = True) -> dict:
    birth: dict = {
        "date": f"{y:04d}-{mo:02d}-{d:02d}",
        "timeKnown": known,
        "gender": gender,
        "tzOffsetHours": tz,
        "sect": sect,
    }
    if known:
        birth["time"] = f"{h:02d}:{mi:02d}"
    if lon is not None:
        birth["longitude"] = lon
    return {"name": name, "birth": birth}


def find_jie_moment(cn: str, year: int) -> dt.datetime:
    """在某公历年的多份节气表中定位该年内的指定节（名称归一化后匹配）。"""
    found: list[dt.datetime] = []
    for ref in (dt.date(year, 1, 10), dt.date(year, 7, 1), dt.date(year, 12, 20), dt.date(year + 1, 3, 1)):
        lunar = LA.to_solar(dt.datetime.combine(ref, dt.time(12, 0))).getLunar()
        for raw, solar in lunar.getJieQiTable().items():
            if LA.normalize_jieqi_name(raw) == cn:
                moment = LA.solar_to_datetime(solar)
                if moment.year == year:
                    found.append(moment)
    if not found:
        raise KeyError(f"未在 {year} 年节气表中找到【{cn}】")
    return min(found)


def straddle_cases(cn: str, year: int, tag: str) -> list[dict]:
    """±25 分钟夹逼：既落进 R4 的 30 分钟警告圈，又在 oracle 黄经 ±12 分钟精度承诺之外。"""
    moment = find_jie_moment(cn, year)
    before = (moment - dt.timedelta(minutes=25)).replace(second=0, microsecond=0)
    after = (moment + dt.timedelta(minutes=25)).replace(second=0, microsecond=0)
    assert before < moment < after, f"{cn} {year} 夹逼失败: {before} < {moment} < {after}"
    return [
        case(f"{tag}_before", before.year, before.month, before.day, before.hour, before.minute),
        case(f"{tag}_after", after.year, after.month, after.day, after.hour, after.minute),
    ]


def build_cases() -> list[dict]:
    cases = [
        case("plan_example_2003", 2003, 8, 18, 14, 30),
        case("basic_1986", 1986, 4, 21, 10, 0),
        case("basic_1990", 1990, 6, 15, 12, 0),
        case("basic_1995", 1995, 8, 8, 6, 30),
        case("midnight_2000", 2000, 1, 1, 0, 15),
        case("winter_1970", 1970, 1, 1, 12, 0),
        case("nye_1999", 1999, 12, 31, 23, 0),
        case("olympic_2008", 2008, 8, 8, 20, 0),
        case("bailu_season_2012", 2012, 9, 7, 12, 0),
        case("female_1983", 1983, 2, 15, 20, 0, gender="female"),
        case("daymaster_1984", 1984, 2, 5, 10, 0),
        case("daymaster_1976", 1976, 7, 16, 4, 0),
        case("daymaster_1968", 1968, 11, 30, 16, 0),
        case("daymaster_1990", 1990, 9, 9, 20, 0),
        case("daymaster_1982", 1982, 4, 4, 8, 30),
        case("late_zi_sect1", 1986, 4, 21, 23, 30, sect=1),
        case("late_zi_sect2", 1986, 4, 21, 23, 30, sect=2),
        case("early_zi_2001", 2001, 5, 5, 0, 30),
        case("midnight_2355", 1990, 6, 14, 23, 55),
        case("midnight_0005", 1990, 6, 15, 0, 5),
        case("unknown_time_1995", 1995, 8, 8, known=False),
        case("dst_1988_midnight", 1988, 7, 11, 0, 30),
        case("dst_1988_winter", 1988, 1, 15, 12, 0),
        case("urumqi_1985", 1985, 4, 20, 10, 0, lon=87.6),
        case("nyc_1990", 1990, 7, 1, 8, 0, tz=-4.0, lon=-74.0),
        case("london_1992", 1992, 8, 8, 14, 0, tz=1.0, lon=-0.1),
        case("leap_day_1996", 1996, 2, 29, 9, 15),
        case("old_1965", 1965, 3, 1, 8, 0),
        case("recent_2025", 2025, 10, 1, 12, 0),
        case("hongkong_1975", 1975, 11, 2, 3, 20, lon=114.17),
        case("india_tz55_1994", 1994, 5, 6, 10, 0, tz=5.5, lon=77.2),
        case("la_crossday_1988", 1988, 7, 6, 20, 0, tz=-7.0, lon=-118.24),
    ]
    # 动态边界夹逼用例（±33 分钟；冬至为中气 → 月柱不应切换，作为"节≠气"反例）
    cases += straddle_cases("立春", 2024, "lichun_2024")
    cases += straddle_cases("立春", 2025, "lichun_2025")
    cases += straddle_cases("小暑", 2025, "xiaoshu_2025")
    cases += straddle_cases("冬至", 2024, "zhongqi_dongzhi_2024")
    return cases


def main() -> None:
    records = []
    for item in build_cases():
        birth = BirthInfo.model_validate(item["birth"])
        chart = build_chart(birth)
        engine = {
            "year": chart.pillars.year.stem + chart.pillars.year.branch,
            "month": chart.pillars.month.stem + chart.pillars.month.branch,
            "day": chart.pillars.day.stem + chart.pillars.day.branch,
            "hour": (chart.pillars.hour.stem + chart.pillars.hour.branch) if chart.pillars.hour else None,
        }
        oracle = oracle_four_pillars(birth)
        if engine != oracle:
            raise SystemExit(
                f"对拍失败 [{item['name']}] engine={four_pillars_str(engine)} "
                f"oracle={four_pillars_str(oracle)}"
            )
        records.append({
            "name": item["name"],
            "birth": item["birth"],
            "expected": {
                "pillars": oracle,
                "verifiedBy": VERIFIED_BY,
                "verifiedAt": dt.date.today().isoformat(),
                "status": "verified",
            },
        })

    payload = {
        "note": "Tianze 排盘回归基线：expected 由 tests/crosscheck/oracle.py 独立路径盖章，从不手填（bazi-atlas 模式）。"
                "实时防线是 tests/test_crosscheck.py 的主引擎 vs oracle 差分；本文件锁历史。",
        "generatedAt": dt.datetime.now().isoformat(timespec="seconds"),
        "count": len(records),
        "cases": records,
    }
    out = ROOT / "tests" / "fixtures" / "charts.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: {len(records)} cases stamped -> {out}")


if __name__ == "__main__":
    main()
