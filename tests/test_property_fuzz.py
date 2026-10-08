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


# ---------- M25 · 关系级解释链 ----------

def test_relation_explanations_three_states():
    """三态：结构事实 / 候选 / 未成立，引用链指向 citations 注册表。"""
    from tianze.sdk import analyze
    r = analyze({"date": "1984-01-05", "time": "10:30", "gender": "male"})
    exs = r.relationExplanations
    statuses = {e["status"] for e in exs}
    assert "ESTABLISHED" in statuses
    assert "CANDIDATE" in statuses      # 子戌暗合
    assert "BLOCKED" in statuses        # 子戌拱亥（不成）
    cand = next(e for e in exs if e["status"] == "CANDIDATE")
    assert any(c["candidateId"] == "SPZY-34" for c in cand["citations"])
    blk = next(e for e in exs if e["status"] == "BLOCKED")
    assert any("拱实不若拱虚" in c["text"] for c in blk["conditions"])
    assert "未成立" in blk["boundary"]


def test_relation_explanations_blocked_not_established():
    """Grounding 不变量：BLOCKED 解释不得混入 relations，status 词汇固定。"""
    from tianze.sdk import analyze
    r = analyze({"date": "1984-01-05", "time": "10:30", "gender": "male"})
    labels = [x["label"] for x in r.relations]
    for e in r.relationExplanations:
        if e["status"] == "BLOCKED":
            assert e["label"] not in labels or "（不成）" in e["label"]
        assert e["status"] in ("ESTABLISHED", "CANDIDATE", "BLOCKED")


def test_relation_explanations_temporal_fill():
    """temporal 层：填实解释带 ZP-05 禁则语境边界。"""
    from tianze.analysis.temporal import analyze_temporal
    ta = analyze_temporal(natal_stems=["癸", "己", "甲", "乙"],
                          natal_branches=["亥", "丑", "巳", "卯"],
                          day_master="癸", annual_stem="壬", annual_branch="子")
    fills = [e for e in ta.relationExplanations if e["status"] == "CANDIDATE"
             and e["kind"] == "arch_fill"]
    assert fills and "忌刑冲填实" in fills[0]["boundary"]
    assert any(c["candidateId"] == "ZP-05" for c in fills[0]["citations"])


def test_relation_citations_registry_complete():
    """引文注册表完备：citations.json 可载入、逐条带 sourceFile、引文非空。"""
    import json
    d = json.load(open("knowledge/rules/relations/citations.json", encoding="utf-8"))
    assert d["count"] >= 13
    for cid, c in d["citations"].items():
        assert c["quote"], cid
        assert c["sourceFile"], cid
        assert c["sourceKind"] in ("CLASSICAL_EXPLICIT", "CANONICAL_TABLE")


def test_ai_context_blocked_grounding():
    """AI Context：解释链进入 claim_refs；BLOCKED 条目带边界（不得描述为成立）。"""
    from tianze.sdk import analyze
    from tianze.ai.context_builder import build_interpretation_context
    r = analyze({"date": "1984-01-05", "time": "10:30", "gender": "male"})
    ctx = build_interpretation_context(r.model_dump(by_alias=True))
    blocked = [e for e in ctx.relation_explanations if e["status"] == "BLOCKED"]
    assert blocked, "BLOCKED 解释应进入 AI 上下文"
    assert all("未成立" in e["boundary"] for e in blocked)


# ---------- M25 · 拱对全矩阵 + 外格候选泛化审计 ----------

def test_fuzz_arch_full_pair_matrix():
    """全拱对×在场矩阵：12×12 中所有 gap-2 对，靶支在场/不在场两分支。"""
    from tianze.relation.tables import arch_target, BRANCHES
    from tianze.relation.relations import analyze_relations, analyze_blocked_arches
    pos = ["year", "month", "day", "hour"]
    found_pairs = 0
    for i in range(12):
        for j in range(12):
            a, b = BRANCHES[i], BRANCHES[j]
            tgt = arch_target(a, b)
            if tgt is None:
                continue
            found_pairs += 1
            # 靶支不在场 → arch 关系成立
            branches = [a, b, None, None]
            rels = analyze_relations([None] * 4, branches, pos)
            assert any(r.kind.value == "arch" and r.members[2] == tgt for r in rels), (a, b)
            assert not analyze_blocked_arches([None] * 4, branches, pos)
            # 靶支在场 → 无 arch 关系，报未成立候选
            branches2 = [a, b, tgt, None]
            rels2 = analyze_relations([None] * 4, branches2, pos)
            assert not any(r.kind.value == "arch" for r in rels2), (a, b, tgt)
            blk = analyze_blocked_arches([None] * 4, branches2, pos)
            assert any(x.members[2] == tgt for x in blk), (a, b, tgt)
    assert found_pairs == 24  # 每对双向定位 = 12 个无序对 × 2 个有向 hit


