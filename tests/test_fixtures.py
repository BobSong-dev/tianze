"""fixture 回归：排盘结果锁历史（expected 由 tools/stamp_expected.py 盖章，从不手填）。"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from tianze.domain.models import BirthInfo
from tianze.pipeline import build_chart

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "charts.json"
CASES = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["cases"]


def pillars_of(chart):
    p = chart.pillars
    return {
        "year": p.year.stem + p.year.branch,
        "month": p.month.stem + p.month.branch,
        "day": p.day.stem + p.day.branch,
        "hour": (p.hour.stem + p.hour.branch) if p.hour else None,
    }


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
def test_pillars_match_stamped_expected(case: dict):
    birth = BirthInfo.model_validate(case["birth"])
    chart = build_chart(birth)
    assert pillars_of(chart) == case["expected"]["pillars"], (
        f"[{case['name']}] 排盘漂移！expected={case['expected']['pillars']} "
        f"got={pillars_of(chart)}（若为有意变更：修 R 表 + 重新盖章并记录 ERRATA）"
    )
    assert case["expected"]["status"] == "verified"


def test_plan_example_known_values():
    """任务书示例盘：2003-08-18 14:30 → 癸未 庚申 癸亥 己未。"""
    case = next(c for c in CASES if c["name"] == "plan_example_2003")
    chart = build_chart(BirthInfo.model_validate(case["birth"]))
    assert chart.pillars.year.stem + chart.pillars.year.branch == "癸未"
    assert chart.pillars.month.stem + chart.pillars.month.branch == "庚申"
    assert chart.pillars.day.stem + chart.pillars.day.branch == "癸亥"
    assert chart.pillars.hour.stem + chart.pillars.hour.branch == "己未"
    assert chart.day_master.stem == "癸"
    assert chart.day_master.element.value == "WATER"
    assert chart.day_master.yin_yang.value == "YIN"
    # 十神（相对日主癸）：年柱癸=比肩、月柱庚=正印、时柱己=七杀
    assert chart.pillars.year.ten_god.value == "比肩"
    assert chart.pillars.month.ten_god.value == "正印"
    assert chart.pillars.hour.ten_god.value == "七杀"
    # 藏干十神（月支申：庚壬戊）
    month_hidden = {h.stem: h.ten_god.value for h in chart.pillars.month.hidden_stems}
    assert month_hidden == {"庚": "正印", "壬": "劫财", "戊": "正官"}


def test_late_zi_pair_differs_only_in_day_pillar():
    """R1 锁定：sect1/sect2 晚子时成对用例——日柱不同、时柱相同。"""
    c1 = next(c for c in CASES if c["name"] == "late_zi_sect1")["expected"]["pillars"]
    c2 = next(c for c in CASES if c["name"] == "late_zi_sect2")["expected"]["pillars"]
    assert c1["day"] != c2["day"], "两派日柱应不同"
    assert c1["hour"] == c2["hour"], "两派时柱应相同（时干基准均为次日日干）"
    assert c1["year"] == c2["year"] and c1["month"] == c2["month"]


def test_unknown_time_fixture_has_no_hour():
    case = next(c for c in CASES if c["name"] == "unknown_time_1995")
    assert case["expected"]["pillars"]["hour"] is None
    chart = build_chart(BirthInfo.model_validate(case["birth"]))
    assert chart.pillars.hour is None
    assert chart.special_points is not None and chart.special_points.ming_gong is None
    assert chart.luck is None
    assert any("R11" in w for w in chart.meta.warnings)


def test_dst_case_crosses_midnight():
    """1988-07-11 00:30（夏令时窗口内）→ 标准时 07-10 23:30：日柱为 7-10，时柱为晚子。"""
    case = next(c for c in CASES if c["name"] == "dst_1988_midnight")
    chart = build_chart(BirthInfo.model_validate(case["birth"]))
    assert chart.time.dst_applied is True
    assert chart.time.pillar_dt.date() == dt.date(1988, 7, 10)
    assert chart.time.pillar_dt.hour == 23
    assert any("夏令时" in w for w in chart.meta.warnings)


def test_luck_example_1983_female():
    """demo 用例：1983-02-15 20:00 女 → 癸亥 甲寅 甲戌 甲戌；癸=阴干，阴女顺行；
    起运 6 年 2 个月 20 天；大运[1] 乙卯（月柱甲寅顺行一位）。"""
    case = next(c for c in CASES if c["name"] == "female_1983")
    chart = build_chart(BirthInfo.model_validate(case["birth"]))
    assert pillars_of(chart) == {"year": "癸亥", "month": "甲寅", "day": "甲戌", "hour": "甲戌"}
    assert chart.luck is not None
    assert chart.luck.forward is True
    assert (chart.luck.start_years, chart.luck.start_months, chart.luck.start_days) == (6, 2, 20)
    assert chart.luck.da_yun[1].gan_zhi == "乙卯"
    assert chart.luck.da_yun[0].gan_zhi == ""


def test_warnings_on_jie_boundary():
    case = next(c for c in CASES if c["name"] == "lichun_2024_before")
    chart = build_chart(BirthInfo.model_validate(case["birth"]))
    assert any("临界" in w for w in chart.meta.warnings)


def test_zhongqi_boundary_does_not_change_month():
    """冬至是中气：跨过它月柱不得切换（R4 节≠气反例）。"""
    before = next(c for c in CASES if c["name"] == "zhongqi_dongzhi_2024_before")["expected"]["pillars"]
    after = next(c for c in CASES if c["name"] == "zhongqi_dongzhi_2024_after")["expected"]["pillars"]
    assert before["month"] == after["month"]
    assert before["year"] == after["year"]
