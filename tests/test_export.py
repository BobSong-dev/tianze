"""M13：分析报告 Markdown 导出。"""

from __future__ import annotations

from tianze.export import to_markdown
from tianze.sdk import AnalysisOptions, SimplifiedBirthInfo, analyze


def _result(**opts) -> dict:
    r = analyze(SimplifiedBirthInfo(date="2003-08-18", time="14:30", gender="male"),
                AnalysisOptions(**opts))
    return r.model_dump()


def test_export_natal():
    md = to_markdown(_result())
    assert "# Tianze 八字结构分析报告" in md
    assert "## 四柱" in md and "癸未" in md
    assert "## 旺衰" in md
    assert "不构成任何吉凶或人生事件预测" in md


def test_export_with_temporal_delta():
    md = to_markdown(_result(include_temporal=True, target_year=2026,
                             include_temporal_delta=True))
    assert "## 岁运分析（M13）" in md
    assert "大运" in md and "流年丙午" in md
    assert "TR-SPZY-28" in md
    assert "Temporal Delta" in md


def test_export_luck_table():
    md = to_markdown(_result())
    assert "## 大运" in md
    assert "顺逆" in md


def test_export_no_fortune_language():
    md = to_markdown(_result(include_temporal=True, target_year=2026,
                             include_temporal_delta=True))
    for banned in ("一定会发财", "必然升职", "必定结婚"):
        assert banned not in md


def test_export_deterministic():
    r1 = to_markdown(_result(include_temporal=True, target_year=2026,
                             include_temporal_delta=True))
    r2 = to_markdown(_result(include_temporal=True, target_year=2026,
                             include_temporal_delta=True))
    assert r1 == r2


def test_export_with_event_themes():
    md = to_markdown(_result(include_temporal=True, target_year=2026,
                             include_temporal_delta=True, include_event_themes=True))
    assert "事件主题" in md
    assert "CANDIDATE" in md or "DISPUTED" in md or "LIKELY" in md
    assert "非概率" in md
    for banned in ("一定会", "必然发财", "必定结婚"):
        assert banned not in md