def test_xushi_outer_not_overgeneralized():
    """泛化审计锁定：井栏叉限庚日；子邀巳不落地（M25 审计结论）。"""
    from tianze.analysis.case_chart import build_case_chart
    # 甲日 卯刃拱（亥卯? 卯=甲刃：寅辰拱卯 → 甲日不得名井栏叉）
    chart = build_case_chart({"year": "丙寅", "month": "庚辰", "day": "甲申" if False else "甲戌", "hour": "丁卯"})
    for x in chart.advancedAnalysis["specialPattern"]["xushiOuter"]:
        assert "井栏叉" not in x["type"] or chart.day_master.stem == "庚"
    blob = str(chart.advancedAnalysis)
    assert "子邀巳" not in blob


def test_relation_explanations_deterministic():
    """确定性：同盘两次 analyze → relationExplanations JSON 完全一致。"""
    from tianze.sdk import analyze
    a = analyze({"date": "1990-01-01", "time": "03:00", "gender": "male"})
    b = analyze({"date": "1990-01-01", "time": "03:00", "gender": "male"})
    assert a.relationExplanations == b.relationExplanations
    # 与 relations 一一对应（每条关系都有解释）
    assert len(a.relationExplanations) == len(a.relations) + len(a.blockedRelations)


# ---------- M26 · 拱贵（天乙贵人）/ arch_broken（拱位刑冲两说）/ 六乙鼠贵 ----------

def test_arch_noble_subtype():
    """庚日 子寅拱丑：丑为庚之天乙贵人 → 拱贵 sub_type（SS-R17 起例）。"""
    from tianze.relation.relations import analyze_relations
    pos = ["year", "month", "day", "hour"]
    rs = analyze_relations(["庚", None, "庚", None], ["子", None, "寅", None], pos, "庚")
    a = next(r for r in rs if r.kind.value == "arch")
    assert a.sub_type == "拱贵（天乙贵人位）"
    assert "天乙贵人" in a.note


def test_arch_noble_meeting_priority():
    """拱三会方优先级高于拱贵；贵/禄同见时双注记。"""
    from tianze.relation.relations import analyze_relations
    pos = ["year", "month", "day", "hour"]
    # 己日：亥丑拱子——子∈亥子丑（三会方）且子为己贵（乙己鼠猴乡）→ 三会方 + 拱贵同见
    rs = analyze_relations(["己", None, None, None], ["亥", None, "丑", None], pos, "己")
    a = next(r for r in rs if r.kind.value == "arch")
    assert a.sub_type.startswith("拱三会方")
    assert "天乙贵人" in a.note


def test_temporal_arch_broken_clash():
    """原局亥丑拱子；流年未冲丑 → arch_broken（拱破/拱动两说，不判吉凶）。"""
    from tianze.analysis.temporal import analyze_temporal
    ta = analyze_temporal(natal_stems=["癸", "己", "甲", "乙"],
                          natal_branches=["亥", "丑", "巳", "卯"],
                          day_master="癸", annual_stem="己", annual_branch="未")
    kinds = [r.kind for r in ta.relations]
    assert "arch_broken" in kinds
    ev = next(t for t in ta.ruleTriggers if t.ruleId == "TR-DTZ-10")
    assert ev.matched and any("拱破" in o and "拱动" in o for o in ev.observations)


def test_temporal_arch_broken_xing():
    """原局巳未拱午；流年申刑巳（寅巳申三刑部分）→ arch_broken 刑说。"""
    from tianze.analysis.temporal import analyze_temporal
    ta = analyze_temporal(natal_stems=["戊", "甲", "甲", "庚"],
                          natal_branches=["巳", "未", "丑", "亥"],
                          day_master="甲", annual_stem="戊", annual_branch="申")
    kinds = [r.kind for r in ta.relations]
    assert "arch_broken" in kinds
    brk = next(r for r in ta.relations if r.kind == "arch_broken")
    assert "刑" in brk.label and "拱破" in brk.note


