"""M17 · 原文岁运解析（raw temporal spans）：从 raw md 命例块提取岁运表达。

输出：knowledge/normalized/cases/raw_temporal_spans.json
- 每条记录带 source span（字符偏移）、field（所在字段行）、confidence
- 无干支的描述性内容（如「去酉之运」「行南方运」）→ UNRESOLVED 记录（不猜天干）
- 中文数字年龄（「三十九岁」）→ 换算并关联同句干支

纪律：不确定就 UNRESOLVED；MACHINE_EXTRACTED，不升级人工状态。
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GAN = "甲乙丙丁戊己庚辛壬癸"
ZHI = "子丑寅卯辰巳午未申酉戌亥"
RE_YUN = re.compile(f"([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])运")
RE_NIAN = re.compile(f"([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])年")
RE_AGE_CN = "([一二三四五六七八九十]{1,3})岁"
RE_AGE = re.compile(r"(\d{1,3})岁")
RE_FIELD = re.compile(r"^(大运/流年|实际事件|徐乐吾最终判断|分析步骤)：", re.M)

_CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7,
           "八": 8, "九": 9, "十": 10}


def cn_to_int(text: str) -> int | None:
    """中文数字（一~三十九范围）→ int。"""
    if not text:
        return None
    if text.isdigit():
        return int(text)
    if "十" in text:
        parts = text.split("十")
        tens = _CN_NUM.get(parts[0], 1) if parts[0] else 1
        ones = _CN_NUM.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0
        return tens * 10 + ones
    return _CN_NUM.get(text)


def _valid_gz(gz: str) -> bool:
    if len(gz) != 2 or gz[0] not in GAN or gz[1] not in ZHI:
        return False
    si, bi = GAN.index(gz[0]), ZHI.index(gz[1])
    return (si % 2) == (bi % 2)


def parse_block(block: str) -> list[dict]:
    """单命例块 → span 记录列表。"""
    out: list[dict] = []
    # 按字段行切段，记录每段 field
    segments: list[tuple[str, int, str]] = []  # (field, start_offset, text)
    matches = list(RE_FIELD.finditer(block))
    if matches:
        for i, m in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(block)
            segments.append((m.group(1), m.start(), block[m.start():end]))
    else:
        segments.append(("body", 0, block))

    for field, seg_start, text in segments:
        for pat, kind, conf_high in ((RE_YUN, "luck", True), (RE_NIAN, "annual", True)):
            for m in pat.finditer(text):
                gz = m.group(1)
                if not _valid_gz(gz):
                    # OCR 容错：奇偶不合的「干支」如实记录为 UNRESOLVED，不猜
                    out.append({
                        "kind": "unresolved", "ganZhi": None,
                        "span": [seg_start + m.start(1), seg_start + m.end(1)],
                        "field": field, "confidence": None,
                        "rawText": m.group(0),
                        "unresolvedReason": "干支奇偶不合（OCR 疑误），不猜",
                    })
                    continue
                out.append({
                    "kind": kind, "ganZhi": gz,
                    "span": [seg_start + m.start(1), seg_start + m.end(1)],
                    "field": field,
                    "confidence": "high" if conf_high else "medium",
                    "rawText": m.group(0),
                })
        # M18：干支省略（「午运」「行酉运」——仅支，无干）
        for m in re.finditer(r"([子丑寅卯辰巳午未申酉戌亥])运", text):
            out.append({
                "kind": "luck", "ganZhi": None, "partialBranch": m.group(1),
                "span": [seg_start + m.start(1), seg_start + m.end(1)],
                "field": field, "confidence": "low",
                "rawText": m.group(0),
                "unresolvedReason": "仅支无干：干支省略（供规则研究，不可直接排盘）",
            })
        # 年龄→干支关联（同句）
        # M18：一运多年——同段内先出现 X运，后续 X年继承该运（上下文继承，medium）
        seg_luck = None
        for m in RE_YUN.finditer(text):
            if _valid_gz(m.group(1)):
                seg_luck = m.group(1)
        if seg_luck:
            for m in RE_NIAN.finditer(text):
                gz = m.group(1)
                if _valid_gz(gz):
                    out.append({
                        "kind": "annual", "ganZhi": gz, "inheritsLuck": seg_luck,
                        "span": [seg_start + m.start(1), seg_start + m.end(1)],
                        "field": field, "confidence": "medium",
                        "rawText": m.group(0),
                    })

        for am in list(RE_AGE.finditer(text)) + list(re.finditer(RE_AGE_CN, text)):
            age = cn_to_int(am.group(1))
            if age is None:
                continue
            sentence_end = text.find("。", am.end())
            sentence_end = sentence_end if sentence_end > 0 else min(am.end() + 30, len(text))
            sentence = text[am.start():sentence_end]
            for ym in RE_YUN.finditer(sentence):
                gz = ym.group(1)
                if _valid_gz(gz):
                    out.append({
                        "kind": "luck", "ganZhi": gz, "age": age,
                        "span": [seg_start + am.start(), seg_start + am.start() + len(sentence)],
                        "field": field, "confidence": "medium",
                        "rawText": sentence.strip()[:40],
                    })
                break

    # UNRESOLVED：大运/流年字段有内容但无任何干支命中
    yun_field = next((t for f, _s, t in segments if f == "大运/流年"), None)
    has_gz = any(r["span"][0] >= 0 and r["field"] == "大运/流年" for r in out)
    if yun_field and not has_gz:
        body = yun_field.split("：", 1)[1].strip() if "：" in yun_field else yun_field.strip()
        if body and body not in ("—", "—。", ""):
            out.append({
                "kind": "unresolved", "ganZhi": None,
                "span": None, "field": "大运/流年", "confidence": None,
                "rawText": body[:60],
                "unresolvedReason": "描述性内容无可解析干支（不猜）",
            })
    return out


def main() -> int:
    records = []
    stats = {"totalCases": 0, "withSpans": 0, "spanCount": 0,
             "byKind": {}, "byConfidence": {}, "unresolved": 0}
    for f in sorted(glob.glob("knowledge/normalized/cases/*.json")):
        if any(x in f for x in ("temporal_refs", "event_claims", "raw_temporal_spans")):
            continue
        data = json.load(open(f, encoding="utf-8"))
        book = data.get("book", "")
        for c in data["cases"]:
            stats["totalCases"] += 1
            sf = c.get("sourceFile")
            rb = c.get("rawBlockId") or ""
            if not sf or not rb:
                continue
            path = os.path.join("knowledge/raw", sf)
            if not os.path.exists(path):
                continue
            raw = open(path, encoding="utf-8").read()
            i = raw.find(rb.split("（")[0])
            if i < 0:
                continue
            block = raw[i:i + 2400]  # M19：长块（多段落分析）
            j = block.find("## 命例ID", 10)
            block = block[:j] if j > 0 else block
            spans = parse_block(block)
            if spans:
                stats["withSpans"] += 1
            for sp in spans:
                stats["spanCount"] += 1
                stats["byKind"][sp["kind"]] = stats["byKind"].get(sp["kind"], 0) + 1
                if sp["kind"] == "unresolved":
                    stats["unresolved"] += 1
                if sp.get("confidence"):
                    stats["byConfidence"][sp["confidence"]] = \
                        stats["byConfidence"].get(sp["confidence"], 0) + 1
            if spans:
                records.append({
                    "caseId": c["caseId"], "book": book,
                    "sourceFile": sf, "rawBlockId": rb,
                    "spans": spans,
                })

    payload = {
        "schemaVersion": "1.0.0",
        "description": "RawTemporalSpan：原文岁运表达解析（span/confidence/UNRESOLVED，不猜干支）",
        "verification": {"status": "MACHINE_EXTRACTED", "sourceChecked": False},
        "count": len(records),
        "stats": stats,
        "cases": records,
    }
    with open("knowledge/normalized/cases/raw_temporal_spans.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"原文岁运解析：{stats['totalCases']} 例，{stats['withSpans']} 例有 span，"
          f"共 {stats['spanCount']} 条（{stats['byKind']}）")
    print(f"  UNRESOLVED（不猜）：{stats['unresolved']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
