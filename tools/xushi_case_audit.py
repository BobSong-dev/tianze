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
                    has = True
                elif r.kind.value == "hidden_combination":
                    hidden_total += 1
                    slot["hidden"] += 1
                    hidden_by_pair[r.label] += 1
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
            if has:
                cases_with += 1
                slot["withXushi"] += 1

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
        "discipline": "历史断语只用于对照；本审计不输出任何吉凶或事件结论",
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    md = ["# 命例×虚神专题审计（M25）", "",
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