def test_liuyi_shugui_candidate():
    """六乙鼠贵（ZP-06）：乙日子时 → 候选；官煞透 → BLOCKED。"""
    from tianze.analysis.case_chart import build_case_chart
    c = build_case_chart({"year": "丙子", "month": "丁亥", "day": "乙卯", "hour": "庚子"})
    xo = c.advancedAnalysis["specialPattern"]["xushiOuter"]
    m = next(x for x in xo if "六乙鼠贵" in x["type"])
    assert m["status"] == "BLOCKED"  # 庚官透
    assert any("SS-R16" in k or "三要件" in sv
               for k, sv in m["schoolVariants"].items())


# ---------- M26 · 重复支 / arch_broken / 争合 fuzz ----------

def test_fuzz_duplicate_branches_arch():
    """重复支（两亥两丑类）：多拱对并存不崩溃、targets 全部不在场、顺序确定。"""
    import random
    from tianze.relation.relations import analyze_relations
    rng = random.Random(2626)
    pos = ["year", "month", "day", "hour"]
    pool = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    for _ in range(200):
        branches = [rng.choice(pool) for _ in range(4)]
        stems = [rng.choice(list("甲乙丙丁戊己庚辛壬癸")) for _ in range(4)]
        rs1 = [r.model_dump(by_alias=True) for r in
               analyze_relations(stems, branches, pos, stems[2])]
        rs2 = [r.model_dump(by_alias=True) for r in
               analyze_relations(stems, branches, pos, stems[2])]
        assert rs1 == rs2
        present = {b for b in branches if b}
        for r in rs1:
            if r["kind"] == "arch":
                assert r["members"][2] not in present


def test_fuzz_arch_broken_requires_natal_arch():
    """不变量：arch_broken 仅当原局存在拱位虚神且岁运刑/冲其成员。"""
    import random
    from tianze.analysis.temporal import analyze_temporal
    from tianze.relation.tables import arch_target, SIX_CLASHES
    rng = random.Random(2727)
    pool = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    trios = (frozenset({"寅", "巳", "申"}), frozenset({"丑", "戌", "未"}))
    for _ in range(150):
        branches = [rng.choice(pool) for _ in range(4)]
        stems = [rng.choice(list("甲乙丙丁戊己庚辛壬癸")) for _ in range(4)]
        annual = rng.choice(pool)
        ta = analyze_temporal(natal_stems=stems, natal_branches=branches,
                              day_master=stems[2], annual_stem="甲", annual_branch=annual)
        natal = [b for b in branches if b]
        targets = {}
        for x in range(len(natal)):
            for y in range(x + 1, len(natal)):
                t = arch_target(natal[x], natal[y])
                if t and t not in set(natal):
                    targets[t] = (natal[x], natal[y])
        broken = [r for r in ta.relations if r.kind == "arch_broken"]
        if broken:
            assert targets, "无拱位却报 arch_broken"
            for r in broken:
                members = set(r.members)
                pair_hit = any({annual, m} in SIX_CLASHES
                               or {annual, m} == frozenset({"子", "卯"})
                               or any({annual, m} <= trio for trio in trios)
                               for m in members if m != annual)
                assert pair_hit, (branches, annual, r.label)


def test_fuzz_zhenghe_transformation_obstruction():
    """争合：二己二甲 → 甲己候选必带争合 obstruction（或被邻位规则阻断）。"""
    from tianze.analysis.special import analyze_transformation
    ts = analyze_transformation("甲", "子", ["己", "己", "甲", "甲"], ["子", "子", "亥", "卯"])
    pairs = [t for t in ts if t.stem_pair == ("甲", "己")]
    assert pairs
    assert any(t.obstructions for t in pairs)


# ---------- M27 · 三要件条件化 / 去填复现 ----------

def test_liuyi_shugui_three_conditions():
    """SS-R16 三要件：见合（子丑合）→ support；无合 → blocker；午冲子 → blocker。"""
    from tianze.analysis.case_chart import build_case_chart
    # 丑在场 → 子丑合（见合满足）；无午 → 无冲破 blocker
    c = build_case_chart({"year": "丙子", "month": "丁丑", "day": "乙卯", "hour": "丙子"})
    m = next(x for x in c.advancedAnalysis["specialPattern"]["xushiOuter"]
             if "六乙鼠贵" in x["type"])
    texts = [s["text"] for s in m["supports"]]
    assert any("见合" in t for t in texts)
    assert any("交互得" in t for t in texts)  # 待核注记
    assert not any("无冲破」不满足" in b["text"] for b in m["blockers"])
    # 午在场 → 冲破 blocker
    c2 = build_case_chart({"year": "丙子", "month": "戊午", "day": "乙卯", "hour": "丙子"})
    m2 = next(x for x in c2.advancedAnalysis["specialPattern"]["xushiOuter"]
              if "六乙鼠贵" in x["type"])
    assert any("无冲破」不满足" in b["text"] for b in m2["blockers"])


