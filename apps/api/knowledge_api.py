"""M16 · Knowledge Rule Explorer / Review Queue API。

只读数据源（前端不复制任何推理逻辑）：
- GET /api/v1/knowledge/rules        全部 ExecutableRule（provenance/verification/冲突邻接）
- GET /api/v1/knowledge/graph        Conflict Graph（节点+边）
- GET /api/v1/knowledge/conflicts    冲突声明
- GET /api/v1/knowledge/rescues      救应声明
- GET /api/v1/knowledge/review-queue Review Queue（优先级/原因/关联，只读）
- GET /api/v1/knowledge/stats        覆盖统计

优先级（透明 heuristic，仅供排序）：OCR 风险 P1 > 敏感 claim P2 >
MACHINE_CURATED P3 > conflict P2；无自动升级 HUMAN_VERIFIED。
"""

from __future__ import annotations

import glob
import json
import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])

_REVIEW_QUEUE_PATH = "review/review-queue.json"
RELEASE_DIR = "release"


def _load(path: str, default):
    if not os.path.exists(path):
        return default
    return json.load(open(path, encoding="utf-8"))


def _all_rules() -> list[dict]:
    rules = []
    for f in sorted(glob.glob("knowledge/rules/*/rules.json")):
        payload = _load(f, {"rules": []})
        for r in payload.get("rules", []):
            rules.append({
                "id": r["id"],
                "domain": r.get("domain"),
                "theme": r.get("theme"),
                "category": r.get("category"),
                "view": r.get("view"),
                "label": r.get("label", r["id"]),
                "candidateId": r.get("candidateId"),
                "provenanceLevels": sorted({p.get("level") for p in r.get("provenance", [])}),
                "source": r.get("source"),
                "quality": r.get("quality"),
                "verification": r.get("verification"),
                "conflictNote": r.get("conflictNote"),
                "accuracyMatrix": r.get("accuracyMatrix"),
            })
    return rules


def _priority(item: dict) -> str:
    """Review 优先级（排序用 heuristic，透明；不改变任何 verification 状态）。"""
    if item.get("kind") == "ocrRisk":
        return "P1"
    if item.get("kind") in ("sensitiveClaim", "ruleConflict"):
        return "P2"
    return "P3"


@router.get("/rules")
async def rules() -> JSONResponse:
    graph = _load("knowledge/rules/event/conflict-graph.json", {"edges": []})
    adjacency: dict[str, list[dict]] = {}
    for e in graph.get("edges", []):
        ids = e.get("between") or [x for x in (e.get("from"), e.get("to")) if x]
        for x in ids:
            others = [y for y in ids if y != x]
            adjacency.setdefault(x, []).append({
                "edgeType": e["type"], "related": others,
                "resolution": e.get("resolution"),
                "effect": e.get("effect"),
                "specificCondition": e.get("specificCondition"),
            })
    out = []
    for r in _all_rules():
        r["conflictNeighbors"] = adjacency.get(r["id"], [])
        out.append(r)
    return JSONResponse({"count": len(out), "rules": out})


@router.get("/graph")
async def graph() -> JSONResponse:
    return JSONResponse(_load("knowledge/rules/event/conflict-graph.json",
                              {"nodes": [], "edges": []}))


@router.get("/conflicts")
async def conflicts() -> JSONResponse:
    data = _load("knowledge/rules/event/conflicts.json", {"conflicts": []})
    return JSONResponse(data)


@router.get("/rescues")
async def rescues() -> JSONResponse:
    data = _load("knowledge/rules/event/rescues.json", {"rescues": []})
    return JSONResponse(data)


@router.get("/review-queue")
async def review_queue() -> JSONResponse:
    """Review Queue（只读）：priority/reason/关联；不产生任何人工状态。"""
    q = _load(_REVIEW_QUEUE_PATH, None)
    if q is None:
        return JSONResponse({"error": {"code": "REVIEW_QUEUE_NOT_BUILT",
                                       "message": "先运行 tools/review_queue.py",
                                       "details": {}}}, status_code=404)
    flat: list[dict] = []
    for section, items in q.get("queue", {}).items():
        for it in items:
            entry = {"section": section, **it}
            entry["kind"] = section
            entry["priority"] = _priority(entry)
            entry["reviewNote"] = None   # 未来人工审核填写位；系统不伪造
            flat.append(entry)
    order = {"P1": 0, "P2": 1, "P3": 2}
    flat.sort(key=lambda x: (order.get(x["priority"], 9), str(x.get("id") or x.get("caseId") or "")))
    return JSONResponse({"stats": q.get("stats"), "discipline": q.get("discipline"),
                         "count": len(flat), "items": flat})


@router.get("/stats")
async def stats() -> JSONResponse:
    rules = _all_rules()
    from collections import Counter
    by_domain = Counter(r["domain"] for r in rules)
    by_quality = Counter(r.get("quality") for r in rules)
    prov = Counter()
    for r in rules:
        for lv in r["provenanceLevels"]:
            prov[lv] += 1
    from tianze import __version__
    from tianze.knowledge.models import KNOWLEDGE_SCHEMA_VERSION, CASE_SCHEMA_VERSION
    from tianze.ai.models import INTERPRETATION_SCHEMA_VERSION, PROMPT_VERSION
    from tianze.analysis.temporal_delta import DELTA_SCHEMA_VERSION
    from tianze.analysis.event_themes import EVENT_THEME_SCHEMA_VERSION
    return JSONResponse({
        "executableTotal": len(rules),
        "executableByDomain": dict(by_domain),
        "qualityDistribution": {k: v for k, v in by_quality.items() if k},
        "provenanceDistribution": dict(prov),
        "versionDependencies": {
            "knowledge": KNOWLEDGE_SCHEMA_VERSION,
            "case": CASE_SCHEMA_VERSION,
            "analysis": "1.0.0",
            "delta": DELTA_SCHEMA_VERSION,
            "event": EVENT_THEME_SCHEMA_VERSION,
            "interpretation": INTERPRETATION_SCHEMA_VERSION,
            "prompt": PROMPT_VERSION,
            "engine": __version__,
        },
        "note": "candidates 总数（556）与 executable 总数（216）是不同口径，勿混用",
    })


