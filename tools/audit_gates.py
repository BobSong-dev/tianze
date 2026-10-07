"""M17 · Coverage Gates：统一推理质量审计（长期质量门）。

门（全部确定性检查；FAIL → 退出码 1）：
  G1  所有 ExecutableRule 必须有 candidateId（TIANZE-ENGINEERING-* 除外，需 heuristic 佐证）
  G2  CLASSICAL_EXPLICIT 规则必须有 Source（book）
  G3  rescue 边必须指向真实规则；谓词必须已注册
  G4  Conflict Graph 无非法边/自环/未知引用
  G5  规则 JSON ↔ evaluator 一一对应（event/temporal/special）
  G6  从未触发规则清单（对照 evaluation/replay 工件，进审计列表不判死刑）
  G7  异常高触发率 → REVIEW（规则 >60% / 主题 >70%）
  G8  ExplanationChain 无断链（每条 hit 的 ruleId 在图中；quote 必有 source）
  G9  Event Theme 工件无 CONFIRMED
  G10 无机器产生的 HUMAN_* 状态

输出：regression/audit-gates.json
"""

from __future__ import annotations

import glob
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AUDIT_SCHEMA_VERSION = "1.0.0"


def _load(path, default):
    if not os.path.exists(path):
        return default
    return json.load(open(path, encoding="utf-8"))


