"""M16 · Rule-ID 级 Conflict Graph 生成器。

节点：规则（event/temporal）+ 救应谓词。
边（全部有声明出处，无猜测）：
- conflict            conflicts.json 声明（resolution/specific/specificCondition）
- rescues             rescues.json：谓词 → 目标规则（effect: weaken/flip）
- school-conflict     同主题、不同 view 的规则对（流派分歧结构，方向由运行时判定）
- same-theme          同主题关系（弱边，供反查上下文）

输出：knowledge/rules/event/conflict-graph.json
完整性约束（测试锁定）：无自环；exception/specific 引用存在；school-conflict 无重复对。
"""

from __future__ import annotations

import glob
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

EVENT_DIR = os.path.join("knowledge", "rules", "event")


def main() -> int:
    rules: list[dict] = []
    for f in sorted(glob.glob("knowledge/rules/*/rules.json")):
        payload = json.load(open(f, encoding="utf-8"))
        for r in payload["rules"]:
            rules.append({
                "id": r["id"], "domain": r.get("domain"),
                "theme": r.get("theme") or r.get("category"),
                "view": r.get("view"),
                "label": r.get("label", r["id"]),
                "provenanceLevels": sorted({p["level"] for p in r.get("provenance", [])}),
                "candidateId": r.get("candidateId"),
            })
    rule_ids = {r["id"] for r in rules}

    conflicts = json.load(open(os.path.join(EVENT_DIR, "conflicts.json"), encoding="utf-8"))["conflicts"]
    rescues = json.load(open(os.path.join(EVENT_DIR, "rescues.json"), encoding="utf-8"))["rescues"]

    nodes = [{"type": "rule", **r} for r in rules]
    predicate_ids = sorted({d["predicate"] for d in rescues})
    nodes += [{"type": "predicate", "id": pid} for pid in predicate_ids]

    edges: list[dict] = []
    # 1) conflict 边
    for c in conflicts:
        edges.append({
            "type": "conflict", "between": [c["ruleA"], c["ruleB"]],
            "resolution": c.get("resolution"),
            "specific": c.get("specific"),
            "specificCondition": c.get("specificCondition"),
            "note": c.get("note", ""),
        })
    # 2) rescue 边（谓词 → 目标规则）
    for d in rescues:
        edges.append({
            "type": "rescues", "from": d["predicate"], "to": d["target"],
            "effect": d.get("effect", "weaken"), "note": d.get("note", ""),
        })
    # 3) school-conflict 边（同主题不同 view）
    seen_pairs = set()
    by_theme: dict[str, list[dict]] = {}
    for r in rules:
        if r.get("theme") and r.get("view"):
            by_theme.setdefault(r["theme"], []).append(r)
    for theme, rs in sorted(by_theme.items()):
        for i, a in enumerate(rs):
            for b in rs[i + 1:]:
                if a["view"] != b["view"]:
                    pair = frozenset({a["id"], b["id"]})
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        edges.append({
                            "type": "school-conflict", "between": [a["id"], b["id"]],
                            "views": [a["view"], b["view"]], "theme": theme,
                            "note": "同主题不同流派视角：方向冲突时保持 DISPUTED，不裁决",
                        })

    # 完整性校验
    problems = []
    for e in edges:
        ids = e.get("between") or ([e.get("from"), e.get("to")] if e.get("from") else [])
        for x in ids:
            if x not in rule_ids and x not in predicate_ids:
                problems.append(f"边引用不存在节点: {x}（{e['type']}）")
        if len(ids) >= 2 and ids[0] == ids[1]:
            problems.append(f"自环: {ids}")
    # exception/specific 引用必须存在
    for c in conflicts:
        if c.get("specific") and c["specific"] not in rule_ids:
            problems.append(f"specific 引用不存在: {c['specific']}")
        if c.get("specificCondition") and c["specificCondition"] not in predicate_ids:
            problems.append(f"specificCondition 引用不存在: {c['specificCondition']}")

    graph = {
        "schemaVersion": "1.0.0",
        "nodeCount": len(nodes),
        "edgeCount": len(edges),
        "edgeTypes": dict(Counter(e["type"] for e in edges)),
        "problems": problems,
        "nodes": nodes,
        "edges": edges,
    }
    with open(os.path.join(EVENT_DIR, "conflict-graph.json"), "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=1)
    print(f"Conflict Graph：{len(nodes)} 节点 / {len(edges)} 边 {graph['edgeTypes']}")
    if problems:
        for p in problems:
            print("  PROBLEM:", p)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
