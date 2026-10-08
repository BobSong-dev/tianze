"""M25 · 关系引文注册表：从 normalized 候选机械提取（不手写引文）。

知识链路：knowledge/normalized/{DTZ,ZP,SPZY}/rules.json（引文原文所在）
      → tools/build_relation_citations.py
      → knowledge/rules/relations/citations.json（引擎运行时引用）

纪律：
- 引文逐字复制自 normalized 候选（originalQuotes/coreText 摘录），不手工改写；
- 每条带 sourceFile/quality/ocrRisk，可回溯到知识库条目；
- 公版关系表（R9/R10/R13/R14）无独立古籍条目 → 以 CANONICAL_TABLE 条目登记口径。
"""

from __future__ import annotations

import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "knowledge", "rules", "relations", "citations.json")

# 关系类型/条件 → 引文候选 id（normalized 层）
CITATION_SOURCES = {
    "DTZ-10": "arch 主引文（暗冲暗会/拱实不若拱虚）",
    "ZP-05": "拱禄拱贵条件与填实禁则（集于一点/忌刑冲填实）",
    "SPZY-34": "暗合逐对表（两支毗连各取禄旺之气/非以化论）",
    "DTZ-26": "拱夹联珠暗冲遥合不成为格（边界）",
    "DTZ-36": "夹拱遥合非格局非用神（边界）",
    "DTZ-41": "填实破格与伤官变格辨正（外格边界）",
    "ZP-07": "刑合格起例与争议（OCR 残缺）",
    "ZP-11": "子邀巳虚神邀合（OCR 残缺）",
    "ZP-12": "井栏叉/倒冲格（庚日得禄之地，OCR 残缺）",
    "SS-R17": "天乙贵人阳贵阴贵起例（歌诀逐字）",
    "SS-R16": "天乙贵人成格三要件（见合/交互得/生旺无冲破）",
    "ZP-06": "六乙鼠贵（印煞临天乙，忌官煞刑冲）",
}

CANONICAL_TABLES = {
    "R9": {"kind": "CANONICAL_TABLE", "book": "Tianze 关系表（relation/tables.py）",
           "quote": "冲/害/破/刑/三合三会逐对公版口径（多重关系并存不裁决）"},
    "R10": {"kind": "CANONICAL_TABLE", "book": "Tianze 关系表（relation/tables.py）",
            "quote": "三合半合须含中神"},
    "R13": {"kind": "CANONICAL_TABLE", "book": "Tianze 关系表（relation/tables.py）",
            "quote": "干合/六合只报化气候选，不判化气成立"},
    "R14": {"kind": "CANONICAL_TABLE", "book": "Tianze 关系表（relation/tables.py）",
            "quote": "天干四冲（戊己土居中不冲）"},
}


def _load(book: str) -> dict[str, dict]:
    path = os.path.join(REPO, "knowledge", "normalized", book, "rules.json")
    payload = json.load(open(path, encoding="utf-8"))
    return {r["id"]: r for r in payload["rules"]}


def main() -> int:
    books = {}
    for book in ("DTZ", "ZP", "SPZY", "SS"):
        books.update(_load(book))
    citations = {}
    for cid, purpose in CITATION_SOURCES.items():
        r = books.get(cid)
        if r is None:
            print(f"BLOCKED：normalized 候选 {cid} 不存在")
            return 2
        quotes = r.get("originalQuotes") or []
        core = (r.get("coreText") or "").strip()
        citations[cid] = {
            "candidateId": cid,
            "book": r.get("book") or cid.split("-")[0],
            "title": r.get("title", ""),
            "purpose": purpose,
            "quote": (quotes[0] if quotes else core)[:220],
            "sourceFile": r.get("sourceFile", ""),
            "quality": r.get("quality", ""),
            "ocrRisk": bool(r.get("ocrRisk", False)),
            "sourceKind": "CLASSICAL_EXPLICIT",
        }
    for rid, entry in CANONICAL_TABLES.items():
        citations[rid] = {
            "candidateId": rid, "book": entry["book"], "title": "公版关系表",
            "purpose": f"关系口径 {rid}", "quote": entry["quote"],
            "sourceFile": "tianze/relation/tables.py", "quality": "-",
            "ocrRisk": False, "sourceKind": entry["kind"],
        }
    payload = {
        "domain": "relations",
        "schemaVersion": "1.0.0",
        "count": len(citations),
        "description": "关系级解释链引文注册表（M25）：由 tools/build_relation_citations.py "
                       "从 normalized 候选机械生成，引文逐字可回溯；禁止手写引文",
        "citations": citations,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"关系引文注册表：{len(citations)} 条 → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
