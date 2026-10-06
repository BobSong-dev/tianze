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
import random
import subprocess
import sys

import pytest

from tianze.analysis.event_themes import EventStatus, compute_event_themes
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

N_RANDOM = 60


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
        "from tianze.pipeline import build_chart
from tianze.sdk import AnalysisOptions;"
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
