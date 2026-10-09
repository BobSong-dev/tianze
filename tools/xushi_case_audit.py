"""M25 · 命例×虚神专题审计：1147 命例全量拱夹/暗合分布。

只做分布描述与结构统计，不做任何事件拟合（纪律：历史断语只用于对照）。

输出：
- regression/xushi-audit.json / .md
  - casesWithXushi / archBySubType / hiddenByPair / blockedCount
  - perBook 覆盖率；xushiOuter 外格候选分布（候选级，非成格）
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tianze.analysis.case_chart import build_case_chart  # noqa: E402

OUT_JSON = "regression/xushi-audit.json"
OUT_MD = "regression/xushi-audit.md"


def main() -> int:
    books = []
    for f in sorted(os.listdir("knowledge/normalized/cases")):
        if f.endswith(".json") and not any(
                x in f for x in ("temporal_refs", "event_claims", "raw_temporal_spans")):
            books.append(json.load(open(f"knowledge/normalized/cases/{f}", encoding="utf-8")))

    total = arch_total = hidden_total = blocked_total = outer_total = 0
    cases_with = 0
    arch_by_sub = Counter()
    hidden_by_pair = Counter()
    outer_by_type = Counter()
    per_book: dict[str, dict] = {}
    errors = 0

    # M26 · 分布研究维度
    arch_by_daymaster: Counter = Counter()   # 日主×拱夹 sub_type（top 泛化审计）
    arch_by_sub_daymaster_top: Counter = Counter()
    hidden_by_monthbranch: Counter = Counter()
    engine_vs_claims = {"engineCases": 0, "claimsMentionXushi": 0, "overlap": 0}
    # M29 · 假从根气分级分布（SP-CG-E2 文本特征统计）
    grade_dist: Counter = Counter()
    # M35 · 合化专题统计
    hehua_status: Counter = Counter()
    hehua_obstruction: Counter = Counter()
    hehua_adjacent = 0
    kong_stats = {"nobleInDayKong": 0, "nobleInYearKong": 0, "nobleCases": 0,
                  "shuguiKongBlocked": 0, "shuguiTotal": 0}
    XUSHI_KEYWORDS = ("拱", "暗合", "虚神", "邀")

    for book in books:
        for case in book.get("cases", []):
            pillars = (case.get("fact") or {}).get("pillars") or {}
            if not all(pillars.get(k) for k in ("year", "month", "day", "hour")):
                continue
            try:
                chart = build_case_chart(pillars)
            except Exception:
                errors += 1
                continue
            total += 1
            day_master_key = chart.day_master.stem
            bname = case.get("book", "?")
            slot = per_book.setdefault(
                bname, {"cases": 0, "withXushi": 0, "arch": 0, "hidden": 0,
                        "blocked": 0, "xushiOuter": 0})
            slot["cases"] += 1
            has = False
            for r in chart.relations:
                if r.kind.value == "arch":
                    arch_total += 1
                    slot["arch"] += 1
                    arch_by_sub[r.sub_type or "拱夹"] += 1
                    arch_by_daymaster[day_master_key + "|" + (r.sub_type or "拱夹")] += 1
                    has = True
                elif r.kind.value == "hidden_combination":
                    hidden_total += 1
                    slot["hidden"] += 1
                    hidden_by_pair[r.label] += 1
                    hidden_by_monthbranch[(chart.month_command.month_branch if chart.month_command else "?")
                                          + "|" + r.label] += 1
                    has = True
            blocked_total += len(chart.blocked_relations)
            slot["blocked"] += len(chart.blocked_relations)
            if chart.blocked_relations:
                has = True
            xo = chart.advancedAnalysis.get("specialPattern", {}).get("xushiOuter") or []
            for x in xo:
                outer_by_type[f"{x['type']}:{x['status']}"] += 1
                slot["xushiOuter"] += 1
                outer_total += 1
                has = True
            # M28：贵人×旬空（日柱/年柱口径；SS-R16 第三要件语料级统计）
            dm2 = chart.day_master.stem
            from tianze.relation.tables import TIAN_YI_NOBLE, xun_kong_of
            nobles = TIAN_YI_NOBLE.get(dm2, frozenset())
            if nobles:
                kong_stats["nobleCases"] += 1
                day_gz = pillars.get("day") or ""
                year_gz = pillars.get("year") or ""
                dk, yk = xun_kong_of(day_gz), xun_kong_of(year_gz)
                if dk and (nobles & dk):
                    kong_stats["nobleInDayKong"] += 1
                if yk and (nobles & yk):
                    kong_stats["nobleInYearKong"] += 1
            for t in chart.advancedAnalysis.get("specialPattern", {}).get("transformation", []):
                hehua_status[t["status"]] += 1
                for ob in t.get("obstructions", []):
                    kind = ("争合" if "争合" in ob else
                            "隔位" if ("相隔" in ob or "非日主" in ob) else
                            "印比阻化" if "印绶" in ob else "其他")
                    hehua_obstruction[kind] += 1
                if t.get("adjacentToDayMaster"):
                    hehua_adjacent += 1
            for c in chart.advancedAnalysis.get("specialPattern", {}).get("cong", []):
                for e in c.get("exceptions", []):
                    t = e.get("text", "")
                    if "SP-CG-E2" in (e.get("ruleId") or ""):
                        for g in ("强根（本气）", "明根（中气）", "微根（余气/墓库）", "无根"):
                            if g in t:
                                grade_dist[g] += 1
                                break
            for x in xo:
                if "六乙鼠贵" in x["type"]:
                    kong_stats["shuguiTotal"] += 1
                    if x["status"] == "BLOCKED" and any(
                            "空亡" in b.get("text", "") for b in x.get("blockers", [])):
                        kong_stats["shuguiKongBlocked"] += 1
            if has:
                cases_with += 1
                slot["withXushi"] += 1

    # M26 · Engine 检出 vs 原书标注提及（claims 文本为 MACHINE_EXTRACTED 摘要，
    # 非原文——结果只作粗对照，不等同原书明确采用；raw OCR 语料不在仓库，BLOCKED）
    claims_data = json.load(open("knowledge/normalized/cases/event_claims.json",
                                 encoding="utf-8"))
    engine_case_ids = set()
    # 重扫一遍拿 engine 检出的 caseId（与上面循环同口径）
    for book in books:
        for case in book.get("cases", []):
            pillars = (case.get("fact") or {}).get("pillars") or {}
            if not all(pillars.get(k) for k in ("year", "month", "day", "hour")):
                continue
            try:
                ch = build_case_chart(pillars)
            except Exception:
                continue
            if (any(r.kind.value in ("arch", "hidden_combination") for r in ch.relations)
                    or ch.blocked_relations):
                engine_case_ids.add(case["caseId"])
    for c in claims_data.get("cases", []):
        text = " ".join(cl.get("text", "") for cl in c.get("claims", []))
        mentioned = any(k in text for k in XUSHI_KEYWORDS)
        if mentioned:
            engine_vs_claims["claimsMentionXushi"] += 1
        if c["caseId"] in engine_case_ids:
            engine_vs_claims["engineCases"] += 1
            if mentioned:
                engine_vs_claims["overlap"] += 1

    payload = {
        "schemaVersion": "1.0.0",
        "description": "命例×虚神专题审计（M25）：分布描述，不做事件拟合",
        "totalCasesParsed": total,
        "parseErrors": errors,
        "casesWithXushi": cases_with,
        "archTotal": arch_total,
        "archBySubType": dict(arch_by_sub),
        "hiddenTotal": hidden_total,
        "hiddenByPair": dict(hidden_by_pair.most_common()),
        "blockedCandidatesTotal": blocked_total,
        "xushiOuterTotal": outer_total,
        "xushiOuterByTypeStatus": dict(outer_by_type),
        "perBook": per_book,
        "archByDayMasterTop": dict(arch_by_daymaster.most_common(12)),
        "hiddenByMonthBranchTop": dict(hidden_by_monthbranch.most_common(10)),
        "engineVsClaims": dict(engine_vs_claims),
        "nobleKongStats": kong_stats,
        "jiacongGradeDistribution": dict(grade_dist),
        "hehuaStats": {
            "statusDistribution": dict(hehua_status),
            "obstructionTypes": dict(hehua_obstruction),
            "adjacentCandidates": hehua_adjacent,
        },
        "engineVsClaimsCaveat": "claims 文本为 MACHINE_EXTRACTED 摘要，仅作粗对照；"
                                "「原书明确采用」需对照 raw OCR 语料（不在仓库，BLOCKED）",
        "discipline": "历史断语只用于对照；本审计不输出任何吉凶或事件结论",
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    md = ["# 命例×虚神专题审计（M25/M26）", "",
          f"- Engine 检出 vs 原书标注提及（MACHINE_EXTRACTED 粗对照）："
          f"engine {engine_vs_claims['engineCases']} 例 / 标注提及 "
          f"{engine_vs_claims['claimsMentionXushi']} 例 / 重叠 {engine_vs_claims['overlap']} 例",
          f"- 高频泛化审计（日主×拱型 top）："
          f"{dict(arch_by_daymaster.most_common(6))}",
          "",
          f"- 解析 {total} 例（错误 {errors}）；含拱夹/暗合/未成立候选/外格候选的命例 "
          f"**{cases_with}** 例",
          f"- 拱夹 {arch_total} 次（{dict(arch_by_sub.most_common(6))}）",
          f"- 暗合 {hidden_total} 次（top: {dict(hidden_by_pair.most_common(6))}）",
          f"- 未成立候选（拱而不成）{blocked_total} 次",
          f"- 外格候选（xushiOuter）{outer_total} 次（{dict(outer_by_type.most_common(6))}）",
          "", "| 书 | 命例 | 含虚神 | 拱夹 | 暗合 | 未成立 | 外格候选 |", "|---|---|---|---|---|---|---|"]
    for b, s in sorted(per_book.items(), key=lambda kv: -kv[1]["cases"]):
        md.append(f"| {b} | {s['cases']} | {s['withXushi']} | {s['arch']} | "
                  f"{s['hidden']} | {s['blocked']} | {s['xushiOuter']} |")
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(chr(10).join(md) + chr(10))

    print(f"虚神专题审计：{total} 例，{cases_with} 例含虚神/暗合/候选"
          f"（拱 {arch_total}、暗合 {hidden_total}、未成立 {blocked_total}、"
          f"外格候选 {outer_total}）→ {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
