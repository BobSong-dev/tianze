"""M11.1+M11.3 · InterpretationContext builder + claim_refs + prompt data isolation.

claim_refs 由 ContextBuilder deterministic 生成，模型只能引用提供的 refId。
Prompt 严格隔离 INSTRUCTIONS 与 UNTRUSTED REFERENCE DATA。
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
    claim_refs: list[str] = []

    # ---- Chart facts ----
    dm = result.get("dayMaster") or {}
    if dm:
        ctx.chart_facts.append(ContextFact(
            category="dayMaster", fact_type=FactType.FACT,
            statement=f"日主{dm['stem']}（{dm.get('element', '')}·{dm.get('yinYang', '')}）",
            key="dayMaster",
        ))
        claim_refs.append(f"fact:dayMaster")
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
        claim_refs.append(f"fact:pillar:{pos}")

    # ---- Relations ----
    for r in result.get("relations") or []:
        ctx.relations.append(ContextFact(
            category="relations", fact_type=FactType.DERIVED_FACT,
            statement=f"{r['label']}（{'/'.join(r.get('positions', []))}）",
            key=f"rel_{r['kind']}_{r['label']}",
            data={"members": r.get("members", []), "positions": r.get("positions", []),
                  "transformCandidate": r.get("transformCandidate"), "note": r.get("note")},
        ))
        claim_refs.append(f"relation:{r['kind']}:{r['label']}")

    # ---- Structure: roots + visibility + month command ----
    for r in result.get("roots") or []:
        ctx.structure.append(ContextFact(
            category="roots", fact_type=FactType.DERIVED_FACT,
            statement=r.get("statement", ""),
            key=f"root_{r.get('stem', '')}_{r.get('branch', '')}_{r.get('position', '')}",
        ))
    for v in result.get("visibility") or []:
        ctx.structure.append(ContextFact(
            category="visibility", fact_type=FactType.DERIVED_FACT,
            statement=v.get("statement", ""),
            key=f"vis_{v.get('hiddenStem', '')}_{v.get('position', '')}",
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
        claim_refs.append(f"monthCommand:{mc.get('monthBranch', '')}")

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
        if m.get("verdict"):
            claim_refs.append(f"strength:{m['name']}")
            claim_refs.append(f"strength:{m['name']}:{m['verdict']}")
    if ctx.strength_agreement:
        claim_refs.append(f"strength:agreement:{ctx.strength_agreement}")
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
            claim_refs.append(f"pattern:{c['name']}")
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
            claim_refs.append(f"pattern:status:{ev.get('status')}")

    # ---- TiaoHou ----
    th = result.get("tiaohou")
    if th and th.get("resolved"):
        recs = []
        for r in th.get("recommendations") or []:
            stem = r.get("targetStem", "")
            priority = r.get("priority", "")
            recs.append({"stem": stem, "priority": priority,
                         "present": r.get("present"), "ruleIds": r.get("ruleIds", []),
                         "quote": r.get("quote"), "source": r.get("source")})
            claim_refs.append(f"tiaohou:{stem}")
            claim_refs.append(f"tiaohou:{stem}:{priority}")
            src = r.get("source")
            if src:
                sid = f"src_{stem}_{th.get('monthBranch', '')}"
                if not any(s.source_id == sid for s in ctx.sources):
                    ctx.sources.append(ContextSource(
                        source_id=sid, book=src.get("book", ""),
                        chapter=src.get("chapter"), pages=src.get("pages", []),
                        quote=r.get("quote"), source_kind=src.get("sourceKind", "CLASSICAL_TEXT"),
                        verification_status="MACHINE_CURATED",
                        quality=r.get("quality"), commentator=src.get("commentator"),
                    ))
                claim_refs.append(f"source:{sid}")
        ctx.tiaohou = {"dayMaster": th.get("dayMaster"), "monthBranch": th.get("monthBranch"),
                       "recommendations": recs, "conflicts": th.get("conflicts", [])}

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
        for c in sp.get("cong") or []:
            ctype = c.get("type", "")
            cstatus = c.get("status", "")
            claim_refs.append(f"special:cong:{ctype}")
            claim_refs.append(f"special:cong:{ctype}:{cstatus}")
            if cstatus == "UNRESOLVED":
                ctx.unresolved.append(f"从格 {ctype} 证据不足")
        for z in sp.get("zhuanwang") or []:
            ztype = z.get("type", "")
            zstatus = z.get("status", "")
            claim_refs.append(f"special:zhuanwang:{ztype}")
            claim_refs.append(f"special:zhuanwang:{ztype}:{zstatus}")
            if zstatus == "UNRESOLVED":
                ctx.unresolved.append(f"专旺 {ztype} 证据不足")
        for t in sp.get("transformation") or []:
            pair = "".join(t.get("stemPair", []))
            te = t.get("targetElement", "")
            tstatus = t.get("status", "")
            claim_refs.append(f"transformation:{pair}:{te}")
            claim_refs.append(f"transformation:{pair}:{te}:{tstatus}")
            if tstatus == "UNRESOLVED":
                ctx.unresolved.append(f"化气 {pair} 证据不足")
        for p in adv.get("bingYao", {}).get("problems") or []:
            claim_refs.append(f"bingyao:{p.get('target', '')}")
        for b in adv.get("tongGuan", {}).get("bridges") or []:
            claim_refs.append(f"tongguan:{b.get('bridge', '')}")

    # ---- Sources for sources list ----
    for s in ctx.sources:
        claim_refs.append(f"source:{s.source_id}")
        claim_refs.append(f"verification:{s.source_id}:{s.verification_status}")

    # ---- Warnings / fallbacks ----
    ctx.warnings = list(result.get("warnings") or [])
    ctx.unresolved.extend(result.get("fallbacks") or [])

    ctx.all_rule_ids = list(result.get("roots") or []) and [r.get("statement", "") for r in result.get("roots") or []]
    for rec in (th or {}).get("recommendations") or []:
        ctx.all_rule_ids.extend(rec.get("ruleIds") or [])

    ctx.claim_refs = list(dict.fromkeys(claim_refs))  # dedupe preserve order
    return ctx
