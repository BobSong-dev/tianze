"""M7 · 命例引擎派生分析 + Rule↔Case 双向关联 + 索引。

对四柱可解析的命例运行 Tianze 引擎（strength/pattern/tiaohou——全部基于干支，
无需出生日期），填充 tianzeAnalysis（与 sourceAnalysis 严格分离）；
建立 EXPLICITLY_CITED（原书引用）/ ENGINE_TRIGGERED（引擎触发）两种关联并
生成结构化索引（结构化检索，非 RAG）。

产出：knowledge/normalized/cases/*-analyzed.json、knowledge/indexes/cases/*.json
运行：python tools/derive_case_analysis.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

REPO = Path(__file__).resolve().parents[1]
CASES = REPO / "knowledge" / "normalized" / "cases"
IDX = REPO / "knowledge" / "indexes" / "cases"

from tianze.analysis.pattern import analyze_pattern
from tianze.analysis.strength import StrengthFacts, run_strength
from tianze.analysis.strength.methods.dimensional import DimensionalStrengthAnalyzer
from tianze.analysis.strength.methods.fuyi import FuyiStrengthAnalyzer
from tianze.analysis.strength.methods.weighted import WeightedStrengthAnalyzer
from tianze.analysis.tiaohou import analyze_tiaohou
from tianze.analysis.month_command import compute_month_command
from tianze.analysis.roots import collect_roots
from tianze.domain.models import RuleLevel
from tianze.ganzhi.tables import STEM_ELEMENT

POS4 = ["year", "month", "day", "hour"]


def analyze_pillars(pillars: dict[str, str]) -> dict | None:
    stems = [pillars.get(p) or None for p in POS4]
    stems = [s[0] if s else None for s in stems]
    branches = [pillars.get(p) or None for p in POS4]
    branches = [b[1] if b else None for b in branches]
    day_master = stems[2]
    month_branch = branches[1]
    if not day_master or not month_branch:
        return None
    month_command = compute_month_command(month_branch, day_master, stems)
    roots = collect_roots(stems, branches, POS4, day_master)
    facts = StrengthFacts(
        day_master=day_master,
        day_master_element=STEM_ELEMENT[day_master],
        month_command=month_command,
        day_master_roots=tuple(r for r in roots if r.is_day_master),
        other_stems=tuple((s, p) for s, p in zip(stems, POS4) if s and p != "day"),
        pillar_units=tuple(zip(POS4, stems, branches)),
    )
    report = run_strength([DimensionalStrengthAnalyzer(), WeightedStrengthAnalyzer(), FuyiStrengthAnalyzer()], facts)
    verdicts = {m.name: m.verdict for m in report.methods}
    pattern = analyze_pattern(day_master, month_branch, stems, POS4)
    tiaohou = analyze_tiaohou(day_master, month_branch, dict(zip(POS4, stems)))
    primary = [r.target_stem for r in tiaohou.recommendations if r.priority == "primary"]
    return {
        "strengthVerdicts": verdicts,
        "patternCandidate": pattern.candidates[0].name if pattern.candidates else None,
        "patternStatus": pattern.evaluation.status if pattern.evaluation else None,
        "tiaohouTargets": primary + [r.target_stem for r in tiaohou.recommendations if r.priority == "secondary"],
        "tiaohouPrimaryPresent": (next((r.present for r in tiaohou.recommendations if r.priority == "primary"), None)),
        "engineRuleIds": tiaohou.rule_ids,
        "dayMaster": day_master,
        "monthBranch": month_branch,
        "agreement": report.agreement,
    }


def main() -> int:
    IDX.mkdir(parents=True, exist_ok=True)
    rule_to_cases: dict[str, dict] = defaultdict(lambda: {"EXPLICITLY_CITED": [], "ENGINE_TRIGGERED": []})
    by_day: dict[str, list] = defaultdict(list)
    by_month: dict[str, list] = defaultdict(list)
    by_book: dict[str, list] = defaultdict(list)
    computed = 0

    for path in sorted(CASES.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for case in data["cases"]:
            cid = case["caseId"]
            pillars = case["fact"]["pillars"]
            resolved = all(pillars.get(p) for p in POS4)
            if resolved:
                derived = analyze_pillars(pillars)
                if derived:
                    computed += 1
                    case["tianzeAnalysis"] = {
                        "computed": True,
                        "strengthVerdicts": derived["strengthVerdicts"],
                        "patternCandidate": derived["patternCandidate"],
                        "patternStatus": derived["patternStatus"],
                        "tiaohouTargets": derived["tiaohouTargets"],
                        "tiaohouPrimaryPresent": derived["tiaohouPrimaryPresent"],
                        "engineRuleIds": derived["engineRuleIds"],
                        "note": "Tianze 引擎对四柱的结构分析（与原书分析无关，仅记录）",
                    }
                    by_day[derived["dayMaster"]].append(cid)
                    by_month[derived["monthBranch"]].append(cid)
                    for rid in derived["engineRuleIds"]:
                        rule_to_cases[rid]["ENGINE_TRIGGERED"].append(cid)
            for ref in case.get("ruleReferences", []):
                rule_to_cases[ref["ruleId"]].setdefault("EXPLICITLY_CITED", []).append(cid)
                rule_to_cases[ref["ruleId"]].setdefault("ENGINE_TRIGGERED", [])
            case.setdefault("tianzeAnalysis", {"computed": False})
            by_book[case["source"]["book"]].append(cid)

        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    # 候选 ID → 可执行规则的映射（TH-{候选}-{月支}）
    er_rules = json.loads((REPO / "knowledge" / "rules" / "tiaohou" / "rules.json").read_text(encoding="utf-8"))["rules"]
    candidate_to_exec: dict[str, list[str]] = defaultdict(list)
    for r in er_rules:
        candidate_to_exec[r["candidateId"]].append(r["id"])

    by_rule = {}
    for cand_id, exec_ids in sorted(candidate_to_exec.items()):
        entry = {"EXPLICITLY_CITED": [], "ENGINE_TRIGGERED": []}
        for eid in exec_ids:
            linked = rule_to_cases.get(eid, {})
            entry["EXPLICITLY_CITED"] += [c for c in linked.get("EXPLICITLY_CITED", []) if c not in entry["EXPLICITLY_CITED"]]
            entry["ENGINE_TRIGGERED"] += [c for c in linked.get("ENGINE_TRIGGERED", []) if c not in entry["ENGINE_TRIGGERED"]]
        by_rule[cand_id] = entry
    # 结构化块引用的是候选 ID（QBT-甲-02），但有些命例引用的 ID 不在调候候选里（其他书规则）——保留原样
    for rid, linked in rule_to_cases.items():
        if rid not in by_rule:
            by_rule[rid] = linked

    (IDX / "byRule.json").write_text(json.dumps({
        "note": "Rule↔Case 双向索引；EXPLICITLY_CITED=原书命例块明确引用候选；ENGINE_TRIGGERED=Tianze 引擎触发（不冒充古人用了该规则）",
        "byRule": by_rule,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    (IDX / "byDayMaster.json").write_text(json.dumps(by_day, ensure_ascii=False, indent=1), encoding="utf-8")
    (IDX / "byMonthBranch.json").write_text(json.dumps(by_month, ensure_ascii=False, indent=1), encoding="utf-8")
    (IDX / "byBook.json").write_text(json.dumps(by_book, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"computed": computed, "casesWithExplicitRuleRefs":
                      sum(1 for rs in rule_to_cases.values() if rs["EXPLICITLY_CITED"]),
                      "engineTriggeredRules": len([r for r, v in rule_to_cases.items() if v["ENGINE_TRIGGERED"]])},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
