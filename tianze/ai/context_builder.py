"""M11.1 · InterpretationContext builder: 从 SDK AnalyzeResult 提取解释所需最小上下文。

保留事实/方法结论/候选的层次区分（FactType）。
只提取当前命盘实际触发的 Evidence/Rule/Source，不注入整个知识库。
"""

from __future__ import annotations

from typing import Any

from tianze.ai.models import (
    ContextFact,
    ContextMethodResult,
    ContextSource,
    FactType,
    InterpretationContext,
)


def build_interpretation_context(
    result: dict[str, Any],
    engine_version: str = "",
    knowledge_version: str = "",
    analysis_schema_version: str = "",
) -> InterpretationContext:
    ctx = InterpretationContext(
        meta={
            "engineVersion": engine_version,
            "knowledgeSchemaVersion": knowledge_version,
            "analysisSchemaVersion": analysis_schema_version,
        },
    )

    # ---- Chart facts ----
    dm = result.get("dayMaster") or {}
    if dm:
        ctx.chart_facts.append(ContextFact(
            category="dayMaster", fact_type=FactType.FACT,
            statement=f"日主{dm['stem']}（{dm.get('element', '')}·{dm.get('yinYang', '')}）",
            key="dayMaster",
        ))
    for pos in ("year", "month", "day", "hour"):
        p = (result.get("pillars") or {}).get(pos)
        if not p:
            continue
        gz = p["stem"] + p["branch"]
        ten_god = p.get("tenGod") or "日主"
        ctx.chart_facts.append(ContextFact(
            category="pillars", fact_type=FactType.FACT,
            statement=f"{pos}柱 {gz}（{ten_god}）",
            key=f"pillar_{pos}", data={"stem": p["stem"], "branch": p["branch"], "tenGod": ten_god},
        ))

    # ---- Relations ----
    for r in result.get("relations") or []:
        ctx.relations.append(ContextFact(
            category="relations", fact_type=FactType.DERIVED_FACT,
            statement=f"{r['label']}（{'/'.join(r.get('positions', []))}）",
            key=f"rel_{r['kind']}_{r['label']}",
            data={"members": r.get("members", []), "positions": r.get("positions", []),
                  "transformCandidate": r.get("transformCandidate"), "note": r.get("note")},
        ))

    # ---- Structure: roots + visibility + month command ----
    for r in result.get("roots") or []:
        ctx.structure.append(ContextFact(
            category="roots", fact_type=FactType.DERIVED_FACT,
            statement=r.get("statement", ""), key=f"root_{r.get('stem', '')}_{r.get('branch', '')}_{r.get('position', '')}",
        ))
    for v in result.get("visibility") or []:
        ctx.structure.append(ContextFact(
            category="visibility", fact_type=FactType.DERIVED_FACT,
            statement=v.get("statement", ""), key=f"vis_{v.get('hiddenStem', '')}_{v.get('position', '')}",
        ))
    mc = result.get("monthCommand")
    if mc:
        rel = mc.get("relationToDayMaster") or {}
        ctx.structure.append(ContextFact(
            category="monthCommand", fact_type=FactType.DERIVED_FACT,
            statement=f"月令{mc.get('monthBranch', '')}：日主处【{rel.get('state', '')}】"
                      f"{'（得令）' if rel.get('inCommand') else ''}",
            key="month_command",
        ))

    # ---- Strength ----
    sr = result.get("strength") or {}
    ctx.strength_agreement = sr.get("agreement")
    for m in sr.get("methods") or []:
        ctx.strength_methods.append(ContextMethodResult(
            analyzer_id=m.get("analyzerId", ""), method=m.get("name", ""),
            verdict=m.get("verdict"), score=m.get("score"),
            confidence=m.get("confidence"),
            evidence=[e for e in (m.get("evidence") or []) if isinstance(e, str)],
            note=m.get("note"),
        ))
    if ctx.strength_agreement and ctx.strength_agreement in ("PARTIAL", "DISPUTED"):
        ctx.disagreements.append(
            f"旺衰分析多方法分歧（agreement={ctx.strength_agreement}）——Tianze 不强制裁决"
        )

    # ---- Pattern ----
    pa = result.get("pattern")
    if pa:
        for c in pa.get("candidates") or []:
            ctx.pattern_candidates.append({
                "name": c.get("name"), "via": c.get("via"), "tenGod": c.get("tenGod"),
                "monthBranch": c.get("monthBranch"),
            })
        ev = pa.get("evaluation")
        if ev:
            ctx.pattern_evaluation = {
                "status": ev.get("status"),
                "supportsCount": len(ev.get("supports") or []),
                "damagesCount": len(ev.get("damages") or []),
                "rescuesCount": len(ev.get("rescues") or []),
                "conflictsCount": len(ev.get("conflicts") or []),
                "note": ev.get("note"),
            }

    # ---- TiaoHou ----
    th = result.get("tiaohou")
    if th and th.get("resolved"):
        recs = [
            {"stem": r.get("targetStem"), "priority": r.get("priority"),
             "present": r.get("present"), "ruleIds": r.get("ruleIds", []),
             "quote": r.get("quote"), "source": r.get("source")}
            for r in th.get("recommendations") or []
        ]
        ctx.tiaohou = {"dayMaster": th.get("dayMaster"), "monthBranch": th.get("monthBranch"),
                       "recommendations": recs, "conflicts": th.get("conflicts", [])}
        # Populate sources from tiaohou
        for r in th.get("recommendations") or []:
            src = r.get("source")
            if src:
                sid = f"src_{r.get('targetStem', '')}_{th.get('monthBranch', '')}"
                if not any(s.source_id == sid for s in ctx.sources):
                    ctx.sources.append(ContextSource(
                        source_id=sid, book=src.get("book", ""),
                        chapter=src.get("chapter"), pages=src.get("pages", []),
                        quote=r.get("quote"), source_kind=src.get("sourceKind", "CLASSICAL_TEXT"),
                        verification_status="MACHINE_CURATED",
                        quality=r.get("quality"),
                        commentator=src.get("commentator"),
                    ))

    # ---- Advanced (M8) ----
    adv = result.get("advancedAnalysis")
    if adv:
        sp = adv.get("specialPattern") or {}
        ctx.advanced = {
            "cong": sp.get("cong", []),
            "zhuanwang": sp.get("zhuanwang", []),
            "transformation": sp.get("transformation", []),
            "bingYao": adv.get("bingYao", {}),
            "tongGuan": adv.get("tongGuan", {}),
        }
        # UNRESOLVED items
        for c in sp.get("cong") or []:
            if c.get("status") == "UNRESOLVED":
                ctx.unresolved.append(f"从格 {c.get('type', '')} 证据不足")
        for t in sp.get("transformation") or []:
            if t.get("status") == "UNRESOLVED":
                ctx.unresolved.append(f"化气 {t.get('stemPair', '')} 证据不足")

    # ---- Warnings / fallbacks ----
    ctx.warnings = list(result.get("warnings") or [])
    ctx.unresolved.extend(result.get("fallbacks") or [])

    # ---- All rule IDs ----
    for r in result.get("roots") or []:
        if r.get("statement"):
            ctx.all_rule_ids.append(r["statement"])
    for rec in (th or {}).get("recommendations") or []:
        ctx.all_rule_ids.extend(rec.get("ruleIds") or [])

    return ctx
