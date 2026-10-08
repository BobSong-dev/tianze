"""M30 · 命例状态回放统计：重放命例的逐层虚神事件迁移分布。

围绕有结构化大运的重放命例（case_replay 同口径）做 natal→大运→流年 回放：
- 各层引入/移除事件分布；
- 「再次填实」案例数（unfill 之后任何层又出现 fill）；
- 顺序一致性（固定层序由构造保证；此处复核 removed 事件不在同层重现）。

只做分布与一致性统计，不做事件拟合。输出 regression/state-replay.json/.md。
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tianze.analysis.temporal_replay import replay_temporal  # noqa: E402

OUT_JSON = "regression/state-replay.json"
OUT_MD = "regression/state-replay.md"


def main() -> int:
    books = []
    for f in sorted(os.listdir("knowledge/normalized/cases")):
        if f.endswith(".json") and not any(
                x in f for x in ("temporal_refs", "event_claims", "raw_temporal_spans")):
            books.append(json.load(open(f"knowledge/normalized/cases/{f}", encoding="utf-8")))

    total = replayed = 0
    layer_added: Counter = Counter()
    layer_removed: Counter = Counter()
    refill_cases = 0
    order_violations = 0
    errors = 0

    refs = json.load(open("knowledge/normalized/cases/temporal_refs.json",
                          encoding="utf-8"))
    ref_by_id = {c["caseId"]: c for c in refs.get("cases", [])}

    # M32 · 出生年干支锚（caseId 载「·XX年」者）：60 年周期必然多解 →
    # 输出候选集并标 UNRESOLVED，绝不唯一化、不回推编造年份。
    from tianze.ganzhi.tables import STEMS, BRANCHES

    def _year_candidates(gz: str, lo: int = 1500, hi: int = 2100) -> list[int]:
        if len(gz) < 2 or gz[0] not in STEMS or gz[1] not in BRANCHES:
            return []
        si, bi = STEMS.index(gz[0]), BRANCHES.index(gz[1])
        if (si % 2) != (bi % 2):
            return []
        base = next(y for y in range(4, hi)
                    if STEMS[(y - 4) % 10] == gz[0] and BRANCHES[(y - 4) % 12] == gz[1])
        return [y for y in range(base, hi, 60) if y >= lo]

    import re as _re
    year_anchor_stats = {"casesWithYearGz": 0, "unresolvedMulti": 0, "candidatesHistogram": Counter()}

    for book in books:
        for case in book.get("cases", []):
            pillars = (case.get("fact") or {}).get("pillars") or {}
            if not all(pillars.get(k) for k in ("year", "month", "day", "hour")):
                continue
            total += 1
            cid = case["caseId"]
            # 年锚候选统计（全量；多解即 UNRESOLVED，不参与回放）
            m = _re.search(r"[·•]\s*([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])年", cid)
            if m:
                year_anchor_stats["casesWithYearGz"] += 1
                cands = _year_candidates(m.group(1))
                year_anchor_stats["candidatesHistogram"][len(cands)] += 1
                if len(cands) > 1:
                    year_anchor_stats["unresolvedMulti"] += 1
            ref = ref_by_id.get(cid) or {}
            dayun = (ref.get("sourceTemporal") or {}).get("dayun") or []
            if not dayun:
                continue
            gz = dayun[0].get("ganZhi") or ""
            if len(gz) < 2:
                continue
            annual_pair = None
            age = dayun[0].get("age")
            if age:
                # 起运年龄 → 首个流年（起点年无法回推出生年时用干支序近似：
                # 以 age+1970 作为锚点会产生编造年份——改为只在干支可推导时回放，
                # 即不带流年层，仅 natal→大运）
                annual_pair = None
            try:
                from tianze.analysis.case_chart import build_case_chart
                chart = build_case_chart(pillars)
                r = replay_temporal(
                    natal_stems=[chart.pillars.year.stem, chart.pillars.month.stem,
                                 chart.pillars.day.stem, chart.pillars.hour.stem],
                    natal_branches=[chart.pillars.year.branch, chart.pillars.month.branch,
                                    chart.pillars.day.branch, chart.pillars.hour.branch],
                    day_master=chart.day_master.stem,
                    luck=(gz[0], gz[1]), annual=annual_pair)
            except Exception:
                errors += 1
                continue
            replayed += 1
            seen_unfill = False
            seen_fill_after_unfill = False
            for step in r.steps:
                for a in step.added:
                    layer_added[f"{step.layer}:{a['kind']}"] += 1
                    if a["kind"] == "arch_unfill":
                        seen_unfill = True
                    if a["kind"] == "arch_fill" and seen_unfill:
                        seen_fill_after_unfill = True
                for rm in step.removed:
                    layer_removed[f"{step.layer}:{rm['kind']}"] += 1
                added_keys = {a["kind"] + a["label"] for a in step.added}
                removed_keys = {rm["kind"] + rm["label"] for rm in step.removed}
                if added_keys & removed_keys:
                    order_violations += 1
            if seen_fill_after_unfill:
                refill_cases += 1

    payload = {
        "schemaVersion": "1.0.0",
        "description": "命例状态回放统计（M30）：natal→大运→流年 逐层虚神事件迁移；"
                       "只做分布与一致性，不做事件拟合",
        "totalCases": total,
        "replayed": replayed,
        "errors": errors,
        "note": "流年层未回放：命例仅载起运年龄（无出生年可回推干支），"
                "回推会编造年份——natal→大运 两层先行；流年层待有可靠年份锚点",
        "layerAdded": dict(layer_added.most_common()),
        "layerRemoved": dict(layer_removed.most_common()),
        "refillAfterUnfillCases": refill_cases,
        "yearAnchorStats": {
            **{k: v for k, v in year_anchor_stats.items() if k != "candidatesHistogram"},
            "candidatesCountHistogram": dict(year_anchor_stats["candidatesHistogram"]),
            "status": "UNRESOLVED",
            "note": "60 年周期必然多解——流年层回放维持 BLOCKED，"
                    "待原文提供唯一年份（如帝王年号/公历年）方可锚定",
        },
        "orderViolations": order_violations,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    md = ["# 命例状态回放统计（M30）", "",
          f"- 回放 {replayed}/{total} 例（有结构化大运；错误 {errors}）",
          f"- 各层新增事件 top：{dict(layer_added.most_common(8))}",
          f"- 各层移除事件 top：{dict(layer_removed.most_common(6))}",
          f"- 去填后再次填实命例：{refill_cases}",
          f"- 顺序一致性违规：{order_violations}（期望 0，固定层序由构造保证）"]
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(chr(10).join(md) + chr(10))

    print(f"状态回放统计：{replayed} 例；顺序违规 {order_violations}；"
          f"再次填实 {refill_cases} 例 → {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
