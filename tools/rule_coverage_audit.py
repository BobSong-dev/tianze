"""M19 · Rule Coverage / Dead Rule 分析（216 条 ExecutableRule 全分类）。

分类（透明 heuristic，全部进 REVIEW 清单，不自动删除/调整规则）：
- never_triggered   从未触发（探针+replay 均无）
- low_trigger       触发率 <2%
- high_trigger      触发率 >60%
- no_case_coverage  无任何 Case 覆盖（tiaohou：case engineRuleIds；event：replay ruleChains）
- only_silent       主题在 replay 中只有 SOURCE_SILENT
- high_differs      DIFFERS 占比 >70%（≥5 例）
- high_conflict     conflict/school-conflict 度 ≥2
- high_rescue_dep   被 ≥2 个救应谓词指向

数据源：event-evaluation（随机盘触发率）/ case-replay（replay 覆盖）/
case_regression baseline（tiaohou triggeredRuleIds）/ conflict-graph。
输出：regression/rule-coverage-audit.json + review 入口。
"""

from __future__ import annotations

import glob
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AUDIT_SCHEMA_VERSION = "1.0.0"


def _load(path, default):
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), path)
    if not os.path.exists(p):
        return default
    return json.load(open(p, encoding="utf-8"))


def main() -> int:
    rules = []
    for f in sorted(glob.glob("knowledge/rules/*/rules.json")):
        payload = json.load(open(f, encoding="utf-8"))
        for r in payload["rules"]:
            rules.append({**r, "_file": os.path.basename(os.path.dirname(f))})
    evaluation = _load("regression/event-evaluation.json", {})
    rates = evaluation.get("randomAudit", {}).get("ruleTriggerRate", {})
    replay = _load("regression/case-replay.json", {"replays": []})
    graph = _load("knowledge/rules/event/conflict-graph.json", {"edges": []})
    rescues = _load("knowledge/rules/event/rescues.json", {"rescues": []}).get("rescues", [])

    # replay 覆盖（event 规则）：出现次数 + relation 分布（按规则主题）
    rule_occ: Counter = Counter()
    rule_relation: dict[str, Counter] = defaultdict(Counter)
    for rp in replay.get("replays", []):
        theme_relations = {m["theme"]: m["relation"] for m in rp.get("matches", [])}
        for t in rp.get("tianzeThemes", []):
            for rid in t.get("rules", []):
                rule_occ[rid] += 1
                rel = theme_relations.get(t["theme"])
                if rel:
                    rule_relation[rid][rel] += 1

    # tiaohou case 覆盖：baseline 的 triggeredRuleIds
    tiaohou_cases: Counter = Counter()
    baseline = _load("regression/baseline/snapshot.json", {"snapshots": []})
    for snap in baseline.get("snapshots", []):
        for rid in snap.get("triggeredRuleIds", []) or []:
            tiaohou_cases[rid] += 1

    # conflict 度 / rescue 依赖
    conflict_degree: Counter = Counter()
    for e in graph.get("edges", []):
        if e.get("type") in ("conflict", "school-conflict"):
            for x in e.get("between", []):
                conflict_degree[x] += 1
    rescue_dep: Counter = Counter()
    for d in rescues:
        rescue_dep[d["target"]] += 1

    classifications: dict[str, list[str]] = defaultdict(list)
    for r in rules:
        rid = r["id"]
        domain = r.get("domain")
        rate = rates.get(rid)
        occ = rule_occ.get(rid, 0)
        case_cov = tiaohou_cases.get(rid, 0) if domain == "tiaohou" else occ

        if domain == "event" and rate == 0.0 and occ == 0:
            classifications["never_triggered"].append(rid)
        elif domain == "event" and rate is not None and 0 < rate < 0.02:
            classifications["low_trigger"].append(rid)
        if rate is not None and rate > 0.60:
            classifications["high_trigger"].append(rid)
        if case_cov == 0:
            classifications["no_case_coverage"].append(rid)
        rels = rule_relation.get(rid, {})
        total_rel = sum(rels.values())
        if total_rel >= 3 and rels.get("SOURCE_SILENT", 0) == total_rel:
            classifications["only_silent"].append(rid)
        if total_rel >= 5 and rels.get("SOURCE_DIFFERS", 0) / total_rel > 0.70:
            classifications["high_differs"].append(rid)
        if conflict_degree.get(rid, 0) >= 2:
            classifications["high_conflict"].append(rid)
        if rescue_dep.get(rid, 0) >= 2:
            classifications["high_rescue_dep"].append(rid)

    # 事件规则触发率补零（未触发=0.0，dead-rule 分析需要显式 0 而非缺席）
    for r in rules:
        if r.get("domain") == "event" and r["id"] not in rates:
            rates[r["id"]] = 0.0

    payload = {
        "schemaVersion": AUDIT_SCHEMA_VERSION,
        "discipline": "全部分类进入 REVIEW 清单；不自动删除/调整任何规则",
        "ruleCount": len(rules),
        "classifications": {k: sorted(v) for k, v in sorted(classifications.items())},
        "classificationCounts": {k: len(v) for k, v in sorted(classifications.items())},
        "triggerRates": rates,
        "replayOccurrences": {k: v for k, v in sorted(rule_occ.items())},
        "tiaohouCaseCoverage": len(tiaohou_cases),
    }
    with open("regression/rule-coverage-audit.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"Rule Coverage Audit：{len(rules)} 条规则 → {payload['classificationCounts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
