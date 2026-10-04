"""M10.2 API Contract Tests：health / meta / analyze / errors / SDK↔API 一致性。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_meta():
    r = client.get("/api/v1/meta")
    assert r.status_code == 200
    m = r.json()
    assert m["analysisSchemaVersion"] == "1.0.0"
    assert "dimension" in m["supportedStrengthMethods"]


def test_analyze_normal():
    r = client.post("/api/v1/analyze", json={
        "birthInfo": {"date": "2003-08-18", "time": "14:30", "gender": "male"},
    })
    assert r.status_code == 200
    d = r.json()
    assert d["pillars"]["day"]["stem"] == "癸"


def test_analyze_unknown_time_partial():
    r = client.post("/api/v1/analyze", json={
        "birthInfo": {"date": "1995-08-08"},
    })
    assert r.status_code == 200
    d = r.json()
    assert "hour" not in d["pillars"]  # exclude_none
    assert len(d.get("fallbacks", [])) > 0


def test_analyze_late_zi_sect_pair():
    r1 = client.post("/api/v1/analyze", json={
        "birthInfo": {"date": "1986-04-21", "time": "23:30", "sect": 1}})
    r2 = client.post("/api/v1/analyze", json={
        "birthInfo": {"date": "1986-04-21", "time": "23:30", "sect": 2}})
    d1, d2 = r1.json(), r2.json()
    assert d1["pillars"]["day"]["stem"] != d2["pillars"]["day"]["stem"]
    assert d1["pillars"]["hour"]["stem"] == d2["pillars"]["hour"]["stem"]


def test_analyze_dst():
    r = client.post("/api/v1/analyze", json={
        "birthInfo": {"date": "1988-07-11", "time": "00:30", "gender": "male"}})
    assert r.status_code == 200
    assert any("夏令时" in w for w in r.json().get("warnings", []))


def test_analyze_overseas():
    r = client.post("/api/v1/analyze", json={
        "birthInfo": {"date": "1990-07-01", "time": "08:00",
                       "timezoneOffset": -4.0, "gender": "male"}})
    assert r.status_code == 200


def test_analyze_invalid_date():
    r = client.post("/api/v1/analyze", json={
        "birthInfo": {"date": "not-a-date"}})
    assert r.status_code == 422
    assert "error" in r.json()
    assert "traceback" not in r.text.lower()


def test_analyze_invalid_time():
    r = client.post("/api/v1/analyze", json={
        "birthInfo": {"date": "2003-08-18", "time": "25:99"}})
    assert r.status_code == 422


def test_error_schema():
    r = client.post("/api/v1/analyze", json={
        "birthInfo": {"date": "invalid"}})
    e = r.json()["error"]
    assert "code" in e and "message" in e


def test_openapi_available():
    r = client.get("/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    assert "/api/v1/analyze" in spec["paths"]


def test_sdk_api_consistency():
    """SDK↔API 一致性：同一输入，SDK 与 API 的核心字段必须一致。"""
    from tianze.sdk import SimplifiedBirthInfo, analyze

    birth = SimplifiedBirthInfo(date="2003-08-18", time="14:30", gender="male")
    sdk_result = analyze(birth)

    r = client.post("/api/v1/analyze", json={
        "birthInfo": {"date": "2003-08-18", "time": "14:30", "gender": "male"}})
    api_result = r.json()

    # 核心字段对比
    assert api_result["pillars"]["day"]["stem"] == sdk_result.pillars["day"]["stem"]
    assert api_result["dayMaster"]["stem"] == sdk_result.dayMaster["stem"]
    if sdk_result.strength:
        sdk_methods = [m["name"] for m in sdk_result.strength["methods"]]
        api_methods = [m["name"] for m in api_result["strength"]["methods"]]
        assert sdk_methods == api_methods


def test_advanced_analysis_in_response():
    r = client.post("/api/v1/analyze", json={
        "birthInfo": {"date": "1983-02-15", "time": "20:00", "gender": "female"},
        "options": {"includeSpecialPatterns": True}})
    d = r.json()
    assert "advancedAnalysis" in d
    assert "specialPattern" in d["advancedAnalysis"]
