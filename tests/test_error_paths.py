"""M40 · 异常流验收：非法输入、缺字段、AI 不可用降级。"""

from __future__ import annotations

from fastapi.testclient import TestClient


def _client() -> TestClient:
    from apps.api.main import app
    return TestClient(app)


def test_invalid_date_returns_422_without_traceback():
    r = _client().post("/api/v1/analyze", json={
        "birthInfo": {"date": "not-a-date", "time": "10:00", "gender": "male"}})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "INVALID_BIRTH_INFO"
    assert "Traceback" not in r.text


def test_missing_time_still_analyzes_with_fallbacks():
    """缺时辰是合法输入（未知时辰通道），产出 fallbacks 而非报错。"""
    r = _client().post("/api/v1/analyze", json={
        "birthInfo": {"date": "2000-01-01", "gender": "male"}})
    assert r.status_code == 200
    assert r.json()["pillars"]["day"]["stem"]
    assert "时辰未知" in " ".join(r.json().get("fallbacks", []))


def test_interpret_without_provider_returns_503_ai_not_configured():
    r = _client().post("/api/v1/interpret", json={
        "birthInfo": {"date": "1984-02-05", "time": "10:30", "gender": "male"}})
    assert r.status_code in (503, 200)  # 无环境 Provider 时明确降级
    if r.status_code == 503:
        assert r.json()["error"]["code"] == "AI_NOT_CONFIGURED"
        assert "Traceback" not in r.text


def test_cli_invalid_date_exits_nonzero_with_stderr():
    import subprocess
    import sys
    r = subprocess.run([sys.executable, "-m", "tianze.cli", "analyze",
                        "--date", "bad", "--time", "10:00", "--gender", "male"],
                       capture_output=True, encoding="utf-8", errors="replace")
    assert r.returncode != 0
    assert "Traceback" not in (r.stderr or "")
