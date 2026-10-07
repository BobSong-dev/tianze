"""M18 · Rule/Conflict Graph Audit（推理图深化审计）。

审计项（全部确定性，产出 graph-audit.json）：
- A1 SPECIFIC_EXCEPTION 真实性：声明的 specific 规则必须比 general 更具体
     （结构证据：条件数更多，或 specificCondition 存在）——否则标 UNVERIFIED
- A2 rescue 过度激活：随机盘上谓词激活率 >80% → REVIEW（救应近乎恒真即失去条件意义）
- A3 school-conflict 不被误裁决：静态检查 + 随机盘性质（school 冲突对同盘同向命中
     时的 status 必须 DISPUTED/UNRESOLVED，不得单边裁决）——由 fuzz 锁定，此处记录声明
- A4 循环检测：specific-over-general 的 specific 链不得成环
- B1 heuristic 依赖规则：support 全部依赖 ENGINEERING_HEURISTIC provenance 的规则清单
- B2 rescue 高频/从未激活清单（随机盘）

不调参迎合历史；只报告。
"""

from __future__ import annotations

import datetime
import json
import os
import random
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AUDIT_SCHEMA_VERSION = "1.0.0"


def _load(path, default):
    if not os.path.exists(path):
        return default
    return json.load(open(path, encoding="utf-8"))


def main() -> int:
    rules = _load("knowledge/rules/event/rules.json", {"rules": []})["rules"]
    by_id = {r["id"]: r for r in rules}
    conflicts = _load("knowledge/rules/event/conflicts.json", {"conflicts": []})["conflicts"]
    rescues = _load("knowledge/rules/event/rescues.json", {"rescues": []})["rescues"]

    report: dict = {"schemaVersion": AUDIT_SCHEMA_VERSION, "findings": {}, "lists": {}}

    # A1 specificity 真实性
    spec_findings = []
    for c in conflicts:
        if c.get("resolution") != "specific-over-general":
            continue
        specific, general = c.get("specific"), c.get("ruleB" if c.get("specific") == c.get("ruleA") else "ruleA")
        general = c["ruleA"] if c.get("specific") == c.get("ruleB") else c["ruleB"]
        s_rule, g_rule = by_id.get(specific, {}), by_id.get(general, {})
        s_cond = len(s_rule.get("conditions", []))
        g_cond = len(g_rule.get("conditions", []))
        narrower = s_cond > g_cond
        has_condition = bool(c.get("specificCondition"))
        verdict = ("OK" if (narrower or has_condition)
                   else "UNVERIFIED")
        spec_findings.append({
            "pair": [general, specific], "specificCondition": c.get("specificCondition"),
            "conditionCount": {"specific": s_cond, "general": g_cond},
            "narrowerConditions": narrower, "verdict": verdict,
        })
    report["findings"]["A1_specific_exception"] = spec_findings

    # A4 循环：specific 链
    chain: dict[str, str] = {c["ruleB"]: c["ruleA"] for c in conflicts
                             if c.get("resolution") == "specific-over-general"}
    cycles = []
    for start in chain:
        seen, cur = set(), start
        while cur in chain:
            cur = chain[cur]
            if cur in seen or cur == start:
                cycles.append(f"{start} → … → {cur}")
                break
            seen.add(cur)
    report["findings"]["A4_specific_cycles"] = {"cycles": cycles, "pass": not cycles}

    # A2/B2 rescue 激活率（随机盘 80 例）
    from tianze.analysis.rescues import evaluate_rescues
    from tianze.domain.models import BirthInfo, Gender
    from tianze.pipeline import build_chart
    from tianze.ganzhi.tables import STEMS, BRANCHES
    rng = random.Random(77)
    activation: Counter = Counter()
    total = 0
    for _ in range(80):
        y, mo, d = rng.randint(1940, 2015), rng.randint(1, 12), rng.randint(1, 28)
        try:
            chart = build_chart(BirthInfo(date=datetime.date(y, mo, d),
                                          time=datetime.time(rng.randint(0, 23), 30),
                                          gender=Gender(rng.choice(["male", "female"]))))
        except Exception:
            continue
        from types import SimpleNamespace
        # 用与 event_themes 相同的读数提取
        from tianze.analysis.event_themes import build_event_context
        from tianze.analysis.temporal import analyze_temporal
        ai = rng.randint(0, 59)
        ta = analyze_temporal(
            natal_stems=[chart.pillars.year.stem, chart.pillars.month.stem,
                         chart.pillars.day.stem, chart.pillars.hour.stem],
            natal_branches=[chart.pillars.year.branch, chart.pillars.month.branch,
                            chart.pillars.day.branch, chart.pillars.hour.branch],
            day_master=chart.day_master.stem,
            annual_stem=STEMS[ai % 10], annual_branch=BRANCHES[ai % 12])
        ectx = build_event_context(chart, ta.context, None, ta.relations, ta.structures)
        st = evaluate_rescues(ectx)
        for pid, v in st.items():
            if v["active"]:
                activation[pid] += 1
        total += 1
    rates = {pid: round(n / max(1, total), 3) for pid, n in sorted(activation.items())}
    over_active = {p: r for p, r in rates.items() if r > 0.80}
    never_active = sorted(set(RES_IDS := {d["predicate"] for d in rescues}) - set(rates))
    report["findings"]["A2_rescue_activation"] = {
        "samples": total, "rates": rates,
        "overActive REVIEW": over_active,
        "neverActive": sorted(never_active),
    }

    # A3 school-conflict 声明（运行时性质由 fuzz 锁定，此处记录审计口径）
    school_pairs = [e for e in _load("knowledge/rules/event/conflict-graph.json",
                                     {"edges": []}).get("edges", [])
                    if e.get("type") == "school-conflict"]
    report["findings"]["A3_school_conflict"] = {
        "pairs": len(school_pairs),
        "discipline": "运行时该类冲突只能产生 DISPUTED/UNRESOLVED（fuzz + 单测锁定）；"
                      "静态无裁决路径",
    }

    # B1 heuristic 依赖规则（support 语义规则中 provenance 全为 ENGINEERING）
    heur_dep = []
    for r in rules:
        levels = {p.get("level") for p in r.get("provenance", [])}
        if levels and levels <= {"ENGINEERING_HEURISTIC"}:
            heur_dep.append(r["id"])
    report["lists"]["B1_heuristic_only_rules"] = heur_dep

    with open("regression/graph-audit.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print(f"Graph Audit：A1 UNVERIFIED={sum(1 for x in spec_findings if x['verdict'] != 'OK')} "
          f"| A4 cycles={len(cycles)} | A2 overActive={over_active or '无'} | "
          f"heuristic-only 规则={len(heur_dep)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
