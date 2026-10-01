"""K1 · 知识库归一化管线：knowledge/raw/*.md → knowledge/normalized/*.json。

- 只读 raw（只读语义见 knowledge/raw/README.md）；不可逆过程不存在。
- 解析 `##/### 规则ID：` 块与 12 个标注字段（**粗体**/纯文本两种版式）。
- 来源行解析：《书名》·章节；PDF第N-M页。
- OCR 错字照录（不修正），检测【OCR识别待核】等风险标记 → ocr_risk。
- 输出：normalized/{book}/rules.json + normalized/manifest.json（确定性，可重跑）。

运行：python tools/normalize_knowledge.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "knowledge" / "raw"
OUT = REPO / "knowledge" / "normalized"

RULE_HEADER = re.compile(r"^#{2,3} 规则ID：(.+?)\s*$", re.M)
FIELD = re.compile(r"^\*\*(.+?)\*\*[:：]\s*(.*)$|^(主题|规则名称|核心规则|适用条件|需要观察|推理逻辑|例外情况|原文|徐乐吾解释|徐乐吾明确观点|整理者说明|来源|内容性质|标签)[:：]\s*(.*)$")
PAGES = re.compile(r"PDF第(\d+)(?:-(\d+))?页")
BOOK = re.compile(r"《(.+?)》")
OCR_MARKS = ("【OCR识别待核】", "原书文字如此", "OCR")

# 书籍代码 → （全称, 原文层来源类型, 注家）
BOOK_META: dict[str, dict] = {
    "QBT": {"title": "穷通宝鉴评注", "original": "穷通宝鉴", "original_kind": "CLASSICAL_TEXT", "commentator": "徐乐吾"},
    "ZHY": {"title": "造化元钥评注", "original": "造化元钥（穷通宝鉴异名本）", "original_kind": "CLASSICAL_TEXT", "commentator": "徐乐吾"},
    "DTZ": {"title": "滴天髓补注", "original": "滴天髓", "original_kind": "CLASSICAL_TEXT", "commentator": "徐乐吾（补注）/孙正治（注译）"},
    "ZPZ": {"title": "子平真诠评注", "original": "子平真诠", "original_kind": "CLASSICAL_TEXT", "commentator": "徐乐吾（评注）/沈孝瞻（原著）"},
    "SPZY": {"title": "子平粹言", "original": None, "original_kind": "COMMENTARY", "commentator": "徐乐吾（原著）/赵嘉宁（今译）"},
    "MLD": {"title": "命理一得", "original": None, "original_kind": "COMMENTARY", "commentator": "徐乐吾（原著）"},
    "ZP": {"title": "子平一得", "original": None, "original_kind": "COMMENTARY", "commentator": "徐乐吾（原著）"},
    "SS": {"title": "守素室丛谈", "original": None, "original_kind": "COMMENTARY", "commentator": "徐乐吾（原著）"},
}

NATURE_MAP = {
    "古籍原文": "古籍原文",
    "徐乐吾对古籍的解释": "徐乐吾对古籍的解释",
    "徐乐吾明确观点": "徐乐吾明确观点",
    "整理归纳": "整理归纳",
    "书中命例": "书中命例",
}

# 天干代码（用于 candidate 的 dayMaster 推断）
STEMS = "甲乙丙丁戊己庚辛壬癸"
MONTH_LUNISOLAR = {  # 农历月序 → 月支
    "正月": "寅", "二月": "卯", "三月": "辰", "四月": "巳", "五月": "午", "六月": "未",
    "七月": "申", "八月": "酉", "九月": "戌", "十月": "亥", "十一月": "子", "十二月": "丑",
}
MONTH_BRANCHES = "寅卯辰巳午未申酉戌亥子丑"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_fields(block: str) -> dict[str, str]:
    """把规则块解析成 {字段: 文本}。字段行两种版式；字段值可跨行。"""
    fields: dict[str, str] = {}
    current: str | None = None
    for line in block.splitlines():
        m = FIELD.match(line.strip())
        if m:
            name = (m.group(1) or m.group(3)).strip()
            value = (m.group(2) or m.group(4) or "").strip()
            fields[name] = value
            current = name
        elif current and line.strip() and not line.startswith("#"):
            fields[current] += "\n" + line.strip()
    return fields


def parse_source(raw: str, rel_file: str, book_code: str) -> dict:
    book_m = BOOK.search(raw)
    cited_book = book_m.group(1) if book_m else BOOK_META.get(book_code, {}).get("title", book_code)
    chapter = None
    if "·" in raw:
        after = raw.split("·", 1)[1]
        chapter = after.split("；")[0].split("。")[0].strip() or None
    pages: list[int] = []
    for m in PAGES.finditer(raw):
        a = int(m.group(1))
        b = int(m.group(2) or m.group(1))
        pages.extend(range(a, b + 1))
    meta = BOOK_META.get(book_code, {})
    is_commentary_book = meta.get("original_kind") == "COMMENTARY"
    return {
        "sourceKind": "COMMENTARY" if is_commentary_book else "CLASSICAL_TEXT",
        "book": cited_book,
        "chapter": chapter,
        "pages": pages,
        "edition": meta.get("title"),
        "sourceFile": rel_file,
        "confidence": "unverified",
        "commentator": meta.get("commentator"),
    }


def split_quotes(text: str) -> list[str]:
    parts = re.findall(r"「(.+?)」", text, re.S)
    return [p.strip() for p in parts] if parts else ([text.strip()] if text.strip() else [])


def infer_months(fields: dict[str, str]) -> list[str]:
    """从 主题/适用条件/规则名称 推断月支列表（保守：只识别明确月支词）。"""
    text = " ".join(filter(None, [fields.get("主题"), fields.get("适用条件"), fields.get("规则名称"), fields.get("标签")]))
    months: list[str] = []
    for lun, branch in MONTH_LUNISOLAR.items():
        if lun in text:
            months.append(branch)
    for b in MONTH_BRANCHES:
        if f"{b}月" in text:
            months.append(b)
    # 保留月支序
    ordered = [b for b in MONTH_BRANCHES if b in months]
    return ordered


def infer_day_master(rule_id: str, fields: dict[str, str]) -> str | None:
    for ch in STEMS:
        if ch in rule_id:
            return ch
    topic = fields.get("主题") or ""
    for ch in STEMS:
        if topic.startswith(ch):
            return ch
    return None


def parse_file(path: Path) -> list[dict]:
    rel = path.relative_to(RAW).as_posix()
    text = path.read_text(encoding="utf-8")
    matches = list(RULE_HEADER.finditer(text))
    rules = []
    for i, m in enumerate(matches):
        rule_id = m.group(1).strip()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[m.end():end]
        fields = parse_fields(block)
        book_code = rule_id.split("-")[0]
        source = parse_source(fields.get("来源", ""), rel, book_code)
        quote_raw = fields.get("原文")
        quotes = split_quotes(quote_raw) if quote_raw else []
        nature_raw = fields.get("内容性质", "")
        natures = [NATURE_MAP.get(n.strip(), n.strip()) for n in re.split(r"[＋+、]", nature_raw) if n.strip()]
        blob = json.dumps(fields, ensure_ascii=False)
        ocr_risk = any(mk in blob for mk in OCR_MARKS)
        quality = "B" if ("古籍原文" in natures and source["pages"]) else ("C" if source["pages"] or quote_raw else "D")
        if ocr_risk and quality == "B":
            quality = "B"  # OCR 风险不降级，只打标记（修正走 correctedText 流程）
        rules.append({
            "id": rule_id,
            "book": book_code,
            "sourceFile": rel,
            "title": fields.get("规则名称"),
            "topic": fields.get("主题"),
            "coreText": fields.get("核心规则"),
            "applicableCondition": fields.get("适用条件"),
            "observation": fields.get("需要观察"),
            "reasoning": fields.get("推理逻辑"),
            "exceptions": fields.get("例外情况"),
            "originalQuotes": quotes,
            "commentaries": [
                {"author": BOOK_META.get(book_code, {}).get("commentator", "徐乐吾"),
                 "text": fields[k], "nature": "徐乐吾对古籍的解释" if "解释" in k else k}
                for k in ("徐乐吾解释", "徐乐吾明确观点", "整理者说明") if fields.get(k)
            ],
            "source": source,
            "contentNature": natures,
            "tags": [t.strip() for t in (fields.get("标签") or "").replace("，", "、").split("、") if t.strip()],
            "quality": quality,
            "ocrRisk": ocr_risk,
            "dayMaster": infer_day_master(rule_id, fields),
            "months": infer_months(fields),
            "fieldNames": list(fields.keys()),
        })
    return rules


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    md_files = sorted(p for p in RAW.rglob("*.md") if "_文本提取" not in p.parts)
    manifest_files = []
    all_rules: list[dict] = []
    for path in md_files:
        rel = path.relative_to(RAW).as_posix()
        rules = parse_file(path)
        all_rules.extend(rules)
        manifest_files.append({
            "file": rel,
            "sha256": sha256(path)[:16],
            "bytes": path.stat().st_size,
            "rules": len(rules),
        })

    # 全局 ID 唯一性：知识库自身存在跨文件 ID 复用（审计发现）。
    # 处理：首次出现保持原 ID；后续出现加 @2/@3… 后缀（确定性：按排序文件序），
    # 并登记 idConflicts 供审计报告与冲突检测使用。
    seen: dict[str, int] = {}
    id_conflicts: list[dict] = []
    for r in all_rules:
        base = r["id"]
        n = seen.get(base, 0)
        if n == 0:
            seen[base] = 1
        else:
            seen[base] = n + 1
            id_conflicts.append({
                "originalId": base,
                "assignedId": f"{base}@{n + 1}",
                "sourceFile": r["sourceFile"],
            })
            r["id"] = f"{base}@{n + 1}"
            r["idConflict"] = True

    by_book: dict[str, list[dict]] = {}
    for r in all_rules:
        by_book.setdefault(r["book"], []).append(r)
    for book, rules in sorted(by_book.items()):
        out_file = OUT / book / "rules.json"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(json.dumps({"book": book, "count": len(rules), "rules": rules},
                                       ensure_ascii=False, indent=1), encoding="utf-8")

    ids = [r["id"] for r in all_rules]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    manifest = {
        "generatedBy": "tools/normalize_knowledge.py",
        "files": manifest_files,
        "rulesTotal": len(all_rules),
        "books": {b: len(rs) for b, rs in sorted(by_book.items())},
        "duplicateIds": dupes,
        "idConflicts": id_conflicts,
        "dayMasterKnown": sum(1 for r in all_rules if r["dayMaster"]),
        "monthKnown": sum(1 for r in all_rules if r["months"]),
        "ocrRisk": sum(1 for r in all_rules if r["ocrRisk"]),
        "quality": {g: sum(1 for r in all_rules if r["quality"] == g) for g in "ABCD"},
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("rulesTotal", "books", "dayMasterKnown", "monthKnown", "ocrRisk", "quality")}, ensure_ascii=False, indent=1))
    print("idConflicts:", len(id_conflicts), "| duplicateIds after suffix:", len(dupes))


if __name__ == "__main__":
    main()
