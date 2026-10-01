"""M6.1 · 验证审计：182 条调候规则 → 验证矩阵统计 + Golden Set + Review Queue。

产出（全部确定性、可重跑）：
- knowledge/normalized/verification-audit.json   统计矩阵
- knowledge/golden/golden-rules.json             重点人工核验候选集（非"自动宣布正确"）
- review/knowledge-review.csv                    人工复核队列（优先级排序，不自动填 humanVerified）

运行：python tools/audit_verification.py
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parents[1]
RULES = REPO / "knowledge" / "rules" / "tiaohou" / "rules.json"
CONFLICTS = REPO / "knowledge" / "rules" / "tiaohou" / "conflicts.json"
NORM = REPO / "knowledge" / "normalized"
OUT_GOLDEN = REPO / "knowledge" / "golden"
OUT_REVIEW = REPO / "review"

SEASON_OF = {"寅": "spring", "卯": "spring", "辰": "spring",
             "巳": "summer", "午": "summer", "未": "summer",
             "申": "autumn", "酉": "autumn", "戌": "autumn",
             "亥": "winter", "子": "winter", "丑": "winter"}
STORES = {"辰", "戌", "丑", "未"}


def month_of(rule: dict) -> str:
    return next(c["value"] for c in rule["conditions"] if c["field"] == "monthBranch")


def main() -> int:
    rules = json.loads(RULES.read_text(encoding="utf-8"))["rules"]
    conflicts = json.loads(CONFLICTS.read_text(encoding="utf-8"))["conflicts"]
    conflict_rule_ids = {rid.removeprefix("TH-") for c in conflicts for rid in c["ruleIds"]}

    # ---------- 验证矩阵统计 ----------
    stats = Counter()
    by_source_kind: Counter = Counter()
    golden: dict[str, list[str]] = {
        "dayMasters": {}, "seasons": {}, "storeMonths": [],
        "ocrRisk": [], "conflicts": [], "conditionRules": [], "avoidOrException": [],
    }
    seen_day_master: set[str] = set()
    rows: list[dict] = []

    for rule in rules:
        v = rule["verification"]
        a = rule["accuracyMatrix"]
        stats["total"] += 1
        stats[f"verification.{v['status']}"] += 1
        stats[f"traceability.{a['traceability']}"] += 1
        stats[f"textAccuracy.{a['textAccuracy']}"] += 1
        stats[f"engineAccuracy.{a['engineAccuracy']}"] += 1
        # provenance 分层来源统计
        levels = {p["level"] for p in rule["provenance"]}
        for lv in levels:
            by_source_kind[lv] += 1
        if rule.get("normalizationNotes"):
            stats["withNormalizationNotes"] += 1
        if rule.get("conflictNote"):
            stats["withConflictNote"] += 1
        has_quote = any(p.get("note") for p in rule["provenance"] if p["level"] == "CLASSICAL_EXPLICIT")
        stats["withOriginalQuote" if has_quote else "withoutOriginalQuote"] += 1
        if rule["candidateId"] in conflict_rule_ids:
            stats["conflictRules"] += 1

        month = month_of(rule)
        dm = next(c["value"] for c in rule["conditions"] if c["field"] == "dayMaster")
        complex_cond = any(c["field"] not in ("dayMaster", "monthBranch") for c in rule["conditions"])
        has_exception = bool(rule.get("exceptions"))

        # ---------- Golden Set 选择（代表性，非"宣布正确"） ----------
        if dm not in seen_day_master:  # 每日主首条：保证十日主覆盖
            seen_day_master.add(dm)
            golden["dayMasters"].setdefault(dm, rule["id"])
        if SEASON_OF[month] not in golden["seasons"]:
            golden["seasons"][SEASON_OF[month]] = rule["id"]
        if month in STORES and len(golden["storeMonths"]) < 4:
            golden["storeMonths"].append(rule["id"])
        if a["textAccuracy"] == "OCR_RISK" and len(golden["ocrRisk"]) < 20:
            golden["ocrRisk"].append(rule["id"])
        if rule["candidateId"] in conflict_rule_ids:
            golden["conflicts"].append(rule["id"])
        if complex_cond:
            golden["conditionRules"].append(rule["id"])
        if has_exception:
            golden["avoidOrException"].append(rule["id"])

        # ---------- Review Queue 行 ----------
        priority = 0 if rule["candidateId"] in conflict_rule_ids else (
            1 if a["textAccuracy"] == "OCR_RISK" else (
                2 if has_quote else (3 if complex_cond else 4)))
        rows.append({
            "ruleId": rule["id"],
            "candidateId": rule["candidateId"],
            "book": rule["source"]["book"],
            "chapter": rule["source"].get("chapter") or "",
            "pages": ";".join(map(str, rule["source"].get("pages") or [])),
            "rawQuote": next((p["note"] for p in rule["provenance"] if p["level"] == "CLASSICAL_EXPLICIT"), ""),
            "normalizedTargets": ";".join(
                f"{e['targetStem']}({e['priority']})" for e in rule["effects"] if e["kind"] == "needStem"),
            "qualityGrade": rule["quality"],
            "ocrRisk": a["textAccuracy"] == "OCR_RISK",
            "conflictStatus": "CONFLICT" if rule["candidateId"] in conflict_rule_ids else (
                "NOTE" if rule.get("conflictNote") else ""),
            "verificationStatus": v["status"],
            "priority": priority,
            "notes": rule.get("conflictNote") or "",
        })

    rows.sort(key=lambda r: (r["priority"], r["ruleId"]))

    audit = {
        "schemaVersion": "1.1.0",
        "generatedBy": "tools/audit_verification.py",
        "stats": dict(stats),
        "provenanceLevels": dict(by_source_kind),
        "conflictsTotal": len(conflicts),
        "goldenSetSize": len({rid for ids in golden.values() for rid in (ids if isinstance(ids, list) else ids.values())}),
    }
    (NORM / "verification-audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=1), encoding="utf-8")

    OUT_GOLDEN.mkdir(parents=True, exist_ok=True)
    golden_payload = {
        "schemaVersion": "1.1.0",
        "purpose": "重点人工核验候选集合——不是自动宣布正确；进入 HUMAN_VERIFIED 须真人对照扫描件",
        "coverage": {"dayMasters": len(golden["dayMasters"]), "seasons": len(golden["seasons"]),
                     "storeMonths": len(set(golden["storeMonths"]))},
        "rules": golden,
    }
    (OUT_GOLDEN / "golden-rules.json").write_text(
        json.dumps(golden_payload, ensure_ascii=False, indent=1), encoding="utf-8")

    OUT_REVIEW.mkdir(parents=True, exist_ok=True)
    with (OUT_REVIEW / "knowledge-review.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    # 不自动填 humanVerified 列——留给未来真人（见 docs/knowledge/11）

    print(json.dumps(audit["stats"], ensure_ascii=False, indent=1))
    print("provenanceLevels:", dict(by_source_kind))
    print(f"golden candidates: {audit['goldenSetSize']} | review queue: {len(rows)} rows -> review/knowledge-review.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
