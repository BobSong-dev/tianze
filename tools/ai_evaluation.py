"""M15 · Real Provider AI Evaluation（不使用 LLM-as-judge 取代确定性校验）。

- 固定 canonical cases，覆盖：普通格局 / 多流派一致 / DISPUTED / 从格 /
  化气 UNRESOLVED / Temporal Delta / Event Theme / historical claim /
  MACHINE_CURATED / CLASSICAL_EXPLICIT
- Provider：TIANZE_LLM_API_KEY 存在 → 真实调用；否则全部 SKIPPED（不伪造结果）
- 评估全部为**确定性检查**（复用 Grounding Validator + 覆盖率统计），包括：
    * evidence 覆盖率（sections 引用的 claim/evidence 与 Context 的比例）
    * disagreement 是否被漏掉（Context 有 DISPUTED/CONFLICT 而输出未提及）
    * 状态升级（CANDIDATE/LIKELY 被写成「一定/必然」）
    * 事件幻觉/伪概率语言
    * 编造古籍（validate_grounding）
    * EXPERIMENTAL 标注是否正确表达
- CI 用 --mock 跑 MockInterpretationProvider 验证管线本身。

输出：regression/ai-evaluation.json
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tianze import __version__
from tianze.ai import (
    MockInterpretationProvider, build_interpretation_context, interpret,
    validate_grounding,
)
from tianze.ai.models import GroundingSeverity
from tianze.knowledge.models import KNOWLEDGE_SCHEMA_VERSION
from tianze.sdk import AnalysisOptions, SimplifiedBirthInfo, analyze

EVAL_SCHEMA_VERSION = "1.0.0"

BANNED = ("一定会", "必然会", "必定会", "肯定会", "必将", "注定",
          "发财", "升职", "结婚", "离婚", "婚期", "横祸", "暴富",
          "% 的概率", "概率为", "80%", "90%")

CANONICAL_CASES = [
    {"name": "normal_pattern", "birth": {"date": "2003-08-18", "time": "14:30", "gender": "male"},
     "options": {}, "covers": ["普通格局", "MACHINE_CURATED source（调候）"]},
    {"name": "disputed_career", "birth": {"date": "1984-02-05", "time": "10:30", "gender": "male"},
     "options": {"include_temporal": True, "target_year": 2026, "include_temporal_delta": True,
                 "include_event_themes": True},
     "target": {"luck": ("甲", "子"), "annual": ("丙", "午"), "monthly": ("庚", "寅")},
     "covers": ["DISPUTED", "多流派", "Event Theme", "Temporal Delta"]},
    {"name": "multi_view_agree", "birth": {"date": "1983-02-15", "time": "20:00", "gender": "female"},
     "options": {"include_temporal": True, "target_year": 2026, "include_temporal_delta": True,
                 "include_event_themes": True},
     "covers": ["多流派一致", "从格岁运专题", "CLASSICAL_EXPLICIT provenance"]},
    {"name": "event_themes_shensha", "birth": {"date": "1984-02-05", "time": "10:30", "gender": "male"},
     "options": {"include_temporal": True, "target_year": 2026, "target_month": 1,
                 "include_temporal_delta": True, "include_event_themes": True},
     "covers": ["shensha view", "Event Theme"]},
    {"name": "temporal_replay", "birth": {"date": "1984-02-05", "time": "10:30", "gender": "male"},
     "options": {"include_temporal": True, "target_luck_index": 0, "target_year": 2024,
                 "include_temporal_delta": True, "include_temporal_replay": True},
     "covers": ["逐层状态回放", "replay refId Grounding"]},
]


def _evaluate_output(interp, ctx) -> dict:
    """确定性评估（无 LLM-as-judge）。"""
    issues = validate_grounding(interp, ctx)
    blob = json.dumps(interp.model_dump(by_alias=True), ensure_ascii=False)

    content_all = "\n".join(s.content for s in interp.sections)
    banned_hits = [w for w in BANNED if w in content_all]

    # disagreement 遗漏检查
    context_disputes = bool(ctx.disagreements) or any(
        t.get("status") == "DISPUTED" or t.get("agreement") == "CONFLICT"
        for t in ((ctx.event_themes or {}).get("themes") or []))
    mentions_dispute = any(
        w in content_all for w in ("分歧", "冲突", "DISPUTED", "两说", "不裁决", "反对"))

    # EXPERIMENTAL 表达检查
    has_experimental = "EXPERIMENTAL" in blob or "EXPERIMENTAL" in content_all

    # 状态词汇完整性：提到主题时必须用状态词汇
    status_ok = not any(
        t.get("theme") and t["theme"] in content_all and
        not any(v in content_all for v in ("CANDIDATE", "LIKELY", "DISPUTED",
                                           "BLOCKED", "UNRESOLVED"))
        for t in ((ctx.event_themes or {}).get("themes") or []))

    fatal = [i for i in issues if i.severity == GroundingSeverity.FATAL]
    return {
        "groundingPassed": interp.grounding_passed and not fatal,
        "groundingIssues": [f"{i.type.value}: {i.detail[:120]}" for i in issues],
        "bannedLanguage": banned_hits,
        "disagreementMissing": bool(context_disputes and not mentions_dispute),
        "experimentalMentioned": has_experimental,
        "statusVocabularyOk": status_ok,
        "sectionsCount": len(interp.sections),
        "claimRefsUsed": len({c.ref_id for s in interp.sections for c in s.claims}),
        "latencyMs": getattr(ctx, "_last_latency_ms", None),
        "totalTokens": None,
        "retries": getattr(ctx, "_last_retries", 0),
        "errorCategory": getattr(ctx, "_last_error_category", "none"),
    }


def _verdict(eval_result: dict, real: bool) -> str:
    """real 模式：全量判定（含 disagreement 覆盖）；mock 模式：仅管线检查
    （grounding/禁语/状态词汇）——Mock 输出是固定文案，不承担内容质量评估。"""
    pipeline_ok = (eval_result["groundingPassed"] and not eval_result["bannedLanguage"]
                   and eval_result["statusVocabularyOk"])
    if real:
        return "PASS" if (pipeline_ok and not eval_result["disagreementMissing"]) else "FAIL"
    return "PIPELINE_OK" if pipeline_ok else "FAIL"


def run(provider, use_real: bool) -> dict:
    results = []
    for case in CANONICAL_CASES:
        r = analyze(SimplifiedBirthInfo(**case["birth"]),
                    AnalysisOptions(**case["options"]))
        result_dict = r.model_dump()
        if case.get("target"):
            # 注入聚焦岁运上下文（与 Web 路径一致：temporal 由 options 生成的顶层分析 +
            # 额外 luck/monthly 覆盖由 compute_event_themes 的显式参数完成）
            from tianze.domain.models import BirthInfo, Gender
            from tianze.pipeline import build_chart
            import datetime as dt
            y, m, d = (int(x) for x in case["birth"]["date"].split("-"))
            hh, mm = (int(x) for x in case["birth"]["time"].split(":"))
            chart = build_chart(BirthInfo(date=dt.date(y, m, d), time=dt.time(hh, mm),
                                          gender=Gender(case["birth"]["gender"])))
            from tianze.analysis.event_themes import compute_event_themes
            ev = compute_event_themes(chart, luck=case["target"].get("luck"),
                                      annual=case["target"].get("annual"),
                                      monthly=case["target"].get("monthly"))
            result_dict["temporal"]["eventThemes"] = ev.model_dump(by_alias=True, exclude_none=True)
        ctx = build_interpretation_context(
            result_dict, engine_version=__version__,
            knowledge_version=KNOWLEDGE_SCHEMA_VERSION, analysis_schema_version="1.0.0")
        interp, meta = asyncio.run(interpret(ctx, provider, engine_version=__version__))
        ev = _evaluate_output(interp, ctx)
        # M21 遥测：从 metadata 回填（provider 层上报；mock 为 0/None）
        ev["latencyMs"] = meta.latency_ms
        ev["totalTokens"] = meta.total_tokens
        ev["retries"] = meta.retry_count
        ev["errorCategory"] = meta.error_category
        ev["verdict"] = _verdict(ev, use_real)
        results.append({"case": case["name"], "covers": case["covers"],
                        "provider": meta.provider_name if hasattr(meta, "provider_name") else "mock",
                        **ev})

    summary = {
        "total": len(results),
        "pass": sum(1 for r in results if r["verdict"] in ("PASS", "PIPELINE_OK")),
        "fail": sum(1 for r in results if r["verdict"] == "FAIL"),
        "verdictScale": "real=PASS/FAIL（含 disagreement 覆盖）；mock=PIPELINE_OK/FAIL（仅管线检查）",
    }
    telemetry = {
        "latencyMsTotal": sum(r.get("latencyMs") or 0 for r in results),
        "latencyMsAvg": round(sum(r.get("latencyMs") or 0 for r in results)
                              / max(1, len(results)), 1),
        "tokensTotal": sum(r.get("totalTokens") or 0 for r in results),
        "retriesTotal": sum(r.get("retries", 0) for r in results),
        "errorCategories": sorted({r.get("errorCategory") for r in results
                                   if r.get("errorCategory")}),
    }
    result = {"schemaVersion": EVAL_SCHEMA_VERSION, "provider": "real" if use_real else "mock",
              "summary": summary, "telemetry": telemetry, "results": results}

    # M16.6：评估历史版本化（追加 JSONL；确定性评估结果；无 LLM-as-judge 字段）
    provider_name = getattr(provider, "provider_name", "unknown")
    model = "mock" if not use_real else os.environ.get("TIANZE_LLM_MODEL", "unknown")
    from tianze.ai.models import PROMPT_VERSION
    history_entry = {
        "schemaVersion": EVAL_SCHEMA_VERSION,
        "provider": provider_name,
        "model": model,
        "promptVersion": PROMPT_VERSION,
        "interpretationSchemaVersion": "1.1.0",
        "caseSet": [c["name"] for c in CANONICAL_CASES],
        "caseSetHash": __import__("hashlib").md5(
            json.dumps(CANONICAL_CASES, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()[:12],
        "summary": summary,
        "perCase": [{"case": r["case"], "verdict": r["verdict"],
                     "groundingIssues": len(r["groundingIssues"]),
                     "banned": r["bannedLanguage"],
                     "disagreementMissing": r["disagreementMissing"],
                     "claimRefsUsed": r["claimRefsUsed"]} for r in results],
        "telemetry": telemetry,
    }
    with open("regression/ai-evaluation-history.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(history_entry, ensure_ascii=False) + chr(10))
    return result


def main() -> int:
    use_real = bool(os.environ.get("TIANZE_LLM_API_KEY"))
    if "--mock" in sys.argv:
        use_real = False
    if use_real:
        from tianze.ai import create_provider_from_env
        provider = create_provider_from_env()
        if provider is None:
            use_real = False
    if not use_real:
        if "--mock" not in sys.argv:
            payload = {"schemaVersion": EVAL_SCHEMA_VERSION, "provider": "SKIPPED",
                       "reason": "TIANZE_LLM_API_KEY 未设置：不伪造真实评估结果；CI 使用 --mock",
                       "summary": {"total": 0, "pass": 0, "fail": 0}, "results": []}
            with open("regression/ai-evaluation.json", "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=1)
            print("AI Evaluation: SKIPPED（无 API Key）")
            return 0
        provider = MockInterpretationProvider()

    result = run(provider, use_real)
    with open("regression/ai-evaluation.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)

    print(f"AI Evaluation（{result['provider']}）：{result['summary']}")
    for r in result["results"]:
        print(f"  {r['verdict']} {r['case']} issues={len(r['groundingIssues'])} "
              f"banned={r['bannedLanguage']} disputeMissing={r['disagreementMissing']}")
    return 1 if result["summary"]["fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
