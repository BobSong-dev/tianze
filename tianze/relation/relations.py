"""L4 关系扫描器：四柱（含缺时柱）内的合冲刑害破、三合三会。

口径：
- 全配对扫描但输出贴邻/隔柱标注（R3 位置语义）；多重关系并存全量输出（R9）。
- 合只报 transform_candidate，不判化气成立（R13）。
- 半三合必须含中神（R10）。
- 三刑全组优先，只在不全时报部分对（R9）。
"""

from __future__ import annotations

from typing import Sequence

from tianze.domain.models import Adjacency, Interaction, Position, RelationKind
from tianze.ganzhi.tables import BRANCHES, branch_index, stem_index
from tianze.relation import tables as T


def _first_index(items: Sequence[str | None], target: str) -> int:
    for i, item in enumerate(items):
        if item == target:
            return i
    raise AssertionError(f"{target} 不在序列中")  # pragma: no cover


def _pairs_of(items: Sequence[str | None], a: str, b: str) -> list[tuple[int, int]]:
    """a、b（可相同=自刑）在四柱中的全部无序位置对（i<j）。"""
    pairs: list[tuple[int, int]] = []
    idx_a = [i for i, x in enumerate(items) if x == a]
    idx_b = [j for j, x in enumerate(items) if x == b]
    if a == b:
        for p, i in enumerate(idx_a):
            for j in idx_a[p + 1:]:
                pairs.append((i, j))
    else:
        for i in idx_a:
            for j in idx_b:
                pairs.append((i, j) if i < j else (j, i))
    return sorted(set(pairs))


def _month_involved(positions: Sequence[Position], idxs: Sequence[int]) -> bool:
    return any(positions[i] == "month" for i in idxs)


