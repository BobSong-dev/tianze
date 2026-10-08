"""M21：Rescue/Exception Coverage 审计测试。"""

from __future__ import annotations

import json

from tools.rescue_coverage import main as rcm


def test_rescue_coverage_shape():
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rcm()
    d = json.load(open("regression/rescue-coverage.json", encoding="utf-8"))
    assert d["ruleCount"] == 21
    assert d["rescueCoverage"]["rescued"] == 5
    # 全部 rescue 目标真实存在（与 audit gate G3 一致）
    for rid in d["rescuedRules"]:
        assert rid in {f"EV-CAR-0{i}" for i in (1, 3)} | {"EV-REL-05", "EV-WEA-01", "EV-WEA-02"}
    # heuristic 谓词显式暴露（不冒充古籍）
    assert "wealth_favorable" in d["heuristicConditionPredicates"]
    assert d["note"] and "宁缺毋滥" in d["note"]
