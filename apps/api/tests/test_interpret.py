"""M11 AI Interpretation API tests (mock provider only)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_interpret_not_configured():
    """API Key 未配置 → 503 + 确定性分析不受影响。"""
    import os
    old_key = os.environ.pop("TIANZE_LLM_API_KEY", None)
    try:
        r = client.post("/api/v1/interpret", json={"analysis": {}})
        assert r.status_code == 503
        assert r.json()["error"]["code"] == "AI_NOT_CONFIGURED"
        # analyze 仍然正常
        r2 = client.post("/api/v1/analyze", json={"birthInfo": {"date": "2003-08-18", "time": "14:30"}})
        assert r2.status_code == 200
    finally:
        if old_key:
            os.environ["TIANZE_LLM_API_KEY"] = old_key
