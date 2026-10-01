"""M3.1 通根引擎（R15）。

事实定义：天干 X 通根于地支 B ⟺ B 的藏干表中含同字之干。
只回答"有没有根、什么类型的根"，不引入任何旺衰权重；
本气/中气/余气 → strong/medium/weak 仅为**定性深度**映射（R15）。
"""

from __future__ import annotations

from typing import Sequence

from tianze.domain.models import HiddenStemRole, Position, RootDepth, RootEvidence
from tianze.ganzhi.tables import HIDDEN_STEMS, stem_index

_DEPTH_BY_ROLE: dict[HiddenStemRole, RootDepth] = {
    HiddenStemRole.BEN: RootDepth.STRONG,
    HiddenStemRole.ZHONG: RootDepth.MEDIUM,
    HiddenStemRole.YU: RootDepth.WEAK,
}

_POS_CN = {"year": "年", "month": "月", "day": "日", "hour": "时"}


def collect_roots(
    stems: Sequence[str | None],
    branches: Sequence[str | None],
    positions: Sequence[Position],
    day_master: str,
) -> list[RootEvidence]:
    """对给定天干集合（去重，通常是命局四干）逐一在各支藏干中找根。

    `branches`/`positions` 位置对齐；`stems` 是查询集合，长度不必与支数一致。
    未知时辰的 None 自动跳过。
    """
    if len(branches) != len(positions):
        raise ValueError("branches/positions 长度不一致")
    present_stems = sorted({s for s in stems if s}, key=stem_index)
    out: list[RootEvidence] = []
    for stem in present_stems:
        for i, branch in enumerate(branches):
            if not branch:
                continue
            for hidden, role in HIDDEN_STEMS[branch]:
                if hidden != stem:
                    continue
                out.append(RootEvidence(
                    stem=stem,
                    branch=branch,
                    hidden_stem=hidden,
                    root_type=role,
                    depth=_DEPTH_BY_ROLE[role],
                    position=positions[i],
                    is_month_root=positions[i] == "month",
                    is_day_master=stem == day_master,
                    statement=(
                        f"{stem}通根于{_POS_CN[positions[i]]}支{branch}（{role}）"
                        + ("，月令通根" if positions[i] == "month" else "")
                    ),
                ))
    return out


def day_master_roots(roots: Sequence[RootEvidence]) -> list[RootEvidence]:
    """日主的根（含日支坐根）。"""
    return [r for r in roots if r.is_day_master]
