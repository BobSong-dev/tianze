"""M15：方向级规则冲突推理测试（ConflictExplanation）。"""

from __future__ import annotations

import datetime

import pytest

from tianze.domain.models import BirthInfo, Gender
from tianze.pipeline import build_chart
from tianze.analysis.event_themes import EventTheme, compute_event_themes
from tianze.analysis.rule_conflicts import ConflictExplanation, explain_conflicts, load_conflict_declarations
from tianze.knowledge.event_rules import load_event_rules


@pytest.fixture(scope="module")
def chart():
    return build_chart(BirthInfo(date=datetime.date(1984, 2, 5),
                                 time=datetime.time(10, 30), gender=Gender.MALE))


def test_conflict_declarations_loaded():
    decls = load_conflict_declarations()
    assert len(decls) == 4
    pairs = {frozenset({d["ruleA"], d["ruleB"]}) for d in decls}
    assert len(pairs) == 4  # 无重复对
    for d in decls:
        assert d["resolution"] in ("keep-both", "no-adjudication", "specific-over-general")
        assert d.get("note"), "每条声明必须带透明 note"


def test_direction_level_conflict_explanations(chart):
    """career 主题同盘支持+反对 → 逐对 ConflictExplanation（不再是主题级笼统图）。"""
    rep = compute_event_themes(chart, luck=("甲", "子"), annual=("丙", "午"),
                               monthly=("庚", "寅"))
    career = next(t for t in rep.themes if t.theme == EventTheme.CAREER)
    assert career.status.value == "DISPUTED"
    assert len(career.conflictExplanations) >= 2
    for c in career.conflictExplanations:
        assert c["kind"] in ("SPECIFIC_EXCEPTION", "SCHOOL_DIFFERENCE", "CONDITION_OVERLAP")
        assert c["resolution"] in ("specific-over-general", "no-adjudication", "keep-both")
        assert c["ruleA"] and c["ruleB"] and c["refId"].startswith("event:conflict:")
        assert "不裁决" in c["explanation"] or "保留" in c["explanation"]


def test_no_global_precedence_without_declaration(chart):
    """未声明 specific-over-general 的对绝不产生 A>B——引擎只给 keep-both/no-adjudication。"""
    from tianze.analysis.event_themes import EventRuleHit, EventDirection, EventTheme, SchoolView
    hits = [
        EventRuleHit(ruleId="EV-CAR-01", label="官星", theme=EventTheme.CAREER,
                     direction=EventDirection.SUPPORT, view=SchoolView.TRADITIONAL,
                     evidence=["x"], provenanceLevels=["CLASSICAL_EXPLICIT"]),
        EventRuleHit(ruleId="EV-CAR-03", label="伤官见官", theme=EventTheme.CAREER,
                     direction=EventDirection.OPPOSE, view=SchoolView.TRADITIONAL,
                     evidence=["y"], provenanceLevels=["CLASSICAL_EXPLICIT"]),
    ]
    meta = {r["id"]: {"view": r["view"], "label": r["label"],
                      "provenanceLevels": [p["level"] for p in r["provenance"]]}
            for r in load_event_rules()}
    exps = explain_conflicts(hits, view_of_rule={k: v["view"] for k, v in meta.items()},
                             prov_of_rule={k: v["provenanceLevels"] for k, v in meta.items()})
    kinds = {e.kind for e in exps}
    assert "SPECIFIC_EXCEPTION" not in kinds  # 该对未声明 specificity
    assert kinds == {"CONDITION_OVERLAP"}


def test_specific_exception_path_with_declaration(monkeypatch):
    """声明了 specific-over-general 的对 → 以具体规则为主要解释，同时保留一般规则。"""
    import tianze.analysis.rule_conflicts as rc
    monkeypatch.setattr(rc, "load_conflict_declarations", lambda: [
        {"ruleA": "RULE-GENERAL", "ruleB": "RULE-SPECIFIC",
         "resolution": "specific-over-general", "specific": "RULE-SPECIFIC",
         "specificNote": "财为喜神时反主得财",
         "note": "测试声明"},
    ])
    from tianze.analysis.event_themes import (
        EventDirection, EventRuleHit, EventTheme, SchoolView,
    )
    sup = EventRuleHit(ruleId="RULE-GENERAL", label="一般", theme=EventTheme.WEALTH,
                       direction=EventDirection.SUPPORT, view=SchoolView.TRADITIONAL,
                       evidence=["g"], provenanceLevels=["PROJECT_REFERENCE"])
    opp = EventRuleHit(ruleId="RULE-SPECIFIC", label="具体", theme=EventTheme.WEALTH,
                       direction=EventDirection.OPPOSE, view=SchoolView.TRADITIONAL,
                       evidence=["s"], provenanceLevels=["CLASSICAL_EXPLICIT"])
    exps = explain_conflicts([sup, opp],
                             view_of_rule={"RULE-GENERAL": "traditional",
                                           "RULE-SPECIFIC": "traditional"})
    assert len(exps) == 1
    e = exps[0]
    assert e.kind == "SPECIFIC_EXCEPTION"
    assert e.ruleB == "RULE-SPECIFIC" and e.resolution == "specific-over-general"
    assert "主要解释" in e.explanation and "同时记录" in e.explanation


def test_school_difference_explanation(chart):
    """不同流派的反对 → SCHOOL_DIFFERENCE（不裁决）。"""
    from tianze.analysis.event_themes import (
        EventDirection, EventRuleHit, EventTheme, SchoolView,
    )
    sup = EventRuleHit(ruleId="EV-WEA-01", label="财星", theme=EventTheme.WEALTH,
                       direction=EventDirection.SUPPORT, view=SchoolView.TRADITIONAL,
                       evidence=["g"], provenanceLevels=["CLASSICAL_EXPLICIT"])
    opp = EventRuleHit(ruleId="EV-CON-01", label="从格破格", theme=EventTheme.WEALTH,
                       direction=EventDirection.OPPOSE, view=SchoolView.SPECIAL_PATTERN,
                       evidence=["s"], provenanceLevels=["CLASSICAL_EXPLICIT"])
    exps = explain_conflicts([sup, opp],
                             view_of_rule={"EV-WEA-01": "traditional",
                                           "EV-CON-01": "special_pattern"})
    assert exps[0].kind == "SCHOOL_DIFFERENCE"
    assert exps[0].resolution == "no-adjudication"
    assert "保持 DISPUTED" in exps[0].explanation


def test_conflict_explanations_deterministic(chart):
    r1 = compute_event_themes(chart, luck=("甲", "子"), annual=("丙", "午"),
                              monthly=("庚", "寅"))
    r2 = compute_event_themes(chart, luck=("甲", "子"), annual=("丙", "午"),
                              monthly=("庚", "寅"))
    assert r1.model_dump_json(by_alias=True, exclude_none=True) == \
        r2.model_dump_json(by_alias=True, exclude_none=True)


def test_support_only_no_explanations(chart):
    """无方向冲突 → 无解释（不为凑数生成）。"""
    rep = compute_event_themes(chart, monthly=("甲", "寅"))
    mob = next(t for t in rep.themes if t.theme == EventTheme.MOBILITY)
    assert mob.conflictExplanations == []
