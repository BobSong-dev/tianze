"""M16：全链路可解释性测试（EventTheme → Rule → rescue → Quote → Source）。"""

from __future__ import annotations

import datetime

import pytest

from tianze.domain.models import BirthInfo, Gender
from tianze.pipeline import build_chart
from tianze.analysis.event_themes import compute_event_themes, EventTheme
from tianze.analysis.explain import build_explanation_chain, build_explanation_chains
from tianze.analysis.rescues import evaluate_rescues


@pytest.fixture(scope="module")
def chart():
    return build_chart(BirthInfo(date=datetime.date(1984, 2, 5),
                                 time=datetime.time(10, 30), gender=Gender.MALE))


def _rep(chart, **kw):
    return compute_event_themes(chart, **kw)


def test_chain_complete_for_disputed_career(chart):
    """DISPUTED career：支持链+反对链+冲突解释+Quote+Source 全部可达。"""
    from tianze.analysis.temporal_delta import compute_temporal_delta
    delta = compute_temporal_delta(chart, luck=("甲", "子"), annual=("丙", "午"),
                                   monthly=("庚", "寅"))
    rescue_state = evaluate_rescues(
        _ctx_of(chart, delta))
    rep = compute_event_themes(chart, luck=("甲", "子"), annual=("丙", "午"),
                               monthly=("庚", "寅"), delta_report=delta)
    career = next(t for t in rep.themes if t.theme == EventTheme.CAREER)
    chain = build_explanation_chain(career, rescue_state)
    assert chain["theme"] == "career" and chain["status"] == "DISPUTED"
    assert chain["reasoning"]["supportingChain"]
    assert chain["reasoning"]["opposingChain"]
    assert chain["reasoning"]["conflictExplanations"]
    hit = chain["reasoning"]["supportingChain"][0]
    assert hit["source"]["book"]  # Source 可达
    assert hit["quote"]           # Quote 可达（CLASSICAL_EXPLICIT 注记）
    assert hit["engineFacts"]     # Engine 事实口径
    assert "不裁决" in chain["reasoning"]["verdictStatement"]


def _ctx_of(chart, delta):
    from tianze.analysis.event_themes import build_event_context
    from tianze.analysis.temporal import analyze_temporal
    ta = analyze_temporal(natal_stems=delta.context.natal_stems,
                          natal_branches=delta.context.natal_branches,
                          day_master=chart.day_master.stem,
                          luck_stem=delta.context.luck_stem,
                          luck_branch=delta.context.luck_branch,
                          annual_stem=delta.context.annual_stem,
                          annual_branch=delta.context.annual_branch,
                          monthly_stem=delta.context.monthly_stem,
                          monthly_branch=delta.context.monthly_branch)
    return build_event_context(chart, delta.context, delta, ta.relations, ta.structures)


def test_chain_has_rescue_when_applicable(chart):
    """救应命中时进入解释链（rescueApplied + mayChangeResultConditions）。"""
    from tianze.analysis.temporal_delta import compute_temporal_delta
    delta = compute_temporal_delta(chart, luck=("甲", "子"), annual=("丙", "午"),
                                   monthly=("庚", "寅"))
    rep = compute_event_themes(chart, luck=("甲", "子"), annual=("丙", "午"),
                               monthly=("庚", "寅"), delta_report=delta)
    career = next(t for t in rep.themes if t.theme == EventTheme.CAREER)
    chain = build_explanation_chain(career)
    all_hits = chain["reasoning"]["supportingChain"] + chain["reasoning"]["opposingChain"]
    opp = next(h for h in all_hits if h["ruleId"] == "EV-CAR-03")
    assert opp["rescueApplied"] is not None          # 印救应
    assert any(c["mayChangeResultConditions"] or c["conflictNeighbors"]
               for c in all_hits)


def test_chains_deterministic(chart):
    r1 = build_explanation_chains(_rep(chart, annual=("丙", "午")))
    r2 = build_explanation_chains(_rep(chart, annual=("丙", "午")))
    assert json.dumps(r1, ensure_ascii=False, sort_keys=True) == \
        json.dumps(r2, ensure_ascii=False, sort_keys=True)


def test_chain_no_fortune_language(chart):
    chain = build_explanation_chains(_rep(chart, annual=("丙", "午")))
    blob = json.dumps(chain, ensure_ascii=False)
    for banned in ("一定会", "必然会", "必定", "横祸"):
        assert banned not in blob


import json  # noqa: E402
