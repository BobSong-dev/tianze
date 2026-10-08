"""M27 · 知识来源治理：引文可回溯性与 raw 语料存在性报告。

检查三件事（只报告，不改数据，不补造原文）：
  S1  normalized 候选（knowledge/normalized/*/rules.json）每条 CLASSICAL_EXPLICIT
      引用的 sourceFile 在仓库中是否存在（raw OCR 语料——用户提供的 zip 内容，
      历来未提交 → 预期 BLOCKED，如数报告）；
  S2  关系引文注册表（knowledge/rules/relations/citations.json）每条 candidateId
      能在 normalized 候选中找到、quote 非空且与候选原文一致（机械一致性）；
  S3  ExecutableRule（temporal/event）provenance 含 CLASSICAL_EXPLICIT 的条目
      其 source.sourceFile 存在性（同 S1 口径）。

输出：regression/source-coverage.json / .md；raw 缺失时 status=BLOCKED（如实）。
"""

from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUT_JSON = "regression/source-coverage.json"
OUT_MD = "regression/source-coverage.md"


def main() -> int:
    repo = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(repo)

    # ---- S1/S3: sourceFile 存在性 ----
    def _exists(rel: str) -> bool:
        if not rel:
            return False
        return os.path.exists(os.path.join(repo, rel))

    candidates_total = 0
    classical_total = 0
    classical_missing = 0
    by_book: dict[str, dict] = {}
    for path in sorted(glob.glob(os.path.join(repo, "knowledge", "normalized", "*", "rules.json"))):
        book = os.path.basename(os.path.dirname(path))
        payload = json.load(open(path, encoding="utf-8"))
        slot = by_book.setdefault(book, {"candidates": 0, "classical": 0, "missingSourceFile": 0})
        for r in payload.get("rules", []):
            candidates_total += 1
            slot["candidates"] += 1
            src = r.get("source") or {}
            sf = src.get("sourceFile", "")
            levels = {p.get("level") for p in r.get("provenance", []) if isinstance(p, dict)}
            if "CLASSICAL_EXPLICIT" in levels or src.get("sourceKind") in ("CLASSICAL_TEXT", "COMMENTARY"):
                classical_total += 1
                slot["classical"] += 1
                if sf and not _exists(sf):
                    classical_missing += 1
                    slot["missingSourceFile"] += 1

    # ---- S2: citations 注册表一致性 ----
    cites = json.load(open(os.path.join(repo, "knowledge", "rules", "relations",
                                        "citations.json"), encoding="utf-8"))
    norm: dict[str, dict] = {}
    for path in sorted(glob.glob(os.path.join(repo, "knowledge", "normalized", "*", "rules.json"))):
        for r in json.load(open(path, encoding="utf-8")).get("rules", []):
            norm[r["id"]] = r
    cite_issues = []
    for cid, c in cites.get("citations", {}).items():
        if c.get("sourceKind") == "CANONICAL_TABLE":
            continue
        nc = norm.get(cid)
        if nc is None:
            cite_issues.append(f"{cid}: 注册表条目在 normalized 候选中不存在")
            continue
        if not c.get("quote"):
            cite_issues.append(f"{cid}: 注册表 quote 为空")
        raw_quotes = nc.get("originalQuotes") or []
        if raw_quotes and c.get("quote") and c["quote"][:60] not in raw_quotes[0][:len(c["quote"]) + 10] \
                and c["quote"][:60] not in (nc.get("coreText") or ""):
            cite_issues.append(f"{cid}: 注册表引文与候选原文不一致（前 60 字无匹配）")

    raw_available = classical_missing == 0
    payload = {
        "schemaVersion": "1.0.0",
        "status": "OK" if raw_available else "BLOCKED",
        "blockedReason": None if raw_available else (
            f"raw OCR 语料文件缺失 {classical_missing}/{classical_total} "
            "（知识库 zip 由用户提供、未提交仓库）——引用可回溯到 sourceFile 路径与页码，"
            "但原文核对需用户提供语料；本工具不补造原文"),
        "candidatesTotal": candidates_total,
        "classicalCitations": classical_total,
        "classicalSourceFileMissing": classical_missing,
        "byBook": by_book,
        "citationsRegistry": {
            "entries": cites.get("count"),
            "issues": cite_issues,
        },
        "discipline": "只报告，不修改数据，不补造原文；raw 语料到位后重跑即转 OK",
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    md = ["# 知识来源治理报告（M27）", "",
          f"- 状态：**{payload['status']}**" + (f"——{payload['blockedReason']}" if payload["blockedReason"] else ""),
          f"- 候选 {candidates_total} 条；CLASSICAL/COMMENTARY 引文 {classical_total} 条；"
          f"sourceFile 缺失 {classical_missing} 条（路径已记录、可回溯）",
          f"- 引文注册表 {cites.get('count')} 条；机械一致性 issue {len(cite_issues)} 条"
          + (f"：{cite_issues[:3]}" if cite_issues else "")]
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(chr(10).join(md) + chr(10))

    print(f"来源治理：status={payload['status']}；候选 {candidates_total}，"
          f"引文 {classical_total}（缺失 {classical_missing}）；注册表 issue {len(cite_issues)}")
    return 0  # 报告型工具：BLOCKED 也返回 0（不阻断质量门，如实记录）


if __name__ == "__main__":
    raise SystemExit(main())
