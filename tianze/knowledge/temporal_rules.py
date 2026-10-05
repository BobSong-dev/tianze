"""M13 · 岁运知识规则：ExecutableRule(domain=temporal) → TemporalEvidence。

知识链路（与 M6/M8 相同纪律）：
    Source → Quote → RuleCandidate(normalized/*) → ExecutableRule(domain=temporal)
           → evaluate_temporal_rules() → TemporalEvidence

Provenance 纪律：
- 有原文引文链（normalized candidates 的 originalQuotes）→ CLASSICAL_EXPLICIT
- 概念为传统命理通说、但 Tianze 知识库暂无引文链 → PROJECT_REFERENCE（如实注明）
- 检测口径本身是工程约定（阈值/位置判定）→ ENGINEERING_HEURISTIC
- 规则效果只输出结构观察（matched/观察项），绝不输出吉凶断语
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

from tianze.ganzhi.tables import STEMS, BRANCHES, STEM_ELEMENT, ten_god, YANG_STEM_REN, STEM_LU
from tianze.analysis.temporal import (
    TemporalContext, TemporalRelation, TemporalStructure, TemporalEvidence,
)
from tianze.knowledge.models import ProvenanceRef

__all__ = [
    "TemporalEvidence", "load_temporal_rules", "evaluate_temporal_rules",
    "TEMPORAL_RULES_PATH",
]

TEMPORAL_RULES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "knowledge", "rules", "temporal", "rules.json",
)

# 继善篇救应之法（SS-R09 原文引文内的确定性映射）：键=克者（攻击方，日犯岁君中即日主）→ 制克者之救神
_RESCUE_MAP: dict[str, set[str]] = {
    "庚": {"丙", "丁"}, "辛": {"丙", "丁"},     # 庚辛来伤甲乙，丙丁先见无危
    "丙": {"壬", "癸"}, "丁": {"壬", "癸"},     # 丙丁反克庚辛，壬癸遇之不畏
    "甲": {"庚", "辛"}, "乙": {"庚", "辛"},     # 戊己愁逢甲乙，干头须要庚辛
    "戊": {"甲", "乙"}, "己": {"甲", "乙"},     # 壬癸虑遭戊己，甲乙临之有救
    "壬": {"戊"}, "癸": {"己"},                 # 壬来克丙须要戊字当头；癸去伤丁却得己来相助
}

# 三刑（DTZ-09）：寅巳申为剧、丑戌未相刑、子卯相刑
_SAN_XING: tuple[frozenset[str], ...] = (
    frozenset({"寅", "巳", "申"}),
    frozenset({"丑", "戌", "未"}),
    frozenset({"子", "卯"}),
)

# 墓库四支（DTZ-35 杂气）
_MU_KU = {"辰", "戌", "丑", "未"}


@lru_cache(maxsize=1)
def load_temporal_rules() -> list[dict]:
    if not os.path.exists(TEMPORAL_RULES_PATH):
        return []
    payload = json.load(open(TEMPORAL_RULES_PATH, encoding="utf-8"))
    return payload["rules"]


def _gz_index(gz: str) -> int | None:
    if len(gz) != 2 or gz[0] not in STEMS or gz[1] not in BRANCHES:
        return None
    si, bi = STEMS.index(gz[0]), BRANCHES.index(gz[1])
    if (si % 2) != (bi % 2):
        return None
    for i in range(60):
        if STEMS[i % 10] == gz[0] and BRANCHES[i % 12] == gz[1]:
            return i
    return None


def _stem_ke(a: str, b: str) -> bool:
    """a 克 b（五行相克，不考虑阴阳）。"""
    from tianze.ganzhi.tables import Element
    ke = {Element.WOOD: Element.EARTH, Element.EARTH: Element.WATER,
          Element.WATER: Element.FIRE, Element.FIRE: Element.METAL,
          Element.METAL: Element.WOOD}
    ea, eb = STEM_ELEMENT.get(a), STEM_ELEMENT.get(b)
    return ea is not None and eb is not None and ke[ea] == eb


def _branch_chong(a: str, b: str) -> bool:
    if a not in BRANCHES or b not in BRANCHES:
        return False
    return (BRANCHES.index(a) - BRANCHES.index(b)) % 6 == 0


def _day_master_clash_branch(dm: str) -> str | None:
    """阳日主的阳刃支（阴日主用临官，此处按 SS-R10 刃头财口径只取阳刃）。"""
    return YANG_STEM_REN.get(dm)


def _day_master_lu_branch(dm: str) -> str | None:
    return STEM_LU.get(dm)


def _evaluate_tr_ss_r09(ctx: TemporalContext,
                        relations: list[TemporalRelation],
                        structures: list[TemporalStructure]) -> tuple[bool, list[str]]:
    """日犯岁君（SS-R09）：日主克流年天干（岁君干头为财），检查救应。

    继善篇救应法语义：克者伤受者，救神制克者——日犯岁君中日主是克者，
    故救应之神 = 制日主之干（如甲日主犯岁君，救神为庚辛）。
    """
    if not ctx.annual_stem or ctx.day_master not in STEMS:
        return False, []
    a_stem = ctx.annual_stem
    if not _stem_ke(ctx.day_master, a_stem):
        return False, []
    obs = [f"流年天干{a_stem}被日主{ctx.day_master}所克：日犯岁君结构（岁君干头为日主之财）"]
    rescuers = _RESCUE_MAP.get(ctx.day_master, set())
    natal_rescue = [s for s in ctx.natal_stems if s and s != ctx.day_master and s in rescuers]
    luck_rescue = [s for s in [ctx.luck_stem] if s and s in rescuers]
    if natal_rescue or luck_rescue:
        where = "原局" if natal_rescue else ""
        if luck_rescue:
            where = (where + "大运").strip()
        obs.append(f"救应之神（继善篇救应法：制{ctx.day_master}者{'、'.join(sorted(rescuers))}）："
                   f"{'、'.join(natal_rescue + luck_rescue)} 已见（{where}）")
    else:
        obs.append(f"救应之神（{'、'.join(sorted(rescuers))}，制日主{ctx.day_master}）原局与大运均未见")
    return True, obs


def _evaluate_tr_ss_r10a(ctx: TemporalContext,
                         relations: list[TemporalRelation],
                         structures: list[TemporalStructure]) -> tuple[bool, list[str]]:
    """刃头财（SS-R10）：流年支为日主阳刃、流年干为日主之财。"""
    ren = _day_master_clash_branch(ctx.day_master)
    if not ctx.annual_stem or not ctx.annual_branch or not ren:
        return False, []
    if ctx.annual_branch != ren:
        return False, []
    god = ten_god(ctx.day_master, ctx.annual_stem)
    if god.value not in ("正财", "偏财"):
        return False, []
    return True, [f"流年{ctx.annual_stem}{ctx.annual_branch}：支逢阳刃{ren}、干见{god.value}{ctx.annual_stem}"
                  f"——刃头财结构（销镕煞）"]


def _evaluate_tr_ss_r10b(ctx: TemporalContext,
                         relations: list[TemporalRelation],
                         structures: list[TemporalStructure]) -> tuple[bool, list[str]]:
    """禄头财（SS-R10）：流年支为日主临官禄位、流年干为日主之财。"""
    lu = _day_master_lu_branch(ctx.day_master)
    if not ctx.annual_stem or not ctx.annual_branch or not lu:
        return False, []
    if ctx.annual_branch != lu:
        return False, []
    god = ten_god(ctx.day_master, ctx.annual_stem)
    if god.value not in ("正财", "偏财"):
        return False, []
    return True, [f"流年{ctx.annual_stem}{ctx.annual_branch}：支逢禄位{lu}、干见{god.value}{ctx.annual_stem}"
                  f"——禄头财结构（捆缛煞）"]


def _evaluate_tr_dtz_35(ctx: TemporalContext,
                        relations: list[TemporalRelation],
                        structures: list[TemporalStructure]) -> tuple[bool, list[str]]:
    """杂气财官须运程引出（DTZ-35）：月支墓库 + 岁运支与之会合 → 引出候选观察。"""
    mb = ctx.month_branch()
    if mb not in _MU_KU:
        return False, []
    obs: list[str] = []
    matched = False
    for rel in relations:
        if rel.kind in ("three_harmony_completed", "six_combination") \
                and ctx.month_branch() in rel.members and rel.is_new:
            matched = True
            obs.append(f"月支{mb}为墓库；岁运{'补齐三合' if rel.kind == 'three_harmony_completed' else '六合'}"
                       f"（{'、'.join(rel.members)}）构成引出候选（DTZ-35：见运程引出方为真正杂气财官）")
    return matched, obs


def _evaluate_tr_dtz_09(ctx: TemporalContext,
                        relations: list[TemporalRelation],
                        structures: list[TemporalStructure]) -> tuple[bool, list[str]]:
    """支神以冲为重（DTZ-09）：岁运支冲月令提纲 / 三刑全备观察。"""
    obs: list[str] = []
    mb = ctx.month_branch()
    temporal_branches = [(label, b) for label, _s, b in ctx.temporal_units() if b]
    for label, b in temporal_branches:
        if mb and _branch_chong(b, mb):
            obs.append(f"岁运{_CN_LAYER[label]}支{b}冲月令提纲{mb}（支神只以冲为重）")
    branches = [b for b in ctx.natal_branches if b] + [b for _l, b in temporal_branches]
    for trio in _SAN_XING:
        if trio.issubset(set(branches)):
            missing_here = trio.issubset({b for b in ctx.natal_branches if b})
            if not missing_here:
                obs.append(f"{''.join(sorted(trio))}三刑因岁运而全备（寅巳申为剧）"
                           if trio == frozenset({"寅", "巳", "申"}) else
                           f"{''.join(sorted(trio))}三刑因岁运而全备")
    return bool(obs), obs


def _evaluate_tr_fuyin(ctx: TemporalContext,
                       relations: list[TemporalRelation],
                       structures: list[TemporalStructure]) -> tuple[bool, list[str]]:
    """伏吟（PROJECT_REFERENCE）：岁运柱与原局柱完全相同（大运 fuyin / 流年 identical）。"""
    obs = [f"{s.label}（{s.description}）" for s in structures
           if s.type in ("fuyin", "identical")]
    return bool(obs), obs


def _evaluate_tr_fanyin(ctx: TemporalContext,
                        relations: list[TemporalRelation],
                        structures: list[TemporalStructure]) -> tuple[bool, list[str]]:
    """反吟（PROJECT_REFERENCE）：岁运柱与原局柱天克地冲（检测口径：支冲）。"""
    obs = [f"{s.label}（{s.description}）" for s in structures if s.type == "fanyin"]
    return bool(obs), obs


def _evaluate_tr_binglin(ctx: TemporalContext,
                         relations: list[TemporalRelation],
                         structures: list[TemporalStructure]) -> tuple[bool, list[str]]:
    """岁运并临（PROJECT_REFERENCE）：大运与流年干支完全相同。"""
    obs = [f"{s.label}（{s.description}）" for s in structures if s.type == "binglin"]
    return bool(obs), obs


def _evaluate_tr_tiankedi(ctx: TemporalContext,
                          relations: list[TemporalRelation],
                          structures: list[TemporalStructure]) -> tuple[bool, list[str]]:
    """天克地冲（PROJECT_REFERENCE）：流年天克大运天干 + 流年支冲大运支。"""
    obs = [f"{s.label}（{s.description}）" for s in structures if s.type == "tiankedi"]
    return bool(obs), obs


def _evaluate_tr_spzy_28(ctx: TemporalContext,
                         relations: list[TemporalRelation],
                         structures: list[TemporalStructure]) -> tuple[bool, list[str]]:
    """流年即太岁（SPZY-28，PROJECT_REFERENCE）：术语框架观察。"""
    if not ctx.annual_stem:
        return False, []
    return True, [f"流年{ctx.annual_stem}{ctx.annual_branch or ''}即本年太岁"
                  "（SPZY-28：太岁为一岁之尊神，八字神煞从当生太岁出、一年神煞从游行太岁出；"
                  "Tianze 仅记录该术语框架，不做神煞吉凶推断）"]


_EVALUATORS = {
    "TR-SS-R09": _evaluate_tr_ss_r09,
    "TR-SS-R10A": _evaluate_tr_ss_r10a,
    "TR-SS-R10B": _evaluate_tr_ss_r10b,
    "TR-DTZ-35": _evaluate_tr_dtz_35,
    "TR-DTZ-09": _evaluate_tr_dtz_09,
    "TR-FUYIN-01": _evaluate_tr_fuyin,
    "TR-FANYIN-01": _evaluate_tr_fanyin,
    "TR-BINGLIN-01": _evaluate_tr_binglin,
    "TR-TIANKEDI-01": _evaluate_tr_tiankedi,
    "TR-SPZY-28": _evaluate_tr_spzy_28,
}

_CN_LAYER = {"luck": "大运", "annual": "流年", "monthly": "流月", "daily": "流日"}


def evaluate_temporal_rules(ctx: TemporalContext,
                            relations: list[TemporalRelation],
                            structures: list[TemporalStructure]) -> list[TemporalEvidence]:
    """对 TemporalContext 执行全部岁运规则 → TemporalEvidence 列表。

    每条 JSON 规则必须有对应 evaluator（缺失即抛错，不静默跳过）。
    未触发的规则 matched=False 保留（可审计哪些规则参与过判定）。
    """
    rules = load_temporal_rules()
    evidence: list[TemporalEvidence] = []
    for r in rules:
        rid = r["id"]
        fn = _EVALUATORS.get(rid)
        if fn is None:
            raise KeyError(f"岁运规则 {rid} 缺少执行器（engine 不得静默跳过规则）")
        matched, obs = fn(ctx, relations, structures)
        evidence.append(TemporalEvidence(
            ruleId=rid,
            category=r.get("category", "generic"),
            label=r.get("label", rid),
            matched=matched,
            observations=obs,
            provenance=[p.model_dump(by_alias=True) for p in (ProvenanceRef(**p) for p in r.get("provenance", []))],
            refId=f"temporal:rule:{rid}",
        ))
    return evidence
