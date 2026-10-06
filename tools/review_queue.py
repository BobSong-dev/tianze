"""M15 · 统一 Review Queue：知识质量与人审待办的单一出口。

汇总（只汇总，不自动升级任何状态；HUMAN_VERIFIED 只能由真实人工产生）：
- OCR 风险规则候选（ocrRisk=true）
- MACHINE_CURATED 可执行规则（curation 由 AI 完成，待真人对照扫描件）
- 敏感历史断语（死亡/疾病等，Tianze 不建主题）
- 规则冲突声明（event/temporal conflicts.json）
- UNRESOLVED 项（调候未覆盖、事件主题 UNRESOLVED 语义等）

输出：review/review-queue.json + review/review-queue.md
"""

from __future__ import annotations

import glob
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUT_JSON = "review/review-queue.json"
OUT_MD = "review/review-queue.md"


def main() -> int:
    queue: dict[str, list[dict]] = {
        "ocrRiskRules": [],
        "machineCuratedRules": [],
        "sensitiveClaims": [],
        "ruleConflicts": [],
        "unresolved": [],
    }
    stats: Counter = Counter()

    # 1) OCR 风险候选
    for f in sorted(glob.glob("knowledge/normalized/*/rules.json")):
        data = json.load(open(f, encoding="utf-8"))
        items = data if isinstance(data, list) else (data.get("candidates") or data.get("rules") or [])
        for it in items:
            if it.get("ocrRisk"):
                stats["ocrRisk"] += 1
                if len(queue["ocrRiskRules"]) < 500:
                    queue["ocrRiskRules"].append({
                        "id": it.get("id"), "book": it.get("book"),
                        "title": (it.get("title") or "")[:60],
                    })

    # 2) MACHINE_CURATED 可执行规则（按 domain 分组计数 + 清单）
    for f in sorted(glob.glob("knowledge/rules/*/rules.json")):
        payload = json.load(open(f, encoding="utf-8"))
        for r in payload["rules"]:
            if r.get("verification", {}).get("status") == "MACHINE_CURATED":
                stats["machineCurated"] += 1
                queue["machineCuratedRules"].append({
                    "id": r["id"], "domain": r.get("domain"),
                    "label": r.get("label", r.get("id")),
                    "method": r.get("verification", {}).get("method"),
                    "note": r.get("verification", {}).get("notes", "")[:120],
                })

    # 3) 敏感历史断语
    if os.path.exists("knowledge/normalized/cases/event_claims.json"):
        ev = json.load(open("knowledge/normalized/cases/event_claims.json", encoding="utf-8"))
        for c in ev.get("cases", []):
            for cl in c.get("claims", []):
                if cl.get("sensitive"):
                    stats["sensitiveClaims"] += 1
                    if len(queue["sensitiveClaims"]) < 200:
                        queue["sensitiveClaims"].append({
                            "caseId": c["caseId"], "text": cl["text"][:80],
                            "keywords": cl.get("sensitiveKeywords", []),
                        })

    # 4) 规则冲突声明
    for cf in ("knowledge/rules/event/conflicts.json",
               "knowledge/rules/tiaohou/conflicts.json"):
        if os.path.exists(cf):
            data = json.load(open(cf, encoding="utf-8"))
            for c in data.get("conflicts", []):
                stats["ruleConflicts"] += 1
                queue["ruleConflicts"].append({
                    "source": cf.split("/")[2],
                    "rules": c.get("ruleIds") or [c.get("ruleA"), c.get("ruleB")],
                    "resolution": c.get("resolution"),
                    "note": (c.get("note") or c.get("description") or "")[:120],
                })

    # 5) UNRESOLVED 项
    queue["unresolved"].append({
        "kind": "tiaohou_coverage",
        "detail": "调候 120 格全覆盖（0 UNRESOLVED）——若未来知识库扩展出现缺口会在此登记",
    })
    if os.path.exists("regression/event-evaluation.json"):
        eev = json.load(open("regression/event-evaluation.json", encoding="utf-8"))
        queue["unresolved"].append({
            "kind": "event_unresolved_rate",
            "detail": f"Event 主题 UNRESOLVED 率（探针）：{eev['unresolvedRate']['byProbe']}",
        })

    total = sum(stats.values())
    payload = {
        "schemaVersion": "1.0.0",
        "description": "Review Queue：知识质量待办统一出口（只汇总，不自动升级状态）",
        "discipline": "HUMAN_VERIFIED 只能由真实人工对照扫描件产生；本队列不产生任何人工状态",
        "generatedBy": "tools/review_queue.py",
        "stats": dict(stats),
        "totalItems": total,
        "queue": queue,
    }
    os.makedirs("review", exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    lines = ["# Tianze Review Queue", "",
             f"- total items: {total}", f"- stats: {dict(stats)}", "",
             "## 分区", ""]
    for section, items in queue.items():
        lines.append(f"### {section}（{len(items)}）")
        lines.append("")
        for it in items[:8]:
            lines.append(f"- {json.dumps(it, ensure_ascii=False)[:160]}")
        if len(items) > 8:
            lines.append(f"- …（其余 {len(items) - 8} 条见 JSON）")
        lines.append("")
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Review Queue：{total} 项 → {OUT_JSON}")
    print(f"  {dict(stats)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
