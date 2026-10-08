"""M15 · Property / Fuzz 质量门（自建 property harness，LCG 确定性种子）。

决定：暂不引入 hypothesis 依赖（收益/成本比不高）——用固定种子的 LCG 随机盘
扫描以下不变量：
- 事件/岁运规则评估器在任意随机盘上不崩溃
- EventTheme 永远无 CONFIRMED；status 词汇受控
- TemporalDelta supportLevel/kind 受控；无非法状态
- refId / 序列化跨 hash-seed 稳定
- Grounding：引用不存在 refId 必被拦截（UNKNOWN_CLAIM_REF / UNKNOWN_EVIDENCE_ID）
- Timeline 月边界连续性（随机年份扫描）
"""

from __future__ import annotations

import datetime
import json
import os
import random
import subprocess
import sys

import pytest

from tianze.analysis.event_themes import EventStatus, compute_event_themes
from tianze.sdk import AnalysisOptions
from tianze.analysis.temporal_delta import compute_temporal_delta
from tianze.domain.models import BirthInfo, Gender
from tianze.pipeline import build_chart
from tianze.sdk import AnalysisOptions
from tianze.analysis.temporal_extended import month_windows_for_year
from tianze.ganzhi.tables import STEMS, BRANCHES

VALID_STATUS = {"CANDIDATE", "LIKELY", "DISPUTED", "BLOCKED", "UNRESOLVED"}
VALID_SUPPORT = {"SUPPORTED", "EXPERIMENTAL", "UNSUPPORTED"}
VALID_KIND = {"added", "removed", "strengthened", "weakened", "status_changed",
              "blocked", "unblocked", "disagreement_changed"}

N_RANDOM = 120


def _random_charts(n: int, seed: int = 2026):
    rng = random.Random(seed)
    for _ in range(n):
        y, mo, d = rng.randint(1940, 2015), rng.randint(1, 12), rng.randint(1, 28)
        g = rng.choice(["male", "female"])
        try:
            chart = build_chart(BirthInfo(date=datetime.date(y, mo, d),
                                          time=datetime.time(rng.randint(0, 23), rng.choice([0, 30])),
                                          gender=Gender(g)))
        except Exception:
            continue
        ai = rng.randint(0, 59)
        li = rng.randint(0, 59)
        yield chart, (STEMS[ai % 10], BRANCHES[ai % 12]), (STEMS[li % 10], BRANCHES[li % 12])


def test_fuzz_event_and_delta_invariants():
    """随机盘 60 例：评估器不崩溃 + status/supportLevel/kind 全受控 + 无 CONFIRMED。"""
    checked = 0
    for chart, annual, luck in _random_charts(N_RANDOM):
        delta = compute_temporal_delta(chart, luck=luck, annual=annual)
        for it in delta.items:
            assert it.supportLevel.value in VALID_SUPPORT
            assert it.kind.value in VALID_KIND
        for f in delta.specialFindings:
            assert f["status"] == "CANDIDATE"
            assert f["transition"] in ("unchanged", "appeared", "disappeared",
                                       "blocked", "unblocked", "regraded")
        ev = compute_event_themes(chart, luck=luck, annual=annual,
                                  delta_report=delta)
        for t in ev.themes:
            assert t.status.value in VALID_STATUS
            assert "CONFIRMED" not in t.status.value
        blob = delta.model_dump_json(by_alias=True, exclude_none=True)
        ev_blob = ev.model_dump_json(by_alias=True, exclude_none=True)
        for banned in ("发财", "大凶", "必有灾", "横死"):
            assert banned not in ev_blob
        checked += 1
    assert checked >= N_RANDOM - 5  # 排盘失败可忽略，但绝大多数须成功


def test_refid_serialization_stability_across_hash_seeds():
    """refId/序列化跨 hash seed 稳定（子进程模拟不同进程）。"""
    code = (
        "import datetime;"
        "from tianze.domain.models import BirthInfo, Gender;"
        "from tianze.pipeline import build_chart;"
        "from tianze.analysis.event_themes import compute_event_themes;"
        "chart = build_chart(BirthInfo(date=datetime.date(1984,2,5),"
        "time=datetime.time(10,30), gender=Gender.MALE));"
        "rep = compute_event_themes(chart, luck=('甲','子'), annual=('丙','午'),"
        "monthly=('庚','寅'));"
        "print(rep.model_dump_json(by_alias=True, exclude_none=True))"
    )
    outs = set()
    for seed in ("0", "7", "12345"):
        env = {"PYTHONHASHSEED": seed, "PATH": __import__("os").environ.get("PATH", ""),
               "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", "")}
        env["PYTHONIOENCODING"] = "utf-8"
        res = subprocess.run([sys.executable, "-X", "utf8", "-c", code],
                             capture_output=True, env=env,
                             cwd=__import__("os").path.dirname(
                                 __import__("os").path.dirname(__import__("os").path.abspath(__file__))))
        assert res.returncode == 0, res.stderr.decode("utf-8", "replace")[:500]
        outs.add(res.stdout.decode("utf-8", "replace").strip())
    assert len(outs) == 1, "事件主题 JSON 随 hash seed 变化（存在 set/dict 迭代序泄漏）"


