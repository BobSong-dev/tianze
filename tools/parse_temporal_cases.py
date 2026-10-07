"""M13 · 从 1147 个 CaseReference 批量解析原书岁运信息 → TemporalCaseReference。

输入：knowledge/normalized/cases/*.json（normalize_cases.py 产物，只读）
输出：knowledge/normalized/cases/temporal_refs.json + temporal_refs_stats.json

三层分离（绝不混合）：
    sourceTemporalAnalysis  原书大运序列 + 文本中的岁运提及（原样保留，含 OCR 噪声）
    tianzeTemporalAnalysis  Tianze 引擎计算（命例缺出生信息 → 显式 not_computed）
    historicalClaims        原书历史断言（不是 truth）

校验（岁运干支一致性，不依赖出生信息）：
    相邻大运干支指数 +1（mod 60）且年龄差 +10 → sequence_consistent=True
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tianze.ganzhi.tables import STEMS, BRANCHES
from tianze.knowledge.temporal_cases import (
    HistoricalClaim, SourceDayunEntry, SourceTemporalAnalysis,
    TemporalCaseReference, TemporalMention, TianzeTemporalAnalysis,
)

GAN = "".join(STEMS)
ZHI = "".join(BRANCHES)
_GZ = f"([{GAN}][{ZHI}])"
_RE_DAYUN_ITEM = re.compile(rf"(\d{{1,3}})\s*{_GZ}")
_RE_LUCK = re.compile(rf"行?{_GZ}运")
_RE_ANNUAL = re.compile(rf"流年{_GZ}|岁在{_GZ}|({_GZ})年")
_RE_BRANCH_YUN = re.compile(rf"([{ZHI}])运")
_RE_SUIJUN = re.compile(r"岁君|犯岁|日犯岁")
_RE_TAISUI = re.compile(r"太岁")

# 年份干支反查：用于 "丙子年" 这类干支纪年（不是流年数字）
_VALID_YEAR_GZ = {f"{s}{b}" for i in range(60)
                  for s, b in [(STEMS[i % 10], BRANCHES[i % 12])]}


def gz_index(gz: str) -> int | None:
    if len(gz) != 2 or gz[0] not in STEMS or gz[1] not in BRANCHES:
        return None
    # 干支同奇偶才存在于六十甲子
    si, bi = STEMS.index(gz[0]), BRANCHES.index(gz[1])
    if (si % 2) != (bi % 2):
        return None
    for i in range(60):
        if STEMS[i % 10] == gz[0] and BRANCHES[i % 12] == gz[1]:
            return i
    return None


def parse_dayun_field(text: str | None) -> tuple[list[SourceDayunEntry], bool | None, str | None]:
    """原书大运字段 → 结构化条目 + 序列一致性 + 未解析残文。"""
    if not text or not text.strip():
        return [], None, None, None
    entries: list[SourceDayunEntry] = []
    consumed_spans: list[tuple[int, int]] = []
    for m in _RE_DAYUN_ITEM.finditer(text):
        age = int(m.group(1))
        gz = m.group(2)
        if gz_index(gz) is None:
            continue
        entries.append(SourceDayunEntry(age=age, gan_zhi=gz, raw_text=m.group(0)))
        consumed_spans.append(m.span())
    residual = text
    if entries:
        # 残文 = 去掉已匹配片段后的剩余（诚实保留噪声）
        parts, last = [], 0
        for a, b in consumed_spans:
            parts.append(text[last:a]); last = b
        parts.append(text[last:])
        residual = "".join(parts).strip() or None

    consistent: bool | None = None
    direction = None
    if len(entries) >= 2:
        diffs = []
        for a, b in zip(entries, entries[1:]):
            ia, ib = gz_index(a.gan_zhi), gz_index(b.gan_zhi)
            if ia is None or ib is None:
                diffs = None
                break
            diffs.append((ib - ia) % 60)  # 1=顺行, 59=逆行
        if diffs is not None:
            if all(d == 1 for d in diffs):
                consistent, direction = True, "forward"
            elif all(d == 59 for d in diffs):
                consistent, direction = True, "backward"
            else:
                consistent = False
            if consistent:
                for a, b in zip(entries, entries[1:]):
                    if a.age is not None and b.age is not None and (b.age - a.age) != 10:
                        consistent = False
                        break
    return entries, consistent, direction, residual


def parse_mentions(events: list[dict], dayun_text: str | None = None
                   ) -> tuple[list[TemporalMention], list[HistoricalClaim]]:
    mentions: list[TemporalMention] = []
    claims: list[HistoricalClaim] = []
    # 大运字段本身也是岁运文本（如「乙卯、甲寅运；子运；亥运；流年戊寅」）——
    # 只用于提及解析，不生成 historical claim（大运字段不是历史事件断言）
    mention_sources = [(e, False) for e in events]
    if dayun_text:
        mention_sources.append(({"text": dayun_text,
                                 "claimType": "AUTHOR_INTERPRETATION"}, True))
    for e, from_dayun_field in mention_sources:
        text = (e.get("text") or "").strip()
        if not text:
            continue
        ct = e.get("claimType", "HISTORICAL_CLAIM")
        full_gz_spans: list[tuple[int, int]] = []  # 每段文本独立（坐标不可跨文本比较）

        def _ctx(s: int, ee: int) -> str:
            return text[max(0, s - 12):min(len(text), ee + 12)]

        for m in _RE_LUCK.finditer(text):
            full_gz_spans.append((m.start(1), m.end(1)))
            mentions.append(TemporalMention(
                kind="luck", gan_zhi=m.group(1), raw_text=m.group(0),
                context=_ctx(m.start(), m.end()), claim_type=ct,
            ))
        for m in _RE_BRANCH_YUN.finditer(text):
            if any(a <= m.start(1) < b for a, b in full_gz_spans):
                continue  # 已作为完整干支运记录
            mentions.append(TemporalMention(
                kind="luck", partial_gz=m.group(1), raw_text=m.group(0),
                context=_ctx(m.start(), m.end()), claim_type=ct,
            ))
        for m in _RE_ANNUAL.finditer(text):
            gz = m.group(1) or m.group(2) or m.group(3)
            if gz and gz in _VALID_YEAR_GZ:
                mentions.append(TemporalMention(
                    kind="annual", gan_zhi=gz, raw_text=m.group(0),
                    context=_ctx(m.start(), m.end()), claim_type=ct,
                ))
        for m in _RE_SUIJUN.finditer(text):
            mentions.append(TemporalMention(
                kind="suijun", gan_zhi=None, raw_text=m.group(0),
                context=_ctx(m.start(), m.end()), claim_type=ct,
            ))
        for m in _RE_TAISUI.finditer(text):
            mentions.append(TemporalMention(
                kind="taisui", gan_zhi=None, raw_text=m.group(0),
                context=_ctx(m.start(), m.end()), claim_type=ct,
            ))
        if not from_dayun_field:
            claims.append(HistoricalClaim(text=text, claim_type=ct))
    return mentions, claims


def main() -> int:
    case_files = sorted(glob.glob("knowledge/normalized/cases/*.json"))
    case_files = [f for f in case_files
                 if not any(x in f for x in ("temporal_refs", "event_claims", "raw_temporal_spans"))]
    refs: list[dict] = []
    stats = {
        "totalCases": 0, "withSourceDayun": 0, "dayunConsistent": 0,
        "dayunInconsistent": 0, "dayunUnparsedResidual": 0,
        "withMentions": 0, "mentionTotal": 0,
        "mentionByKind": {}, "historicalClaims": 0,
        "tianzeComputed": 0, "tianzeNotComputed": 0,
    }

    for cf in case_files:
        data = json.load(open(cf, encoding="utf-8"))
        book = data["book"]
        for case in data["cases"]:
            stats["totalCases"] += 1
            cid = case["caseId"]
            sa = case.get("sourceAnalysis") or {}

            dayun_text = sa.get("dayun")
            dayun_entries, consistent, direction, residual = parse_dayun_field(dayun_text)
            if dayun_entries:
                stats["withSourceDayun"] += 1
                if consistent is True:
                    stats["dayunConsistent"] += 1
                    stats["dayunForward"] = stats.get("dayunForward", 0) + (direction == "forward")
                    stats["dayunBackward"] = stats.get("dayunBackward", 0) + (direction == "backward")
                elif consistent is False:
                    stats["dayunInconsistent"] += 1
            if residual and dayun_text and dayun_text.strip() not in ("原文未载", "（原文未载）", "—", ""):
                stats["dayunUnparsedResidual"] += 1
            if dayun_text and dayun_text.strip() in ("原文未载", "（原文未载）", "—", ""):
                stats["dayunNotRecorded"] = stats.get("dayunNotRecorded", 0) + 1

            mentions, claims = parse_mentions(sa.get("events") or [], dayun_text)
            if mentions:
                stats["withMentions"] += 1
            stats["mentionTotal"] += len(mentions)
            for m in mentions:
                stats["mentionByKind"][m.kind] = stats["mentionByKind"].get(m.kind, 0) + 1
            stats["historicalClaims"] += len(claims)

            # Tianze 侧：命例缺出生日期/性别 → 无法重算起运（显式 not_computed）
            fact = case.get("fact") or {}
            has_birth = bool(fact.get("birthText"))
            if has_birth:
                stats["tianzeComputed"] += 1
                tta = TianzeTemporalAnalysis(
                    computed=True,
                    comparison_note="含出生文本：起运重算需 M13 后续工具接入（解析器仅标记能力）",
                )
            else:
                stats["tianzeNotComputed"] += 1
                tta = TianzeTemporalAnalysis(
                    computed=False,
                    not_computed_reason="命例缺出生日期/性别，无法重算起运（不编造）",
                )

            ref = TemporalCaseReference(
                case_id=cid,
                book=book,
                source_temporal=SourceTemporalAnalysis(
                    dayun=dayun_entries,
                    unparsed_dayun_text=residual,
                    dayun_sequence_consistent=consistent,
                    dayun_direction=direction,
                    mentions=mentions,
                ),
                tianze_temporal=tta,
                historical_claims=claims,
            )
            refs.append(json.loads(ref.model_dump_json(by_alias=True, exclude_none=True)))

    out = {
        "schemaVersion": "1.0.0",
        "description": "TemporalCaseReference：原书岁运信息三层分离（source/tianze/historicalClaims）",
        "provenance": "tools/parse_temporal_cases.py 解析 knowledge/normalized/cases/*.json（MACHINE_EXTRACTED，未人工复核）",
        "verification": {"status": "MACHINE_EXTRACTED", "sourceChecked": False},
        "count": len(refs),
        "cases": refs,
    }
    os.makedirs("knowledge/normalized/cases", exist_ok=True)
    with open("knowledge/normalized/cases/temporal_refs.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    with open("knowledge/normalized/cases/temporal_refs_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"TemporalCaseReference 解析完成：{stats['totalCases']} 例")
    print(f"  原书大运序列：{stats['withSourceDayun']} 例（一致 {stats['dayunConsistent']} / 不一致 {stats['dayunInconsistent']}）")
    print(f"  残文保留：{stats['dayunUnparsedResidual']} 例")
    print(f"  岁运提及：{stats['mentionTotal']} 处（{stats['mentionByKind']}），覆盖 {stats['withMentions']} 例")
    print(f"  历史断言（claims，非 truth）：{stats['historicalClaims']} 条")
    print(f"  Tianze 侧：computed={stats['tianzeComputed']}，not_computed={stats['tianzeNotComputed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
