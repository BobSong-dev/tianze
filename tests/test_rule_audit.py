"""M18：Graph/Rule Audit 测试。"""

from __future__ import annotations

import json
import subprocess
import sys
import os

from tools.graph_audit import main as graph_audit_main
from tools.rule_audit import main as rule_audit_main


def test_graph_audit_clean():
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        graph_audit_main()
    d = json.load(open("regression/graph-audit.json", encoding="utf-8"))
    assert d["findings"]["A4_specific_cycles"]["pass"] is True
    a1 = d["findings"]["A1_specific_exception"]
    assert all(x["verdict"] == "OK" for x in a1)   # specificity 均有条件佐证
    assert not d["findings"]["A2_rescue_activation"]["overActive REVIEW"]
    assert d["lists"]["B1_heuristic_only_rules"] == []


def test_rule_audit_shape():
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rule_audit_main()
    d = json.load(open("regression/rule-audit.json", encoding="utf-8"))
    assert d["ruleCount"] == 21
    by_id = {r["ruleId"]: r for r in d["rules"]}
    ev = by_id["EV-CAR-01"]
    assert ev["conditions"]                      # 什么条件触发
    assert "randomTriggerRate" in ev
    assert "relationDistribution" in ev          # 支持/不同/沉默分布
    for r in d["rules"]:
        assert len(r["samples"]) <= 8


def test_audit_tools_deterministic():
    """审计产物确定性（同输入同输出）。"""
    d1 = json.dumps(json.load(open("regression/graph-audit.json", encoding="utf-8")),
                    sort_keys=True, ensure_ascii=False)
    d2 = json.dumps(json.load(open("regression/rule-audit.json", encoding="utf-8")),
                    sort_keys=True, ensure_ascii=False)
    # 重跑
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        graph_audit_main(); rule_audit_main()
    d1b = json.dumps(json.load(open("regression/graph-audit.json", encoding="utf-8")),
                     sort_keys=True, ensure_ascii=False)
    d2b = json.dumps(json.load(open("regression/rule-audit.json", encoding="utf-8")),
                     sort_keys=True, ensure_ascii=False)
    # graph-audit 的 A2 激活率来自固定种子随机盘 → 确定
    assert d1 == d1b
    # rule-audit 依赖 replay 工件（同工件 → 确定）
    assert d2 == d2b
