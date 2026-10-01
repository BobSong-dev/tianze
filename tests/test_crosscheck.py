"""差分对拍（M1 实时防线）：主引擎 vs 独立路径 oracle。

- 35+ 个盖章 fixture 全量对拍；
- 50 个确定性随机盘差分（LCG 种子固定）；
- 黄经 oracle 精度承诺：距节气交界 >12 分钟（oracle 黄经 ±6 分钟 + 主引擎余量），
  落入交界窗口的样本跳过并留痕（bazi-atlas "逐条归因" 纪律的测试化）。
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from tianze.calendar import lunar_adapter as LA
from tianze.calendar.time_resolution import resolve_time
from tianze.domain.models import BirthInfo
from tianze.pipeline import build_chart
from tests.crosscheck.oracle import four_pillars_str, oracle_four_pillars

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "charts.json"
JIE_UNCERTAINTY = dt.timedelta(minutes=12)


def engine_pillars(birth: BirthInfo) -> dict[str, str | None]:
    chart = build_chart(birth)
    p = chart.pillars
    return {
        "year": p.year.stem + p.year.branch,
        "month": p.month.stem + p.month.branch,
        "day": p.day.stem + p.day.branch,
        "hour": (p.hour.stem + p.hour.branch) if p.hour else None,
    }


def assert_agree(birth: BirthInfo) -> None:
    engine = engine_pillars(birth)
    oracle = oracle_four_pillars(birth)
    if engine != oracle:
        tr, _ = resolve_time(birth)
        prev_jie, next_jie = LA.nearest_jie(tr.beijing_dt)
        for item in (prev_jie, next_jie):
            if item is not None:
                _name, moment = item
                if abs(tr.beijing_dt - moment) <= JIE_UNCERTAINTY:
                    pytest.skip(
                        f"距交节【{_name}】<12 分钟，超出 oracle 黄经精度承诺；"
                        f"engine={four_pillars_str(engine)} oracle={four_pillars_str(oracle)}"
                    )
    assert engine == oracle, (
        f"主引擎与独立路径不一致: engine={four_pillars_str(engine)} "
        f"oracle={four_pillars_str(oracle)} birth={birth.model_dump(mode='json', by_alias=True)}"
    )


def test_oracle_anchors():
    """外部锚点自检（真值来自引擎之外）。"""
    from tests.crosscheck.oracle import BRANCHES, STEMS, jdn, _ANCHOR_JDN

    def day_of(y: int, m: int, d: int) -> str:
        idx = (jdn(y, m, d) - _ANCHOR_JDN) % 60
        return STEMS[idx % 10] + BRANCHES[idx % 12]

    assert day_of(1949, 10, 1) == "甲子"
    assert day_of(2000, 1, 1) == "戊午"
    assert day_of(2024, 1, 1) == "甲子"


@pytest.mark.parametrize("case", json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["cases"],
                         ids=lambda c: c["name"])
def test_fixture_crosscheck(case: dict):
    assert_agree(BirthInfo.model_validate(case["birth"]))


def test_random_differential_50():
    state = 20261001

    def rnd(n: int) -> int:
        nonlocal state
        state = (state * 6364136223846793005 + 1442695040888963407) % (2**64)
        return (state >> 17) % n

    timezones = [8.0, 8.0, 8.0, 8.0, -4.0, 1.0, 5.5, 9.0]
    checked = 0
    for _ in range(50):
        year, month, day = 1950 + rnd(76), 1 + rnd(12), 1 + rnd(28)
        hour, minute = rnd(24), rnd(60)
        if rnd(6) == 0:  # 加权采样中国夏令时夏季
            year, month, day = 1986 + rnd(6), 7, 1 + rnd(28)
        birth = BirthInfo(
            date=dt.date(year, month, day),
            time=dt.time(hour, minute),
            gender="male" if rnd(2) == 0 else "female",
            tz_offset_hours=timezones[rnd(len(timezones))],
            sect=1 + rnd(2),
        )
        assert_agree(birth)
        checked += 1
    assert checked == 50
