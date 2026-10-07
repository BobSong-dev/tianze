"""M8.0 · Case Regression Infrastructure：命例领域回归系统。

把 1147 个 CaseReference 中可运行引擎的命例升级为 Domain Regression Corpus：
- snapshot：对全部可解析命例运行引擎，产出稳定字段快照（regression/baseline/snapshot.json）；
- compare：重算并与 baseline 对比，输出 changedCases / severity（INFO/EXPECTED/REVIEW/BREAKING）；
- report：人类可读摘要。

原则：Regression 只回答"发生了什么变化"，不裁决新版本/旧版本谁对，不自动回滚。
统计口径（M8.0 修正）：caseCount（案例数）与 comparisonItemCount/agreementItemCount/
differenceItemCount（比较项数）严格分离——一项对比可能同时含一致与差异。
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

REPO = Path(__file__).resolve().parents[1]
CASES = REPO / "knowledge" / "normalized" / "cases"
REGRESSION = REPO / "regression"
BASELINE = REGRESSION / "baseline" / "snapshot.json"

import tianze
from tianze.knowledge.models import CASE_SCHEMA_VERSION, KNOWLEDGE_SCHEMA_VERSION
from tianze.ganzhi.tables import HIDDEN_STEMS, STEM_ELEMENT, ten_god
from tianze.analysis.month_command import compute_month_command
from tianze.analysis.roots import collect_roots


def compute_snapshots() -> list[dict]:
    """对全部可解析命例生成 CaseAnalysisSnapshot（稳定字段，非完整 JSON 复制）。"""
    from tools.derive_case_analysis import analyze_pillars  # 复用引擎派生

    snapshots = []
    for path in sorted(CASES.glob("*.json")):
        if any(x in path.name for x in ("temporal_refs", "event_claims", "raw_temporal_spans")):
            continue  # M13 TemporalCaseReference 工具产物，非命例书册
        data = json.loads(path.read_text(encoding="utf-8"))
        for case in data["cases"]:
            pillars = case["fact"]["pillars"]
            if not all(pillars.get(k) for k in ("year", "month", "day", "hour")):
                snapshots.append({
                    "caseId": case["caseId"], "unresolved": True,
                    "chartFingerprint": None,
                })
                continue
            derived = analyze_pillars(pillars)
            if not derived:
                snapshots.append({"caseId": case["caseId"], "unresolved": True,
                                  "chartFingerprint": None})
                continue
            # M10.0: compute M8 special/bingYao/tongGuan results
            from tianze.analysis.special import analyze_all_special
            from tianze.ganzhi.tables import Element as _E
            dm_stem = pillars["day"][:1]
            stems_list = [pillars.get(k, "")[:1] or None for k in ("year", "month", "day", "hour")]
            branches_list = [pillars.get(k, "")[1:2] or None for k in ("year", "month", "day", "hour")]
            ec = {}
            for e in _E:
                v = sum(1 for st in stems_list if st and STEM_ELEMENT.get(st) == e)
                h = sum(1 for b in branches_list if b and b in HIDDEN_STEMS
                        for h, _ in HIDDEN_STEMS[b] if STEM_ELEMENT.get(h) == e)
                ec[e.value.lower()] = {"visible": v, "hidden": h}
            mc = compute_month_command(branches_list[1], dm_stem, stems_list)
            roots = collect_roots(stems_list, branches_list, ["year", "month", "day", "hour"], dm_stem)
            dm_roots = sum(1 for r in roots if r.is_day_master)
            helpers = [st for st in stems_list if st and st != dm_stem and
                       ten_god(dm_stem, st).value in ("比肩", "劫财", "正印", "偏印")]
            verdicts = {"weighted": None, "fuyi": None, "dimension": None}  # 简化：M8 不依赖 verdicts
            special = analyze_all_special(dm_stem, branches_list[1], stems_list, branches_list,
                                          verdicts, None, dm_roots, helpers, ec)
            # Derive bingYao and tongGuan summaries
            by_summary = len(special.get("bingYao", {}).get("problems", []))
            tg_count = len(special.get("tongGuan", {}).get("conflictPairs", []))
            fingerprint = hashlib.sha256(
                "|".join(pillars[k] for k in ("year", "month", "day", "hour")).encode("utf-8")
            ).hexdigest()[:16]
            snapshots.append({
                "caseId": case["caseId"],
                "chartFingerprint": fingerprint,
                "unresolved": False,
                "strength": derived["strengthVerdicts"],       # {dimension/weighted/fuyi: verdict}
                "agreement": derived["agreement"],
                "patternCandidate": derived["patternCandidate"],
                "patternStatus": derived["patternStatus"],
                "tiaohouTargets": derived["tiaohouTargets"],
                "tiaohouPrimaryPresent": derived["tiaohouPrimaryPresent"],
                "triggeredRuleIds": sorted(derived["engineRuleIds"]),
                "specialPattern": {
                    "cong": [c["type"] + ":" + c["status"] for c in special["specialPattern"]["cong"]],
                    "zhuanwang": [z["type"] + ":" + z["status"] for z in special["specialPattern"]["zhuanwang"]],
                    "transformation": [t["stemPair"][0] + t["stemPair"][1] + ":" + t["status"] for t in special["specialPattern"]["transformation"]],
                },
                "bingYao": {"problemCount": by_summary, "medicineCount": len(special.get("bingYao", {}).get("medicines", []))},
                "tongGuan": {"pairCount": tg_count, "bridgePresent": sum(1 for b in special.get("tongGuan", {}).get("bridges", []) if b["present"])},
                "warnings": [],
            })
    return snapshots


def write_baseline(snapshots: list[dict]) -> dict:
    meta = {
        "schemaVersion": {"knowledge": KNOWLEDGE_SCHEMA_VERSION, "case": CASE_SCHEMA_VERSION},
        "engineVersion": tianze.__version__,
        "engineStage": tianze.ENGINE_STAGE,
        "generatedBy": "tools/case_regression.py snapshot",
        "count": len(snapshots),
    }
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE.write_text(json.dumps({"meta": meta, "snapshots": snapshots},
                                   ensure_ascii=False, indent=1), encoding="utf-8")
    return meta


def load_baseline() -> dict:
    return json.loads(BASELINE.read_text(encoding="utf-8"))


SEVERITY_ORDER = {"BREAKING": 0, "REVIEW": 1, "EXPECTED": 2, "INFO": 3}


def compare(baseline: dict, current: list[dict], expected_labels: set[str] | None = None) -> dict:
    """对比 baseline 与当前重算结果。expected_labels: 标记为 EXPECTED 的新能力名。"""
    expected_labels = expected_labels or set()
    base_by_id = {s["caseId"]: s for s in baseline["snapshots"]}
    cur_by_id = {s["caseId"]: s for s in current}
    changed: list[dict] = []
    new_cases = sorted(set(cur_by_id) - set(base_by_id))
    removed_cases = sorted(set(base_by_id) - set(cur_by_id))
    severity_counter: Counter = Counter()

    for cid in sorted(set(base_by_id) & set(cur_by_id)):
        b, c = base_by_id[cid], cur_by_id[cid]
        if b.get("unresolved") or c.get("unresolved"):
            continue
        fields: list[dict] = []
        # BREAKING：排盘（四柱指纹）
        if b.get("chartFingerprint") != c.get("chartFingerprint"):
            fields.append({"field": "chartFingerprint", "before": b.get("chartFingerprint"),
                           "after": c.get("chartFingerprint"), "severity": "BREAKING"})
        # REVIEW：既有结论变化
        for method in ("dimension", "weighted", "fuyi"):
            if (b.get("strength") or {}).get(method) != (c.get("strength") or {}).get(method):
                fields.append({"field": f"strength.{method}",
                               "before": (b.get("strength") or {}).get(method),
                               "after": (c.get("strength") or {}).get(method),
                               "severity": "REVIEW"})
        for f in ("patternCandidate", "patternStatus"):
            if b.get(f) != c.get(f):
                fields.append({"field": f, "before": b.get(f), "after": c.get(f),
                               "severity": "REVIEW"})
        bt, ct = set(b.get("tiaohouTargets") or []), set(c.get("tiaohouTargets") or [])
        if bt != ct:
            fields.append({"field": "tiaohouTargets", "before": sorted(bt), "after": sorted(ct),
                           "severity": "REVIEW"})
        bt, ct = set(b.get("triggeredRuleIds") or []), set(c.get("triggeredRuleIds") or [])
        if bt != ct:
            fields.append({"field": "triggeredRuleIds",
                           "new": sorted(ct - bt), "removed": sorted(bt - ct),
                           "severity": "REVIEW"})
        # EXPECTED：新 M8 模块首次产生结果
        for f in ("specialPattern", "bingYao", "tongGuan"):
            if not b.get(f) and c.get(f):
                label = next((l for l in expected_labels if l in f), None)
                fields.append({"field": f, "before": None, "after": c.get(f),
                               "severity": "EXPECTED",
                               "reason": f"新模块 {label or f} 首次产生结果" if label else None})
        # INFO：其他新增字段
        for f in ("agreement", "tiaohouPrimaryPresent"):
            if b.get(f) != c.get(f):
                fields.append({"field": f, "before": b.get(f), "after": c.get(f),
                               "severity": "INFO"})
        if fields:
            worst = min((f["severity"] for f in fields), key=lambda s: SEVERITY_ORDER[s])
            severity_counter[worst] += 1
            changed.append({"caseId": cid, "severity": worst, "changes": fields})

    changed.sort(key=lambda x: (SEVERITY_ORDER[x["severity"]], x["caseId"]))
    return {
        "meta": {"baseline": baseline["meta"],
                 "current": {"engineVersion": tianze.__version__,
                             "engineStage": tianze.ENGINE_STAGE,
                             "knowledge": KNOWLEDGE_SCHEMA_VERSION, "case": CASE_SCHEMA_VERSION}},
        "caseCount": {"baseline": len(base_by_id), "current": len(cur_by_id)},
        "newCases": new_cases, "removedCases": removed_cases,
        "changedCases": changed,
        "severityCounts": dict(severity_counter),
    }


def write_report(result: dict) -> Path:
    lines = [
        "# Case Regression Report",
        "",
        f"- baseline: engine {result['meta']['baseline']['engineVersion']}"
        f" ({result['meta']['baseline']['engineStage']})",
        f"- current: engine {result['meta']['current']['engineVersion']}"
        f" ({result['meta']['current']['engineStage']})",
        f"- caseCount: baseline {result['caseCount']['baseline']} / current {result['caseCount']['current']}"
        "（caseCount=案例数；比较项数见 changedCases 内 changes[]，两口径分离）",
        f"- severity: {result['severityCounts']}",
        f"- newCases {len(result['newCases'])} / removedCases {len(result['removedCases'])}",
        "",
        "## REVIEW / BREAKING 明细（仅此类需关注；EXPECTED 为新模块首次产出）",
        "",
    ]
    for c in result["changedCases"]:
        if c["severity"] in ("REVIEW", "BREAKING"):
            for f in c["changes"]:
                lines.append(f"- [{c['severity']}] {c['caseId']} · {f['field']}: "
                             f"{f.get('before')} → {f.get('after')}")
    out = REGRESSION / "report.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    md = REGRESSION / "report.md"
    md.write_text("\n".join(lines), encoding="utf-8")
    return out


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "snapshot"
    if cmd == "snapshot":
        snapshots = compute_snapshots()
        meta = write_baseline(snapshots)
        print(f"baseline written: {meta['count']} cases (engine {meta['engineVersion']}/{meta['engineStage']})")
        return 0
    if cmd == "compare":
        current = compute_snapshots()
        result = compare(load_baseline(), current)
        write_report(result)
        print(json.dumps({"severityCounts": result["severityCounts"],
                          "changedCases": len(result["changedCases"]),
                          "caseCount": result["caseCount"]}, ensure_ascii=False, indent=1))
        return 0
    if cmd == "report":
        print((REGRESSION / "report.md").read_text(encoding="utf-8"))
        return 0
    print("usage: python tools/case_regression.py snapshot|compare|report")
    return 1


if __name__ == "__main__":
    sys.exit(main())
