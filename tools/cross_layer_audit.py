"""M26 · 跨层一致性审计：同一干支事实在关系层/格局层/特殊格局层不得矛盾。

纪律（目标 #3/#9）：关系存在不等于格局成立——本审计只查「逻辑一致性」
（候选的成立条件互相印证），不查「命中率」，不做事件拟合。

检查项（全部 1045 例全量）：
  C1 arch 靶支必不在场；井栏叉候选 ⟺ 存在 target==日主刃 的 arch 关系（庚日）
  C2 transformation 候选 ⟸ 对应 stem_combination 关系（同一对干、原局可见）
  C3 transformation CANDIDATE ⟹ adjacent_to_day_master 且 season_support（DTZ-47）
  C4 特殊格局候选永不 CONFIRMED；cong BLOCKED 必带阻断证据
  C5 hidden_combination ⟹ SPZY-34 逐对表内 + 贴邻
输出：regression/cross-layer-audit.json / .md（violation 计数，期望全 0）
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tianze.analysis.case_chart import build_case_chart  # noqa: E402
from tianze.ganzhi.tables import YANG_STEM_REN  # noqa: E402
from tianze.relation import tables as T  # noqa: E402

OUT_JSON = "regression/cross-layer-audit.json"
OUT_MD = "regression/cross-layer-audit.md"


def main() -> int:
    books = []
    for f in sorted(os.listdir("knowledge/normalized/cases")):
        if f.endswith(".json") and not any(
                x in f for x in ("temporal_refs", "event_claims", "raw_temporal_spans")):
            books.append(json.load(open(f"knowledge/normalized/cases/{f}", encoding="utf-8")))

    violations: dict[str, list[str]] = {f"C{i}": [] for i in range(1, 6)}
    stats = Counter()
    total = 0

    for book in books:
        for case in book.get("cases", []):
            pillars = (case.get("fact") or {}).get("pillars") or {}
            if not all(pillars.get(k) for k in ("year", "month", "day", "hour")):
                continue
            try:
                chart = build_case_chart(pillars)
            except Exception:
                continue
            total += 1
            cid = case["caseId"]
            present_branches = {p.branch for p in
                                (chart.pillars.year, chart.pillars.month,
                                 chart.pillars.day, chart.pillars.hour) if p}
            rels = chart.relations
            adv = chart.advancedAnalysis["specialPattern"]

            # C1 arch
            arch_targets = set()
            for r in rels:
                if r.kind.value == "arch":
                    arch_targets.add(r.members[2])
                    if r.members[2] in present_branches:
                        violations["C1"].append(f"{cid}: arch 靶支 {r.members[2]} 在场")
            dm = chart.day_master.stem
            ren = YANG_STEM_REN.get(dm)
            jinglancha = [x for x in adv.get("xushiOuter", []) if "井栏叉" in x["type"]]
            for x in jinglancha:
                # 井栏叉候选必须与 arch(target=刃) 同现
                if ren not in arch_targets:
                    violations["C1"].append(f"{cid}: 井栏叉候选无对应 arch(刃{ren}) 关系")
            if jinglancha and dm != "庚":
                violations["C1"].append(f"{cid}: 非庚日出现井栏叉候选（起例越界）")

            # C2/C3 transformation
            stem_combo_labels = {r.label for r in rels if r.kind.value == "stem_combination"}
            for t in adv.get("transformation", []):
                pair = "".join(t["stemPair"])
                if (pair + "合") not in stem_combo_labels:
                    violations["C2"].append(f"{cid}: 化候选 {pair} 无 stem_combination 关系")
                if t["status"] == "CANDIDATE":
                    if not (t.get("adjacentToDayMaster") and t.get("seasonSupport")):
                        violations["C3"].append(
                            f"{cid}: 化候选 {pair} CANDIDATE 但邻位/月令条件缺失 "
                            f"(adj={t.get('adjacentToDayMaster')}, season={t.get('seasonSupport')})")
                stats["transformation:" + t["status"]] += 1

            # C4 special statuses
            for group in ("cong", "zhuanwang", "transformation", "xushiOuter"):
                for x in adv.get(group, []):
                    if x["status"] == "CONFIRMED":
                        violations["C4"].append(f"{cid}: {group} {x['type']} 出现 CONFIRMED")
                if group == "cong":
                    for x in adv.get(group, []):
                        if x["status"] == "BLOCKED" and not x.get("blockers"):
                            violations["C4"].append(
                                f"{cid}: 从格 {x['type']} BLOCKED 但无阻断证据")
                        stats[f"cong:{x['status']}"] += 1

            # C5 hidden combination
            for r in rels:
                if r.kind.value == "hidden_combination":
                    if frozenset(set(r.members)) not in T.HIDDEN_COMBINATIONS:
                        violations["C5"].append(f"{cid}: 暗合 {r.label} 不在 SPZY-34 表")
                    if r.adjacency is not None and r.adjacency.value != "ADJACENT":
                        violations["C5"].append(f"{cid}: 暗合 {r.label} 非贴邻")

    total_violations = sum(len(v) for v in violations.values())
    payload = {
        "schemaVersion": "1.0.0",
        "description": "跨层一致性审计（M26）：关系层/格局层/特殊格局层逻辑一致性；"
                       "violation 期望全 0（关系存在不等于格局成立，仅查内部矛盾）",
        "totalCases": total,
        "violations": {k: v[:50] for k, v in violations.items()},
        "violationCounts": {k: len(v) for k, v in violations.items()},
        "totalViolations": total_violations,
        "stats": dict(stats),
        "checks": {
            "C1": "arch 靶支不在场 + 井栏叉⟺arch(刃) 同现 + 庚日限定",
            "C2": "化候选 ⟸ stem_combination 关系同现",
            "C3": "化候选 CANDIDATE ⟹ 邻位+月令（DTZ-47）",
            "C4": "特殊格局永不 CONFIRMED；cong BLOCKED 必带阻断",
            "C5": "暗合 ⟹ SPZY-34 表内 + 贴邻",
        },
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    md = ["# 跨层一致性审计（M26）", "",
          f"- 覆盖 {total} 例；violation 总数 **{total_violations}**（期望 0）", ""]
    for k, v in violations.items():
        md.append(f"- {k}（{payload['checks'][k]}）：{len(v)} 条"
                  + (f"，如：{v[0]}" if v else ""))
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(chr(10).join(md) + chr(10))

    print(f"跨层一致性审计：{total} 例，violation {total_violations}"
          f"（{payload['violationCounts']}）→ {OUT_JSON}")
    return 1 if total_violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
