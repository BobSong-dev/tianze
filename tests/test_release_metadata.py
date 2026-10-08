"""M18：Release Metadata 测试（真实数据来源，无硬编码统计）。"""

from __future__ import annotations

import json
import os

from tools.release_metadata import main as release_main


def test_metadata_generated():
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        release_main()
    d = json.load(open("release/release-metadata.json", encoding="utf-8"))
    assert d["release"]["gitCommit"], "commit 必须来自 git"
    assert d["counts"]["executableRules"] == 221
    assert d["counts"]["rulesByDomain"] == {"event": 21, "temporal": 18, "tiaohou": 182}
    assert d["counts"]["ruleCandidates"] == 556
    assert d["counts"]["cases"] == 1147
    assert d["counts"]["tests"] > 0                # 来自真实 pytest 采集
    assert d["quality"]["allGatesPass"] is True


def test_md_report_readable():
    md = open("release/release-report.md", encoding="utf-8").read()
    assert "# Tianze Release Report" in md
    assert "ExecutableRule" in md
    assert "Audit Gates" in md
    for banned in ("TODO", "FIXME"):
        assert banned not in md