def test_grounding_intercepts_fake_refs():
    """Grounding：引用不存在的 evidence/source/claim ref 必须被拦截。"""
    from tianze.ai import build_interpretation_context, validate_grounding
    from tianze.ai.models import (
        GroundingIssueType, InterpretationResult, InterpretationSection,
    )
    from tianze.sdk import SimplifiedBirthInfo, analyze
    r = analyze(SimplifiedBirthInfo(date="2003-08-18", time="14:30", gender="male"),
                AnalysisOptions(include_temporal=True, target_year=2026,
                                include_event_themes=True))
    ctx = build_interpretation_context(r.model_dump())
    fake = InterpretationResult(
        summary="伪造引用测试",
        sections=[InterpretationSection(
            type="event_themes", title="伪造",
            content="结构描述（无禁语）。",
            claims=[], evidence_ids=["fake_evidence_1"], source_ids=["fake_source_1"],
        )],
        source_references=["fake_source_1"],
    )
    issues = validate_grounding(fake, ctx)
    types = {i.type for i in issues}
    assert GroundingIssueType.UNKNOWN_EVIDENCE_ID in types
    assert GroundingIssueType.UNKNOWN_SOURCE_ID in types


def test_conflict_graph_live_integrity():
    """图完整性（运行时）：全部边端点存在；每条 event 规则可反查。"""
    import glob as _glob
    g = json.load(open("knowledge/rules/event/conflict-graph.json", encoding="utf-8"))
    node_ids = {n["id"] for n in g["nodes"]}
    for e in g["edges"]:
        ids = e.get("between") or [x for x in (e.get("from"), e.get("to")) if x]
        assert all(x in node_ids for x in ids), e
        if len(ids) >= 2:
            assert ids[0] != ids[1], e
    from tianze.analysis.rule_conflicts import explain_rule
    for f in _glob.glob("knowledge/rules/event/rules.json"):
        for r in json.load(open(f, encoding="utf-8"))["rules"]:
            info = explain_rule(r["id"])
            assert info["rule"]["id"] == r["id"]


def test_case_chart_replay_robustness():
    """随机四柱 → case chart 不崩溃；不完整四柱 → ValueError（显式拒绝）。"""
    from tianze.analysis.case_chart import build_case_chart
    rng = random.Random(11)
    ok = 0
    for _ in range(30):
        pillars = {}
        for pos in ("year", "month", "day", "hour"):
            i = rng.randint(0, 59)
            pillars[pos] = STEMS[i % 10] + BRANCHES[i % 12]
        chart = build_case_chart(pillars)
        assert chart.day_master.stem == pillars["day"][0]
        ok += 1
    assert ok == 30
    with pytest.raises(ValueError):
        build_case_chart({"year": "甲子", "day": "甲子"})


def test_cache_correctness_random():
    """进程内缓存正确性：随机同参调用输出一致（缓存不改变结果）。"""
    from tianze.analysis.temporal_extended import _analyze_temporal_cached
    rng = random.Random(13)
    for _ in range(20):
        natal = tuple(STEMS[rng.randint(0, 9)] for _ in range(4))
        natal_b = tuple(BRANCHES[rng.randint(0, 11)] for _ in range(4))
        layer = lambda: (STEMS[rng.randint(0, 9)], BRANCHES[rng.randint(0, 11)])
        args = ((natal, natal_b), natal[2], layer(), layer(), layer(), layer())
        r1 = _analyze_temporal_cached(*args)
        r2 = _analyze_temporal_cached(*args)
        assert r1.model_dump_json(by_alias=True) == r2.model_dump_json(by_alias=True)


