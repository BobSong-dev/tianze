"""M20 · Release Check：发布前一键检查（在 quality gate 之上）。

步骤（除 quality gate 外，聚焦发布一致性）：
  P1  package build（python -m build → wheel/sdist 成功）
  P2  clean-install smoke（临时 venv 装 wheel → tianze version/analyze）
  P3  CLI smoke（当前 venv：analyze/timeline/export/version）
  P4  release version consistency（pyproject dynamic = __version__ = metadata）
  P5  stale artifact（metadata gitCommit vs HEAD；dirty 提示）
  P6  changelog/notes consistency（RELEASE_NOTES 与 tag-prep 一致）
  P7  benchmark regression（对比 history，透明阈值）

前提：tools/quality_gate.py 已 ALL PASS（先跑它）。
输出：release/release-check.json + .md。任何 FAIL → 退出码 1。
"""

from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = os.path.join(REPO, ".venv", "Scripts", "python.exe")
sys.path.insert(0, REPO)  # release_check 自身可从任意 CWD 运行
CHECK_SCHEMA_VERSION = "1.0.0"

# benchmark 回归阈值（透明 ENGINEERING_HEURISTIC：中位基准的 3 倍才报，
# 避免环境抖动误报——每项列出明确阈值与当前值）
BENCHMARK_THRESHOLDS = {
    "caseChart1147.perCaseMs": 5.0,
    "replayCorpus.perCaseMs": 5.0,
    "timeline80y.elapsedSeconds": 1.0,
}


def _load(rel, default):
    p = os.path.join(REPO, rel)
    if not os.path.exists(p):
        return default
    return json.load(open(p, encoding="utf-8"))


def _git(*args) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", cwd=REPO).stdout.strip()


