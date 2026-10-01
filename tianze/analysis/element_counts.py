"""M3.4 五行基础统计（R16）。

两个**独立视图**，不加权、不给分：
- visible（显性）：4 天干 + 4 地支主气（8 个字）；
- hidden（潜在）：全部地支藏干（含本气——与 visible 的支主气有意重叠，两视图各自成立）。
missing = 两视图皆 0 的五行。key 用小写五行名（wood/fire/earth/metal/water）。
"""

from __future__ import annotations

from typing import Sequence

from tianze.domain.models import ElementCounts, ElementCountView
from tianze.ganzhi.tables import BRANCH_ELEMENT, HIDDEN_STEMS, STEM_ELEMENT, Element


def _key(elem: Element) -> str:
    return elem.value.lower()


def _zero() -> dict[str, int]:
    return {e.value.lower(): 0 for e in Element}


def count_elements(
    stems: Sequence[str | None],
    branches: Sequence[str | None],
) -> ElementCounts:
    if len(stems) != len(branches):
        raise ValueError("stems/branches 长度不一致")

    stems_view = _zero()
    branches_view = _zero()
    hidden_view = _zero()

    for s in stems:
        if s:
            stems_view[_key(STEM_ELEMENT[s])] += 1
    for b in branches:
        if b:
            branches_view[_key(BRANCH_ELEMENT[b])] += 1
            for hidden, _role in HIDDEN_STEMS[b]:
                hidden_view[_key(STEM_ELEMENT[hidden])] += 1

    elements = {
        key: ElementCountView(
            visible=stems_view[key] + branches_view[key],
            hidden=hidden_view[key],
        )
        for key in _zero()
    }
    missing = [key for key, view in elements.items() if view.visible == 0 and view.hidden == 0]

    return ElementCounts(
        elements=elements,
        stems=stems_view,
        branches=branches_view,
        hidden_stems=hidden_view,
        missing=missing,
    )
