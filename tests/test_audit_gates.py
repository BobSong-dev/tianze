"""M17：Coverage Gates 审计测试。"""

from __future__ import annotations

import json
import os
import subprocess
import sys

from tools.audit_gates import main as audit_main


def test_all_gates_pass():
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = audit_main()
    assert rc == 0
    d = json.load(open("regression/audit-gates.json", encoding="utf-8"))
    assert d["allPass"] is True
    assert set(d["gates"]) == {f"G{i}" for i in range(1, 11)}


def test_coverage_section():
    d = json.load(open("regression/audit-gates.json", encoding="utf-8"))
    cov = d["coverage"]
    assert cov["candidatesTotal"] == 556
    assert cov["candidatesUsedAsRules"] > 0
    assert "ruleCaseCoverage" in cov and "eventRulesNeverInReplay" in cov


def test_never_triggered_is_audit_not_failure():
    """G6 是审计列表不是失败门：存在未触发规则时 allPass 仍可为 True。"""
    d = json.load(open("regression/audit-gates.json", encoding="utf-8"))
    g6 = d["gates"]["G6_never_triggered"]
    assert g6["pass"] is True and "list" in g6


def test_coverage_endpoint():
    from fastapi.testclient import TestClient
    from apps.api.main import app
    client = TestClient(app)
    r = client.get("/api/v1/knowledge/coverage")
    assert r.status_code == 200
    d = r.json()
    assert d["allPass"] is True and "coverage" in d