def test_arch_unfill_multi_layer():
    """大运子填实 + 流年午冲子 → arch_unfill（去填说 vs 填实不破说）。"""
    from tianze.analysis.temporal import analyze_temporal
    ta = analyze_temporal(natal_stems=["癸", "己", "甲", "乙"],
                          natal_branches=["亥", "丑", "巳", "卯"],
                          day_master="癸", luck_stem="壬", luck_branch="子",
                          annual_stem="庚", annual_branch="午")
    kinds = [r.kind for r in ta.relations]
    assert "arch_fill" in kinds and "arch_unfill" in kinds
    ev = next(t for t in ta.ruleTriggers if t.ruleId == "TR-DTZ-10")
    assert any("去填" in o and "填实不破" in o for o in ev.observations)
    # 无填实时不得报 unfill
    ta2 = analyze_temporal(natal_stems=["癸", "己", "甲", "乙"],
                           natal_branches=["亥", "丑", "巳", "卯"],
                           day_master="癸", annual_stem="庚", annual_branch="午")
    assert not any(r.kind == "arch_unfill" for r in ta2.relations)


# ---------- M27 · 贵人表 / 外格状态词汇 / 缓存一致性 ----------

def test_tianyi_table_integrity():
    """SS-R17 起例完整性：每干两贵人、互异；歌诀抽样核对。"""
    from tianze.relation.tables import TIAN_YI_NOBLE
    assert set(TIAN_YI_NOBLE) == set("甲乙丙丁戊己庚辛壬癸")
    for stem, nobles in TIAN_YI_NOBLE.items():
        assert len(nobles) == 2 and "辰戌" not in "".join(nobles), stem  # 辰戌为天罗地纲贵人不临
    # 歌诀抽样：甲戊庚牛羊（丑未）、六辛逢马虎（午寅）、壬癸兔蛇藏（卯巳）
    assert TIAN_YI_NOBLE["甲"] == frozenset({"丑", "未"})
    assert TIAN_YI_NOBLE["辛"] == frozenset({"午", "寅"})
    assert TIAN_YI_NOBLE["壬"] == frozenset({"卯", "巳"})
    assert TIAN_YI_NOBLE["癸"] == frozenset({"巳", "卯"})


def test_fuzz_xushi_outer_status_vocabulary():
    """随机盘 xushiOuter：状态 ∈ CANDIDATE/BLOCKED/UNRESOLVED；井栏叉限庚日。"""
    import random
    from tianze.analysis.case_chart import build_case_chart
    rng = random.Random(2828)
    pool = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    for _ in range(120):
        pillars = {"year": rng.choice("甲乙丙丁戊己庚辛壬癸") + rng.choice(pool),
                   "month": rng.choice("甲乙丙丁戊己庚辛壬癸") + rng.choice(pool),
                   "day": rng.choice("甲乙丙丁戊己庚辛壬癸") + rng.choice(pool),
                   "hour": rng.choice("甲乙丙丁戊己庚辛壬癸") + rng.choice(pool)}
        try:
            chart = build_case_chart(pillars)
        except Exception:
            continue
        for x in chart.advancedAnalysis["specialPattern"]["xushiOuter"]:
            assert x["status"] in ("CANDIDATE", "BLOCKED", "UNRESOLVED")
            if "井栏叉" in x["type"]:
                assert chart.day_master.stem == "庚"


def test_temporal_cache_with_new_kinds():
    """缓存一致性：新增关系种类后同参数两次 analyze_temporal 结果逐字段一致。"""
    from tianze.analysis.temporal import analyze_temporal
    args = dict(natal_stems=["癸", "己", "甲", "乙"], natal_branches=["亥", "丑", "巳", "卯"],
                day_master="癸", luck_stem="壬", luck_branch="子",
                annual_stem="庚", annual_branch="午")
    a = [r.model_dump(by_alias=True) for r in analyze_temporal(**args).relations]
    b = [r.model_dump(by_alias=True) for r in analyze_temporal(**args).relations]
    assert a == b


# ---------- M28 · 旬空 / 根气分级 / 多层去填并存 ----------

