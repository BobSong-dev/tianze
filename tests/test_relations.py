"""关系引擎测试（M2）：表完备性、守恒律、金测盘、反例。"""

from __future__ import annotations

from tianze.domain.models import Adjacency, RelationKind
from tianze.ganzhi.tables import BRANCHES, BRANCH_ELEMENT, YANG_CHANGSHENG_START, branch_index
from tianze.relation import tables as T
from tianze.relation.relations import analyze_relations

POS4 = ["year", "month", "day", "hour"]


def rels(branches: list[str | None], stems: list[str | None] | None = None):
    s = stems or ["甲", "乙", "丙", "丁"][: len(branches)]
    return analyze_relations(s, branches, POS4[: len(branches)])


def kind_members(rs):
    return sorted((r.kind.value, tuple(r.members)) for r in rs)


# ---------- 表完备性 ----------

def test_table_completeness():
    assert len(T.STEM_COMBINATIONS) == 5
    assert len(T.SIX_COMBINATIONS) == 6
    assert len(T.SIX_CLASHES) == 6
    assert len(T.SIX_HARMS) == 6
    assert len(T.SIX_BREAKS) == 6
    assert len(T.THREE_HARMONIES) == 4
    assert len(T.THREE_MEETINGS) == 4
    assert len(T.PUNISHMENT_TRIOS) == 2
    assert T.SELF_PUNISHMENT == frozenset({"辰", "午", "酉", "亥"})
    # 经典重合项不许删（atlas 教训）：寅亥、巳申既六合又相破
    assert T.FS({"寅", "亥"}) in T.SIX_COMBINATIONS and T.FS({"寅", "亥"}) in T.SIX_BREAKS
    assert T.FS({"巳", "申"}) in T.SIX_COMBINATIONS and T.FS({"巳", "申"}) in T.SIX_BREAKS


def test_pair_tables_symmetric():
    all_pairs = [frozenset({a, b}) for i, a in enumerate(BRANCHES) for b in BRANCHES[i + 1:]]
    for pair in all_pairs:
        for table in (T.SIX_CLASHES, T.SIX_HARMS, T.SIX_BREAKS):
            assert (pair in table) == (frozenset(reversed(sorted(pair))) in table)


def test_three_harmony_conservation_law():
    """三合局 = 阳干长生/帝旺/墓（结构互证，不抄第二遍真值）。"""
    yang_of = {"WATER": "壬", "WOOD": "甲", "FIRE": "丙", "METAL": "庚"}
    for trio, elem in T.THREE_HARMONIES.items():
        start = branch_index(YANG_CHANGSHENG_START[yang_of[elem.value]])
        expected = {BRANCHES[start], BRANCHES[(start + 4) % 12], BRANCHES[(start + 8) % 12]}
        assert set(trio) == expected, f"{trio} 与 {elem.value} 之阳干长生帝旺墓不符"
        # 中神（帝旺）必在 HARMONY_CENTERS
        assert BRANCHES[(start + 4) % 12] in T.HARMONY_CENTERS


def test_meeting_elements_match_seasons():
    assert T.THREE_MEETINGS[frozenset({"寅", "卯", "辰"})][1].value == "WOOD"
    assert T.THREE_MEETINGS[frozenset({"亥", "子", "丑"})][1].value == "WATER"
    # 守恒：每组三会中非土成员恰两支且五行等于会方五行；库支（土）恰一支
    for trio, (_dir_name, elem) in T.THREE_MEETINGS.items():
        same = [b for b in trio if BRANCH_ELEMENT[b] == elem]
        earth = [b for b in trio if BRANCH_ELEMENT[b].value == "EARTH"]
        assert len(same) == 2 and len(earth) == 1


# ---------- 金测盘 ----------

