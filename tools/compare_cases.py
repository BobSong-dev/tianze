"""M7 · 命例对比：sourceAnalysis vs tianzeAnalysis——只记录，不裁决谁对。

机械化、可辩护的对比仅有两类：
1. EXPLICITLY_CITED 规则的效果目标干 vs 引擎触发规则的效果目标干（同格条件）；
2. 其余全部进 unresolved（语义对比待人工）。
运行：python tools/compare_cases.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parents[1]
CASES = REPO / "knowledge" / "normalized" / "cases"
OUT = REPO / "knowledge" / "normalized" / "case-comparisons.json"


def main() -> int:
    rules = json.loads((REPO / "knowledge" / "rules" / "tiaohou" / "rules.json").read_text(encoding="utf-8"))["rules"]
    effects_of: dict[str, list[str]] = {}
    for r in rules:
        effects_of[r["id"]] = [e["targetStem"] for e in r["effects"] if e["kind"] == "needStem" and e.get("targetStem")]

    comparisons = []
    # 口径（M8.0 修正）：caseCount=案例数；comparisonItem/agreementItem/differenceItem=比较项数。
    # 一例可同时产生一致项与差异项，故 item 数之和可与案例数不等。
    stats = {"caseCount": 0, "withSourceClaims": 0, "mechanicallyComparedCaseCount": 0,
             "comparisonItemCount": 0, "agreementItemCount": 0, "differenceItemCount": 0}
    for path in sorted(CASES.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for case in data["cases"]:
            stats["caseCount"] += 1
            src = case.get("sourceAnalysis") or {}
            tz = case.get("tianzeAnalysis") or {}
            claims = []
            if src.get("verdict"):
                claims.append(f"作者判断：{src['verdict'][:60]}")
            for ev in src.get("events", []):
                claims.append(f"事件(HISTORICAL_CLAIM)：{ev['text'][:40]}")
            results = []
            if tz.get("computed"):
                results.append(f"旺衰 {tz.get('strengthVerdicts', {}).get('weighted')}/"
                               f"{tz.get('strengthVerdicts', {}).get('fuyi')}")
                if tz.get("patternCandidate"):
                    results.append(f"格局候选 {tz['patternCandidate']}({tz.get('patternStatus')})")
                if tz.get("tiaohouTargets"):
                    results.append(f"调候目标 {'、'.join(tz['tiaohouTargets'])}")

            agreements, differences, unresolved = [], [], []
            # 机械化对比：命例明确引用的规则（候选 ID → 各格 ExecutableRule）效果干
            # vs 引擎调候目标干——两侧同时存在才比
            cited = [ref["ruleId"] for ref in case.get("ruleReferences", [])]
            engine_targets = set(tz.get("tiaohouTargets") or [])
            cited_targets: set[str] = set()
            for cand in cited:
                for rid, effs in effects_of.items():
                    if rid.startswith(f"TH-{cand}-"):
                        cited_targets |= set(effs)
            if cited and engine_targets and cited_targets:
                stats["mechanicallyComparedCaseCount"] += 1
                hit = cited_targets & engine_targets
                miss = engine_targets - cited_targets
                if hit:
                    agreements.append(f"双方均指向目标干 {'、'.join(sorted(hit))}")
                if miss:
                    differences.append(f"引擎目标 {'、'.join(sorted(miss))} 未见于引用规则效果（口径差异，仅记录）")
                stats["comparisonItemCount"] += len(hit) + len(miss)

            if not agreements and not differences:
                unresolved.append("语义级对比（作者断语 vs 引擎结论）需人工复核，本轮不自动判定")
            if claims:
                stats["withSourceClaims"] += 1
            stats["agreementItemCount"] += len(agreements)
            stats["differenceItemCount"] += len(differences)
            comparisons.append({
                "caseId": case["caseId"],
                "sourceClaims": claims,
                "engineResults": results,
                "agreements": agreements,
                "differences": differences,
                "unresolved": unresolved,
            })

    payload = {"schemaVersion": "1.0.0", "generatedBy": "tools/compare_cases.py",
               "note": "只记录差异与一致，不裁决 Tianze 或古籍谁正确",
               "stats": stats, "comparisons": comparisons}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
