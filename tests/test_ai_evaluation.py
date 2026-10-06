"""M15：Real Provider AI Evaluation 工具测试（mock 管线 + SKIPPED 语义）。"""

from __future__ import annotations

import json
import os
import subprocess
import sys

from tools.ai_evaluation import _evaluate_output, _verdict, run, CANONICAL_CASES
from tianze.ai import MockInterpretationProvider, build_interpretation_context
from tianze.knowledge.models import KNOWLEDGE_SCHEMA_VERSION
from tianze import __version__
from tianze.sdk import AnalysisOptions, SimplifiedBirthInfo, analyze


def test_mock_pipeline_passes():
    """CI 模式：Mock provider 下管线检查全过（grounding/禁语/状态词汇）。"""
    result = run(MockInterpretationProvider(), use_real=False)
    assert result["summary"]["fail"] == 0
    assert result["summary"]["pass"] == result["summary"]["total"]


def test_canonical_cases_cover_scenarios():
    """canonical 语料覆盖：普通格局/DISPUTED/从格岁运/Event Theme/shensha。"""
    covers = " | ".join(" | ".join(c["covers"]) for c in CANONICAL_CASES)
    for token in ("普通格局", "DISPUTED", "从格", "Event Theme"):
        assert token in covers


def test_verdict_real_mode_fails_on_dispute_missing():
    """real 模式：disagreement 遗漏 → FAIL（mock 模式仅管线检查）。"""
    fake = {"groundingPassed": True, "bannedLanguage": [],
            "disagreementMissing": True, "statusVocabularyOk": True}
    assert _verdict(fake, real=True) == "FAIL"
    assert _verdict(fake, real=False) == "PIPELINE_OK"


def test_skipped_without_key(monkeypatch, tmp_path):
    """无 API Key → SKIPPED，不伪造结果。"""
    monkeypatch.delenv("TIANZE_LLM_API_KEY", raising=False)
    import tools.ai_evaluation as ae
    r = subprocess.run([sys.executable, "tools/ai_evaluation.py"],
                       capture_output=True, text=True, env={
                           "PATH": os.environ.get("PATH", ""),
                           "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")},
                       cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    assert "SKIPPED" in r.stdout
    d = json.load(open("regression/ai-evaluation.json", encoding="utf-8"))
    assert d["provider"] == "SKIPPED" and d["summary"]["total"] == 0