def test_dense_zi_chou_wu_wei():
    rs = rels(["子", "丑", "午", "未"])
    assert kind_members(rs) == sorted([
        (RelationKind.SIX_COMBINATION.value, ("子", "丑")),
        (RelationKind.SIX_COMBINATION.value, ("午", "未")),
        (RelationKind.CLASH.value, ("子", "午")),
        (RelationKind.CLASH.value, ("丑", "未")),
        (RelationKind.PUNISHMENT_PAIR.value, ("丑", "未")),  # 丑戌未三刑部分对（戌缺）
        (RelationKind.HARM.value, ("子", "未")),
        (RelationKind.HARM.value, ("丑", "午")),
    ])
    pair = next(r for r in rs if r.kind == RelationKind.PUNISHMENT_PAIR)
    assert pair.sub_type == "恃势之刑"
    by_key = {(r.members[0], r.kind): r for r in rs}
    assert by_key[("子", RelationKind.SIX_COMBINATION)].adjacency == Adjacency.ADJACENT      # 年-月
    assert by_key[("午", RelationKind.SIX_COMBINATION)].adjacency == Adjacency.ADJACENT      # 日-时
    assert by_key[("子", RelationKind.CLASH)].adjacency == Adjacency.SEPARATED               # 年-日
    assert by_key[("丑", RelationKind.CLASH)].adjacency == Adjacency.SEPARATED               # 月-时
    assert by_key[("子", RelationKind.HARM)].adjacency == Adjacency.SEPARATED                # 年-时
    assert by_key[("丑", RelationKind.HARM)].adjacency == Adjacency.ADJACENT                 # 月-日
    # 月令参与
    assert by_key[("子", RelationKind.SIX_COMBINATION)].month_involved is True
    assert by_key[("丑", RelationKind.CLASH)].month_involved is True
    assert by_key[("子", RelationKind.HARM)].month_involved is False


def test_yin_si_shen_full_trio_suppresses_pairs():
    rs = rels(["巳", "申", "寅", "子"])
    kinds = kind_members(rs)
    assert (RelationKind.PUNISHMENT_TRIO.value, ("寅", "巳", "申")) in kinds
    assert all(k != RelationKind.PUNISHMENT_PAIR.value for k, _ in kinds), "全组存在时不得再报部分对"
    assert (RelationKind.SIX_COMBINATION.value, ("巳", "申")) in kinds   # 合
    assert (RelationKind.BREAK.value, ("巳", "申")) in kinds             # 破
    assert (RelationKind.CLASH.value, ("寅", "申")) in kinds             # 冲
    assert (RelationKind.THREE_HARMONY_HALF.value, ("申", "子")) in kinds  # 半合（含中神子，传统序）
    trio = next(r for r in rs if r.kind == RelationKind.PUNISHMENT_TRIO)
    assert trio.sub_type == "无恩之刑" and trio.note  # R9 命名分歧注记


def test_partial_punishment_pair_when_trio_incomplete():
    rs = rels(["寅", "巳", "午", "酉"])
    pairs = [r for r in rs if r.kind == RelationKind.PUNISHMENT_PAIR]
    assert len(pairs) == 1
    assert pairs[0].members == ["寅", "巳"] and pairs[0].sub_type == "无恩之刑"


def test_zimao_punishment():
    rs = rels(["子", "卯", "午", "子"])
    zm = [r for r in rs if r.kind == RelationKind.PUNISHMENT_ZIMAO]
    assert len(zm) == 2  # 年-月 与 时-月 两处子卯
    assert all(r.sub_type == "无礼之刑" for r in zm)


def test_self_punishment_requires_duplicate():
    assert not [r for r in rels(["辰", "酉", "戌", "丑"]) if r.kind == RelationKind.SELF_PUNISHMENT]
    rs = rels(["辰", "酉", "戌", "辰"])
    self_ps = [r for r in rs if r.kind == RelationKind.SELF_PUNISHMENT]
    assert len(self_ps) == 1
    assert self_ps[0].members == ["辰", "辰"]
    assert self_ps[0].positions == ["year", "hour"]
    assert self_ps[0].adjacency == Adjacency.SEPARATED
    # 同时存在 辰酉合 / 辰戌冲 / 酉戌害（多重关系并存）
    kinds = kind_members(rs)
    assert (RelationKind.SIX_COMBINATION.value, ("辰", "酉")) in kinds
    assert (RelationKind.CLASH.value, ("辰", "戌")) in kinds
    assert (RelationKind.HARM.value, ("酉", "戌")) in kinds


