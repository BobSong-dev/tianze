"""M18：一键质量门测试。"""

from __future__ import annotations

import json
import os

from tools.quality_gate import main as qg_main


def test_quality_gate_summary():
    """summary 结构完整（17 步）。allPass 标志是发布时点状态：
    质量门内的 pytest 步骤运行时 summary 尚未（或刚被上一次运行）刷新，
    断言 allPass 会造成"门必须先通过才能通过"的自指死锁——freshness
    由 release_check P0 与发布流程负责。"""
    d = json.load(open("release/quality-summary.json", encoding="utf-8"))
    assert len(d["steps"]) == 18  # M20: +release_check
    assert {"failed", "totalSeconds"} <= set(d)
    steps = {s["step"] for s in d["steps"]}
    assert {"pytest", "audit_gates", "case_regression", "benchmark",
            "release_metadata", "rule_coverage_audit", "ai_eval_compare",
            "release_automation_dryrun"} <= steps
    md = open("release/quality-summary.md", encoding="utf-8").read()
    assert "Quality Gate Summary" in md
