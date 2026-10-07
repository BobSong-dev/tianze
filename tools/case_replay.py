"""M15 · Historical Case Replay：原书岁运上下文重放 + 事件主题对照。

对有结构化大运序列的命例（M13 解析出 101 例）：
    当时原局（四柱重建分析上下文）
    → 原书大运（source dayun，作 luck 层输入）
    → 原书流年干支（claims 共现 gz，作 annual 层输入，若有）
    → Temporal Delta + EventThemeCandidate
    → 与 historicalClaims 主题标注对照

对照分级（不是真理裁决）：
    SOURCE_SUPPORTS    claim 主题与 Tianze 主题同向（tianze 该主题有支持证据）
    SOURCE_DIFFERS     claim 主题在 Tianze 侧只有反对证据或无候选
    SOURCE_SILENT      Tianze 有主题候选但原书 claim 未提及该主题
    TIANZE_UNRESOLVED  Tianze 主题为 UNRESOLVED（输入不足）

纪律：统计只描述覆盖与分歧；严禁为提高命中率调整规则。
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tianze.analysis.case_chart import build_case_chart
from tianze.analysis.event_themes import EventTheme, EventStatus, compute_event_themes

REPLAY_SCHEMA_VERSION = "1.0.0"


def _claim_themes(event_claims: dict, case_id: str) -> list[str]:
    for c in event_claims.get("cases", []):
        if c["caseId"] == case_id:
            themes: list[str] = []
            for cl in c.get("claims", []):
                themes.extend(cl.get("eventThemes") or [])
            return sorted(set(themes))
    return []


def replay_case(case: dict, temporal_ref: dict | None,
                claim_themes: list[str], book: str | None = None,
                raw_spans: list[dict] | None = None) -> dict | None:
    """单命例重放。缺结构化大运 → 跳过（scope 限制如实报告）。"""
    pillars = (case.get("fact") or {}).get("pillars") or {}
    if not all(pillars.get(k) for k in ("year", "month", "day", "hour")):
        return None
    st = (temporal_ref or {}).get("sourceTemporal") or {}
    dayun = st.get("dayun") or []
    mentions = st.get("mentions") or []
    # 岁运上下文来源（两路，均来自原书记载）：
    #   a) 结构化大运序列首项；b) 文本中的完整干支运提及（如「行辛亥运」）
    # 文本提及的运优先（原书分析针对的具体运）；无提及再用结构化大运首项
    luck_gz = None
    luck_src = None
    annual_gz = None
    import re
    for m in mentions:
        if m.get("kind") == "luck" and m.get("ganZhi") and not luck_gz:
            luck_gz = m["ganZhi"]
            luck_src = f"mention:{m.get('rawText', '')}"
        if m.get("kind") == "annual" and m.get("ganZhi") and not annual_gz:
            annual_gz = m["ganZhi"]
    # M17：原文 span 源（confidence=high 才采用；UNRESOLVED 不猜）
    for sp in (raw_spans or []):
        if sp.get("confidence") != "high":
            continue
        if sp["kind"] == "luck" and not luck_gz:
            luck_gz = sp["ganZhi"]
            luck_src = f"raw-span:{sp.get('field')}"
        elif sp["kind"] == "annual" and not annual_gz:
            annual_gz = sp["ganZhi"]
    if not luck_gz and dayun:
        luck_gz = dayun[0].get("ganZhi")
        luck_src = "dayun[0]"
    # 仅有流年提及（无大运）也可重放——annual-only 上下文
    annual_only = False
    if not luck_gz:
        if not annual_gz:
            return None
        annual_only = True
        luck_src = "annual-only"
    gender = (case.get("fact") or {}).get("gender")

    chart = build_case_chart(pillars, gender=gender)

    luck = (luck_gz[0], luck_gz[1]) if luck_gz else None
    annual = (annual_gz[0], annual_gz[1]) if annual_gz else None

    report = compute_event_themes(chart, luck=luck, annual=annual)
    tianze_themes = {t.theme.value: t for t in report.themes}

    matches: list[dict] = []
    for theme in claim_themes:
        t = tianze_themes.get(theme)
        if t is None:
            matches.append({"theme": theme, "relation": "SOURCE_DIFFERS",
                            "note": "claim 有主题，Tianze 无该主题候选"})
        elif t.status == EventStatus.UNRESOLVED:
            matches.append({"theme": theme, "relation": "TIANZE_UNRESOLVED",
                            "note": "Tianze 输入不足（UNRESOLVED）"})
        elif t.supportingEvidence:
            matches.append({"theme": theme, "relation": "SOURCE_SUPPORTS",
                            "note": f"status={t.status.value}，支持证据 {len(t.supportingEvidence)} 条"
                                    + (f"，反对 {len(t.opposingEvidence)} 条" if t.opposingEvidence else "")})
        else:
            matches.append({"theme": theme, "relation": "SOURCE_DIFFERS",
                            "note": f"status={t.status.value}，仅反对证据"})
    silent = [th for th in tianze_themes if th not in claim_themes]
    for th in silent:
        matches.append({"theme": th, "relation": "SOURCE_SILENT",
                        "note": "Tianze 有候选，原书 claim 未提及"})

    return {
        "caseId": case["caseId"],
        "book": book,
        "luck": luck_gz,
        "luckSource": luck_src,
        "annualOnly": annual_only,
        "annual": annual_gz,
        "claimThemes": claim_themes,
        "tianzeThemes": [
            {"theme": t.theme.value, "status": t.status.value,
             "agreement": t.agreement, "confidence": t.confidence,
             "rules": [h.ruleId for h in t.triggeredRules]}
            for t in report.themes
        ],
        "matches": matches,
        "specialFindings": len((report.params or {}).get("specialFindings", []) or []),
        "note": "原书大运/流年按原书记载重放（无出生年份，无法重算起运）；"
                "对照不裁决谁对",
    }


def main() -> int:
    books = []
    for f in sorted(os.listdir("knowledge/normalized/cases")):
        if f.endswith(".json") and not any(x in f for x in ("temporal_refs", "event_claims", "raw_temporal_spans")):
            books.append(json.load(open(f"knowledge/normalized/cases/{f}", encoding="utf-8")))
    temporal_refs = json.load(open("knowledge/normalized/cases/temporal_refs.json",
                                   encoding="utf-8"))
    event_claims = json.load(open("knowledge/normalized/cases/event_claims.json",
                                  encoding="utf-8"))
    ref_by_id = {c["caseId"]: c for c in temporal_refs["cases"]}
    raw_spans_path = "knowledge/normalized/cases/raw_temporal_spans.json"
    spans_by_id = {}
    if os.path.exists(raw_spans_path):
        raw_spans = json.load(open(raw_spans_path, encoding="utf-8"))
        spans_by_id = {c["caseId"]: c.get("spans", []) for c in raw_spans.get("cases", [])}

    replays = []
    stats = {
        "totalCases": 0, "replayed": 0, "skippedNoDayun": 0,
        "relationCounts": Counter(), "themeCoverage": Counter(),
        "unresolvedRate": 0.0, "disagreementRate": 0.0,
        "ruleHitCoverage": Counter(), "statusDistribution": Counter(),
    }
    unresolved_themes = 0
    disputed_themes = 0
    total_themes = 0

    for book_data in books:
        book_name = book_data.get("book")
        for case in book_data["cases"]:
            stats["totalCases"] += 1
            cid = case["caseId"]
            r = replay_case(case, ref_by_id.get(cid),
                            _claim_themes(event_claims, cid), book_name,
                            raw_spans=spans_by_id.get(cid, []))
            if r is None:
                stats["skippedNoDayun"] += 1
                continue
            stats["luckSourceCounts"] = stats.get("luckSourceCounts", Counter())
            src_kind = "dayun" if (r.get("luckSource") or "").startswith("dayun") else "mention"
            stats["luckSourceCounts"][src_kind] += 1
            stats["replayed"] += 1
            for m in r["matches"]:
                stats["relationCounts"][m["relation"]] += 1
            for t in r["tianzeThemes"]:
                total_themes += 1
                stats["themeCoverage"][t["theme"]] += 1
                stats["statusDistribution"][t["status"]] += 1
                if t["status"] == "UNRESOLVED":
                    unresolved_themes += 1
                if t["status"] == "DISPUTED":
                    disputed_themes += 1
                for rid in t["rules"]:
                    stats["ruleHitCoverage"][rid] += 1
            replays.append(r)

    stats["luckSourceCounts"] = dict(stats.get("luckSourceCounts", {}))
    stats["relationCounts"] = dict(stats["relationCounts"])
    stats["themeCoverage"] = dict(stats["themeCoverage"])
    stats["ruleHitCoverage"] = dict(sorted(stats["ruleHitCoverage"].items()))
    stats["statusDistribution"] = dict(stats["statusDistribution"])
    stats["unresolvedRate"] = round(unresolved_themes / max(1, total_themes), 3)
    stats["disagreementRate"] = round(disputed_themes / max(1, total_themes), 3)

    payload = {
        "schemaVersion": REPLAY_SCHEMA_VERSION,
        "description": "Historical Case Replay：原书岁运重放 × EventThemeCandidate 对照",
        "verification": {"status": "MACHINE_EXTRACTED", "sourceChecked": False},
        "count": len(replays),
        "stats": stats,
        "replays": replays,
    }
    os.makedirs("regression", exist_ok=True)
    with open("regression/case-replay.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    print(f"Case Replay：{stats['replayed']}/{stats['totalCases']} 例重放"
          f"（跳过 {stats['skippedNoDayun']}：无结构化大运）")
    print(f"  对照分级：{stats['relationCounts']}")
    print(f"  主题覆盖：{stats['themeCoverage']}")
    print(f"  status 分布：{stats['statusDistribution']}")
    print(f"  unresolved 率：{stats['unresolvedRate']} | disagreement 率：{stats['disagreementRate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
