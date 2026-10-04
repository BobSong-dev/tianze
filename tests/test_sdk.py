"""M9 SDK 测试：determinism / partial result / serialization / version / error model / options。"""

from __future__ import annotations

import json

import pytest

from tianze import AnalysisOptions, SimplifiedBirthInfo, TianzeError, analyze
from tianze.knowledge.models import CASE_SCHEMA_VERSION, KNOWLEDGE_SCHEMA_VERSION


def _birth(**kw) -> dict:
    base = {"date": "2003-08-18", "time": "14:30", "gender": "male"}
    base.update(kw)
    return base


# ---------- 基本功能 ----------

def test_basic_analyze():
    r = analyze(_birth())
    assert r.pillars["day"]["stem"] == "癸"
    assert r.meta["engineVersion"]
    assert r.meta["analysisSchemaVersion"] == "1.0.0"


def test_json_serialization_deterministic():
    """Deterministic Contract：同输入 → 同输出 JSON。"""
    r1 = analyze(_birth())
    r2 = analyze(_birth())
    j1 = json.dumps(r1.model_dump(), sort_keys=True, ensure_ascii=False)
    j2 = json.dumps(r2.model_dump(), sort_keys=True, ensure_ascii=False)
    assert j1 == j2, "同输入必须产生相同 JSON"


def test_late_zi_sect_pair():
    """晚子时 sect1/sect2 成对用例：日柱不同、时柱相同。"""
    b1 = analyze(_birth(date="1986-04-21", time="23:30"), AnalysisOptions(include_strength=False))
    # sect1
    b1 = analyze(SimplifiedBirthInfo(date="1986-04-21", time="23:30", sect=1))
    b2 = analyze(SimplifiedBirthInfo(date="1986-04-21", time="23:30", sect=2))
    d1 = b1.pillars["day"]["stem"] + b1.pillars["day"]["branch"]
    d2 = b2.pillars["day"]["stem"] + b2.pillars["day"]["branch"]
    assert d1 != d2, "两派日柱应不同"
    h1 = b1.pillars["hour"]["stem"] + b1.pillars["hour"]["branch"]
    h2 = b2.pillars["hour"]["stem"] + b2.pillars["hour"]["branch"]
    assert h1 == h2, "两派时柱应相同"


def test_overseas_timezone():
    """海外时区：NYC 1990-07-01 08:00 EDT (-4)。"""
    r = analyze(_birth(date="1990-07-01", time="08:00", timezone_offset=-4.0))
    assert r.pillars["year"]["stem"] in "甲乙丙丁戊己庚辛壬癸"


def test_unknown_time_partial_result():
    """未知时辰 → Partial Result（不 crash，hour 为 null）。"""
    r = analyze({"date": "1995-08-08"})
    assert "hour" not in r.pillars  # exclude_none 剔除
    assert r.pillars["day"]["stem"]  # 日柱照常
    assert len(r.fallbacks) > 0  # 缺失能力记录


# ---------- Error Model ----------

def test_invalid_date_raises():
    with pytest.raises(TianzeError) as exc_info:
        analyze({"date": "not-a-date"})
    assert exc_info.value.code == "INVALID_BIRTH_INFO"


def test_invalid_time_raises():
    with pytest.raises(TianzeError) as exc_info:
        analyze({"date": "2003-08-18", "time": "25:99"})
    assert exc_info.value.code == "INVALID_BIRTH_INFO"


# ---------- Options 开关 ----------

def test_options_exclude_strength():
    r = analyze(_birth(), AnalysisOptions(include_strength=False))
    assert r.strength is None
    assert r.pillars["day"]["stem"] == "癸"  # 排盘照常


def test_options_exclude_all():
    r = analyze(_birth(), AnalysisOptions(
        include_strength=False, include_pattern=False, include_tiaohou=False,
        include_special_patterns=False, include_relations=False, include_element_counts=False,
    ))
    assert r.strength is None and r.pattern is None and r.tiaohou is None
    assert r.relations == [] and r.elementCounts is None
    assert r.pillars["day"]["stem"]  # 排盘仍完整


# ---------- Version fields ----------

def test_version_fields():
    r = analyze(_birth())
    m = r.meta
    assert m["engineVersion"]
    assert m["analysisSchemaVersion"] == "1.0.0"
    assert m["knowledgeSchemaVersion"] == KNOWLEDGE_SCHEMA_VERSION
    assert m["caseSchemaVersion"] == CASE_SCHEMA_VERSION
    assert m["lunarPythonVersion"]


# ---------- Canonical Cases Snapshot ----------

CANONICAL_CASES = [
    {"name": "plan_2003", "birth": {"date": "2003-08-18", "time": "14:30", "gender": "male"},
     "expectedDay": "癸"},
    {"name": "female_1983", "birth": {"date": "1983-02-15", "time": "20:00", "gender": "female"},
     "expectedDay": "甲"},
    {"name": "late_zi_sect2", "birth": {"date": "1986-04-21", "time": "23:30", "gender": "male", "sect": 2},
     "expectedMonth": "壬辰"},
]


@pytest.mark.parametrize("case", CANONICAL_CASES, ids=lambda c: c["name"])
def test_canonical_snapshot(case):
    """Canonical Cases：少量命例的 SDK 输出快照（非 1147 例全量回归）。"""
    r = analyze(case["birth"])
    if "expectedDay" in case:
        assert r.pillars["day"]["stem"] == case["expectedDay"]
    if "expectedMonth" in case:
        assert r.pillars["month"]["stem"] + r.pillars["month"]["branch"] == case["expectedMonth"]
    # 结构完整性
    assert "meta" in r.model_dump()
    assert "conventions" in r.model_dump()
