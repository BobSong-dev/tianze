"""M7 · 命例归一化：knowledge/raw/*.md 的命例块 + 检索索引行 → 结构化 CaseReference。

- 解析两种格式：结构化命例块（## 命例ID：…，748 块）与检索索引行（"- **姓名**｜四柱｜…｜PDF第N页"）。
- 三层分离：fact / sourceAnalysis（作者判断+历史事件分层标记）/ tianzeAnalysis（空占位，
  由 tools/derive_case_analysis.py 填充）。
- 去重：CaseIdentity（四柱有序+姓名+书籍）候选重复登记 possibleDuplicates，不自动合并。
- 产出 knowledge/normalized/cases/*.json + cases-manifest.json（含输入 hash/pipeline 版本）。
- 不确定数据一律 UNRESOLVED（unresolved=true 或字段留空），不猜测。

运行：python tools/normalize_cases.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "knowledge" / "raw"
OUT = REPO / "knowledge" / "normalized" / "cases"
PIPELINE_VERSION = "normalize_cases.py@1.0.0"

CASE_HEADER = re.compile(r"^#{2,3} 命例ID[:：]\s*(\S+)", re.M)
PILLAR_LINE = re.compile(r"四柱\*{0,2}[:：]\s*(.+)")
PAGES = re.compile(r"PDF第(\d+)(?:-(\d+))?页")
BOOK = re.compile(r"《(.+?)》")
GAZ = re.compile(r"([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])")
STEMS = "甲乙丙丁戊己庚辛壬癸"

BOOK_BY_PREFIX = {"QBTM": "穷通宝鉴评注", "DTZM": "滴天髓补注", "MLYD": "命理一得",
                  "SS": "守素室丛谈", "ZPZM": "子平真诠评注", "ZHY": "造化元钥评注",
                  "ZPY": "子平一得"}


def parse_pillars(text: str) -> dict[str, str] | None:
    """从四柱行提取 {year,month,day,hour}；解析失败返回 None（unresolved）。"""
    m = PILLAR_LINE.search(text)
    if not m:
        return None
    pairs = GAZ.findall(m.group(1))
    # 只保留干支对序列（去重连续）
    seen, ordered = set(), []
    for p in pairs:
        if p not in seen or len(ordered) < 4 and p == pairs[0]:
            ordered.append(p)
    # 简化：直接取全部出现的干支对，若 >=4 取前 4（命例常带重复干支，需按分隔序）
    # 更稳妥：按分隔符切
    raw = re.split(r"[·｜|,，、\s（）()]+", m.group(1))
    cleaned = [seg for seg in raw if (gz := GAZ.fullmatch(seg.strip().rstrip("年月日时。").strip() or seg.strip()))]
    if len(cleaned) < 4:
        # 回退：全文干支对顺序抽取
        cleaned = pairs
    if len(cleaned) < 4:
        return None
    keys = ["year", "month", "day", "hour"]
    return dict(zip(keys, [c if len(c) == 2 else c for c in cleaned[:4]]))


def split_name(raw_id: str, block: str) -> str | None:
    m = re.search(r"姓名/称谓[:：]\s*(.+)", block) or re.search(r"^## 命例ID[:：]\s*\S+（(.+?)）", block, re.M)
    if m:
        return m.group(1).strip()
    return None


def parse_case_block(rule_id: str, block: str, rel_file: str) -> dict | None:
    prefix = rule_id.split("-")[0].split("～")[0]
    book = BOOK_BY_PREFIX.get(prefix)
    if not book:
        return None
    pillars = parse_pillars(block)
    pages = []
    for pm in PAGES.finditer(block):
        a = int(pm.group(1)); b = int(pm.group(2) or pm.group(1))
        pages.extend(range(a, b + 1))
    def field(name: str) -> str | None:
        m = re.search(rf"{name}[:：]\s*(.+)", block)
        return m.group(1).strip() if m else None
    verdict = None
    vm = re.search(r"徐乐吾最终判断[:：]\s*(.+)", block)
    if vm:
        verdict = vm.group(1).strip().strip("「」")
    events_raw = field("实际事件") or ""
    purpose = field("该命例主要用于说明")
    cited_rules = []
    rm = re.search(r"涉及规则[:：]\s*(.+)", block)
    if rm:
        cited_rules = re.findall(r"[A-Z]{2,6}-[一-鿿A-Za-z0-9@-]*[0-9A-Za-z@]", rm.group(1))
    name = split_name(rule_id, block)
    gender = "female" if re.search(r"女命|（女）|｜女｜", block) else ("male" if name and "女" not in (name or "") else None)
    if re.search(r"^女$|女命", name or ""):
        gender = "female"
    unresolved = pillars is None
    if pillars is None:
        pillars = {"year": "", "month": "", "day": "", "hour": ""}
    fact = {
        "pillars": pillars, "gender": gender,
        "birthText": field("生年") or (re.search(r"出生[^\n]*", block) or [None])[0] if False else None,
        "name": name, "unresolved": unresolved,
    }
    # 原文生时（断语上下文/出处行中的干支纪时文本）
    bm = re.search(r"(同治|光绪|乾隆|道光|嘉庆|咸丰|民国)[^\n。；｜]{0,30}", block)
    if bm:
        fact["birthText"] = bm.group(0).strip()
    analysis = {
        "verdict": verdict,
        "steps": [],
        "events": ([{"text": events_raw, "claimType": "HISTORICAL_CLAIM", "speaker": "原书"}]
                   if events_raw and events_raw not in ("无记载", "无", "原文无", "—", "无记载。") else []),
        "purpose": purpose,
        "dayun": field("大运/流年") or field("大运"),
    }
    return {
        "caseId": f"CASE-{rule_id}",
        "rawBlockId": rule_id,
        "sourceFile": rel_file,
        "source": {"sourceKind": "CLASSICAL_TEXT", "book": book,
                   "chapter": (BOOK.search(block).group(1) if BOOK.search(block) else book),
                   "pages": pages, "sourceFile": rel_file, "confidence": "unverified"},
        "fact": fact,
        "sourceAnalysis": analysis,
        "ruleReferences": [{"ruleId": rid, "relation": "EXPLICITLY_CITED"} for rid in cited_rules],
        "quality": "B" if pages else "C",
        "verification": {"status": "MACHINE_EXTRACTED", "verifiedBy": f"tianze-pipeline:{PIPELINE_VERSION}",
                         "method": "regex_extraction", "sourceChecked": False},
    }


def parse_index_line(line: str, rel_file: str) -> dict | None:
    m = re.match(r"-\s*\*\*(.+?)\*\*｜([^｜]+)｜([^｜]+)｜PDF第(\d+)页｜(?:断语上下文：)?(.*)", line.strip())
    if not m:
        return None
    name, pillars_raw, section, page, context = (g.strip() for g in m.groups())
    pairs = re.findall(r"([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])", pillars_raw)
    if len(pairs) != 4:
        return None
    gender = "female" if name == "女" else None
    return {
        "caseId": None,  # 由主循环统一编号
        "rawBlockId": None,
        "sourceFile": rel_file,
        "source": {"sourceKind": "CLASSICAL_TEXT", "book": "穷通宝鉴评注",
                   "chapter": section, "pages": [int(page)], "sourceFile": rel_file,
                   "confidence": "unverified"},
        "fact": {"pillars": dict(zip(["year", "month", "day", "hour"], pairs)),
                 "gender": gender, "name": None if name in ("无名例", "按：无名") else name,
                 "birthText": context if re.search(r"(同治|光绪|乾隆|道光|嘉庆|咸丰|民国)", context) else None,
                 "unresolved": False},
        "sourceAnalysis": {"verdict": context if context and not re.fullmatch(r"\d+", context) else None,
                           "steps": [], "events": [], "purpose": None, "dayun": None},
        "ruleReferences": [],
        "quality": "C",  # 索引行为整理归纳层
        "verification": {"status": "MACHINE_EXTRACTED", "verifiedBy": f"tianze-pipeline:{PIPELINE_VERSION}",
                         "method": "regex_extraction", "sourceChecked": False},
        "fromIndex": True,
    }


def identity_key(case: dict) -> tuple | None:
    pillars = case["fact"]["pillars"]
    if not all(pillars.get(k) for k in ("year", "month", "day", "hour")):
        return None
    return (pillars["year"], pillars["month"], pillars["day"], pillars["hour"],
            case["fact"].get("name"), case["source"]["book"])


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cases: list[dict] = []
    blocks_seen = 0
    index_seen = 0
    parse_fail = 0

    for path in sorted(RAW.rglob("*.md")):
        if "_文本提取" in path.parts:
            continue
        rel = path.relative_to(RAW).as_posix()
        text = path.read_text(encoding="utf-8")
        matches = list(CASE_HEADER.finditer(text))
        for i, m in enumerate(matches):
            blocks_seen += 1
            rid = m.group(1).rstrip("。")
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            if "～" in rid:  # 区间头（ZPY-M02～ZPY-M14）跳过——由索引覆盖
                continue
            case = parse_case_block(rid, text[m.end():end], rel)
            if case:
                cases.append(case)
            else:
                parse_fail += 1
        for line in text.splitlines():
            if line.strip().startswith("- **") and "｜" in line:
                index_seen += 1
                case = parse_index_line(line, rel)
                if case:
                    cases.append(case)

    # 去重（CaseIdentity 候选重复，不自动合并）
    groups: dict[tuple, list[int]] = defaultdict(list)
    for idx, c in enumerate(cases):
        key = identity_key(c)
        if key:
            groups[key].append(idx)
    dup_count = 0
    for key, idxs in groups.items():
        if len(idxs) > 1:
            dup_count += 1
            keep = idxs[0]
            for j in idxs[1:]:
                cases[j]["possibleDuplicates"] = [cases[keep]["caseId"] or f"#{keep}"]
            cases[keep].setdefault("possibleDuplicates", [])
            cases[keep]["possibleDuplicates"] += [cases[j]["caseId"] or f"#{j}" for j in idxs[1:]]
    # 编号：结构化块用原 ID（冲突加 @n，与规则 ID 同策略）；索引行给 ID
    seen: dict[str, int] = {}
    id_conflicts = []
    n_index = 0
    for c in cases:
        if c["caseId"] is None:
            n_index += 1
            c["caseId"] = f"CASE-IDX-{n_index:04d}"
        else:
            base = c["caseId"]
            n = seen.get(base, 0)
            if n:
                seen[base] = n + 1
                id_conflicts.append({"originalId": base, "assignedId": f"{base}@{n + 1}",
                                     "sourceFile": c["sourceFile"]})
                c["caseId"] = f"{base}@{n + 1}"
                c["idConflict"] = True
            else:
                seen[base] = 1

    # Manifest
    inputs = sorted(
        ({"path": p.relative_to(RAW).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()[:16]}
         for p in RAW.rglob("*.md") if "_文本提取" not in p.parts),
        key=lambda d: d["path"],
    )
    manifest = {
        "pipeline": PIPELINE_VERSION,
        "caseSchemaVersion": "1.0.0",
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "inputs": inputs,
        "stats": {
            "rawCaseBlocks": blocks_seen,
            "indexLinesSeen": index_seen,
            "parsedCases": len(cases),
            "fromStructuredBlocks": blocks_seen - parse_fail,
            "fromIndexLines": n_index,
            "parseFailures": parse_fail,
            "duplicateGroups": dup_count,
            "uniqueIdentityKeys": len(groups),
            "unresolvedPillars": sum(1 for c in cases if c["fact"]["unresolved"]),
            "idConflicts": id_conflicts,
        },
    }
    (OUT.parent / "cases-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")

    by_book: dict[str, list] = defaultdict(list)
    for c in cases:
        by_book[c["source"]["book"]].append(c)
    for book, cs in sorted(by_book.items()):
        (OUT / f"{book}.json").write_text(
            json.dumps({"book": book, "count": len(cs), "cases": cs}, ensure_ascii=False, indent=1),
            encoding="utf-8")
    print(json.dumps(manifest["stats"], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
