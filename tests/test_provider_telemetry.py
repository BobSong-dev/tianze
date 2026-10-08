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
