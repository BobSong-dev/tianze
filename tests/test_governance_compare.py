"""M19：评估对比 + 陈旧工件检测测试。"""

from __future__ import annotations

import json
import os

from fastapi.testclient import TestClient

from apps.api.main import app
from tools.ai_eval_compare import main as cmp_main

client = TestClient(app)


def test_eval_compare_deterministic_metrics():
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = cmp_main()
    assert rc == 0
    d = json.load(open("regression/ai-eval-compare.json", encoding="utf-8"))
    assert d["entryCount"] >= 1
    for c in d["comparisons"]:
        m = c["metrics"]
        assert {"groundingIssueTotal", "bannedTotal",
                "disagreementMissingCount", "verdictPass"} <= set(m)
        # 无 judge/准确率字段
        blob = json.dumps(c, ensure_ascii=False)
        for banned in ("llm_judge", "accuracy", "准确率"):
            assert banned not in blob


def test_stale_artifact_detection():
    r = client.get("/api/v1/knowledge/release").json()
    assert "stale" in r
    assert isinstance(r["stale"]["stale"], bool)
    assert "reasons" in r["stale"]


def test_versioning_doc_exists():
    assert os.path.exists("docs/VERSIONING.md")
    txt = open("docs/VERSIONING.md", encoding="utf-8").read()
    assert "禁止静默兼容" in txt
    assert "不自动产生" in txt or "永远不由机器产生" in txt
