"""M19：Release Automation 测试（dry-run，不建 tag 不 push）。"""

from __future__ import annotations

import json
import os
import subprocess
import sys

from tools.release_automation import main as ra_main


def test_release_notes_generated(monkeypatch):
    """notes/tag-prep 生成验证；--skip-gate-check（gate 内测试运行时
    summary 尚未刷新，gate 依赖检查由 release_check P0 负责）。"""
    import io, contextlib
    monkeypatch.setattr(sys, "argv", ["release_automation.py", "--skip-gate-check"])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = ra_main()
    assert rc == 0
    d = json.load(open("release/tag-prep.json", encoding="utf-8"))
    assert d["tagPrepared"]["created"] is False          # dry-run 默认
    assert "不自动 push" in d["tagPrepared"]["push"]
    assert d["bumpKind"] in ("minor", "patch")
    md = open("release/RELEASE_NOTES.md", encoding="utf-8").read()
    assert "Release Notes" in md
    assert "SKIPPED，不伪造" in md or "AI Evaluation"
    assert "Migration 要求" in md and "不静默改历史" in md
    assert "命中率" not in md


def test_no_tag_created():
    """dry-run 不得创建新 tag（v0.3.0 是 RC 期间人工创建的本地 tag；
    automation 建议的下一个 tag 不得被 dry-run 自动创建）。"""
    d = json.load(open("release/tag-prep.json", encoding="utf-8"))
    suggested = d["tagPrepared"]["tag"]
    r = subprocess.run(["git", "tag", "-l", suggested], capture_output=True, text=True,
                       encoding="utf-8",
                       cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    assert suggested not in r.stdout.split()