def main() -> int:
    gates: dict[str, dict] = {}

    # 收集规则
    all_rules: list[dict] = []
    for f in sorted(glob.glob("knowledge/rules/*/rules.json")):
        payload = _load(f, {"rules": []})
        for r in payload.get("rules", []):
            all_rules.append({**r, "_file": f})
    candidate_ids = set()
    for f in sorted(glob.glob("knowledge/normalized/*/rules.json")):
        data = _load(f, [])
        items = data if isinstance(data, list) else (data.get("candidates") or data.get("rules") or [])
        candidate_ids.update(it.get("id") for it in items)

    # G1 candidateId
    bad = [r["id"] for r in all_rules
           if r["candidateId"] not in candidate_ids
           and not (str(r["candidateId"]).startswith("TIANZE-ENGINEERING-")
                    and any(p.get("level") == "ENGINEERING_HEURISTIC" for p in r.get("provenance", [])))]
    gates["G1_candidate_refs"] = {"pass": not bad, "violations": bad}

    # G2 CLASSICAL 必有 Source
    bad = [r["id"] for r in all_rules
           if any(p.get("level") == "CLASSICAL_EXPLICIT" for p in r.get("provenance", []))
           and not (r.get("source") or {}).get("book")]
    gates["G2_classical_source"] = {"pass": not bad, "violations": bad}

    # G3 rescue 边
    rescues = _load("knowledge/rules/event/rescues.json", {"rescues": []})["rescues"]
    rule_ids = {r["id"] for r in all_rules}
    from tianze.analysis.rescues import RESCUE_PREDICATES
    bad = [d["id"] for d in rescues
           if d.get("target") not in rule_ids or d.get("predicate") not in RESCUE_PREDICATES]
    gates["G3_rescue_edges"] = {"pass": not bad, "violations": bad}

    # G4 graph
    graph = _load("knowledge/rules/event/conflict-graph.json", {"problems": ["missing"]})
    gates["G4_graph_integrity"] = {"pass": not graph.get("problems"),
                                   "violations": graph.get("problems", [])}

    # G5 evaluator 对应
    from tianze.knowledge.event_rules import load_event_rules
    from tianze.knowledge.temporal_rules import load_temporal_rules
    from tianze.analysis import event_themes, special_temporal
    violations = []
    for r in load_event_rules():
        if r["id"] not in event_themes.EVALUATORS:
            violations.append(r["id"])
    temporal_rules = load_temporal_rules()
    generic = [r for r in temporal_rules if r.get("category") != "special-pattern"]
    special = [r for r in temporal_rules if r.get("category") == "special-pattern"]
    for r in generic:
        if r["id"] not in __import__("tianze.knowledge.temporal_rules", fromlist=["x"])._EVALUATORS:
            violations.append(r["id"])
    for r in special:
        if r["id"] not in special_temporal._SPECIAL_EVALUATORS:
            violations.append(r["id"])
    gates["G5_evaluator_mapping"] = {"pass": not violations, "violations": violations}

    # G6/G7 触发率（工件）
    evaluation = _load("regression/event-evaluation.json", {})
    rates = evaluation.get("randomAudit", {}).get("ruleTriggerRate", {})
    never = sorted(r["id"] for r in all_rules if r["domain"] == "event"
                   and rates.get(r["id"], 0) == 0)
    gates["G6_never_triggered"] = {"pass": True, "list": never,
                                   "note": "进审计列表（可能只是探针未覆盖，不判死刑）"}
    abnormal_rules = evaluation.get("randomAudit", {}).get("abnormalTriggerRate", {}).get("rules", {})
    abnormal_themes = evaluation.get("randomAudit", {}).get("abnormalTriggerRate", {}).get("themes", {})
    gates["G7_abnormal_trigger"] = {"pass": not abnormal_rules and not abnormal_themes,
                                    "rules": abnormal_rules, "themes": abnormal_themes}

    # G8 ExplanationChain 无断链
    chain_violations = []
    from tianze.analysis.explain import _rule_meta
    meta = _rule_meta()
    graph_nodes = {n["id"] for n in graph.get("nodes", [])}
    for r in load_event_rules():
        rid = r["id"]
        if rid not in meta:
            chain_violations.append(f"{rid}: 规则元数据缺失")
            continue
        for p in r.get("provenance", []):
            if p.get("level") == "CLASSICAL_EXPLICIT" and p.get("note") \
                    and not (r.get("source") or {}).get("book"):
                chain_violations.append(f"{rid}: 有 Quote 无 Source（断链）")
        if rid not in graph_nodes:
            chain_violations.append(f"{rid}: 不在 conflict graph（断链）")
    gates["G8_explanation_chain"] = {"pass": not chain_violations, "violations": chain_violations}

    # G9 无 CONFIRMED
    violations = []
    for f in ("regression/case-replay.json", "regression/event-evaluation.json"):
        if os.path.exists(f):
            blob = open(f, encoding="utf-8").read()
            if '"CONFIRMED"' in blob or 'CONFIRMED"' in blob:
                violations.append(f)
    gates["G9_no_confirmed"] = {"pass": not violations, "violations": violations}

    # G10 无机器 HUMAN
    violations = [r["id"] for r in all_rules
                  if str(r.get("verification", {}).get("status", "")).startswith("HUMAN")]
    gates["G10_no_machine_human"] = {"pass": not violations, "violations": violations}

    # Coverage 统计（workbench 数据源）
    used_candidates = Counter(r["candidateId"] for r in all_rules
                              if not str(r["candidateId"]).startswith("TIANZE-ENGINEERING-"))
    unused_candidates = sorted(candidate_ids - set(used_candidates))
    replay = _load("regression/case-replay.json", {"replays": []})
    rule_case_coverage: Counter = Counter()
    for rp in replay.get("replays", []):
        for t in rp.get("tianzeThemes", []):
            for rid in t.get("rules", []):
                rule_case_coverage[rid] += 1
    coverage = {
        "candidatesTotal": len(candidate_ids),
        "candidatesUsedAsRules": len(set(used_candidates)),
        "candidatesUnused": len(unused_candidates),
        "unusedCandidateIds": unused_candidates[:80],
        "ruleCaseCoverage": dict(sorted(rule_case_coverage.items())),
        "eventRulesNeverInReplay": sorted(
            r["id"] for r in all_rules if r["domain"] == "event"
            and rule_case_coverage.get(r["id"], 0) == 0),
    }

    all_pass = all(g["pass"] for g in gates.values())
    payload = {
        "schemaVersion": AUDIT_SCHEMA_VERSION,
        "allPass": all_pass,
        "gates": gates,
        "coverage": coverage,
    }
    with open("regression/audit-gates.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    for name, g in gates.items():
        print(f"  {'PASS' if g['pass'] else 'FAIL'} {name}"
              + (f"（{len(g.get('violations', []))} 违规）" if g.get("violations") else ""))
    print(f"Audit Gates：{'ALL PASS' if all_pass else 'FAILURES'} → regression/audit-gates.json")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
