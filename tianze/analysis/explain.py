"""M16 · 推理可解释性：EventThemeCandidate → 完整解释链。

回答「Tianze 为什么这么判断」：

    Event Theme
    → Reasoning Result（status/agreement/confidence 及其公式依据）
    → Rule Hit（applicability / rescue / conflict 邻接）
    → Temporal Evidence（岁运干支层引用）
    → Engine Fact（十神表/旺衰判定/结构检测——复用口径说明）
    → Quote（CLASSICAL_EXPLICIT 原文注记，仅知识层引用）
    → Source（book/chapter/sourceFile）

反对链（opposing chain）同时给出；冲突不裁决，只解释。
"""

from __future__ import annotations

from typing import Any

from tianze.analysis.event_themes import EventThemeCandidate
from tianze.analysis.rule_conflicts import explain_rule
from tianze.knowledge.event_rules import load_event_rules

__all__ = ["build_explanation_chain", "build_explanation_chains"]


def _rule_meta() -> dict[str, dict]:
    return {r["id"]: r for r in load_event_rules()}


def _source_of(rule: dict) -> dict | None:
    src = rule.get("source") or {}
    if not src:
        return None
    return {
        "book": src.get("book"),
        "chapter": src.get("chapter"),
        "sourceFile": src.get("sourceFile"),
        "sourceKind": src.get("sourceKind"),
        "confidence": src.get("confidence"),
    }


def _quote_of(rule: dict) -> str | None:
    """CLASSICAL_EXPLICIT provenance 的原文注记（知识层引用）。"""
    for p in rule.get("provenance", []):
        if p.get("level") == "CLASSICAL_EXPLICIT" and p.get("note"):
            return p["note"]
    return None


def _hit_chain(hit, rule: dict, rescue_state: dict | None) -> dict:
    """单条 Rule Hit 的解释子链。"""
    graph = None
    try:
        graph = explain_rule(hit.ruleId)
    except KeyError:
        graph = {"related": [], "note": "不在 conflict graph（非 event 域规则）"}
    applicable_rescues = [e for e in graph.get("related", []) if e["edgeType"] == "rescues"]
    chain = {
        "ruleId": hit.ruleId,
        "label": hit.label,
        "view": hit.view.value if hasattr(hit.view, "value") else hit.view,
        "direction": hit.direction.value if hasattr(hit.direction, "value") else hit.direction,
        "evidence": list(hit.evidence),                      # Temporal Evidence（岁运层引用）
        "engineFacts": _engine_facts(hit),
        "quote": _quote_of(rule),                            # Quote（知识层原文注记）
        "source": _source_of(rule),                          # Source
        "provenanceLevels": hit.provenanceLevels,
        "rescueApplied": hit.rescueApplied,                  # 救应（applicability 修正）
        "mayChangeResultConditions": [
            e for e in graph.get("related", []) if e.get("mayChangeResult")
        ],
        "conflictNeighbors": [
            {"edgeType": e["edgeType"], "related": e["related"],
             "resolution": e.get("resolution"), "note": e.get("note", "")}
            for e in graph.get("related", []) if e["edgeType"] in ("conflict", "school-conflict")
        ],
    }
    return chain


def _engine_facts(hit) -> list[str]:
    """底层 Engine 事实口径说明（复用声明，非重算）。"""
    facts = ["十神判定：tianze.ganzhi.tables.ten_god（R 体系推导表）"]
    if hit.rescueApplied and "旺衰" in str(hit.rescueApplied.get("evidence", [])):
        facts.append("旺衰判定：weighted analyzer（R20，参数随结果输出）")
    if any("驿马" in e or "咸池" in e for e in hit.evidence):
        facts.append("神煞起例：三合马位/沐浴位（SS-R22 去取原则约束）")
    if any("三刑" in e or "冲" in e for e in hit.evidence):
        facts.append("刑冲：六冲/三刑表（R9 命名口径）")
    return facts


def build_explanation_chain(candidate: EventThemeCandidate,
                            rescue_state: dict | None = None) -> dict:
    """单个事件主题候选 → 完整解释链（含反对链与冲突解释）。"""
    meta = _rule_meta()
    supporting = []
    opposing = []
    for h in candidate.triggeredRules:
        rule = meta.get(h.ruleId, {})
        chain = _hit_chain(h, rule, rescue_state)
        d = h.direction.value if hasattr(h.direction, "value") else h.direction
        (supporting if d == "support" else opposing).append(chain)

    return {
        "theme": candidate.theme.value,
        "themeCn": candidate.themeCn,
        "status": candidate.status.value,
        "agreement": candidate.agreement,
        "confidence": candidate.confidence,
        "confidenceBasis": candidate.confidenceBasis,
        "reasoning": {
            "supportingChain": supporting,
            "opposingChain": opposing,
            "conflictExplanations": [
                c.model_dump(by_alias=True, exclude_none=True)
                if hasattr(c, "model_dump") else c
                for c in candidate.conflictExplanations
            ],
            "verdictStatement": (
                f"主题 {candidate.themeCn} 判定为 {candidate.status.value}"
                + (f"（agreement={candidate.agreement}）" if candidate.agreement else "")
                + "：以上链路为全部依据；冲突保留双方，不裁决。"),
        },
        "warnings": list(candidate.warnings),
        "refId": candidate.refId,
    }


def build_explanation_chains(event_report, rescue_state: dict | None = None) -> dict[str, dict]:
    """整份 EventThemeReport → {theme: chain}。"""
    return {t.theme.value: build_explanation_chain(t, rescue_state)
            for t in event_report.themes}
