"""M21 · Rescue / Exception Coverage 审计。

回答任务书四问（全部来自真实声明与随机盘，只报告不调参）：
- 哪些 event rule 已有 rescue（rescues.json 按 target 汇总）
- 哪些 classical exception 尚未结构化（有 CLASSICAL provenance 但无 specificCondition
  声明、且 conflictNote 含「例外/救应/救应法」语义的规则）
- 哪些 specific condition 仍依赖粗粒度 heuristic（specificCondition 谓词为强度类）
- 哪些 conflict 永远 keep-both（resolution 分布）

输出：regression/rescue-coverage.json
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCHEMA_VERSION = "1.0.0"

_HEURISTIC_PREDICATES = {"wealth_favorable", "wealth_unfavorable",
                         "sha_weak_body_strong"}   # 强度类映射（ADR-049）


def _load(rel, default):
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), rel)
    if not os.path.exists(p):
        return default
    return json.load(open(p, encoding="utf-8"))


def main() -> int:
    rules = _load("knowledge/rules/event/rules.json", {"rules": []})["rules"]
    rescues = _load("knowledge/rules/event/rescues.json", {"rescues": []}).get("rescues", [])
    conflicts = _load("knowledge/rules/event/conflicts.json", {"conflicts": []})["conflicts"]

    by_target: dict[str, list[dict]] = defaultdict(list)
    for d in rescues:
        by_target[d.get("target")].append(d)

    cond_predicates = {c.get("specificCondition") for c in conflicts
                       if c.get("specificCondition")}
    heuristic_conds = sorted(cond_predicates & _HEURISTIC_PREDICATES)

    # 未结构化的经典例外候选：有 CLASSICAL 引文 + conflictNote 提示例外语义 + 无 specificCondition
    unstructured = []
    note_markers = ("例外", "救应", "救", "有救", "非可一例", "须察")
    rule_ids = {r["id"] for r in rules}
    cond_pairs = {frozenset({c.get("ruleA"), c.get("ruleB")}) for c in conflicts}
    for r in rules:
        has_classical = any(p.get("level") == "CLASSICAL_EXPLICIT" for p in r.get("provenance", []))
        note = r.get("conflictNote") or ""
        if not (has_classical and any(m in note for m in note_markers)):
            continue
        in_cond_pair = any(r["id"] in pair and any(
            c.get("specificCondition") for c in conflicts
            if frozenset({c.get("ruleA"), c.get("ruleB")}) == pair)
            for pair in cond_pairs if r["id"] in pair)
        if not in_cond_pair:
            unstructured.append({
                "ruleId": r["id"], "note": note[:100],
                "hint": "有经典例外/救应语义但未启用 specificCondition——需更强文献支撑再结构化",
            })

    resolution_dist = Counter(c.get("resolution") for c in conflicts)

    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "ruleCount": len(rules),
        "rescuedRules": {rid: [{"id": d["id"], "predicate": d["predicate"],
                                "effect": d.get("effect")} for d in ds]
                         for rid, ds in sorted(by_target.items())},
        "rescueCoverage": {"rescued": len(by_target), "total": len(rules),
                           "ratio": round(len(by_target) / max(1, len(rules)), 3)},
        "heuristicConditionPredicates": heuristic_conds,
        "keepBothConflicts": [c.get("ruleA", "") + "×" + c.get("ruleB", "")
                              for c in conflicts if c.get("resolution") == "keep-both"],
        "resolutionDistribution": dict(resolution_dist),
        "unstructuredClassicalExceptions": unstructured,
        "note": "审计只报告；证据不足保持现状（宁缺毋滥，ADR-049）",
    }
    with open("regression/rescue-coverage.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"Rescue Coverage：{len(by_target)}/{len(rules)} 规则有救应；"
          f"heuristic 谓词 {heuristic_conds}；keep-both {payload['keepBothConflicts'].__len__()}；"
          f"未结构化经典例外 {len(unstructured)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
