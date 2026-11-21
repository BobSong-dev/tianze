"""M18 · 一键质量门（quality gate runner）：release 前完整质量栈 + summary。

步骤（顺序执行；每步记录 exit code 与耗时）：
  1. pytest 全量（tests + apps/api/tests）
  2. knowledge validator
  3. conflict graph 构建（0 problems）
  4. graph audit
  5. audit gates（10 门）
  6. rule audit
  7. case regression compare（BREAKING 必须为 0）
  8. temporal regression compare（BREAKING 必须为 0）
  9. event evaluation（problems 必须为空）
 10. case replay
 11. AI evaluation（--mock；SKIPPED 允许）
 12. review queue
 13. benchmark
 14. release metadata

输出：release/quality-summary.json + .md。任何 FAIL → 退出码 1。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable

STEPS = [
    ("pytest", [PY, "-m", "pytest", "tests", "apps/api/tests", "-q"]),
    # M19：版本兼容矩阵/治理测试包含在 pytest 内
    ("knowledge_validator", [PY, "tools/validate_knowledge.py"]),
    ("conflict_graph", [PY, "tools/build_conflict_graph.py"]),
    ("graph_audit", [PY, "tools/graph_audit.py"]),
    ("audit_gates", [PY, "tools/audit_gates.py"]),
    ("rule_audit", [PY, "tools/rule_audit.py"]),
    ("case_regression", [PY, "tools/case_regression.py", "compare"]),
    ("temporal_regression", [PY, "tools/temporal_regression.py", "compare"]),
    ("event_evaluation", [PY, "tools/event_evaluation.py"]),
    ("case_replay", [PY, "tools/case_replay.py"]),
    ("xushi_case_audit", [PY, "tools/xushi_case_audit.py"]),
    ("cross_layer_audit", [PY, "tools/cross_layer_audit.py"]),
    ("source_coverage", [PY, "tools/source_coverage.py"]),
    ("ai_evaluation_mock", [PY, "tools/ai_evaluation.py", "--mock"]),
    ("review_queue", [PY, "tools/review_queue.py"]),
    ("rule_coverage_audit", [PY, "tools/rule_coverage_audit.py"]),
    ("rescue_coverage", [PY, "tools/rescue_coverage.py"]),
    ("ai_eval_compare", [PY, "tools/ai_eval_compare.py"]),
    ("benchmark", [PY, "tools/benchmark.py"]),
    ("release_metadata", [PY, "tools/release_metadata.py"]),
    ("release_check", [PY, "tools/release_check.py", "--skip-stale-check"]),
    ("release_automation_dryrun", [PY, "tools/release_automation.py", "--skip-gate-check"]),
    ("release_history", [PY, "tools/release_history.py"]),
]

SKIP_CASE_REGRESSION_BREAKING = {"case_regression", "temporal_regression"}


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        return _run(os.path.join(directory, "gate-progress.json"))


def _run(progress_path: str) -> int:
    results = []
    t_all = time.perf_counter()
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, encoding="utf-8", cwd=REPO, check=True).stdout.strip()
    for name, cmd in STEPS:
        if name in {"release_check", "release_automation_dryrun", "release_history"}:
            for result in results:
                if result["step"] in SKIP_CASE_REGRESSION_BREAKING and result["exitCode"] == 1:
                    path = "regression/report.json" if result["step"] == "case_regression" else "regression/temporal-compare.json"
                    report = _load(path, {})
                    if "severityCounts" in report and not report["severityCounts"].get("BREAKING", 0):
                        result["exitCode"] = 0
                        result["note"] = "REVIEW 级变化，无 BREAKING"
            failed = [result["step"] for result in results if result["exitCode"] != 0]
            os.makedirs(os.path.join(REPO, "release"), exist_ok=True)
            with open(progress_path, "w", encoding="utf-8") as stream:
                json.dump({"schemaVersion": "1.0.0", "gitCommit": head, "phase": "prerelease",
                           "allPass": not failed, "failed": failed, "steps": results,
                           "totalSeconds": round(time.perf_counter() - t_all, 1)}, stream, ensure_ascii=False, indent=1)
            cmd = [*cmd, "--gate-progress", progress_path]
        t0 = time.perf_counter()
        try:
            r = subprocess.run(cmd, capture_output=True, encoding="utf-8",
                               errors="replace", cwd=REPO, timeout=900)
            code = r.returncode
            tail = (r.stdout or "").strip().split("\n")[-3:]
        except subprocess.TimeoutExpired:
            code, tail = 124, ["TIMEOUT"]
        results.append({
            "step": name, "exitCode": code,
            "elapsedSeconds": round(time.perf_counter() - t0, 2),
            "tail": tail,
        })
        status = "PASS" if code == 0 else "FAIL"
        print(f"  {status} {name}（{results[-1]['elapsedSeconds']}s）")
        if code != 0 and name != "case_replay":
            print("\n".join(tail))

    # regression 特殊判定：exit 1 = 有变化（REVIEW 级以上）→ 检查 severity
    regression_ok = {}
    case_reg = _load("regression/report.json", {})
    temporal_reg = _load("regression/temporal-compare.json", {})
    regression_ok["case_regression"] = "severityCounts" in case_reg and not case_reg["severityCounts"].get("BREAKING", 0)
    regression_ok["temporal_regression"] = "severityCounts" in temporal_reg and not temporal_reg["severityCounts"].get("BREAKING", 0)
    for r in results:
        if r["step"] in regression_ok and r["exitCode"] == 1:
            if regression_ok[r["step"]]:
                r["exitCode"] = 0
                r["note"] = "exit 1 因存在 REVIEW 级变化，无 BREAKING → 视为通过"

    failed = [r["step"] for r in results if r["exitCode"] != 0]
    all_pass = not failed
    summary = {
        "schemaVersion": "1.0.0",
        "gitCommit": head,
        "phase": "complete",
        "allPass": all_pass,
        "failed": failed,
        "totalSeconds": round(time.perf_counter() - t_all, 1),
        "steps": results,
    }
    os.makedirs(os.path.join(REPO, "release"), exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=os.path.join(REPO, "release"),
                                     encoding="utf-8", delete=False) as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=1)
    os.replace(stream.name, os.path.join(REPO, "release/quality-summary.json"))
    md = ["# Tianze Quality Gate Summary", "",
          f"- 结果：{'ALL PASS' if all_pass else 'FAIL: ' + ', '.join(failed)}",
          f"- 总耗时：{summary['totalSeconds']}s", "",
          "| step | 状态 | 耗时 |", "|---|---|---|"]
    for r in results:
        md.append(f"| {r['step']} | {'PASS' if r['exitCode'] == 0 else 'FAIL'} "
                  f"| {r['elapsedSeconds']}s |")
    with open(os.path.join(REPO, "release/quality-summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(f"\nQuality Gate：{'ALL PASS' if all_pass else 'FAIL'}"
          f"（{summary['totalSeconds']}s）→ release/quality-summary.md")
    return 0 if all_pass else 1


def _load(path, default):
    p = os.path.join(REPO, path)
    if not os.path.exists(p):
        return default
    return json.load(open(p, encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
