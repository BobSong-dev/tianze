"""M18 · Release Metadata：一键生成机器可读 JSON + Markdown 发布报告。

全部数据来自真实运行（git/工具工件/pytest 采集），无硬编码统计。
"""

from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _git(*args) -> str:
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", cwd=REPO
                              ).stdout.strip()
    except Exception:
        return ""


def _load(path, default):
    path = os.path.join(REPO, path)
    if not os.path.exists(path):
        return default
    return json.load(open(path, encoding="utf-8"))


def _count_tests() -> int:
    try:
        r = subprocess.run([os.path.join(REPO, ".venv", "Scripts", "python.exe"),
                            "-m", "pytest", "tests", "apps/api/tests",
                            "--collect-only", "-q"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", cwd=REPO, timeout=180)
        for line in r.stdout.strip().split("\n"):
            if "tests collected" in line or line.endswith(" tests"):
                return int(line.split()[0])
        return 0
    except Exception:
        return 0


def main() -> int:
    import tianze
    from tianze.knowledge.models import KNOWLEDGE_SCHEMA_VERSION, CASE_SCHEMA_VERSION
    from tianze.ai.models import INTERPRETATION_SCHEMA_VERSION, PROMPT_VERSION
    from tianze.analysis.temporal_delta import DELTA_SCHEMA_VERSION
    from tianze.analysis.event_themes import EVENT_THEME_SCHEMA_VERSION

    rules = []
    for f in sorted(glob.glob(os.path.join(REPO, "knowledge/rules/*/rules.json"))):
        payload = _load(os.path.relpath(f, REPO), {"rules": []})
        for r in payload.get("rules", []):
            rules.append(r)
    by_domain = Counter(r.get("domain") for r in rules)

    candidates = 0
    for f in sorted(glob.glob(os.path.join(REPO, "knowledge/normalized/*/rules.json"))):
        data = _load(os.path.relpath(f, REPO), [])
        items = data if isinstance(data, list) else (data.get("candidates") or data.get("rules") or [])
        candidates += len(items)

    case_total = 0
    for f in sorted(glob.glob(os.path.join(REPO, "knowledge/normalized/cases/*.json"))):
        if any(x in f for x in ("temporal_refs", "event_claims", "raw_temporal_spans")):
            continue
        data = _load(os.path.relpath(f, REPO), {})
        case_total += len(data.get("cases", []))

    audit = _load("regression/audit-gates.json", {})
    case_reg = _load("regression/report.json", {})
    temporal_reg = _load("regression/temporal-compare.json", {})
    benchmark = _load("regression/benchmark.json", {})
    replay = _load("regression/case-replay.json", {"count": 0, "stats": {}})
    migration_hist = os.path.exists(os.path.join(REPO, "regression/migration-history.jsonl"))
    ai_eval = _load("regression/ai-evaluation.json", {"provider": "unknown"})

    metadata = {
        "schemaVersion": "1.0.0",
        "release": {
            "gitCommit": _git("rev-parse", "HEAD"),
            "gitBranch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty": bool(_git("status", "--porcelain")),
            "generatedBy": "tools/release_metadata.py（全部数据来自真实运行）",
        },
        "engineVersion": tianze.__version__,
        "versions": {
            "knowledge": KNOWLEDGE_SCHEMA_VERSION,
            "case": CASE_SCHEMA_VERSION,
            "analysis": "1.0.0",
            "delta": DELTA_SCHEMA_VERSION,
            "event": EVENT_THEME_SCHEMA_VERSION,
            "interpretation": INTERPRETATION_SCHEMA_VERSION,
            "prompt": PROMPT_VERSION,
            "python": sys.version.split()[0],
        },
        "counts": {
            "executableRules": len(rules),
            "rulesByDomain": dict(by_domain),
            "ruleCandidates": candidates,
            "cases": case_total,
            "replays": replay.get("count", 0),
            "tests": _count_tests(),
        },
        "quality": {
            "auditGates": {k: v.get("pass") for k, v in (audit.get("gates") or {}).items()},
            "allGatesPass": audit.get("allPass"),
            "caseRegressionSeverity": case_reg.get("severityCounts", {}),
            "temporalRegressionSeverity": temporal_reg.get("severityCounts", {}),
            "eventEvaluationProblems": _load("regression/event-evaluation.json", {}).get("problems", []),
        },
        "benchmark": benchmark,
        "governance": {
            "migrationRanBefore": migration_hist,
            "aiEvaluationStatus": ai_eval.get("provider", "unknown"),
        },
    }

    os.makedirs(os.path.join(REPO, "release"), exist_ok=True)
    with open(os.path.join(REPO, "release/release-metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=1)

    md = [
        "# Tianze Release Report", "",
        f"- commit: `{metadata['release']['gitCommit'][:12]}`"
        f"（{'含未提交改动' if metadata['release']['dirty'] else '工作区干净'}）",
        f"- engine: {metadata['engineVersion']}",
        f"- versions: {metadata['versions']}", "",
        "## 规模", "",
        f"- ExecutableRule：**{metadata['counts']['executableRules']}**"
        f"（{metadata['counts']['rulesByDomain']}）",
        f"- RuleCandidate：{metadata['counts']['ruleCandidates']}（不同口径）",
        f"- 命例：{metadata['counts']['cases']}；Replay：{metadata['counts']['replays']}",
        f"- 测试：{metadata['counts']['tests']}", "",
        "## 质量状态", "",
        f"- Audit Gates：{'ALL PASS' if metadata['quality']['allGatesPass'] else 'FAIL'}",
        f"- Case Regression：{metadata['quality']['caseRegressionSeverity'] or '无变化'}",
        f"- Temporal Regression：{metadata['quality']['temporalRegressionSeverity'] or '无变化'}",
        f"- Event Evaluation problems：{metadata['quality']['eventEvaluationProblems'] or '无'}",
        f"- AI Evaluation：{metadata['governance']['aiEvaluationStatus']}", "",
        "## 基准", "",
        "```json", json.dumps(benchmark, ensure_ascii=False, indent=1), "```",
    ]
    with open(os.path.join(REPO, "release/release-report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(json.dumps({"counts": metadata["counts"], "quality": metadata["quality"]},
                     ensure_ascii=False, indent=1))
    print("→ release/release-metadata.json + release/release-report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
