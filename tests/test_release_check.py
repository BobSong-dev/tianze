"""M20：Release Check 测试。"""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import subprocess
import pytest

from tools.release_check import BENCHMARK_THRESHOLDS, main as rc_main, quality_gate_status
from tools.quality_gate import STEPS


@pytest.fixture
def quality_evidence(tmp_path):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, encoding="utf-8", check=True).stdout.strip()
    path = tmp_path / "quality-fixture.json"
    path.write_text(json.dumps({"allPass": True, "failed": [], "gitCommit": head,
                                "phase": "complete", "steps": [{"step": name, "exitCode": 0} for name, _ in STEPS]}), encoding="utf-8")
    return str(path)


def test_release_check_all_pass(monkeypatch, quality_evidence):
    """结构 + 逐步骤断言。P5 stale 用 --skip-stale-check：gate 内调用时
    metadata 必然落后一个 commit（freshness 由外部 release_check 与发布
    流程负责——与 ADR-056 release_automation 同类解法）。"""
    # 版本 bump 后 metadata 可能 stale（P4 读 engineVersion）——先刷新
    import subprocess
    subprocess.run([sys.executable, "tools/release_metadata.py"],
                   capture_output=True, encoding="utf-8", errors="replace",
                   cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    monkeypatch.setattr(sys, "argv", ["release_check.py", "--skip-stale-check", "--quality-summary", quality_evidence])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = rc_main()
    assert rc == 0
    d = json.load(open("release/release-check.json", encoding="utf-8"))
    assert d["allPass"] is True, [s for s in d["steps"] if not s["pass"]]
    steps = {s["step"] for s in d["steps"]}
    assert {"P0_quality_gate", "P1_package_build", "P2_clean_install_smoke",
            "P3_cli_smoke", "P4_version_consistency", "P5_stale_artifact",
            "P6_notes_consistency", "P7_benchmark_regression"} == steps


def test_benchmark_thresholds_transparent():
    """阈值透明：每项有明确数值（避免环境噪声误报）。"""
    assert all(isinstance(v, float) and v >= 1.0 for v in BENCHMARK_THRESHOLDS.values())
    assert len(BENCHMARK_THRESHOLDS) == 3


def test_benchmark_history_signals():
    """benchmark history 存在且每次记录含 regressionSignals 字段（透明阈值）。"""
    path = "regression/benchmark-history.jsonl"
    assert os.path.exists(path)
    last = json.loads(open(path, encoding="utf-8").read().strip().split("\n")[-1])
    assert "regressionSignals" in last and "commit" in last and "engine" in last


def test_release_history_and_ready_marker(quality_evidence):
    """Release history 记录 + RC READY_FOR_RELEASE 标记（不伪造外部权限）。
    先刷新工件（metadata/check/history），避免断言 stale 记录。"""
    import subprocess
    py = sys.executable
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for tool in ("tools/release_metadata.py", "tools/release_check.py",
                 "tools/release_history.py"):
        arguments = [py, tool]
        if tool == "tools/release_check.py":
            arguments += ["--quality-summary", quality_evidence]
        r = subprocess.run(arguments, capture_output=True, encoding="utf-8",
                           errors="replace", cwd=root)
        assert r.returncode == 0, f"{tool}: {r.stdout[-200:]}"
    import tianze
    hist = [json.loads(x) for x in open("release/release-history.jsonl", encoding="utf-8")]
    last = hist[-1]
    assert last["version"] == tianze.__version__ and last["commit"]
    assert last["releaseCheck"]["allPass"] is True
    assert "qualityGate" in last   # quality-summary 是滚动文件，可能 stale（结构断言）
    ready = json.load(open("release/READY_FOR_RELEASE.json", encoding="utf-8"))
    assert ready["gateEvidenceAtRc"]["qualityGateAllPass"] is True
    ready = json.load(open("release/READY_FOR_RELEASE.json", encoding="utf-8"))
    assert ready["status"] == "READY_FOR_RELEASE" and ready["tagCreatedLocally"] is True
    assert any("push" in b for b in ready["blockedActions"])
    # 本地 tag 存在
    tags = subprocess.run(["git", "tag", "-l"], capture_output=True, text=True,
                          encoding="utf-8",
                          cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))).stdout
    assert "v0.3.0" in tags


@pytest.mark.parametrize("summary,expected", [
    ({}, False),
    ({"allPass": False, "gitCommit": "current", "failed": ["pytest"]}, False),
    ({"allPass": True, "gitCommit": "old", "steps": [{"exitCode": 0}]}, False),
    ({"allPass": True, "gitCommit": "current", "steps": [{"exitCode": 1}]}, False),
    ({"allPass": True, "gitCommit": "current", "steps": []}, False),
    ({"allPass": True, "gitCommit": "current", "failed": [], "steps": [{"exitCode": 0}]}, False),
])
def test_quality_precondition_matrix(summary, expected):
    assert quality_gate_status(summary, "current")[0] is expected


def test_failed_quality_stops_before_build(monkeypatch, tmp_path):
    from tools import release_check
    monkeypatch.setattr(release_check, "REPO", str(tmp_path))
    monkeypatch.setattr(release_check, "_git", lambda *args: "current")
    monkeypatch.setattr(release_check, "_load", lambda *args: {"allPass": False, "failed": ["pytest"]})
    monkeypatch.setattr(sys, "argv", ["release_check.py"])
    monkeypatch.setattr(release_check.subprocess, "run", lambda *args, **kwargs: pytest.fail("must not build"))
    assert release_check.main() == 1
    assert json.loads((tmp_path / "release/release-check.json").read_text(encoding="utf-8"))["allPass"] is False
