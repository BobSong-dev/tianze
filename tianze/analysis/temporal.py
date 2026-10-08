"""M12 · 大运/流年确定性结构分析。

设计原则：
- 复用现有 Tianze Engine（关系/旺衰/格局/调候/特殊格局），不重写算法
- 每个事实标记来源位置（natal / luck / annual）
- 只输出结构变化（TemporalDelta），不做吉凶事件预测
- 月令保持原局事实，不允许被岁运替代
- 分析适用性标记：SUPPORTED / EXPERIMENTAL / UNSUPPORTED
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Sequence

from tianze.domain.models import CamelizeModel
from pydantic import BaseModel, ConfigDict

__all__ = [
    "TemporalSource", "TemporalContext", "TemporalRelation",
    "TemporalStructure", "TemporalDelta", "TemporalAnalysis",
    "TemporalEvidence", "AnalysisSupport", "analyze_temporal",
]


class TemporalSource(str, Enum):
    NATAL = "natal"
    LUCK = "luck"
    ANNUAL = "annual"
    MONTHLY = "monthly"
    DAILY = "daily"


class AnalysisSupport(str, Enum):
    SUPPORTED = "SUPPORTED"
    EXPERIMENTAL = "EXPERIMENTAL"
    UNSUPPORTED = "UNSUPPORTED"


class TemporalContext(CamelizeModel):
    """岁运合并后的扩展上下文。"""
    natal_stems: list[str | None] = []
    natal_branches: list[str | None] = []
    luck_stem: str | None = None
    luck_branch: str | None = None
    annual_stem: str | None = None
    annual_branch: str | None = None
    monthly_stem: str | None = None   # 流月干（M13）
    monthly_branch: str | None = None
    daily_stem: str | None = None     # 流日干（M13）
    daily_branch: str | None = None
    luck_index: int | None = None
    annual_year: int | None = None
    day_master: str = ""

    def all_stems(self) -> list[tuple[str, TemporalSource]]:
        """返回 (干, 来源) 序列：原局四干 + 岁运干。"""
        out = [(s, TemporalSource.NATAL) for s in self.natal_stems if s]
        if self.luck_stem:
            out.append((self.luck_stem, TemporalSource.LUCK))
        if self.annual_stem:
            out.append((self.annual_stem, TemporalSource.ANNUAL))
        if self.monthly_stem:
            out.append((self.monthly_stem, TemporalSource.MONTHLY))
        if self.daily_stem:
            out.append((self.daily_stem, TemporalSource.DAILY))
        return out

    def all_branches(self) -> list[tuple[str, TemporalSource]]:
        out = [(b, TemporalSource.NATAL) for b in self.natal_branches if b]
        if self.luck_branch:
            out.append((self.luck_branch, TemporalSource.LUCK))
        if self.annual_branch:
            out.append((self.annual_branch, TemporalSource.ANNUAL))
        if self.monthly_branch:
            out.append((self.monthly_branch, TemporalSource.MONTHLY))
        if self.daily_branch:
            out.append((self.daily_branch, TemporalSource.DAILY))
        return out

    def temporal_units(self) -> list[tuple[str, str | None, str | None]]:
        """岁运层单元：(层标签, 干, 支)，按 大运→流年→流月→流日 顺序。"""
        out = []
        if self.luck_stem or self.luck_branch:
            out.append(("luck", self.luck_stem, self.luck_branch))
        if self.annual_stem or self.annual_branch:
            out.append(("annual", self.annual_stem, self.annual_branch))
        if self.monthly_stem or self.monthly_branch:
            out.append(("monthly", self.monthly_stem, self.monthly_branch))
        if self.daily_stem or self.daily_branch:
            out.append(("daily", self.daily_stem, self.daily_branch))
        return out

    def natal_positions(self) -> list[str]:
        return ["year", "month", "day", "hour"][:len(self.natal_stems)]

    def month_branch(self) -> str | None:
        """原局月支（岁运分析中月令永远取原局，R4/月令原则）。"""
        return self.natal_branches[1] if len(self.natal_branches) > 1 else None


class TemporalRelation(CamelizeModel):
    """带来源标记的岁运关系。"""
    kind: str
    label: str
    members: list[str] = []
    positions: list[str] = []           # e.g. ["natal:month", "annual"]
    sources: list[TemporalSource] = []  # 参与方来源
    is_new: bool = False                # 原局不存在、由岁运引入
    completes_harmony: bool = False     # 岁运补齐三合/三会
    transform_candidate: str | None = None  # 合化候选五行
    note: str | None = None


class TemporalStructure(CamelizeModel):
    """可定义的结构现象（不判断吉凶）。"""
    type: str                           # fuyin / fanyin / binglin / tiankedi / identical / pillar_clash
    label: str
    description: str
    positions: list[str] = []
    sources: list[TemporalSource] = []


class TemporalDelta(CamelizeModel):
    """岁运前后变化对比。"""
    analysis: str                       # strength / pattern / tiaohou / special / bingyao / tongguan
    support_level: AnalysisSupport = AnalysisSupport.EXPERIMENTAL
    natal_value: Any = None
    temporal_value: Any = None
    changed: bool = False
    description: str = ""


class TemporalEvidence(CamelizeModel):
    """一条岁运规则触发证据（M13：ExecutableRule(domain=temporal) → 结构观察，非吉凶）。"""
    ruleId: str
    category: str = "generic"
    label: str = ""
    matched: bool = False
    observations: list[str] = []
    provenance: list[Any] = []
    refId: str | None = None


class TemporalAnalysis(CamelizeModel):
    """M12/M13 完整岁运结构分析结果。"""
    context: TemporalContext
    relations: list[TemporalRelation] = []
    structures: list[TemporalStructure] = []
    deltas: list[TemporalDelta] = []
    evidence: list[str] = []
    ruleTriggers: list[TemporalEvidence] = []
    warnings: list[str] = []


# ---- 时间结构检测 ----

def _detect_structures(ctx: TemporalContext) -> list[TemporalStructure]:
    structures: list[TemporalStructure] = []
    n_gz = [f"{s or ''}{b or ''}" for s, b in
            zip(ctx.natal_stems, ctx.natal_branches)]

    if ctx.luck_stem and ctx.luck_branch:
        luck_gz = ctx.luck_stem + ctx.luck_branch
        # 伏吟：大运干支与原局某柱完全相同
        for i, ngz in enumerate(n_gz):
            if ngz == luck_gz:
                structures.append(TemporalStructure(
                    type="fuyin", label=f"大运伏吟{_natal_name(i)}",
                    description=f"大运{luck_gz}与原局{_natal_name(i)}{ngz}完全相同",
                    positions=[f"natal:{_pos(i)}", "luck"],
                    sources=[TemporalSource.NATAL, TemporalSource.LUCK],
                ))
        # 反吟：大运干支与原局某柱天克地冲（简化：地支相冲）
        from tianze.ganzhi.tables import BRANCHES
        for i, b in enumerate(ctx.natal_branches):
            if not b:
                continue
            bi = BRANCHES.index(b) if b in BRANCHES else -1
            li = BRANCHES.index(ctx.luck_branch) if ctx.luck_branch in BRANCHES else -1
            if bi >= 0 and li >= 0 and bi != li and (bi - li) % 6 == 0:
                structures.append(TemporalStructure(
                    type="fanyin", label=f"大运反吟（{b}{ctx.luck_branch}冲）",
                    description=f"大运地支{ctx.luck_branch}与原局{_pos(i)}支{b}相冲",
                    positions=[f"natal:{_pos(i)}", "luck"],
                    sources=[TemporalSource.NATAL, TemporalSource.LUCK],
                ))

    # 岁运并临：流年干支 == 大运干支
    if ctx.luck_stem and ctx.annual_stem:
        if ctx.luck_stem == ctx.annual_stem and ctx.luck_branch == ctx.annual_branch:
            structures.append(TemporalStructure(
                type="binglin", label=f"岁运并临{ctx.luck_stem}{ctx.luck_branch}",
                description=f"大运{ctx.luck_stem}{ctx.luck_branch}与流年{ctx.annual_stem}{ctx.annual_branch}完全相同",
                positions=["luck", "annual"],
                sources=[TemporalSource.LUCK, TemporalSource.ANNUAL],
            ))

    # 天克地冲：流年天干克大运天干 + 流年地支冲大运地支
    if ctx.luck_stem and ctx.annual_stem and ctx.luck_branch and ctx.annual_branch:
        from tianze.ganzhi.tables import STEM_ELEMENT, BRANCH_ELEMENT
        ls, ab = ctx.luck_stem, ctx.annual_stem
        se_l = STEM_ELEMENT.get(ls)
        se_a = STEM_ELEMENT.get(ab)
        # 克
        from tianze.ganzhi.tables import Element
        _CTL = {Element.WOOD: Element.EARTH, Element.EARTH: Element.WATER,
                Element.WATER: Element.FIRE, Element.FIRE: Element.METAL,
                Element.METAL: Element.WOOD}
        stem_ke = (se_a and se_l) and (_CTL.get(se_a) == se_l or _CTL.get(se_l) == se_a)
        bi_l = BRANCHES.index(ctx.luck_branch) if ctx.luck_branch in BRANCHES else -1
        bi_a = BRANCHES.index(ctx.annual_branch) if ctx.annual_branch in BRANCHES else -1
        branch_chong = bi_l >= 0 and bi_a >= 0 and bi_l != bi_a and (bi_l - bi_a) % 6 == 0
        if stem_ke and branch_chong:
            structures.append(TemporalStructure(
                type="tiankedi", label=f"天克地冲（{ab}{ctx.annual_branch} ↔ {ls}{ctx.luck_branch}）",
                description=f"流年天干{ab}克大运天干{ls}，流年地支{ctx.annual_branch}冲大运地支{ctx.luck_branch}",
                positions=["luck", "annual"],
                sources=[TemporalSource.LUCK, TemporalSource.ANNUAL],
            ))

    # 流年与原局某柱完全相同
    if ctx.annual_stem and ctx.annual_branch:
        annual_gz = ctx.annual_stem + ctx.annual_branch
        for i, ngz in enumerate(n_gz):
            if ngz == annual_gz:
                structures.append(TemporalStructure(
                    type="identical", label=f"流年与原局{_natal_name(i)}柱相同",
                    description=f"流年{annual_gz}与原局{_pos(i)}柱{ngz}完全相同",
                    positions=[f"natal:{_pos(i)}", "annual"],
                    sources=[TemporalSource.NATAL, TemporalSource.ANNUAL],
                ))

    return structures


def _pos(i: int) -> str:
    return ["year", "month", "day", "hour"][i] if i < 4 else f"pos{i}"


_LAYER_CN = {"luck": "大运", "annual": "流年", "monthly": "流月", "daily": "流日"}


def _natal_name(i: int) -> str:
    return ["年柱", "月柱", "日柱", "时柱"][i] if i < 4 else f"第{i}柱"


# ---- 主入口 ----

def analyze_temporal(
    natal_stems: list[str | None],
    natal_branches: list[str | None],
    day_master: str,
    luck_stem: str | None = None,
    luck_branch: str | None = None,
    annual_stem: str | None = None,
    annual_branch: str | None = None,
    monthly_stem: str | None = None,
    monthly_branch: str | None = None,
    daily_stem: str | None = None,
    daily_branch: str | None = None,
    luck_index: int | None = None,
    annual_year: int | None = None,
    luck_pillar: dict | None = None,     # DaYunEntry dict
    annual_pillar: dict | None = None,   # LiuNianEntry dict
) -> TemporalAnalysis:
    """M12/M13 岁运结构分析入口。

    输入原局四柱 + 可选大运/流年/流月/流日干支。
    输出：岁运关系（带来源标记）、结构现象、与原局的 Delta。
    月令保持原局事实：岁运字不参与月令判定。
    """
    ctx = TemporalContext(
        natal_stems=list(natal_stems), natal_branches=list(natal_branches),
        luck_stem=luck_stem, luck_branch=luck_branch,
        annual_stem=annual_stem, annual_branch=annual_branch,
        monthly_stem=monthly_stem, monthly_branch=monthly_branch,
        daily_stem=daily_stem, daily_branch=daily_branch,
        luck_index=luck_index, annual_year=annual_year,
        day_master=day_master,
    )

    relations: list[TemporalRelation] = []
    evidence: list[str] = []

    # 岁运干与原局四干的天干关系
    from tianze.relation.tables import STEM_COMBINATIONS, STEM_OPPOSITIONS
    from tianze.ganzhi.tables import ten_god, stem_index

    for source_label, st, br in _iter_temporal_stems_branches(ctx):
        if st:
            for i, ns in enumerate(ctx.natal_stems):
                if not ns:
                    continue
                pair = {st, ns}
                pair_fs = frozenset(pair)
                if pair_fs in STEM_COMBINATIONS:
                    transform = STEM_COMBINATIONS.get(pair_fs)
                    relations.append(TemporalRelation(
                        kind="stem_combination",
                        label=f"{st}{ns}合",
                        members=sorted([st, ns]),
                        positions=[f"natal:{_pos(i)}", source_label],
                        sources=[TemporalSource.NATAL, _src(source_label)],
                        is_new=True,
                        transform_candidate=transform.value if hasattr(transform, "value") else transform,
                    ))
                    evidence.append(f"岁运{_LAYER_CN.get(source_label, source_label)}干{st}与原局{_pos(i)}干{ns}构成天干五合")
                if pair in STEM_OPPOSITIONS:
                    relations.append(TemporalRelation(
                        kind="stem_opposition",
                        label=f"{st}{ns}冲",
                        members=sorted([st, ns]),
                        positions=[f"natal:{_pos(i)}", source_label],
                        sources=[TemporalSource.NATAL, _src(source_label)],
                        is_new=True,
                    ))
                    evidence.append(f"岁运{_LAYER_CN.get(source_label, source_label)}干{st}与原局{_pos(i)}干{ns}天干相冲")
        # 岁运支与原局支的地支关系
        if br:
            for i, nb in enumerate(ctx.natal_branches):
                if not nb:
                    continue
                pair = {br, nb}
                from tianze.relation.tables import (
                    SIX_CLASHES, SIX_COMBINATIONS, SIX_HARMS, SIX_BREAKS,
                    THREE_HARMONIES, HARMONY_CENTERS, THREE_MEETINGS,
                )
                pair_fs = frozenset(pair)
                if pair_fs in SIX_CLASHES:
                    relations.append(TemporalRelation(
                        kind="clash", label=f"{br}{nb}冲",
                        members=sorted([br, nb]),
                        positions=[f"natal:{_pos(i)}", source_label],
                        sources=[TemporalSource.NATAL, _src(source_label)],
                        is_new=True,
                    ))
                    evidence.append(f"岁运{_LAYER_CN.get(source_label, source_label)}支{br}与原局{_pos(i)}支{nb}相冲")
                if pair_fs in SIX_COMBINATIONS:
                    transform = SIX_COMBINATIONS[pair_fs]
                    relations.append(TemporalRelation(
                        kind="six_combination", label=f"{br}{nb}合",
                        members=sorted([br, nb]),
                        positions=[f"natal:{_pos(i)}", source_label],
                        sources=[TemporalSource.NATAL, _src(source_label)],
                        is_new=True, transform_candidate=transform.value if hasattr(transform, "value") else transform,
                    ))
                    evidence.append(f"岁运{_LAYER_CN.get(source_label, source_label)}支{br}与原局{_pos(i)}支{nb}六合")
                if pair_fs in SIX_HARMS:
                    relations.append(TemporalRelation(
                        kind="harm", label=f"{br}{nb}害",
                        members=sorted([br, nb]),
                        positions=[f"natal:{_pos(i)}", source_label],
                        sources=[TemporalSource.NATAL, _src(source_label)],
                        is_new=True,
                    ))
                if pair_fs in SIX_BREAKS:
                    relations.append(TemporalRelation(
                        kind="break", label=f"{br}{nb}破",
                        members=sorted([br, nb]),
                        positions=[f"natal:{_pos(i)}", source_label],
                        sources=[TemporalSource.NATAL, _src(source_label)],
                        is_new=True,
                    ))

    # 三合补齐检测：原局有 2 支 + 岁运补第 3 支
    from tianze.relation.tables import THREE_HARMONIES
    natal_branch_set = {b for b in ctx.natal_branches if b}
    from tianze.ganzhi.tables import BRANCHES as _BR

    # M24 · 拱夹/暗合/填实（DTZ-10/ZP-05/SPZY-34）：岁运 × 原局虚神
    # 口径：复用 relation.tables 的 arch_target / HIDDEN_COMBINATIONS（不重复实现）。
    # - 岁运支 == 原局拱位虚神 → 填实（ZP-05：忌刑冲填实之凶——结构观察，不判吉凶）
    # - 岁运支 + 原局支 隔二缺一成新拱（虚神原局岁运均不见）→ EXPERIMENTAL（岁运能否入拱两说）
    # - 岁运支 + 原局支 暗合（SPZY-34 逐对）→ 岁运引入暗合
    from tianze.relation.tables import arch_target, HIDDEN_COMBINATIONS, HIDDEN_COMBO_EXCEPTIONS
    temporal_branches = [(label, b) for label, _s, b in ctx.temporal_units() if b]
    temporal_branch_set = {b for _l, b in temporal_branches}
    natal_arch_targets: dict[str, tuple[str, str]] = {}
    natal_b_list = [b for b in ctx.natal_branches if b]
    for x in range(len(natal_b_list)):
        for y in range(x + 1, len(natal_b_list)):
            tgt = arch_target(natal_b_list[x], natal_b_list[y])
            if tgt and tgt not in natal_branch_set:
                natal_arch_targets[tgt] = (natal_b_list[x], natal_b_list[y])
    for label, br in temporal_branches:
        filled = natal_arch_targets.get(br)
        if filled:
            relations.append(TemporalRelation(
                kind="arch_fill",
                label=f"岁运{_LAYER_CN.get(label, label)}{br}填实拱位（{''.join(filled)}拱{br}）",
                members=[filled[0], filled[1], br],
                positions=[f"natal:{_pos(ctx.natal_branches.index(filled[0]))}",
                           f"natal:{_pos(ctx.natal_branches.index(filled[1]))}", label],
                sources=[TemporalSource.NATAL, _src(label)],
                is_new=True,
                note="虚神被填（ZP-05：拱禄拱贵忌刑冲填实之凶——原典禁则，候选级观察，不判吉凶）",
            ))
            evidence.append(
                f"岁运{_LAYER_CN.get(label, label)}支{br}为原局拱位虚神"
                f"（{''.join(filled)}拱{br}）——填实（忌刑冲填实之凶，ZP-05）")
            continue
        for i, nb in enumerate(ctx.natal_branches):
            if not nb:
                continue
            tgt = arch_target(nb, br)
            if tgt and tgt not in natal_branch_set and tgt not in temporal_branch_set:
                meeting_cn = ""
                from tianze.relation.tables import THREE_MEETINGS
                for trio, (direction, _el) in THREE_MEETINGS.items():
                    if tgt in trio and nb in trio and br in trio:
                        meeting_cn = f"（{direction}中支——暗会口径）"
                        break
                relations.append(TemporalRelation(
                    kind="arch",
                    label=f"{nb}{br}拱{tgt}（岁运成拱）",
                    members=[nb, br, tgt],
                    positions=[f"natal:{_pos(i)}", label],
                    sources=[TemporalSource.NATAL, _src(label)],
                    is_new=True,
                    note=f"岁运与原局隔二缺一成拱{meeting_cn}；岁运能否入拱两说（EXPERIMENTAL）——"
                         "候选关系，非格局（DTZ-26/36）",
                ))
                evidence.append(
                    f"岁运{_LAYER_CN.get(label, label)}支{br}与原局{_pos(i)}支{nb}"
                    f"隔二缺一，拱虚神{tgt}（DTZ-10：拱实不若拱虚）")
            pair_hs = HIDDEN_COMBINATIONS.get(frozenset({nb, br}))
            if pair_hs and frozenset({nb, br}) not in SIX_COMBINATIONS:
                combo_cn = "、".join(f"{a}{b}合" for a, b in pair_hs)
                note = f"岁运引入暗合：藏干{combo_cn}（SPZY-34）；暗合非化"
                exc = HIDDEN_COMBO_EXCEPTIONS.get(frozenset({nb, br}))
                if exc and exc[0] in natal_branch_set:
                    note += f"；另有{exc[1]}——两读保留"
                relations.append(TemporalRelation(
                    kind="hidden_combination",
                    label=f"{nb}{br}暗合（岁运）",
                    members=sorted([nb, br]),
                    positions=[f"natal:{_pos(i)}", label],
                    sources=[TemporalSource.NATAL, _src(label)],
                    is_new=True, note=note,
                ))
                evidence.append(
                    f"岁运{_LAYER_CN.get(label, label)}支{br}与原局{_pos(i)}支{nb}暗合"
                    f"（{combo_cn}；SPZY-34，非化）")

    for trio, elem in THREE_HARMONIES.items():
        # 集合迭代序受 PYTHONHASHSEED 影响 → 按地支序确定性排序（回归稳定性）
        natal_members = sorted({b for b in ctx.natal_branches if b and b in trio},
                               key=_BR.index)
        if len(natal_members) == 2:
            missing = trio - set(natal_members)
            missing_branch = list(missing)[0]
            # 检查岁运是否补齐（大运/流年/流月/流日）
            temporal_branch = None
            temporal_src = None
            for label, st, br in ctx.temporal_units():
                if br == missing_branch:
                    temporal_branch = br
                    temporal_src = label
                    break
            if temporal_branch:
                relations.append(TemporalRelation(
                    kind="three_harmony_completed",
                    label=f"{''.join(sorted(trio, key=lambda x: __import__('tianze.ganzhi.tables', fromlist=['BRANCHES']).BRANCHES.index(x)))}三合补齐（{elem.value}局）",
                    members=sorted(trio),
                    positions=[f"natal:{_pos(ctx.natal_branches.index(b))}" for b in natal_members] + [temporal_src],
                    sources=[TemporalSource.NATAL, _src(temporal_src)],
                    is_new=True, completes_harmony=True,
                    transform_candidate=elem.value if hasattr(elem, "value") else elem,
                    note=f"原局{'+'.join(natal_members)}，"
                         f"岁运{_LAYER_CN.get(temporal_src, temporal_src)}补{missing_branch}",
                ))
                evidence.append(
                    f"三合补齐：原局{'+'.join(natal_members)}，"
                    f"岁运{_LAYER_CN.get(temporal_src, temporal_src)}地支{missing_branch}"
                    f"补齐{''.join(sorted(trio))}三合{elem.value}局条件"
                )

    # 结构现象
    structures = _detect_structures(ctx)

    # M13：岁运知识规则 → TemporalEvidence（懒加载避免循环依赖）
    from tianze.knowledge.temporal_rules import evaluate_temporal_rules
    rule_triggers = evaluate_temporal_rules(ctx, relations, structures)

    return TemporalAnalysis(
        context=ctx, relations=relations, structures=structures,
        evidence=evidence, ruleTriggers=rule_triggers,
        warnings=["M12/M13 岁运分析为结构变化检测，不构成任何吉凶预测。"],
    )


def _iter_temporal_stems_branches(ctx: TemporalContext):
    """迭代岁运干支对：大运 → 流年 → 流月 → 流日。"""
    for label, stem, branch in ctx.temporal_units():
        if stem:
            yield label, stem, branch


_SRC_MAP = {"luck": TemporalSource.LUCK, "annual": TemporalSource.ANNUAL,
            "monthly": TemporalSource.MONTHLY, "daily": TemporalSource.DAILY}


def _src(label: str) -> TemporalSource:
    return _SRC_MAP.get(label, TemporalSource.LUCK)
