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


def test_html_export_printable():
    """打印友好 HTML：目录/免责声明/状态词汇/确定性/print CSS。"""
    from tianze.export_html import to_html
    r = _result(include_temporal=True, target_year=2026,
                include_temporal_delta=True, include_event_themes=True)
    html = to_html(r)
    assert "<!DOCTYPE html>" in html and "@media print" in html
    assert 'class="toc"' in html and "目录" in html
    assert "不构成任何吉凶或人生事件预测" in html
    assert "非概率" in html
    assert "CONFIRMED" not in html
    assert to_html(_result()) == to_html(_result())  # 确定性


def test_html_explanation_chains():
    """HTML 报告渲染解释链（支持/反对链 + 原文引注）。"""
    from tianze.export_html import to_html
    r = _result(include_temporal=True, target_year=2026,
                include_temporal_delta=True, include_event_themes=True,
                include_explanations=True)
    html = to_html(r)
    assert "解释链" in html
    assert "支持链" in html and "反对链" in html
    assert "原文：" in html  # quote 渲染
    assert "滴天髓补注" in html or "守素室丛谈" in html or "命理一得" in html


def test_sdk_explanations_deterministic():
    r1 = _result(include_temporal=True, target_year=2026,
                 include_event_themes=True, include_explanations=True)
    r2 = _result(include_temporal=True, target_year=2026,
                 include_event_themes=True, include_explanations=True)
    assert r1["temporal"]["eventThemes"]["explanations"] == \
        r2["temporal"]["eventThemes"]["explanations"]
