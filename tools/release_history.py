"""M20/M21 · Release History：每次 RC/release 追加版本化记录。

数据全部来自真实工件（metadata/quality-summary/audit-gates/benchmark）。
输出：release/release-history.jsonl
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIST = os.path.join(REPO, "release", "release-history.jsonl")


def _load(rel, default):
    p = os.path.join(REPO, rel)
    if not os.path.exists(p):
        return default
    return json.load(open(p, encoding="utf-8"))


def main() -> int:
    import tianze
    meta = _load("release/release-metadata.json", None)
    internal = "--gate-progress" in sys.argv
    path = sys.argv[sys.argv.index("--gate-progress") + 1] if internal else "release/quality-summary.json"
    qg = _load(path, None)
    rc = _load("release/release-check.json", None)
    tag_prep = _load("release/tag-prep.json", {})
    if not meta:
        print("BLOCKED：release metadata 缺失（先 quality_gate + release_metadata）")
        return 2
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, encoding="utf-8", cwd=REPO).stdout.strip()
    entry = {
        "schemaVersion": "1.0.0",
        "version": tianze.__version__,
        "tagSuggested": tag_prep.get("suggestedTag"),
        "commit": head,
        "counts": meta.get("counts", {}),
        "schemaVersions": meta.get("versions", {}),
        "qualityGate": {"allPass": None if internal else (qg or {}).get("allPass"),
                        "phase": (qg or {}).get("phase"),
                        "steps": len((qg or {}).get("steps", []))},
        "releaseCheck": {"allPass": (rc or {}).get("allPass")},
        "auditGatesAllPass": meta.get("quality", {}).get("allGatesPass"),
        "benchmark": meta.get("benchmark", {}),
        "aiEvaluation": meta.get("governance", {}).get("aiEvaluationStatus"),
        "migration": {"historyExists":
                      os.path.exists(os.path.join(REPO, "regression/migration-history.jsonl"))},
    }
    with open(HIST, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + chr(10))
    print(f"Release History：v{entry['version']} @ {head[:12]} 已记录 → release-history.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
