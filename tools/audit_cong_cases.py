"""M8.6.1 · 从格 LIKELY 命例专项审计 + M8.6.2 阴阳干证据搜索 + M8.6.6 PopulationStats。

产出（确定性可重跑）：
- review/cong-likely-cases.csv       LIKELY 命例列表（含原书对照分类）
- docs/advanced/01-CONG-CASE-AUDIT.md
- knowledge/normalized/yinyang-evidence.json   阴阳干从格证据链
- docs/advanced/02-CONG-YINYANG-EVIDENCE.md
- knowledge/normalized/population-stats.json   PopulationStats（denominator 统一）
运行：python tools/audit_cong_cases.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

REPO = Path(__file__).resolve().parents[1]
CASES = REPO / "knowledge" / "normalized" / "cases"
NORM = REPO / "knowledge" / "normalized"
RAW = REPO / "knowledge" / "raw"
OUT_REVIEW = REPO / "review"
OUT_DOCS = REPO / "docs" / "advanced"
OUT_DOCS.mkdir(parents=True, exist_ok=True)

CONG_KEYWORDS = ["从财", "从杀", "从官", "从儿", "从势", "从强", "从旺", "弃命", "从格"]


def analyze_pillars(pillars: dict[str, str]) -> dict | None:
    from tools.derive_case_analysis import analyze_pillars as _ap
    return _ap(pillars)


def compute_special(pillars: dict[str, str]) -> dict | None:
    """实时计算 M8 特殊格局（从格/专旺/化气/病药/通关）。"""
    from tianze.analysis.special import analyze_all_special
    from tianze.analysis.month_command import compute_month_command
    from tianze.analysis.roots import collect_roots
    from tianze.ganzhi.tables import STEM_ELEMENT, HIDDEN_STEMS, ten_god

    stems = [pillars.get(p, "")[:1] or None for p in ("year", "month", "day", "hour")]
    branches = [pillars.get(p, "")[1:2] or None for p in ("year", "month", "day", "hour")]
    dm = stems[2]
    if not dm or not branches[1]:
        return None
    mc = compute_month_command(branches[1], dm, stems)
    roots = collect_roots(stems, branches, ["year", "month", "day", "hour"], dm)
    dm_roots = sum(1 for r in roots if r.is_day_master)
    helpers = [s for s in stems if s and s != dm and
               ten_god(dm, s).value in ("比肩", "劫财", "正印", "偏印")]
    # 简化旺衰：weighted 由 fuyi 替代（此处仅作从格证据，不替代正式分析）
    from tianze.analysis.strength import StrengthFacts, default_run
    facts = StrengthFacts(
        day_master=dm, day_master_element=STEM_ELEMENT[dm],
        month_command=mc, day_master_roots=tuple(r for r in roots if r.is_day_master),
        other_stems=tuple((s, p) for s, p in zip(stems, ["year", "month", "day", "hour"]) if s and p != "day"),
        pillar_units=tuple(zip(["year", "month", "day", "hour"], stems, branches)),
    )
    report = default_run(facts)
    verdicts = {m.name: m.verdict for m in report.methods}
    weighted_score = next((m.score for m in report.methods if m.name == "weighted"), None)

    from tianze.ganzhi.tables import Element
    ec = {}
    for e in Element:
        v = sum(1 for s in stems if s and STEM_ELEMENT.get(s) == e)
        h = sum(1 for b in branches if b and b in HIDDEN_STEMS for h, _ in HIDDEN_STEMS[b] if STEM_ELEMENT[h] == e)
        ec[e.value.lower()] = {"visible": v, "hidden": h}

    from tianze.analysis.special import analyze_all_special
    return analyze_all_special(dm, branches[1], stems, branches, verdicts,
                               weighted_score, dm_roots, helpers, ec)


def check_source_support(case: dict) -> str:
    """检查 sourceAnalysis 是否出现从格相关分析。返回分类标签。"""
    src = json.dumps(case.get("sourceAnalysis") or {}, ensure_ascii=False)
    src += " " + json.dumps(case.get("ruleReferences") or [], ensure_ascii=False)
    for kw in CONG_KEYWORDS:
        if kw in src:
            return "SOURCE_SUPPORTS"
    # 检查是否判了正格（间接否定从格）
    if re.search(r"正官格|七杀格|正财|偏财|正印|偏印|食神格|伤官格|建禄|阳刃", src):
        return "SOURCE_DIFFERENT_PATTERN"
    if "原书" in src or "断语" in src or "判断" in src:
        return "SOURCE_SILENT"
    return "SOURCE_UNRESOLVED"


def main() -> int:
    # ---- M8.6.1 从格 LIKELY 审计 ----
    rows: list[dict] = []
    support_counter: Counter = Counter()
    total_likely = 0
    total_computed = 0

    for path in sorted(CASES.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        book = data["book"]
        for case in data["cases"]:
            total_computed += 1
            tz = case.get("tianzeAnalysis") or {}
            if not tz.get("computed"):
                continue
            pillars = case["fact"]["pillars"]
            if not all(pillars.get(k) for k in ("year", "month", "day", "hour")):
                continue
            special = compute_special(pillars)
            if not special:
                continue
            cong_list = special["specialPattern"]["cong"]
            for c in cong_list:
                if c.get("status") != "LIKELY":
                    continue
                total_likely += 1
                support = check_source_support(case)
                support_counter[support] += 1
                verdicts = tz.get("strengthVerdicts") or {}
                rows.append({
                    "caseId": case["caseId"],
                    "pillars": " ".join(case["fact"]["pillars"].get(k, "") for k in ("year", "month", "day", "hour")),
                    "dayMaster": derived_dm(case),
                    "monthBranch": derived_mb(case),
                    "strengthWeighted": verdicts.get("weighted"),
                    "strengthFuyi": verdicts.get("fuyi"),
                    "strengthAgreement": tz.get("agreement"),
                    "congType": c.get("type"),
                    "congStatus": c.get("status"),
                    "supports": json.dumps(c.get("supports", []), ensure_ascii=False)[:200],
                    "blockers": json.dumps(c.get("blockers", []), ensure_ascii=False)[:200],
                    "sourceBook": book,
                    "sourceVerdict": (case.get("sourceAnalysis") or {}).get("verdict") or "",
                    "sourceSupport": support,
                    "tianzeAnalysis": json.dumps(tz, ensure_ascii=False)[:300],
                    "comparisonStatus": "HAS_SOURCE_CLAIMS" if (case.get("sourceAnalysis") or {}).get("verdict") else "SOURCE_SILENT",
                })

    OUT_REVIEW.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_REVIEW / "cong-likely-cases.csv"
    if rows:
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    # 审计报告
    md = [
        "# 01 · 从格 LIKELY 命例专项审计（CONG CASE AUDIT）",
        "",
        f"> 生成：tools/audit_cong_cases.py。数据：review/cong-likely-cases.csv（{len(rows)} 行）。",
        "",
        "## 统计",
        "",
        f"- 引擎可计算命例：{total_computed}",
        f"- 从格 LIKELY 总数：**{total_likely}**",
        "",
        "| 原书对照分类 | 数量 | 占 LIKELY 比例 |",
        "|---|---|---|",
    ]
    for label in ("SOURCE_SUPPORTS", "SOURCE_REJECTS", "SOURCE_DIFFERENT_PATTERN",
                  "SOURCE_SILENT", "SOURCE_UNRESOLVED"):
        n = support_counter.get(label, 0)
        pct = f"{n / total_likely:.1%}" if total_likely else "N/A"
        md.append(f"| {label} | {n} | {pct} |")
    md += [
        "",
        "## 口径说明",
        "",
        "- SOURCE_SUPPORTS：原书分析文本中出现从格相关关键词（从财/从杀/…）",
        "- SOURCE_DIFFERENT_PATTERN：原书判了正格（间接否定从格——但不等于 Tianze 错）",
        "- SOURCE_SILENT：原书有判断但未提及从格",
        "- 原书未提及从格 **不等于** Tianze 判断错误——口径差异/详略差异均正常",
        "",
        "## 下一步",
        "",
        "1. 对 SOURCE_SUPPORTS：人工逐条核对原书依据是否为从格（升级验证状态）",
        "2. 对 SOURCE_DIFFERENT_PATTERN：分析 Tianze 从格条件是否过松（可能阈值问题）",
        "3. 对 SOURCE_SILENT：无信息，不调参",
        "4. 禁止自动调参迎合古籍——先归因再决策",
    ]
    (OUT_DOCS / "01-CONG-CASE-AUDIT.md").write_text("\n".join(md), encoding="utf-8")

    # ---- M8.6.2 阴阳干从格证据搜索 ----
    keywords = ["从气", "从势", "阴干", "阳干", "阳干从气", "阴干从势", "从强", "从旺", "弃命"]
    evidence = search_knowledge(keywords)
    yinyang_doc = [
        "# 02 · 阴阳干从格证据（CONG YINYANG EVIDENCE）",
        "",
        f"> 生成：tools/audit_cong_cases.py 关键词搜索。搜索词：{keywords}",
        "",
        "## 结论（当前）",
        "",
    ]
    if evidence:
        yinyang_doc.append(f"知识库中找到 {len(evidence)} 条相关候选：\n")
        yinyang_doc.append("| 候选 ID | 书 | 来源文件 | 匹配关键词 | 引文摘要 |")
        yinyang_doc.append("|---|---|---|---|---|")
        for e in evidence:
            quote = (e["quote"][:60] + "…") if len(e["quote"]) > 60 else e["quote"]
            yinyang_doc.append(f"| {e['id']} | {e['book']} | {e['sourceFile']} | {e['matchedKeywords']} | {quote} |")
        yinyang_doc.append("\n## 后续步骤\n")
        yinyang_doc.append("1. 逐条核对原文是否来自古籍原文层（而非徐注/整理层）")
        yinyang_doc.append("2. 如确认古籍层：升级 RuleCandidate → ExecutableRule（CLASSICAL_EXPLICIT）")
        yinyang_doc.append("3. 如仅评注层：标 COMMENTARY（PROJECT_REFERENCE）")
        yinyang_doc.append("4. 如证据不足：保持 UNRESOLVED，不强行实现阴阳干差异")
    else:
        yinyang_doc.append("**证据不足**：知识库 556 条候选中未找到阴阳干从格的直接引文。\n")
        yinyang_doc.append("结论：**保留 UNRESOLVED，不强行实现阴阳干差异。**\n")
        yinyang_doc.append("如需进一步核实：需查《滴天髓》'阳干从气不从势，阴干从势不从气'\n")
        yinyang_doc.append("原始章节的扫描件对照。")
    (OUT_DOCS / "02-CONG-YINYANG-EVIDENCE.md").write_text("\n".join(yinyang_doc), encoding="utf-8")
    (NORM / "yinyang-evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- M8.6.6 PopulationStats ----
    from tools.normalize_cases import main as _nc  # noqa
    stats = build_population_stats()
    (NORM / "population-stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")

    print(json.dumps({
        "likelyTotal": total_likely,
        "support": dict(support_counter),
        "yinyangEvidence": len(evidence),
        "populationStats": stats,
    }, ensure_ascii=False, indent=1, default=str))
    return 0


def derived_dm(case: dict) -> str:
    p = case["fact"]["pillars"]
    return p.get("day", "")[:1] if p.get("day") else ""


def derived_mb(case: dict) -> str:
    p = case["fact"]["pillars"]
    return p.get("month", "")[1:2] if p.get("month") else ""


def search_knowledge(keywords: list[str]) -> list[dict]:
    """在 normalized 候选库中搜索关键词，返回证据链。"""
    results = []
    for rules_file in sorted(NORM.glob("*/rules.json")):
        data = json.loads(rules_file.read_text(encoding="utf-8"))
        for r in data["rules"]:
            searchable = " ".join(filter(None, [
                r.get("coreText"), r.get("originalQuotes") and " ".join(r["originalQuotes"]),
                r.get("applicableCondition"), "、".join(r.get("tags") or []),
                r.get("commentaries") and " ".join(c.get("text", "") for c in r["commentaries"]),
            ]))
            matched = [kw for kw in keywords if kw in searchable]
            if matched:
                quotes = r.get("originalQuotes") or [""]
                results.append({
                    "id": r["id"], "book": r["book"], "sourceFile": r.get("sourceFile", ""),
                    "matchedKeywords": ",".join(matched),
                    "quote": quotes[0][:100], "title": r.get("title") or "",
                    "contentNature": r.get("contentNature") or [],
                })
    return results


def build_population_stats() -> dict:
    """M8.6.6：统一 denominator——所有分布输出 count/eligibleCount/rate。"""
    cases = []
    for path in sorted(CASES.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        cases.extend(data["cases"])

    total = len(cases)
    parseable = sum(1 for c in cases
                    if all(c["fact"]["pillars"].get(k) for k in ("year", "month", "day", "hour")))
    computed = sum(1 for c in cases if (c.get("tianzeAnalysis") or {}).get("computed"))

    def rate(count: int, eligible: int) -> float:
        return round(count / eligible, 4) if eligible else 0.0

    return {
        "totalCases": total,
        "parseableCases": parseable,
        "engineEligibleCases": computed,
        "strengthEligibleCases": computed,
        "patternEligibleCases": computed,
        "tiaohouEligibleCases": computed,
        "specialPatternEligibleCases": computed,
        "transformationEligibleCases": total,  # 化气对全部命例有意义（无四柱也可报 UNRESOLVED）
        "unresolvedCases": total - parseable,
    }


if __name__ == "__main__":
    sys.exit(main())