def analyze_relations(
    stems: Sequence[str | None],
    branches: Sequence[str | None],
    positions: Sequence[Position],
) -> list[Interaction]:
    if not (len(stems) == len(branches) == len(positions)):
        raise ValueError("stems/branches/positions 长度不一致")
    out: list[Interaction] = []

    def append(rec: Interaction) -> None:
        out.append(rec)

    n = len(positions)
    # —— 成对扫描（干与支各自 C(n,2)）——
    for i in range(n):
        for j in range(i + 1, n):
            adjacency = Adjacency.ADJACENT if j - i == 1 else Adjacency.SEPARATED
            month_flag = _month_involved(positions, (i, j))
            s1, s2 = stems[i], stems[j]
            if s1 and s2:
                pair = T.FS({s1, s2})
                transform = T.STEM_COMBINATIONS.get(pair)
                if transform is not None:
                    a, b = sorted((s1, s2), key=stem_index)
                    append(Interaction(
                        kind=RelationKind.STEM_COMBINATION, label=f"{a}{b}合",
                        members=[a, b], positions=[positions[i], positions[j]],
                        adjacency=adjacency, month_involved=month_flag,
                        transform_candidate=transform, convention_id="R13",
                    ))
                if pair in T.STEM_OPPOSITIONS:
                    a, b = sorted((s1, s2), key=stem_index)
                    append(Interaction(
                        kind=RelationKind.STEM_OPPOSITION, label=f"{a}{b}冲",
                        members=[a, b], positions=[positions[i], positions[j]],
                        adjacency=adjacency, month_involved=month_flag, convention_id="R14",
                    ))
            b1, b2 = branches[i], branches[j]
            if b1 and b2:
                pair = T.FS({b1, b2})
                transform = T.SIX_COMBINATIONS.get(pair)
                if transform is not None:
                    a, b = sorted((b1, b2), key=branch_index)
                    note = "午未化气有土/火（日月）两说，默认土" if pair == T.FS({"午", "未"}) else None
                    append(Interaction(
                        kind=RelationKind.SIX_COMBINATION, label=f"{a}{b}合",
                        members=[a, b], positions=[positions[i], positions[j]],
                        adjacency=adjacency, month_involved=month_flag,
                        transform_candidate=transform, note=note, convention_id="R13",
                    ))
                if pair in T.SIX_CLASHES:
                    a, b = sorted((b1, b2), key=branch_index)
                    append(Interaction(
                        kind=RelationKind.CLASH, label=f"{a}{b}冲",
                        members=[a, b], positions=[positions[i], positions[j]],
                        adjacency=adjacency, month_involved=month_flag, convention_id="R9",
                    ))
                if pair in T.SIX_HARMS:
                    a, b = sorted((b1, b2), key=branch_index)
                    append(Interaction(
                        kind=RelationKind.HARM, label=f"{a}{b}害",
                        members=[a, b], positions=[positions[i], positions[j]],
                        adjacency=adjacency, month_involved=month_flag, convention_id="R9",
                    ))
                if pair in T.SIX_BREAKS:
                    a, b = sorted((b1, b2), key=branch_index)
                    append(Interaction(
                        kind=RelationKind.BREAK, label=f"{a}{b}破",
                        members=[a, b], positions=[positions[i], positions[j]],
                        adjacency=adjacency, month_involved=month_flag,
                        note="寅亥/巳申既合又破，两表并存不删（R9）" if pair in (T.FS({"寅", "亥"}), T.FS({"巳", "申"})) else None,
                        convention_id="R9",
                    ))

    present = {b for b in branches if b}

    # —— 三刑（全组优先，不全报部分对；R9）——
    for trio, name in T.PUNISHMENT_TRIOS.items():
        order = T.PUNISHMENT_TRIO_ORDER[trio]
        ps = [b for b in order if b in present]
        if len(ps) == 3:
            idxs = [_first_index(branches, b) for b in ps]
            note = "义理派与此组名称互换（分组一致），见 R9" if trio == T.FS({"寅", "巳", "申"}) else None
            append(Interaction(
                kind=RelationKind.PUNISHMENT_TRIO, label=f"{''.join(ps)}三刑·{name}",
                members=ps, positions=[positions[i] for i in idxs],
                month_involved=_month_involved(positions, idxs),
                sub_type=name, note=note, convention_id="R9",
            ))
        elif len(ps) == 2:
            for i, j in _pairs_of(branches, ps[0], ps[1]):
                append(Interaction(
                    kind=RelationKind.PUNISHMENT_PAIR, label=f"{ps[0]}{ps[1]}刑",
                    members=[ps[0], ps[1]], positions=[positions[i], positions[j]],
                    adjacency=Adjacency.ADJACENT if j - i == 1 else Adjacency.SEPARATED,
                    month_involved=_month_involved(positions, (i, j)),
                    sub_type=name, note="三刑部分对（不成全组）", convention_id="R9",
                ))

    if T.PUNISHMENT_ZIMAO <= present:
        for i, j in _pairs_of(branches, "子", "卯"):
            a, b = ("子", "卯")
            append(Interaction(
                kind=RelationKind.PUNISHMENT_ZIMAO, label=f"{a}{b}相刑·{T.ZIMAO_NAME}",
                members=[a, b], positions=[positions[i], positions[j]],
                adjacency=Adjacency.ADJACENT if j - i == 1 else Adjacency.SEPARATED,
                month_involved=_month_involved(positions, (i, j)),
                sub_type=T.ZIMAO_NAME, convention_id="R9",
            ))

    for b in sorted(present, key=branch_index):
        if b in T.SELF_PUNISHMENT:
            for i, j in _pairs_of(branches, b, b):
                append(Interaction(
                    kind=RelationKind.SELF_PUNISHMENT, label=f"{b}{b}自刑",
                    members=[b, b], positions=[positions[i], positions[j]],
                    adjacency=Adjacency.ADJACENT if j - i == 1 else Adjacency.SEPARATED,
                    month_involved=_month_involved(positions, (i, j)), convention_id="R9",
                ))

    # —— 三合 / 半合（R10）/ 三会 ——
    for trio, elem in T.THREE_HARMONIES.items():
        order = T.THREE_HARMONIES_ORDER[trio]
        ps = [b for b in order if b in present]
        if len(ps) == 3:
            idxs = [_first_index(branches, b) for b in ps]
            append(Interaction(
                kind=RelationKind.THREE_HARMONY, label=f"{''.join(ps)}三合（{elem.value}局）",
                members=ps, positions=[positions[i] for i in idxs],
                month_involved=_month_involved(positions, idxs),
                transform_candidate=elem, note="成局与否（力量/化气）留给分析层（R13）", convention_id="R10",
            ))
        elif len(ps) == 2 and (set(ps) & T.HARMONY_CENTERS):
            idxs = [_first_index(branches, b) for b in ps]
            append(Interaction(
                kind=RelationKind.THREE_HARMONY_HALF, label=f"{''.join(ps)}半合（{elem.value}）",
                members=ps, positions=[positions[i] for i in idxs],
                month_involved=_month_involved(positions, idxs),
                transform_candidate=elem, note="半合须含中神（R10），不判成败", convention_id="R10",
            ))

    for trio, (direction, elem) in T.THREE_MEETINGS.items():
        order = T.THREE_MEETINGS_ORDER[trio]
        ps = [b for b in order if b in present]
        if len(ps) == 3:
            idxs = [_first_index(branches, b) for b in ps]
            append(Interaction(
                kind=RelationKind.THREE_MEETING, label=f"{''.join(ps)}三会·{direction}",
                members=ps, positions=[positions[i] for i in idxs],
                month_involved=_month_involved(positions, idxs),
                transform_candidate=elem, convention_id="R9",
            ))

    return out
