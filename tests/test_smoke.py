"""冒烟测试：包可导入、引擎可出盘。"""

from __future__ import annotations

import datetime as dt

import tianze
from tianze.domain.models import BirthInfo
from tianze.pipeline import build_chart


def test_version():
    assert tianze.__version__ == "0.4.0.dev0"
    assert tianze.ENGINE_STAGE in {"M2", "M3", "M4", "M5"}


def test_build_chart_smoke():
    chart = build_chart(BirthInfo(date=dt.date(2003, 8, 18), time=dt.time(14, 30), gender="male"))
    assert chart.pillars.day.stem == "癸"
    assert len(chart.relations) >= 1
    assert chart.meta.engine_stage == tianze.ENGINE_STAGE
