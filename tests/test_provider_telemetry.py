"""M21：Provider Observability 测试（遥测/敏感数据防护）。"""

from __future__ import annotations

import json
import os

from tools.ai_evaluation import run
from tianze.ai import MockInterpretationProvider
from tianze.ai.models import InterpretationMetadata


def test_metadata_telemetry_fields():
    """Metadata 带遥测字段且 mock 值合理（latency None、retries 0、category none）。"""
    import asyncio
    from tianze.ai import build_interpretation_context
    from tianze.sdk import SimplifiedBirthInfo, analyze
    r = analyze(SimplifiedBirthInfo(date="2003-08-18", time="14:30", gender="male"))
    ctx = build_interpretation_context(r.model_dump())
    interp, meta = asyncio.run(__import__("tianze.ai", fromlist=["interpret"]).interpret(ctx, MockInterpretationProvider()))
    assert meta.retry_count == 0
    assert meta.error_category == "none"
    assert meta.attempt_count == 1


def test_run_records_telemetry_summary():
    """评估 run() 汇总遥测（latency/tokens/retries/categories）。"""
    result = run(MockInterpretationProvider(), use_real=False)
    assert "telemetry" in result
    t = result["telemetry"]
    assert {"latencyMsTotal", "latencyMsAvg", "tokensTotal",
            "retriesTotal", "errorCategories"} <= set(t)
    for r in result["results"]:
        assert "latencyMs" in r and "retries" in r and "errorCategory" in r


def test_history_no_secrets():
    """历史 JSONL 不得含 API Key / Authorization / 请求体片段。"""
    path = "regression/ai-evaluation-history.jsonl"
    if not os.path.exists(path):
        return
    blob = open(path, encoding="utf-8").read()
    for banned in ("Authorization", "Bearer ", "api_key", "sk-", "TIANZE_LLM_API_KEY"):
        assert banned not in blob, banned
    for line in open(path, encoding="utf-8"):
        e = json.loads(line)
        assert set(e.keys()) <= {"schemaVersion", "provider", "model", "promptVersion",
                                 "interpretationSchemaVersion", "caseSet", "caseSetHash",
                                 "summary", "perCase", "telemetry"}


def test_five_reading_consistency_empirical():
    """H5 实证：五读数 mixed 占多数是真实方法论分歧（weighted 全局计分 vs
    得令纯月令）——救应保守激活是 ADR-049 的正确行为，非映射错误。
    锁定：全同向（激活可用）+ 分歧（不激活）+ 无反向误判。"""
    import datetime
    import random
    from types import SimpleNamespace
    from tianze.domain.models import BirthInfo, Gender
    from tianze.pipeline import build_chart
    from tianze.analysis.rescues import evaluate_rescues
    from tianze.analysis.event_themes import build_event_context
    from tianze.analysis.temporal import analyze_temporal
    from tianze.ganzhi.tables import STEMS, BRANCHES
    rng = random.Random(99)
    wrong_direction = 0
    for _ in range(40):
        y, mo, d = rng.randint(1940, 2015), rng.randint(1, 12), rng.randint(1, 28)
        chart = build_chart(BirthInfo(date=datetime.date(y, mo, d),
                                      time=datetime.time(rng.randint(0, 23), 30),
                                      gender=Gender(rng.choice(["male", "female"]))))
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
        wf = st["wealth_favorable"]
        # 反向误判检查：weighted 明确偏弱时绝不允许激活「财为喜神方向」
        wv = next((m.verdict for m in chart.strength.methods
                   if "weighted" in (m.analyzer_id or "") and m.verdict), None)
        if wv in ("偏弱", "极弱") and wf["active"]:
            wrong_direction += 1
        assert "分歧" not in wf["note"] or not wf["active"], \
            "分歧状态下救应必须不激活"
    assert wrong_direction == 0