def test_month_windows_continuity_random_years():
    """随机 20 年：流月窗口首尾相接且干支月序连续。"""
    rng = random.Random(7)
    for _ in range(20):
        year = rng.randint(1950, 2050)
        mws = month_windows_for_year(year)
        assert len(mws) == 12
        for a, b in zip(mws, mws[1:]):
            assert a["end"] == b["start"]
            si = (STEMS.index(b["stem"]) - STEMS.index(a["stem"])) % 10
            bi = (BRANCHES.index(b["branch"]) - BRANCHES.index(a["branch"])) % 12
            assert (si, bi) == (1, 1)


def test_review_queue_discipline():
    """Review Queue：只汇总不升级——全库不得出现机器生成的 HUMAN_* 状态。"""
    import glob as _glob
    for f in _glob.glob("knowledge/rules/*/rules.json"):
        for r in json.load(open(f, encoding="utf-8"))["rules"]:
            assert not str(r["verification"]["status"]).startswith("HUMAN"), r["id"]
    assert os.path.exists("review/review-queue.json")
    q = json.load(open("review/review-queue.json", encoding="utf-8"))
    assert q["discipline"] and "不产生任何人工状态" in q["discipline"]
    assert q["stats"].get("machineCurated", 0) >= 24  # temporal 14 + event 20 均 MACHINE_CURATED


def test_migrated_semantic_compat_fuzz():
    """随机规则 dict 迁移语义兼容（conditions/effects/provenance 恒不变）。"""
    from tools.migrate_knowledge import migrate_rule_v1_1_to_1_2
    rng = random.Random(21)
    for _ in range(30):
        rule = {
            "id": f"X-{rng.randint(0, 999)}",
            "domain": rng.choice(["tiaohou", "temporal", "event"]),
            "conditions": [{"field": "f", "value": rng.randint(0, 9)}],
            "effects": [{"kind": "note", "text": "t"}],
            "provenance": [{"level": "PROJECT_REFERENCE"}],
        }
        new, _ = migrate_rule_v1_1_to_1_2(rule)
        for key in ("id", "conditions", "effects", "provenance"):
            assert new[key] == rule[key]


def test_rescue_predicates_random_robust():
    """救应谓词在随机盘上不崩溃且输出结构恒定（active/evidence/note）。"""
    from tianze.analysis.rescues import RESCUE_PREDICATES, evaluate_rescues
    from types import SimpleNamespace
    rng = random.Random(31)
    for _ in range(20):
        dm = STEMS[rng.randint(0, 9)]
        ectx = SimpleNamespace(
            day_master=dm,
            natal_stems=[STEMS[rng.randint(0, 9)] for _ in range(4)],
            natal_branches=[BRANCHES[rng.randint(0, 11)] for _ in range(4)],
            temporal_units=[{"layer": "annual", "stem": STEMS[rng.randint(0, 9)],
                             "branch": BRANCHES[rng.randint(0, 11)]}],
            strength_verdict=rng.choice([None, "偏强", "中和", "偏弱"]),
            fuyi_verdict=rng.choice([None, "偏强", "中和"]),
            dimension_de_shi=rng.choice([None, True, False]),
        )
        st = evaluate_rescues(ectx)
        for pid, v in st.items():
            assert isinstance(v["active"], bool)
            assert isinstance(v["evidence"], list)
            assert v["note"]


# ---------- M24 · 拱夹/暗合关系不变量（随机盘） ----------

def _random_branch_chart(rng):
    pool = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    return [rng.choice(pool) for _ in range(4)]


def test_fuzz_arch_target_absence_invariant():
    """不变量：arch 关系的被拱支（members[2]）必须不在原局（拱虚；见则不报）。"""
    import random
    from tianze.relation.relations import analyze_relations
    rng = random.Random(2424)
    pos = ["year", "month", "day", "hour"]
    for _ in range(300):
        branches = _random_branch_chart(rng)
        stems = [rng.choice(list("甲乙丙丁戊己庚辛壬癸")) for _ in range(4)]
        rels = analyze_relations(stems, branches, pos)
        present = {b for b in branches if b}
        for r in rels:
            if r.kind.value == "arch":
                target = r.members[2]
                assert target not in present, f"{branches}: 拱{target} 但 {target} 在场"
                # 隔二缺一：members 前两支在地支环上恰夹 target
                from tianze.ganzhi.tables import BRANCHES
                i1, i2, it = (BRANCHES.index(r.members[0]), BRANCHES.index(r.members[1]),
                              BRANCHES.index(target))
                assert (i1 + 1) % 12 == it or (i1 - 1) % 12 == it
                assert (i2 + 1) % 12 == it or (i2 - 1) % 12 == it
                assert r.transform_candidate is None  # 虚神不产化候选


