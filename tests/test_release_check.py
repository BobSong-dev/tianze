"""M20：Release Check 测试。"""

from __future__ import annotations

import json
import os

from tools.release_check import BENCHMARK_THRESHOLDS, main as rc_main


def test_release_check_all_pass():
    import io, contextlib
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
