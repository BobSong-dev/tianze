"""M15 · 从命例四柱构建分析上下文（case chart shim）。

用途：1147 命例只有四柱、没有完整出生时刻（无法走 pipeline 排盘）。
本模块用与 pipeline 完全相同的引擎函数（month_command/roots/strength/pattern/
tiaohou/special/element_counts）从四柱直接组装分析上下文，供 Case Replay 使用。

纪律：这是引擎复用，不是重新实现；缺时辰的口径与 R11 一致（hour=None）。
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from tianze.ganzhi import tables as G
from tianze.analysis import (collect_roots, compute_month_command, count_elements)
from tianze.relation.relations import analyze_relations
from tianze.analysis.strength import StrengthFacts, default_run
from tianze.analysis.pattern import analyze_pattern
from tianze.analysis.tiaohou import analyze_tiaohou
from tianze.analysis.special import analyze_all_special
from tianze.ganzhi.tables import ten_god

__all__ = ["build_case_chart"]


def _pillar(position: str, gz: str, day_master: str) -> SimpleNamespace:
    return SimpleNamespace(
        position=position, stem=gz[0], branch=gz[1],
        stem_element=G.STEM_ELEMENT[gz[0]],
        branch_element=G.BRANCH_ELEMENT[gz[1]],
    )


def build_case_chart(pillars: dict[str, str], gender: str | None = None) -> Any:
    """四柱 dict {"year": "甲子", ...} → 分析上下文（duck-typed chart）。

    只组装 compute_temporal_delta / compute_event_themes 实际消费的字段。
    """
    positions = ["year", "month", "day", "hour"]
    day_gz = pillars.get("day") or ""
    if not day_gz or len(day_gz) < 2 or not pillars.get("month"):
        raise ValueError("命例四柱不完整（缺日柱或月柱）")
    day_master = day_gz[0]

    stems: list[str | None] = []
    branches: list[str | None] = []
    pillar_ns: dict[str, Any] = {}
    for pos in positions:
        gz = pillars.get(pos)
        if gz and len(gz) >= 2:
            stems.append(gz[0])
            branches.append(gz[1])
        else:
            stems.append(None)
            branches.append(None)
        pillar_ns[pos] = _pillar(pos, gz, day_master) if gz else None
    month_branch = branches[1]
    if not day_master or not month_branch:
        raise ValueError("命例四柱不完整（缺日柱或月柱）")

    month_command = compute_month_command(month_branch, day_master, stems)
    roots = collect_roots(stems, branches, positions, day_master)
    element_counts = count_elements(stems, branches)
    dm_roots = tuple(r for r in roots if r.is_day_master)

    facts = StrengthFacts(
        day_master=day_master,
        day_master_element=G.STEM_ELEMENT[day_master],
        month_command=month_command,
        day_master_roots=dm_roots,
        other_stems=tuple((s, p) for s, p in zip(stems, positions) if s and p != "day"),
        pillar_units=tuple((p, s, b) for p, s, b in zip(positions, stems, branches)),
    )
    strength = default_run(facts)
    pattern = analyze_pattern(day_master, month_branch, stems, positions)
    tiaohou = analyze_tiaohou(day_master, month_branch,
                              {p: s for p, s in zip(positions, stems)})

    ec = {k: {"visible": v.visible, "hidden": v.hidden}
          for k, v in element_counts.elements.items()}
    from tianze.relation.tables import xun_kong_of
    advanced = analyze_all_special(
        day_master=day_master, month_branch=month_branch,
        stems=stems, branches=branches,
        day_xun_kong=xun_kong_of(day_gz),
        year_xun_kong=xun_kong_of(pillars.get("year") or ""),
        strength_verdicts={
            "dimension": strength.methods[0].verdict if len(strength.methods) > 0 else None,
            "weighted": strength.methods[1].verdict if len(strength.methods) > 1 else None,
            "fuyi": strength.methods[2].verdict if len(strength.methods) > 2 else None,
        },
        weighted_score=strength.methods[1].score if len(strength.methods) > 1 else None,
        day_master_roots=len(dm_roots),
        helper_stems=[s for s in stems if s and s != day_master and
                      ten_god(day_master, s).value in ("比肩", "劫财", "正印", "偏印")],
        element_counts=ec,
        day_master_roots_evidence=list(dm_roots),
    )

    # M24/M25：关系层（拱夹/暗合等）+ 未成立候选进命例研究——与 pipeline 同一函数
    relations = analyze_relations(stems, branches, positions, day_master=day_master)
    from tianze.relation.relations import analyze_blocked_arches
    blocked_relations = analyze_blocked_arches(stems, branches, positions, day_master=day_master)

    return SimpleNamespace(
        day_master=SimpleNamespace(stem=day_master),
        pillars=SimpleNamespace(**pillar_ns),
        birth=SimpleNamespace(gender=gender),
        month_command=month_command,
        roots=roots,
        strength=strength,
        pattern=pattern,
        tiaohou=tiaohou,
        element_counts=element_counts,
        advancedAnalysis=advanced,
        relations=relations,
        blocked_relations=blocked_relations,
    )
