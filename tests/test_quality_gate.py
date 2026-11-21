"""M18：一键质量门测试。"""

from __future__ import annotations

import json
import os
import subprocess
import pytest

from tools.quality_gate import main as qg_main


def test_quality_gate_summary():
    """summary 结构完整（17 步）。allPass 标志是发布时点状态：
    质量门内的 pytest 步骤运行时 summary 尚未（或刚被上一次运行）刷新，
    断言 allPass 会造成"门必须先通过才能通过"的自指死锁——freshness
    由 release_check P0 与发布流程负责。"""
    d = json.load(open("release/quality-summary.json", encoding="utf-8"))
    assert len(d["steps"]) == 23  # M27: +source_coverage（M26: +cross_layer_audit）
    assert {"failed", "totalSeconds"} <= set(d)
    steps = {s["step"] for s in d["steps"]}
    assert {"pytest", "audit_gates", "case_regression", "benchmark",
            "release_metadata", "rule_coverage_audit", "ai_eval_compare",
            "release_automation_dryrun"} <= steps
    md = open("release/quality-summary.md", encoding="utf-8").read()
    assert "Quality Gate Summary" in md


@pytest.mark.parametrize("failed_step", [None, "pytest", "release_metadata"])
def test_release_check_receives_current_run_evidence(monkeypatch, tmp_path, failed_step):
    from tools import quality_gate
    from tools.release_check import quality_gate_status
    monkeypatch.setattr(quality_gate, "REPO", str(tmp_path))
    monkeypatch.setattr(quality_gate, "STEPS", [(name, [name]) for name in ["pytest", "release_metadata", "release_check"]])
    observed = []

    def run(command, **kwargs):
        name = command[0]
        if name == "git":
            return subprocess.CompletedProcess(command, 0, "current\n", "")
        if name == "release_check":
            assert not (tmp_path / "release/quality-summary.json").exists()
            with open(command[command.index("--gate-progress") + 1], encoding="utf-8") as stream:
                summary = json.load(stream)
            assert not quality_gate_status(summary, "current")[0]
            passed = quality_gate_status(summary, "current", internal=True)[0]
            observed.append(passed)
            return subprocess.CompletedProcess(command, 0 if passed else 1, "", "")
        return subprocess.CompletedProcess(command, 1 if name == failed_step else 0, "", "")

    monkeypatch.setattr(quality_gate.subprocess, "run", run)
    assert quality_gate.main() == (1 if failed_step else 0)
    assert observed == [failed_step is None]
    completed = json.loads((tmp_path / "release/quality-summary.json").read_text(encoding="utf-8"))
    assert quality_gate_status(completed, "current")[0] is (failed_step is None)
    assert not quality_gate_status(completed, "older")[0]
    completed["steps"].pop()
    assert not quality_gate_status(completed, "current")[0]