@router.get("/evaluation-history")
async def evaluation_history() -> JSONResponse:
    """AI Evaluation History（只读；确定性指标，无 LLM-as-judge 评分）。"""
    path = "regression/ai-evaluation-history.jsonl"
    if not os.path.exists(path):
        return JSONResponse({"count": 0, "entries": [],
                             "note": "尚无评估记录（真实 provider 运行后写入）"})
    entries = [json.loads(line) for line in
               open(path, encoding="utf-8").read().strip().split(chr(10)) if line]
    return JSONResponse({"count": len(entries), "entries": entries})


@router.get("/coverage")
async def coverage() -> JSONResponse:
    """Coverage Workbench 数据：审计门 + 覆盖统计（未用候选/未触发规则/Rule→Case）。"""
    audit = _load("regression/audit-gates.json", None)
    if audit is None:
        return JSONResponse({"error": {"code": "AUDIT_NOT_BUILT",
                                       "message": "先运行 tools/audit_gates.py",
                                       "details": {}}}, status_code=404)
    return JSONResponse({"allPass": audit.get("allPass"),
                         "gates": audit.get("gates", {}),
                         "coverage": audit.get("coverage", {})})


@router.get("/funnel")
async def funnel() -> JSONResponse:
    """Knowledge 漏斗与密度（Quality Dashboard 数据源）。"""
    audit = _load("regression/audit-gates.json", {"coverage": {}})
    cov = audit.get("coverage", {})
    rules = _all_rules()
    graph = _load("knowledge/rules/event/conflict-graph.json", {"nodeCount": 0, "edgeCount": 0})
    candidates = cov.get("candidatesTotal", 556)
    from collections import Counter
    domains = Counter(r["domain"] for r in rules)
    return JSONResponse({
        "funnel": {
            "sources": 8,               # knowledge/normalized 书册数（固定盘）
            "candidates": candidates,
            "executable": len(rules),
        },
        "candidatesUnused": cov.get("candidatesUnused", 0),
        "neverTriggered": len(audit.get("gates", {}).get("G6_never_triggered", {}).get("list", [])),
        "conflictDensity": round(graph.get("edgeCount", 0) / max(1, graph.get("nodeCount", 1)), 3),
        "domainCoverage": dict(domains),
        "ruleCaseCoverage": cov.get("ruleCaseCoverage", {}),
    })


@router.get("/coverage-audit")
async def coverage_audit() -> JSONResponse:
    """Rule Coverage / Dead Rule 分类（REVIEW 清单，不自动调整）。"""
    d = _load("regression/rule-coverage-audit.json", None)
    if d is None:
        return JSONResponse({"error": {"code": "NOT_BUILT",
                                       "message": "先运行 tools/rule_coverage_audit.py",
                                       "details": {}}}, status_code=404)
    return JSONResponse(d)


@router.get("/rule-audit")
async def rule_audit() -> JSONResponse:
    """逐规则 replay 样本与 relation 分布。"""
    d = _load("regression/rule-audit.json", None)
    if d is None:
        return JSONResponse({"error": {"code": "NOT_BUILT",
                                       "message": "先运行 tools/rule_audit.py",
                                       "details": {}}}, status_code=404)
    return JSONResponse(d)


def _stale_flags() -> dict:
    """陈旧工件检测：工件记录的 gitCommit/引擎版本 vs 当前（M19 治理）。"""
    import subprocess
    meta = _load("release/release-metadata.json", None)
    if not meta:
        return {"stale": False, "reason": "无 metadata"}
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))
                                                   + "/..") or ".").stdout.strip()
    except Exception:
        head = ""
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                                text=True, encoding="utf-8", errors="replace",
                                cwd=".").stdout.strip()) if head else False
    stale_commit = bool(head) and meta.get("release", {}).get("gitCommit") != head
    return {
        "stale": stale_commit or dirty,
        "reasons": (["metadata gitCommit != HEAD"] if stale_commit else [])
                   + (["工作区有未提交改动"] if dirty else []),
        "artifactCommit": meta.get("release", {}).get("gitCommit"),
    }


@router.get("/release")
async def release_metadata() -> JSONResponse:
    """Release Metadata + quality summary（真实运行产物 + 陈旧检测）。"""
    return JSONResponse({
        "stale": _stale_flags(),
        "metadata": _load("release/release-metadata.json", None),
        "qualitySummary": _load("release/quality-summary.json", None),
        "releaseNotes": (open(os.path.join(RELEASE_DIR, "RELEASE_NOTES.md"),
                              encoding="utf-8").read()
                         if os.path.exists(os.path.join(RELEASE_DIR, "RELEASE_NOTES.md"))
                         else None),
    })


@router.get("/evaluation-compare")
async def evaluation_compare() -> JSONResponse:
    """AI Evaluation History 对比（确定性指标回归检测）。"""
    d = _load("regression/ai-eval-compare.json", None)
    if d is None:
        return JSONResponse({"error": {"code": "NOT_BUILT",
                                       "message": "先运行 tools/ai_eval_compare.py",
                                       "details": {}}}, status_code=404)
    return JSONResponse(d)