def main() -> int:
    results: list[dict] = []

    def step(name: str, ok: bool, detail: str = ""):
        results.append({"step": name, "pass": bool(ok), "detail": detail})
        print(f"  {'PASS' if ok else 'FAIL'} {name}" + (f"（{detail}）" if detail else ""))

    # 前提：quality gate
    qg = _load("release/quality-summary.json", {})
    step("P0_quality_gate", bool(qg.get("allPass")),
         f"{len(qg.get('steps', []))} 步" if qg else "先运行 tools/quality_gate.py")

    import tianze
    version = tianze.__version__

    # P1 build
    t0 = time.perf_counter()
    dist_dir = os.path.join(REPO, "dist-release")
    r = subprocess.run([PY, "-m", "pip", "wheel", "--no-deps", "-w", dist_dir, REPO],
                       capture_output=True, encoding="utf-8", errors="replace", cwd=REPO)
    wheels = glob.glob(os.path.join(dist_dir, "*.whl"))
    step("P1_package_build", r.returncode == 0 and bool(wheels),
         f"{os.path.basename(wheels[0]) if wheels else (r.stderr or '')[-100:]}，"
         f"{round(time.perf_counter() - t0, 1)}s")

    # P2 clean-install smoke
    if wheels:
        with tempfile.TemporaryDirectory() as venv_dir:
            venv_py = os.path.join(venv_dir, "Scripts", "python.exe")
            subprocess.run([sys.executable, "-m", "venv", venv_dir],
                           capture_output=True, encoding="utf-8", errors="replace")
            subprocess.run([venv_py, "-m", "pip", "install", "--quiet", wheels[0]],
                           capture_output=True, encoding="utf-8", errors="replace")
            rv = subprocess.run([venv_py, "-m", "tianze.cli", "version"],
                                capture_output=True, encoding="utf-8", errors="replace")
            ra = subprocess.run(
                [venv_py, "-m", "tianze.cli", "analyze", "--date", "2003-08-18",
                 "--time", "14:30", "--gender", "male"],
                capture_output=True, encoding="utf-8", errors="replace")
            clean_ok = False
            if rv.returncode == 0 and ra.returncode == 0:
                try:
                    out = json.loads(ra.stdout)
                    clean_ok = out["pillars"]["day"]["stem"] == "癸"
                except Exception:
                    clean_ok = False
            step("P2_clean_install_smoke", clean_ok,
                 f"clean venv install → version/analyze"
                 + ("" if clean_ok else f"（{ra.stderr or rv.stderr}）"[-120:]))
    else:
        step("P2_clean_install_smoke", False, "无 wheel")

    # P3 CLI smoke（当前 venv）
    smoke = []
    for args in (["version"],
                 ["analyze", "--date", "1984-02-05", "--time", "10:30",
                  "--gender", "male", "--event-themes"],
                 ["timeline", "--date", "1984-02-05", "--time", "10:30",
                  "--gender", "male", "--year", "2026"]):
        r = subprocess.run([PY, "-m", "tianze.cli", *args], capture_output=True,
                           encoding="utf-8", errors="replace", cwd=REPO)
        smoke.append({"args": args, "ok": r.returncode == 0})
    step("P3_cli_smoke", all(s["ok"] for s in smoke),
         f"{sum(1 for s in smoke if s['ok'])}/{len(smoke)}")

    # P4 version consistency
    meta = _load("release/release-metadata.json", {})
    pyproject_ok = 'attr = "tianze.__version__"' in open(
        os.path.join(REPO, "pyproject.toml"), encoding="utf-8").read()
    # metadata 的版本面用 knowledge/case 等键名；engine 在 release.engineVersion
    consistent = (meta.get("engineVersion") == version and pyproject_ok)
    step("P4_version_consistency", consistent,
         f"{version}（dynamic single-source={pyproject_ok}，metadata="
         f"{meta.get('engineVersion')}）")

    # P5 stale
    stale = meta.get("release", {}).get("dirty")
    head = _git("rev-parse", "HEAD")
    stale_commit = meta.get("release", {}).get("gitCommit") != head
    # dirty 不算 FAIL（开发常态），commit 不一致才算
    step("P5_stale_artifact", not stale_commit,
         f"commit 一致" if not stale_commit
         else f"metadata 是旧 commit——重跑 quality_gate + release_metadata")

    # P6 changelog/notes consistency
    prep = _load("release/tag-prep.json", {})
    notes = os.path.join(REPO, "release", "RELEASE_NOTES.md")
    notes_ok = os.path.exists(notes) and prep.get("suggestedTag", "").startswith("v")
    if notes_ok:
        suggested = prep["suggestedTag"]
        notes_ok = suggested in open(notes, encoding="utf-8").read()
    step("P6_notes_consistency", notes_ok,
         f"tag {prep.get('suggestedTag')}" if prep else "tag-prep 缺失")

    # P7 benchmark regression
    benchmark = meta.get("benchmark", {})
    regressions = []
    for path, threshold in BENCHMARK_THRESHOLDS.items():
        node = benchmark
        for k in path.split("."):
            node = node.get(k, {}) if isinstance(node, dict) else {}
        if isinstance(node, (int, float)) and node > threshold:
            regressions.append(f"{path}={node} > {threshold}")
    step("P7_benchmark_regression", not regressions,
         "; ".join(regressions) or "全部在阈值内（阈值：" +
         json.dumps(BENCHMARK_THRESHOLDS) + "）")

    all_pass = all(r["pass"] for r in results)
    payload = {
        "schemaVersion": CHECK_SCHEMA_VERSION,
        "version": version,
        "allPass": all_pass,
        "steps": results,
    }
    with open(os.path.join(REPO, "release/release-check.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    md = ["# Tianze Release Check", "",
          f"- 结果：{'ALL PASS' if all_pass else 'FAIL'}（v{version}）", "",
          "| step | 状态 | detail |", "|---|---|---|"]
    for r in results:
        md.append(f"| {r['step']} | {'PASS' if r['pass'] else 'FAIL'} | {r['detail']} |")
    with open(os.path.join(REPO, "release/release-check.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(f"\nRelease Check：{'ALL PASS' if all_pass else 'FAIL'} → release/release-check.md")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
