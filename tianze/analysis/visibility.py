"""M3.2 透干引擎（R18）。

事实定义：地支藏干 X "透出" ⟺ 同字之干出现在任一天干位置。
只记录事实（位置、来源、距离、月令/日主相关性），不判断"透出好不好"。
`day_master_related` = 藏干字即日主（月令藏日主是建禄/得令类判定的关键事实）；
透出位置是否日干由 `position == "day"` 表达。
"""

from __future__ import annotations

from typing import Sequence

from tianze.domain.models import Position, StemVisibility
from tianze.ganzhi.tables import HIDDEN_STEMS

_POS_CN = {"year": "年", "month": "月", "day": "日", "hour": "时"}


def analyze_visibility(
    stems: Sequence[str | None],
    branches: Sequence[str | None],
    positions: Sequence[Position],
    day_master: str,
) -> list[StemVisibility]:
    if not (len(stems) == len(branches) == len(positions)):
        raise ValueError("stems/branches/positions 长度不一致")
    out: list[StemVisibility] = []
    for i, branch in enumerate(branches):
        if not branch:
            continue
        for hidden, role in HIDDEN_STEMS[branch]:
            for j, stem in enumerate(stems):
                if not stem or stem != hidden:
                    continue
                out.append(StemVisibility(
                    hidden_stem=hidden,
                    visible_stem=stem,
                    position=positions[j],
                    source_branch=branch,
                    source_role=role,
                    source_position=positions[i],
                    distance=abs(j - i),
                    month_related=positions[i] == "month",
                    day_master_related=hidden == day_master,
                    statement=(
                        f"{branch}（{_POS_CN[positions[i]]}支）藏{hidden}（{role}）"
                        f"透出于{_POS_CN[positions[j]]}干{stem}（距离 {abs(j - i)}）"
                        + ("，月令透干" if positions[i] == "month" else "")
                        + ("，藏干即日主" if hidden == day_master else "")
                    ),
                ))
    return out
