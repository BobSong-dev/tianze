"""M7 · 规则使用报告：每条规则匹配多少命例 / 明确引用 vs 引擎触发 / 零匹配规则 / 冲突案例。

产出：knowledge/normalized/rule-usage.json + docs/knowledge/09-RULE-USAGE.md
运行：python tools/analyze_rule_usage.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parents[1]
IDX = REPO / "knowledge" / "indexes" / "cases"
RULES = REPO / "knowledge" / "rules" / "tiaohou" / "rules.json"
CONFLICTS = REPO / "knowledge" / "rules" / "tiaohou" / "conflicts.json"
DOCS = REPO / "docs" / "knowledge"


def main() -> int:
    by_rule = json.loads((IDX / "byRule.json").read_text(encoding="utf-8"))["byRule"]
    rules = json.loads(RULES.read_text(encoding="utf-8"))["rules"]
    conflicts = json.loads(CONFLICTS.read_text(encoding="utf-8"))["conflicts"]
    conflict_rule_ids = {rid for c in conflicts for rid in c["ruleIds"]}

    usage = {}
    for cand_id, linked in sorted(by_rule.items()):
        usage[cand_id] = {
            "explicitlyCited": len(linked.get("EXPLICITLY_CITED", [])),
            "engineTriggered": len(linked.get("ENGINE_TRIGGERED", [])),
        }
    never_matched = [rid for rid in usage if usage[rid]["explicitlyCited"] == 0 and usage[rid]["engineTriggered"] == 0]

    # 单命例触发多冲突规则
    case_conflicts: Counter = Counter()
    for c in conflicts:
        for rid in c["ruleIds"]:
            exec_ids = [r["id"] for r in rules if r["candidateId"] == rid]
            for eid in exec_ids:
                for cid in by_rule.get(rid, {}).get("ENGINE_TRIGGERED", []):
                    case_conflicts[cid] += 1
    multi_conflict_cases = {cid: n for cid, n in case_conflicts.items() if n >= 2}

    report = {
        "schemaVersion": "1.1.0",
        "generatedBy": "tools/analyze_rule_usage.py",
        "rulesTotal": len(rules),
        "rulesWithEngineTrigger": sum(1 for u in usage.values() if u["engineTriggered"] > 0),
        "rulesNeverMatched": never_matched,
        "rulesNeverMatchedCount": len(never_matched),
        "explicitlyCitedCandidates": sum(1 for u in usage.values() if u["explicitlyCited"] > 0),
        "explicitCitationsTotal": sum(u["explicitlyCited"] for u in usage.values()),
        "multiConflictCases": multi_conflict_cases,
        "usage": usage,
    }
    (REPO / "knowledge" / "normalized" / "rule-usage.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    md = [
        "# 09 · 规则使用报告（RULE USAGE）",
        "",
        f"> 生成：tools/analyze_rule_usage.py（确定性可重跑）。数据：knowledge/normalized/rule-usage.json",
        "",
        "## 总览",
        "",
        f"- 可执行规则（调候）：{len(rules)} 条（对应 {len(usage)} 个引用键）",
        f"- 有 ENGINE_TRIGGERED 命例的规则：**{report['rulesWithEngineTrigger']}** 条",
        f"- 从未被任何命例匹配的规则：{report['rulesNeverMatchedCount']} 条（' + '、'.join(never_matched[:10]) + ('…' if len(never_matched) > 10 else '') + '）",
        f"- 被原书命例块明确引用的候选：{report['explicitlyCitedCandidates']} 个（引用 {report['explicitCitationsTotal']} 处）",
        f"- 触发 ≥2 组冲突规则的命例：{len(multi_conflict_cases)} 例",
        "",
        "## 口径警告",
        "",
        "- **ENGINE_TRIGGERED ≠ 古人明确用了这条规则**。它只说明 Tianze 引擎对该四柱触发了该规则；",
        "  原书是否据此判断属语义层问题，需人工复核（见 07-VERIFICATION-SYSTEM.md）。",
        "- EXPLICITLY_CITED 来自命例块『涉及规则』字段，是原书/整理者的明确引用。",
        "",
        "## 关系三态",
        "",
        "| 关系 | 含义 | 信任级别 |",
        "|---|---|---|",
        "| EXPLICITLY_CITED | 原书明确引用 | 高（仍属整理层） |",
        "| INFERRED_MATCH | 结构推断相关（预留，当前未自动填） | 低 |",
        "| ENGINE_TRIGGERED | Tianze 引擎触发 | 仅作统计，不可当古籍证据 |",
        "",
    ]
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "09-RULE-USAGE.md").write_text("\n".join(md), encoding="utf-8")
    print(f"rules={len(rules)} engineTriggered={report['rulesWithEngineTrigger']} "
          f"neverMatched={report['rulesNeverMatchedCount']} cited={report['explicitlyCitedCandidates']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