def test_fuzz_hidden_combination_constraints():
    """不变量：暗合只出现在贴邻柱、不与六合重叠、transform_candidate 恒 None。"""
    import random
    from tianze.relation.relations import analyze_relations
    from tianze.relation import tables as T
    rng = random.Random(3434)
    pos = ["year", "month", "day", "hour"]
    for _ in range(300):
        branches = _random_branch_chart(rng)
        stems = [rng.choice(list("甲乙丙丁戊己庚辛壬癸")) for _ in range(4)]
        for r in analyze_relations(stems, branches, pos):
            if r.kind.value == "hidden_combination":
                assert r.adjacency.value == "ADJACENT" or r.adjacency == "ADJACENT",                     f"{branches}: 暗合须贴邻（SPZY-34 两支毗连）"
                assert T.FS(set(r.members)) not in T.SIX_COMBINATIONS
                assert r.transform_candidate is None  # 非以化论也
                pair = T.HIDDEN_COMBINATIONS.get(T.FS(set(r.members)))
                assert pair is not None  # 只允许 SPZY-34 逐对表内暗合


def test_fuzz_relation_determinism_random_charts():
    """确定性：同盘重复分析 → 关系 JSON 完全一致（无 set 迭代序泄漏）。"""
    import random
    from tianze.relation.relations import analyze_relations
    rng = random.Random(4444)
    pos = ["year", "month", "day", "hour"]
    for _ in range(120):
        branches = _random_branch_chart(rng)
        stems = [rng.choice(list("甲乙丙丁戊己庚辛壬癸")) for _ in range(4)]
        dm = stems[2]
        a = [r.model_dump(by_alias=True) for r in analyze_relations(stems, branches, pos, dm)]
        b = [r.model_dump(by_alias=True) for r in analyze_relations(stems, branches, pos, dm)]
        assert a == b


def test_mld12_zhouxi_chart_arch():
    """MLD-12 周熙造（乙丑 己丑 丁亥 辛亥）：两丑两亥 → 丑亥拱子（虚神候选）。"""
    from tianze.relation.relations import analyze_relations
    rs = analyze_relations(["乙", "己", "丁", "辛"], ["丑", "丑", "亥", "亥"],
                           ["year", "month", "day", "hour"], "丁")
    arches = [r for r in rs if r.kind.value == "arch"]
    assert any(r.label == "丑亥拱子" for r in arches), [r.label for r in rs]
    a = next(r for r in arches if r.label == "丑亥拱子")
    assert a.members[2] == "子" and "子" not in {"丑", "亥"}
    # 跨年界拱（亥→丑 经子）：两支隔二缺一
    # 丑亥子 ⊆ 亥子丑（亥在场）→ 拱三会方（北方水·暗会）；丁禄在午，非拱禄
    assert a.sub_type == "拱三会方（北方水·暗会）"
    assert "暗冲暗会两说" in a.note


# ---------- M24 · 未成立拱夹候选（blockedRelations） ----------

def test_blocked_arch_target_present():
    """亥丑对 target 子在场 → blockedRelations 报「拱而不成」，且不入 relations。"""
    from tianze.relation.relations import analyze_blocked_arches, analyze_relations
    pos = ["year", "month", "day", "hour"]
    stems = ["癸", "癸", "丁", "辛"]
    branches = ["亥", "子", "丑", "巳"]
    rels = analyze_relations(stems, branches, pos, "癸")
    assert not any(r.kind.value == "arch" for r in rels), "靶支在场不得报 arch 关系"
    blocked = analyze_blocked_arches(stems, branches, pos, "癸")
    assert any(r.label == "丑亥拱子（不成）" for r in blocked), [r.label for r in blocked]
    b = next(r for r in blocked if r.label == "丑亥拱子（不成）")
    assert b.sub_type == "拱而不成（靶支在场）"
    assert "拱实不若拱虚" in b.note


def test_blocked_arch_sdk_passthrough():
    """blockedRelations 进 SDK 结果（additive），且与 relations 严格分离。"""
    from tianze.sdk import analyze
    r = analyze({"date": "1984-01-05", "time": "10:30", "gender": "male"})
    labels = [x["label"] for x in r.blockedRelations]
    assert any("不成" in x for x in labels), labels
    assert not any("不成" in x["label"] for x in r.relations)
