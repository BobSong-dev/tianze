"""M15：Historical Case Replay 测试。"""

from __future__ import annotations

import json
import os

import pytest

from tianze.analysis.case_chart import build_case_chart
from tools.case_replay import REPLAY_SCHEMA_VERSION, replay_case


def test_case_chart_build():
    """四柱重建分析上下文：day_master/strength/special 与 pipeline 口径一致。"""
    chart = build_case_chart({"year": "癸未", "month": "庚申", "day": "癸亥", "hour": "己未"})
    assert chart.day_master.stem == "癸"
    assert chart.month_command is not None
    assert len(chart.strength.methods) == 3
    assert chart.advancedAnalysis["specialPattern"]


def test_case_chart_incomplete_raises():
    with pytest.raises(ValueError):
        build_case_chart({"year": "癸未", "day": "癸亥"})


def test_replay_relations_vocabulary():
    """对照分级限定在四种（SOURCE_SUPPORTS/DIFFERS/SILENT/TIANZE_UNRESOLVED）。"""
    case = {"caseId": "CASE-T-1", "fact": {"pillars": {
        "year": "癸未", "month": "庚申", "day": "癸亥", "hour": "己未"}, "gender": None}}
    temporal_ref = {
        "sourceTemporal": {"dayun": [{"age": 21, "ganZhi": "戊午"}],
                           "mentions": [{"kind": "luck", "ganZhi": "戊午", "rawText": "戊午运"}]},
        "historicalClaims": [],
    }
    r = replay_case(case, temporal_ref, ["career", "wealth"])
    assert r is not None
    relations = {m["relation"] for m in r["matches"]}
    assert relations <= {"SOURCE_SUPPORTS", "SOURCE_DIFFERS", "SOURCE_SILENT", "TIANZE_UNRESOLVED"}
    assert r["luck"] == "戊午" and r["luckSource"].startswith("mention")


def test_replay_skips_without_temporal_context():
    case = {"caseId": "CASE-T-2", "fact": {"pillars": {
        "year": "癸未", "month": "庚申", "day": "癸亥", "hour": "己未"}}}
    assert replay_case(case, {"sourceTemporal": {"dayun": [], "mentions": []}}, []) is None


def test_no_truth_judgment_language():
    """产物不得包含"命中/正确/验证为真"类裁决语言。"""
    assert os.path.exists("regression/case-replay.json"), "先运行 tools/case_replay.py"
    d = json.load(open("regression/case-replay.json", encoding="utf-8"))
    blob = json.dumps(d["stats"], ensure_ascii=False)
    for banned in ("命中率", "准确率", "验证为真"):
        assert banned not in blob
    assert d["verification"]["status"] == "MACHINE_EXTRACTED"


def test_replay_product_stats_shape():
    d = json.load(open("regression/case-replay.json", encoding="utf-8"))
    assert d["schemaVersion"] == REPLAY_SCHEMA_VERSION
    s = d["stats"]
    assert s["replayed"] > 0
    assert s["unresolvedRate"] < 1.0
    assert set(s["relationCounts"]) <= {"SOURCE_SUPPORTS", "SOURCE_DIFFERS",
                                        "SOURCE_SILENT", "TIANZE_UNRESOLVED"}
