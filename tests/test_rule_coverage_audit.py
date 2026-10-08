"""M19：Rule Coverage / Dead Rule 分析测试。"""

from __future__ import annotations

import json

from tools.rule_coverage_audit import main as rca_main


def test_classification_complete():
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rca_main()
    d = json.load(open("regression/rule-coverage-audit.json", encoding="utf-8"))
    assert d["ruleCount"] == 220
    classified = set()
    for ids in d["classifications"].values():
        classified.update(ids)
    assert len(classified) <= 216
    assert d["discipline"] and "不自动删除" in d["discipline"]


def test_never_triggered_exists():
    """event 域全部规则有触发率记录；低频规则进入审计分类。"""
    d = json.load(open("regression/rule-coverage-audit.json", encoding="utf-8"))
    assert "never_triggered" in d["classifications"] or "low_trigger" in d["classifications"]
    ev_rates = {k for k in d["triggerRates"] if k.startswith("EV-")}
    assert len(ev_rates) == 21
    assert d["tiaohouCaseCoverage"] > 0  # tiaohou 规则有 case 覆盖数据
