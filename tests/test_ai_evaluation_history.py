"""M16：AI Evaluation History 版本化记录测试。"""

from __future__ import annotations

import json
import os

from tools.ai_evaluation import run
from tianze.ai import MockInterpretationProvider


def test_history_entry_appended(tmp_path):
    hist_path = "regression/ai-evaluation-history.jsonl"
    before = sum(1 for _ in open(hist_path, encoding="utf-8")) if os.path.exists(hist_path) else 0
    run(MockInterpretationProvider(), use_real=False)
    lines = open(hist_path, encoding="utf-8").read().strip().split("\n")
    assert len(lines) == before + 1
    entry = json.loads(lines[-1])
    assert entry["provider"] == "mock"
    assert entry["promptVersion"]
    assert len(entry["caseSetHash"]) == 12
    assert entry["summary"]["total"] == 4
    for pc in entry["perCase"]:
        assert pc["verdict"] in ("PASS", "FAIL", "PIPELINE_OK")


def test_history_no_llm_judge_fields():
    """历史记录只含确定性评估字段（无 LLM-judge 评分字段）。"""
    hist_path = "regression/ai-evaluation-history.jsonl"
    if not os.path.exists(hist_path):
        return
    entry = json.loads(open(hist_path, encoding="utf-8").read().strip().split("\n")[-1])
    blob = json.dumps(entry, ensure_ascii=False)
    for banned in ("llm_judge_score", "subjective", "ai_rating"):
        assert banned not in blob