def test_half_harmony_requires_center():
    # 申子（含中神子）→ 半合
    assert (RelationKind.THREE_HARMONY_HALF.value, ("申", "子")) in kind_members(rels(["申", "子", "午", "卯"]))
    # 申辰（无中神）→ 不报（R10；拱 V1 不实现）
    rs = rels(["申", "辰", "午", "未"])
    assert not [r for r in rs if r.kind == RelationKind.THREE_HARMONY_HALF]
    # 午戌（含中神午）→ 半合火
    assert (RelationKind.THREE_HARMONY_HALF.value, ("午", "戌")) in kind_members(rels(["午", "戌", "子", "丑"]))


def test_full_harmony_beats_half():
    rs = rels(["申", "子", "辰", "午"])
    assert (RelationKind.THREE_HARMONY.value, ("申", "子", "辰")) in kind_members(rs)
    assert not [r for r in rs if r.kind == RelationKind.THREE_HARMONY_HALF]
    full = next(r for r in rs if r.kind == RelationKind.THREE_HARMONY)
    assert full.label == "申子辰三合（WATER局）"  # 传统序（长生-中神-墓），非支序


def test_three_meeting():
    rs = rels(["寅", "卯", "辰", "午"])
    meetings = [r for r in rs if r.kind == RelationKind.THREE_MEETING]
    assert len(meetings) == 1
    assert meetings[0].label == "寅卯辰三会·东方木"
    assert meetings[0].transform_candidate.value == "WOOD"
    assert meetings[0].month_involved is True


def test_stem_combination_and_opposition():
    rs = analyze_relations(["甲", "己", "庚", "乙"], ["子", "丑", "午", "未"], POS4)
    kinds = {(r.kind, tuple(r.members)) for r in rs}
    assert (RelationKind.STEM_COMBINATION, ("甲", "己")) in kinds
    assert (RelationKind.STEM_COMBINATION, ("乙", "庚")) in kinds
    combo = next(r for r in rs if r.members == ["甲", "己"])
    assert combo.transform_candidate.value == "EARTH"
    assert combo.adjacency == Adjacency.ADJACENT and combo.convention_id == "R13"

    # 隔柱五合也检出，但标注 SEPARATED（全配对 + 位置标注，不裁决是否能化）
    rs2 = analyze_relations(["甲", "庚", "己", "乙"], ["子", "丑", "午", "未"], POS4)
    combos = {tuple(r.members): r for r in rs2 if r.kind == RelationKind.STEM_COMBINATION}
    assert set(combos) == {("甲", "己"), ("乙", "庚")}
    assert combos[("甲", "己")].adjacency == Adjacency.SEPARATED  # 年-日（隔日柱）
    assert combos[("乙", "庚")].adjacency == Adjacency.SEPARATED  # 月-时（隔日柱）
    opp = [r for r in rs2 if r.kind == RelationKind.STEM_OPPOSITION]
    assert len(opp) == 1 and opp[0].members == ["甲", "庚"] and opp[0].convention_id == "R14"


def test_transform_candidate_only_no_verdict():
    """R13：合只给候选，不判成化。"""
    for r in rels(["子", "丑", "午", "未"]):
        if r.kind in (RelationKind.SIX_COMBINATION, RelationKind.THREE_HARMONY, RelationKind.THREE_HARMONY_HALF):
            assert r.transform_candidate is not None
            assert "化" not in r.label  # 标签不含"化"字断言（jiwenxu 反例测试模式）


def test_order_independence():
    """反例守卫：柱位反序不漏检（OBE 刑漏检 bug 的守卫）。"""
    a = kind_members(rels(["巳", "申", "寅", "子"]))
    b = kind_members(rels(["子", "寅", "申", "巳"]))
    assert a == b
    c = kind_members(rels(["寅", "巳", "申", "子"]))
    assert a == c


def test_three_branches_when_hour_unknown():
    """未知时辰：只在三柱内扫描（R11）。"""
    rs = analyze_relations(["甲", "乙", "丙"], ["子", "丑", "午"], ["year", "month", "day"])
    kinds = kind_members(rs)
    assert (RelationKind.SIX_COMBINATION.value, ("子", "丑")) in kinds
    assert (RelationKind.CLASH.value, ("子", "午")) in kinds
