"""M18：一键质量门测试。"""

from __future__ import annotations

import json
import os

from tools.quality_gate import main as qg_main


def test_quality_gate_summary():
    """summary 存在且最近一次运行全过（步骤 14、无 FAIL）。"""
    d = json.load(open("release/quality-summary.json", encoding="utf-8"))
    assert len(d["steps"]) == 14
    assert d["allPass"] is True, d["failed"]
    steps = {s["step"] for s in d["steps"]}
    assert {"pytest", "audit_gates", "case_regression", "benchmark",
            "release_metadata"} <= steps
    md = open("release/quality-summary.md", encoding="utf-8").read()
    assert "Quality Gate Summary" in md