def test_xun_kong_table():
    """六旬旬空表与 lunar-python 柱旬空一致性（抽样）。"""
    from tianze.relation.tables import xun_kong_of
    assert xun_kong_of("甲子") == frozenset({"戌", "亥"})
    assert xun_kong_of("甲戌") == frozenset({"申", "酉"})
    assert xun_kong_of("甲寅") == frozenset({"子", "丑"})
    assert xun_kong_of("癸亥") == frozenset({"子", "丑"})   # 甲寅旬末
    assert xun_kong_of("乙卯") == frozenset({"子", "丑"})   # 甲寅旬


def test_liuyi_shugui_kongwang_blocker():
    """SS-R16 第三要件空亡：贵人子落日柱旬空 → blocker；年柱两说注记。"""
    from tianze.analysis.case_chart import build_case_chart
    c = build_case_chart({"year": "丙子", "month": "戊子", "day": "乙卯", "hour": "丙子"})
    m = next(x for x in c.advancedAnalysis["specialPattern"]["xushiOuter"]
             if "六乙鼠贵" in x["type"])
    kong = [b for b in m["blockers"] if "空亡" in b["text"]]
    assert kong and "日柱旬空" in kong[0]["text"]
    # 乙亥日（甲戌旬，申酉空）→ 无空亡阻断
    c2 = build_case_chart({"year": "丙子", "month": "戊子", "day": "乙亥", "hour": "丙子"})
    m2 = next(x for x in c2.advancedAnalysis["specialPattern"]["xushiOuter"]
              if "六乙鼠贵" in x["type"])
    assert not [b for b in m2["blockers"] if "空亡" in b["text"]]


def test_root_grade_in_jiacong_evidence():
    """假从说证据带根气分级（强根/明根/微根），不改状态映射。"""
    from tianze.analysis.case_chart import build_case_chart
    c = build_case_chart({"year": "壬寅", "month": "丁未", "day": "己卯", "hour": "乙亥"})
    x = next(x for x in c.advancedAnalysis["specialPattern"]["cong"]
             if x["type"] == "从财")
    e2 = next(e for e in x["exceptions"] if e["ruleId"] == "SP-CG-E2")
    assert "强根（本气）" in e2["text"] and "有印比生助" in e2["text"]
    assert x["status"] == "DISPUTED"  # 状态映射不变（M26 锁定）


def test_arch_unfill_multi_layer_coexist():
    """多层同见填实字 + 冲 → unfill 证据带并存注记（单层冲不误报并存）。"""
    from tianze.analysis.temporal import analyze_temporal
    # 两层都见子（大运+流日），另一层午冲 → 去填与填实并存
    ta = analyze_temporal(natal_stems=["癸", "己", "甲", "乙"],
                          natal_branches=["亥", "丑", "巳", "卯"],
                          day_master="癸", luck_stem="壬", luck_branch="子",
                          annual_stem="庚", annual_branch="午",
                          daily_stem="壬", daily_branch="子")
    unfill = next(r for r in ta.relations if r.kind == "arch_unfill")
    assert "并存" in unfill.note or "两说" in unfill.note
    fills = [r for r in ta.relations if r.kind == "arch_fill"]
    assert len(fills) >= 1  # 大运子与流日子各产生 fill


# ---------- M29 · 旬空差分验证（独立表 vs lunar-python 上游） ----------

def test_xunkong_differential_against_lunar_python():
    """差分：随机日期盘 → 六旬表 xun_kong_of 与 lunar-python 柱 xunKong 逐一一致。"""
    import datetime as dt
    import random
    from tianze.pipeline import build_chart
    from tianze.domain.models import BirthInfo
    from tianze.relation.tables import xun_kong_of
    rng = random.Random(2929)
    mismatches = []
    for _ in range(300):
        d = dt.date(1900, 1, 1) + dt.timedelta(days=rng.randrange(0, 50000))
        t = dt.time(rng.randrange(0, 24), rng.randrange(0, 60))
        chart = build_chart(BirthInfo(date=d, time=t, gender="male"))
        for pos in ("year", "month", "day", "hour"):
            p = getattr(chart.pillars, pos)
            if not p:
                continue
            upstream = frozenset(p.xun_kong) if p.xun_kong else None
            mine = xun_kong_of(p.stem + p.branch)
            if upstream != mine:
                mismatches.append((pos, p.stem + p.branch, upstream, mine))
    assert not mismatches, mismatches[:5]
