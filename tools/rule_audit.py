"""M18 · Rule Audit：逐规则历史样本抽取与泛化检查。

数据源（真实工件，不重算）：case-replay.json / event-evaluation.json / rules.json。
每条 event 规则回答：
- 在哪些盘/案例出现（replay 样本，最多 8 条摘录）
- 什么条件触发（规则 conditions + label）
- 哪些案例支持/不同/沉默（relation 分布，按规则主题关联）
- 是否存在异常泛化（主题触发率 / replay 出现率超阈值 → REVIEW）

禁止根据历史案例自动调参迎合结果——本报告只描述。
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AUDIT_SCHEMA_VERSION = "1.0.0"


def main() -> int:
    rules = _load("knowledge/rules/event/rules.json", {"rules": []})["rules"]
    replay = _load("regression/case-replay.json", {"replays": [], "stats": {}})
    evaluation = _load("regression/event-evaluation.json", {})

    rates = evaluation.get("randomAudit", {}).get("ruleTriggerRate", {})
    theme_rates = evaluation.get("randomAudit", {}).get("themeTriggerRate", {})

    # replay 样本索引：rule → 出现的 replay（含该规则主题的对照关系）
    rule_occurrences: dict[str, list[dict]] = defaultdict(list)
    rule_relations: dict[str, Counter] = defaultdict(Counter)
    for rp in replay.get("replays", []):
        for t in rp.get("tianzeThemes", []):
            for rid in t.get("rules", []):
                sample = {
                    "caseId": rp["caseId"], "book": rp.get("book"),
                    "luck": rp.get("luck"), "annual": rp.get("annual"),
                    "theme": t["theme"], "status": t["status"],
                    "agreement": t.get("agreement"),
                }
                # 对照关系（同主题 claim 匹配）
                for m in rp.get("matches", []):
                    if m.get("theme") == t["theme"]:
                        sample["relation"] = m["relation"]
                        rule_relations[rid][m["relation"]] += 1
                rule_occurrences[rid].append(sample)

    rule_reports = []
    review_rules = []
    for r in rules:
        rid = r["id"]
        rate = rates.get(rid, 0.0)
        occurrences = rule_occurrences.get(rid, [])
        relations = dict(rule_relations.get(rid, {}))
        differs = relations.get("SOURCE_DIFFERS", 0)
        total_related = sum(relations.values())
        # 异常泛化信号（透明 heuristic，仅提示）：
        #   随机盘触发率 >60%，或 replay 中该规则主题的 DIFFERS 占比 >70%
        over_generalization = rate > 0.60 or (
            total_related >= 5 and differs / total_related > 0.70)
        if over_generalization:
            review_rules.append(rid)
        rule_reports.append({
            "ruleId": rid,
            "label": r.get("label", rid),
            "view": r.get("view"),
            "conditions": r.get("conditions", []),
            "provenanceLevels": sorted({p.get("level") for p in r.get("provenance", [])}),
            "randomTriggerRate": rate,
            "relationDistribution": relations,
            "occurrenceCount": len(occurrences),
            "samples": occurrences[:8],
            "overGeneralizationSignal": over_generalization,
        })

    payload = {
        "schemaVersion": AUDIT_SCHEMA_VERSION,
        "note": "只描述不调参：本报告不修改任何规则；relation 分布来自 replay 工件",
        "reviewRules": review_rules,
        "ruleCount": len(rule_reports),
        "rules": rule_reports,
    }
    with open("regression/rule-audit.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"Rule Audit：{len(rule_reports)} 条规则；"
          f"异常泛化信号 {review_rules or '无'}")
    return 0


def _load(path, default):
    if not os.path.exists(path):
        return default
    return json.load(open(path, encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
