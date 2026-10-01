"""领域契约测试：camelCase JSON、round-trip、输入校验。"""

from __future__ import annotations

import datetime as dt
import json

import pytest
from pydantic import ValidationError

from tianze import __version__
from tianze.domain.models import BirthInfo
from tianze.pipeline import build_chart


def test_birthinfo_defaults_and_validation():
    b = BirthInfo.model_validate({"date": "2003-08-18", "time": "14:30"})
    assert b.date == dt.date(2003, 8, 18)
    assert b.time_known is True and b.sect == 2 and b.tz_offset_hours == 8.0
    b2 = BirthInfo.model_validate({"date": "2003-08-18"})  # 无时辰
    assert b2.time is None and b2.time_known is False
    b3 = BirthInfo(date=dt.date(2000, 1, 1), time=dt.time(10, 0), time_known=False)
    assert b3.time is None and b3.time_known is False  # 显式声明未知 → 时间被清空


def test_birthinfo_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        BirthInfo.model_validate({"date": "2003-08-18", "what": 1})


def test_chart_json_camel_and_roundtrip():
    chart = build_chart(BirthInfo(date=dt.date(2003, 8, 18), time=dt.time(14, 30), gender="male"))
    data = chart.to_json_dict()
    raw = json.dumps(data, ensure_ascii=False)
    assert isinstance(raw, str)
    # camelCase 契约
    for key in ("dayMaster", "lunarDate", "specialPoints", "timeKnown", "stemElement",
                "hiddenStems", "tenGod", "monthInvolved", "transformCandidate"):
        assert key in json.dumps(data), f"缺少 camelCase 字段 {key}"
    assert "stem_element" not in raw and "time_known" not in raw
    # 关键内容
    assert data["pillars"]["year"]["stem"] == "癸"
    assert data["pillars"]["month"]["hiddenStems"][0]["role"] == "本气"
    assert data["dayMaster"]["stem"] == "癸"
    assert "tenGod" not in data["pillars"]["day"]  # 日主自己无十神（exclude_none 剔除）
    # birth round-trip
    BirthInfo.model_validate(data["birth"])
    # conventions 回显与 meta
    assert data["conventions"]["lateZiSect"] == "R1"
    assert data["meta"]["engineVersion"] == __version__
    assert data["meta"]["lunarPythonVersion"]


def test_relations_in_chart_json():
    """2003-08-18 14:30：地支未申亥未 → 仅申亥害一处（月-日贴邻，月令参与）。"""
    chart = build_chart(BirthInfo(date=dt.date(2003, 8, 18), time=dt.time(14, 30), gender="male"))
    assert [tuple(r.members) for r in chart.relations] == [("申", "亥")]
    harm = chart.relations[0]
    assert harm.kind.value == "harm"
    assert tuple(harm.positions) == ("month", "day")
    assert harm.adjacency.value == "ADJACENT"
    assert harm.month_involved is True
