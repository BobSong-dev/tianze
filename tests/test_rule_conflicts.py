"""M15：方向级规则冲突推理测试（ConflictExplanation）。"""

from __future__ import annotations

import datetime
import json

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
    assert len(decls) == 5
    pairs = {frozenset({d["ruleA"], d["ruleB"]}) for d in decls}
    assert len(pairs) == 5  # 无重复对
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
    """声明 specific-over-general + specificCondition 且救应成立 → 以具体规则为主要解释。"""
    import tianze.analysis.rule_conflicts as rc
    monkeypatch.setattr(rc, "load_conflict_declarations", lambda: [
        {"ruleA": "RULE-GENERAL", "ruleB": "RULE-SPECIFIC",
         "resolution": "specific-over-general", "specific": "RULE-SPECIFIC",
         "specificCondition": "test_rescue",
         "specificConditionNote": "财为喜神时反主得财",
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
    rescue_state = {"test_rescue": {"active": True,
                                    "evidence": ["weighted 旺衰判定：偏强"],
                                    "note": "测试谓词"}}
    exps = explain_conflicts([sup, opp],
                             view_of_rule={"RULE-GENERAL": "traditional",
                                           "RULE-SPECIFIC": "traditional"},
                             rescue_state=rescue_state)
    assert len(exps) == 1
    e = exps[0]
    assert e.kind == "SPECIFIC_EXCEPTION"
    assert e.ruleB == "RULE-SPECIFIC" and e.resolution == "specific-over-general"
    assert "主要解释" in e.explanation and "保留为背景证据" in e.explanation
    assert "偏强" in e.explanation  # 救应依据进入解释链


def test_specific_exception_inactive_condition_falls_back(monkeypatch):
    """specificCondition 存在但不成立 → 回落 CONDITION_OVERLAP（不启用优先级）。"""
    import tianze.analysis.rule_conflicts as rc
    monkeypatch.setattr(rc, "load_conflict_declarations", lambda: [
        {"ruleA": "RULE-GENERAL", "ruleB": "RULE-SPECIFIC",
         "resolution": "specific-over-general", "specific": "RULE-SPECIFIC",
         "specificCondition": "test_rescue", "note": "测试声明"},
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
    exps = explain_conflicts([sup, opp], rescue_state={"test_rescue": {"active": False}})
    assert exps[0].kind == "CONDITION_OVERLAP"


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


# ---------- M16 真实救应 / SPECIFIC_EXCEPTION 集成 ----------

def test_rescue_applied_on_hit():
    """伤官见官 + 印星可见 → EV-CAR-03 命中带 RSC-SHANGGUAN-YIN 救应标记。"""
    import datetime
    from tianze.domain.models import BirthInfo, Gender
    from tianze.pipeline import build_chart
    from tianze.analysis.event_themes import compute_event_themes, EventTheme
    chart = build_chart(BirthInfo(date=datetime.date(1984, 2, 5),
                                  time=datetime.time(10, 30), gender=Gender.MALE))
    rep = compute_event_themes(chart, luck=("甲", "子"), annual=("丙", "午"),
                               monthly=("庚", "寅"))
    career = next(t for t in rep.themes if t.theme == EventTheme.CAREER)
    hit = next(h for h in career.triggeredRules if h.ruleId == "EV-CAR-03")
    assert hit.rescueApplied is not None
    assert hit.rescueApplied["id"] == "RSC-SHANGGUAN-YIN"
    assert hit.rescueApplied["effect"] == "weaken"
    assert any("正印" in e or "印" in e for e in hit.rescueApplied["evidence"])


def test_specific_exception_real_chart():
    """伤官见官 + 财救应成立 → SPECIFIC_EXCEPTION：官星支持为主要解释，伤官见官降为背景。"""
    import datetime
    from tianze.domain.models import BirthInfo, Gender
    from tianze.pipeline import build_chart
    from tianze.analysis.event_themes import compute_event_themes, EventTheme
    chart = build_chart(BirthInfo(date=datetime.date(1984, 2, 5),
                                  time=datetime.time(10, 30), gender=Gender.MALE))
    # 岁运：甲（正官 support）+ 庚（伤官 oppose）+ 壬（正财，救应）
    rep = compute_event_themes(chart, luck=("甲", "子"), annual=("壬", "辰"),
                               monthly=("庚", "申"))
    career = next(t for t in rep.themes if t.theme == EventTheme.CAREER)
    kinds = [c["kind"] for c in career.conflictExplanations]
    assert "SPECIFIC_EXCEPTION" in kinds, kinds
    se = next(c for c in career.conflictExplanations if c["kind"] == "SPECIFIC_EXCEPTION")
    # ruleA=general（背景）、ruleB=specific（主要解释）
    assert se["ruleA"] == "EV-CAR-03" and se["ruleB"] == "EV-CAR-01"
    assert "主要解释" in se["explanation"] and "保留为背景证据" in se["explanation"]
    assert "正财" in se["explanation"] or "偏财" in se["explanation"]  # 救应依据进入解释
    # 状态仍为 DISPUTED（背景证据保留，不销毁反对信息）
    assert career.status.value == "DISPUTED"


def test_cai_yin_guan_bridge_rescue():
    """财印不容 + 官星通关 → EV-REL-05 命中带 RSC-CAI-YIN-GUAN 救应。"""
    import datetime
    from tianze.domain.models import BirthInfo, Gender
    from tianze.pipeline import build_chart
    from tianze.analysis.event_themes import compute_event_themes, EventTheme
    chart = build_chart(BirthInfo(date=datetime.date(1984, 2, 5),
                                  time=datetime.time(10, 30), gender=Gender.MALE))
    # 己日主：印=丙/丁，财=壬/癸，官=甲/乙 —— 岁运配齐三组
    rep = compute_event_themes(chart, luck=("丙", "子"), annual=("壬", "辰"),
                               monthly=("甲", "戌"))
    rel = next(t for t in rep.themes if t.theme == EventTheme.RELATIONSHIP)
    hit = next((h for h in rel.triggeredRules if h.ruleId == "EV-REL-05"), None)
    if hit:  # 财印并见成立时
        assert hit.rescueApplied is not None
        assert hit.rescueApplied["id"] == "RSC-CAI-YIN-GUAN"
        assert "通关" in hit.rescueApplied["note"]


def test_rescue_predicates_engineering_label():
    """ENGINEERING 映射的谓词（wealth_favorable/sha_weak_body_strong）必须显式标注。"""
    from tianze.analysis.rescues import evaluate_rescues
    from types import SimpleNamespace
    ectx = SimpleNamespace(
        day_master="甲", gender="male",
        natal_stems=["甲", "丙", "甲", "庚"], natal_branches=["子", "寅", "戌", "午"],
        temporal_units=[{"layer": "annual", "stem": "戊", "branch": "子"}],
        strength_verdict="偏强", weighted_score=0.6)
    st = evaluate_rescues(ectx)
    for pid in ("wealth_favorable", "sha_weak_body_strong"):
        assert "ENGINEERING" in st[pid]["note"]
    assert st["wealth_favorable"]["active"] is True
    assert st["cai_present"]["active"] is True   # 戊 = 甲之偏财（甲克戊）


# ---------- M16.2 Rule-ID Conflict Graph ----------

def test_conflict_graph_integrity():
    """图完整性：节点引用存在、无自环、specific/specificCondition 引用有效。"""
    import subprocess, sys, os
    r = subprocess.run([sys.executable, "tools/build_conflict_graph.py"],
                       capture_output=True, text=True, encoding="utf-8",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
                       cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Conflict Graph" in r.stdout and "节点" in r.stdout
    g = json.load(open("knowledge/rules/event/conflict-graph.json", encoding="utf-8"))
    assert g["problems"] == []
    assert g["edgeTypes"]["conflict"] == 5
    assert g["edgeTypes"]["rescues"] == 6
    assert g["edgeTypes"]["school-conflict"] >= 1


def test_explain_rule_reverse_lookup():
    """反查：EV-CAR-03 → 冲突对 + 救应谓词 + 可能改变结果的条件。"""
    from tianze.analysis.rule_conflicts import explain_rule
    info = explain_rule("EV-CAR-03")
    assert info["rule"]["id"] == "EV-CAR-03"
    types = {e["edgeType"] for e in info["related"]}
    assert "conflict" in types and "rescues" in types
    rescue_edges = [e for e in info["related"] if e["edgeType"] == "rescues"]
    assert any(e["mayChangeResult"] for e in rescue_edges)
    # specificCondition 反查可见
    conflict_edges = [e for e in info["related"] if e["edgeType"] == "conflict"]
    assert any(e.get("specificCondition") for e in conflict_edges)


def test_explain_rule_unknown_raises():
    import pytest
    from tianze.analysis.rule_conflicts import explain_rule
    with pytest.raises(KeyError):
        explain_rule("EV-NOT-EXIST")
