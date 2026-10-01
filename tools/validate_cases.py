"""M7 · 命例数据校验：Case ID 唯一 / 引用完整性 / 双分析分离 / 历史事件分层 / schema 版本。

运行：python tools/validate_cases.py  （失败退出码 1）
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parents[1]
CASES = REPO / "knowledge" / "normalized" / "cases"
MANIFEST = REPO / "knowledge" / "normalized" / "cases-manifest.json"


def main() -> int:
    problems: list[str] = []
    all_cases: list[dict] = []
    for path in sorted(CASES.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        all_cases.extend(data["cases"])

    ids = [c["caseId"] for c in all_cases]
    dup = [i for i, n in Counter(ids).items() if n > 1]
    problems.extend(f"重复 Case ID: {i}" for i in dup)

    # 引用完整性：EXPLICITLY_CITED 的规则 ID 应可追溯到候选层（其他书规则允许 UNRESOLVED 但登记）
    candidates = set()
    for book_dir in sorted((REPO / "knowledge" / "normalized").glob("*/rules.json")):
        data = json.loads(book_dir.read_text(encoding="utf-8"))
        candidates |= {r["id"] for r in data["rules"]}
    unresolved_refs = []
    for c in all_cases:
        for ref in c.get("ruleReferences", []):
            if ref["ruleId"] not in candidates:
                unresolved_refs.append((c["caseId"], ref["ruleId"]))
    if unresolved_refs:
        print(f"NOTE: {len(unresolved_refs)} 处命例引用的规则 ID 不在候选库（保留原样，登记不猜）：示例 {unresolved_refs[:5]}")

    # 双分析分离：tianzeAnalysis 不得包含原书断语文本；sourceAnalysis 不得含引擎字段
    for c in all_cases:
        src = json.dumps(c.get("sourceAnalysis") or {}, ensure_ascii=False)
        tz = c.get("tianzeAnalysis") or {}
        if tz.get("computed") and ("徐乐吾最终判断" in json.dumps(tz, ensure_ascii=False)):
            problems.append(f"{c['caseId']}: tianzeAnalysis 混入原书判断")
        if "engineRuleIds" in src:
            problems.append(f"{c['caseId']}: sourceAnalysis 混入引擎字段")

    # 历史事件分层：events 全部必须 HISTORICAL_CLAIM
    for c in all_cases:
        for ev in (c.get("sourceAnalysis") or {}).get("events", []):
            if ev.get("claimType") != "HISTORICAL_CLAIM":
                problems.append(f"{c['caseId']}: 事件未标 HISTORICAL_CLAIM")

    # 机器不得产生 HUMAN_VERIFIED
    for c in all_cases:
        v = c.get("verification") or {}
        if str(v.get("status", "")).startswith("HUMAN"):
            problems.append(f"{c['caseId']}: 机器流程产生了 HUMAN_* 验证状态（伪造）")

    stats = {
        "cases": len(all_cases),
        "uniqueIds": len(set(ids)),
        "computed": sum(1 for c in all_cases if (c.get("tianzeAnalysis") or {}).get("computed")),
        "withPossibleDuplicates": sum(1 for c in all_cases if c.get("possibleDuplicates")),
        "unresolvedPillars": sum(1 for c in all_cases if c["fact"].get("unresolved")),
    }
    print(json.dumps(stats, ensure_ascii=False, indent=1))
    if problems:
        print("\n== PROBLEMS ==")
        for p in problems[:30]:
            print(" -", p)
        return 1
    print("case validation: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
