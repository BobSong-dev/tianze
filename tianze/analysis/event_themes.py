"""M14 · Event Theme 层：结构变化 → 事件主题候选（不是事件预测）。

定位（任务书边界）：
    Temporal Facts / Delta → Structural Theme → Event Rule → School-aware Reasoning
    → EventThemeCandidate（CANDIDATE/LIKELY/DISPUTED/BLOCKED/UNRESOLVED，绝无 CONFIRMED）

- 主题（career/wealth/relationship/study/mobility/family/social）描述"当前结构下
  哪类生活主题更值得关注"，不输出"某年一定升职/结婚/发财"。
- 每条规则命中带 schoolView：不同体系（traditional/pattern/strength/tiaohou/
  special_pattern/shensha/temporal_rule）分别给出方向，冲突显式保留为 DISPUTED。
- confidence 是 0..1 的透明 heuristic 加权（参数随结果输出，ENGINEERING_HEURISTIC），
  不是统计概率——输出永不使用百分比概率口吻。
- 规则来自 Knowledge Framework（Source → Quote → RuleCandidate → ExecutableRule(domain=event)），
  evaluator 与规则 JSON 一一对应，缺失即抛错。
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Sequence

from tianze.domain import models as M
from tianze.domain.models import CamelizeModel
from tianze.ganzhi.tables import BRANCHES, STEMS, ten_god
from tianze.analysis.temporal import AnalysisSupport, TemporalContext
from tianze.analysis.temporal_delta import TemporalDeltaReport

__all__ = [
    "EventTheme", "EventStatus", "SchoolView", "EventDirection", "EventRuleHit",
    "EventThemeCandidate", "EventThemeReport", "EventContext",
    "compute_event_themes", "EVENT_THEME_SCHEMA_VERSION", "CONFIDENCE_PARAMS",
]

EVENT_THEME_SCHEMA_VERSION = "1.0.0"


class EventTheme(str, Enum):
    CAREER = "career"
    WEALTH = "wealth"
    RELATIONSHIP = "relationship"
    STUDY = "study"
    MOBILITY = "mobility"
    FAMILY = "family"
    SOCIAL = "social"


class EventStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    LIKELY = "LIKELY"
    DISPUTED = "DISPUTED"
    BLOCKED = "BLOCKED"
    UNRESOLVED = "UNRESOLVED"
    # 永远不引入 CONFIRMED：现实事件不是 Tianze 的输出对象


class SchoolView(str, Enum):
    TRADITIONAL = "traditional"
    PATTERN = "pattern"
    STRENGTH = "strength"
    TIAOHOU = "tiaohou"
    SPECIAL_PATTERN = "special_pattern"
    SHENSHA = "shensha"          # 神煞视角（驿马/桃花等，受 SS-R22 去取原则约束）
    TEMPORAL_RULE = "temporal_rule"


class EventDirection(str, Enum):
    SUPPORT = "support"
    OPPOSE = "oppose"
    BLOCK = "block"


THEME_CN: dict[str, str] = {
    "career": "事业/职务", "wealth": "财务", "relationship": "关系/婚恋",
    "study": "学习/资格", "mobility": "迁动/环境", "family": "家庭", "social": "人际/竞争",
}


class EventRuleHit(CamelizeModel):
    """单条事件规则的命中记录。"""
    ruleId: str
    label: str
    theme: EventTheme
    direction: EventDirection
    view: SchoolView
    evidence: list[str] = []
    provenanceLevels: list[str] = []
    rescueApplied: dict[str, Any] | None = None   # M16：救应命中（id/effect/evidence/note）
    refId: str | None = None

    def model_post_init(self, __context: Any) -> None:
        if self.refId is None:
            object.__setattr__(self, "refId", f"event:rule:{self.ruleId}")


class EventThemeCandidate(CamelizeModel):
    """事件主题候选：结构层面的"值得关注的主题"，不是现实事件断言。"""
    theme: EventTheme
    themeCn: str = ""
    status: EventStatus = EventStatus.CANDIDATE
    supportingEvidence: list[str] = []
    opposingEvidence: list[str] = []
    triggeredRules: list[EventRuleHit] = []
    schoolViews: dict[str, str] = {}      # view → "support" / "oppose" / "both" / "block"
    agreement: str | None = None          # HIGH / PARTIAL / CONFLICT / None
    temporalRefs: list[str] = []
    conflictExplanations: list[Any] = []   # M15：方向冲突的上下文相关解释（dict 形态）
    confidence: float = 0.0
    confidenceBasis: list[str] = []
    warnings: list[str] = []
    refId: str | None = None

    def model_post_init(self, __context: Any) -> None:
        if not self.themeCn:
            object.__setattr__(self, "themeCn", THEME_CN.get(self.theme.value, self.theme.value))
        if self.refId is None:
            object.__setattr__(self, "refId", f"event:{self.theme.value}")


class EventThemeReport(CamelizeModel):
    """事件主题报告（一个岁运上下文一份）。"""
    eventSchemaVersion: str = EVENT_THEME_SCHEMA_VERSION
    context: dict[str, Any] = {}          # 岁运链 + 性别（可缺失）
    themes: list[EventThemeCandidate] = []
    unmatchedRules: list[str] = []        # 参与判定但未命中的规则 id（可审计）
    params: dict[str, Any] = {}           # confidence 参数（透明、ENGINEERING_HEURISTIC）
    explanations: dict[str, Any] = {}     # M17：theme → 全链路解释（with_explanations 时）
    warnings: list[str] = []


class EventContext(CamelizeModel):
    """事件规则评估输入：结构事实 + 岁运事实（只读快照）。"""
    day_master: str
    gender: str | None = None                 # male / female / None
    natal_stems: list[str | None] = []
    natal_branches: list[str | None] = []
    temporal_units: list[dict[str, Any]] = [] # [{layer, stem, branch}]
    ten_god_counts: dict[str, int] = {}       # 岁运干十神计数（不含日主）
    theme_strength: dict[str, int] = {}       # StructuralTheme 十神主题增量（印星/官杀/财星…）
    relations: list[dict[str, Any]] = []      # temporal relations（dict 形态）
    structures: list[dict[str, Any]] = []
    special_events: list[dict[str, Any]] = [] # special Delta（candidate 状态迁移/BLOCKED）
    strength_verdict: str | None = None       # weighted verdict（救应谓词复用，不另造算法）
    fuyi_verdict: str | None = None           # fuyi verdict（多方法读数，M17）
    dimension_de_shi: bool | None = None      # dimension 得势（多方法读数，M17）
    weighted_score: float | None = None
    context_ref: str = ""                     # 岁运链描述（temporal:chain:...）


# ---- 传 统 起 例 表（神煞；SS-R22：先明其理，去取从严） ----

# 驿马（三合局马位）：申子辰马在寅、寅午戌马在申、巳酉丑马在亥、亥卯未马在巳
_YIMA: dict[str, str] = {"申": "寅", "子": "寅", "辰": "寅",
                         "寅": "申", "午": "申", "戌": "申",
                         "巳": "亥", "酉": "亥", "丑": "亥",
                         "亥": "巳", "卯": "巳", "未": "巳"}

# 咸池桃花（三合沐浴位）：申子辰见酉、寅午戌见卯、巳酉丑见午、亥卯未见子
_XIANCHI: dict[str, str] = {"申": "酉", "子": "酉", "辰": "酉",
                            "寅": "卯", "午": "卯", "戌": "卯",
                            "巳": "午", "酉": "午", "丑": "午",
                            "亥": "子", "卯": "子", "未": "子"}

# 五行墓库（冲开财库用）
_ELEMENT_MU: dict[str, str] = {"WOOD": "未", "FIRE": "戌", "METAL": "丑", "WATER": "辰"}

_BRANCHES = BRANCHES


def _branch_clash(a: str, b: str) -> bool:
    if a not in _BRANCHES or b not in _BRANCHES:
        return False
    i, j = _BRANCHES.index(a), _BRANCHES.index(b)
    return i != j and (i - j) % 6 == 0


def _branch_six_combination(a: str, b: str) -> bool:
    from tianze.relation.tables import SIX_COMBINATIONS
    return frozenset({a, b}) in SIX_COMBINATIONS


def _stem_ke(a: str, b: str) -> bool:
    from tianze.ganzhi.tables import Element, STEM_ELEMENT
    ke = {Element.WOOD: Element.EARTH, Element.EARTH: Element.WATER,
          Element.WATER: Element.FIRE, Element.FIRE: Element.METAL,
          Element.METAL: Element.WOOD}
    ea, eb = STEM_ELEMENT.get(a), STEM_ELEMENT.get(b)
    return ea is not None and eb is not None and ke[ea] == eb


def _temporal_stems(ctx: EventContext) -> list[tuple[str, str]]:
    return [(u["layer"], u["stem"]) for u in ctx.temporal_units if u.get("stem")]


def _temporal_branches(ctx: EventContext) -> list[tuple[str, str]]:
    return [(u["layer"], u["branch"]) for u in ctx.temporal_units if u.get("branch")]


def _layers_cn(layer: str) -> str:
    return {"luck": "大运", "annual": "流年", "monthly": "流月", "daily": "流日"}.get(layer, layer)


# ---- 规则评估器 ----
# 每个 evaluator 返回 (direction, evidence)。theme/view/label 由规则 JSON 提供，
# evaluator 只负责"条件是否命中 + 证据文本"，保证与 Knowledge JSON 同源。

def _ev_car_guan(ctx: EventContext) -> tuple[EventDirection | None, list[str]]:
    """官星透岁运 + 官杀主题增强 → career 支持（DTZ-33：制化用官杀）。"""
    ev: list[str] = []
    for layer, st in _temporal_stems(ctx):
        god = ten_god(ctx.day_master, st).value
        if god in ("正官", "七杀"):
            ev.append(f"岁运{_layers_cn(layer)}干{st}为{god}（官星透出）")
    if ev and ctx.theme_strength.get("官杀", 0) > 0:
        ev.append(f"官杀主题增强 ×{ctx.theme_strength['官杀']}（StructuralTheme）")
        return EventDirection.SUPPORT, ev
    return (None, ev)


def _ev_car_guan_yin(ctx: EventContext) -> tuple[EventDirection | None, list[str]]:
    """官印相生（岁运印 + 命/岁有官）→ career/study 支持（DTZ-33：化用印绶）。"""
    yin_layers = [(l, s) for l, s in _temporal_stems(ctx)
                  if ten_god(ctx.day_master, s).value in ("正印", "偏印")]
    if not yin_layers:
        return None, []
    ev = [f"岁运{_layers_cn(l)}干{s}为{ten_god(ctx.day_master, s).value}"
          for l, s in yin_layers]
    guan_present = any(ten_god(ctx.day_master, s).value in ("正官", "七杀")
                       for s, _ in ((s, None) for s in ctx.natal_stems if s)) \
        or any(ten_god(ctx.day_master, s).value in ("正官", "七杀")
               for _l, s in _temporal_stems(ctx))
    if guan_present:
        ev.append("官星并见（原局或岁运）：官印相生结构（印化官杀生身）")
        return EventDirection.SUPPORT, ev
    return None, ev


def _ev_car_shangguan(ctx: EventContext) -> tuple[EventDirection | None, list[str]]:
    """伤官见官（岁运伤官克命/岁官星）→ career 反对（DTZ-39：伤官见官最难辨）。"""
    ev: list[str] = []
    for layer, st in _temporal_stems(ctx):
        if ten_god(ctx.day_master, st).value != "伤官":
            continue
        for i, ns in enumerate(ctx.natal_stems):
            if ns and ten_god(ctx.day_master, ns).value == "正官":
                ev.append(f"岁运{_layers_cn(layer)}干{st}（伤官）克原局{'年月日时'[i]}干{ns}（正官）")
        for tl, ts in _temporal_stems(ctx):
            if ts != st and ten_god(ctx.day_master, ts).value == "正官":
                ev.append(f"岁运{_layers_cn(layer)}干{st}（伤官）与岁运{_layers_cn(tl)}干{ts}（正官）并见相克")
    return (EventDirection.OPPOSE, ev) if ev else (None, [])


def _ev_wea_cai(ctx: EventContext) -> tuple[EventDirection | None, list[str]]:
    """财星透岁运 + 财主题增强 → wealth 支持（SS-R10 / ZPZ-12 财格口径）。"""
    ev: list[str] = []
    for layer, st in _temporal_stems(ctx):
        if ten_god(ctx.day_master, st).value in ("正财", "偏财"):
            ev.append(f"岁运{_layers_cn(layer)}干{st}为{ten_god(ctx.day_master, st).value}（财星透出）")
    if ev and ctx.theme_strength.get("财星", 0) > 0:
        ev.append(f"财星主题增强 ×{ctx.theme_strength['财星']}（StructuralTheme）")
        return EventDirection.SUPPORT, ev
    return (None, ev)


def _ev_wea_bijie(ctx: EventContext) -> tuple[EventDirection | None, list[str]]:
    """刃头财/比劫夺财结构 → wealth 反对（SS-R10：流年遇之主因财启争）。"""
    ev: list[str] = []
    # 结构现象复用 temporal 检测：special 里没有，直接查 relations? 刃头财是 TR-SS-R10A/B 的事——
    # 事件层用十神组合独立判定：岁运支=阳刃/禄位 且 岁运干=财，或比劫主题增强+财星并见
    from tianze.ganzhi.tables import YANG_STEM_REN, STEM_LU
    for layer, st in _temporal_stems(ctx):
        for tbl, name in ((YANG_STEM_REN, "阳刃"), (STEM_LU, "禄位")):
            ren = tbl.get(ctx.day_master)
            for _l2, br in _temporal_branches(ctx):
                if ren and br == ren and ten_god(ctx.day_master, st).value in ("正财", "偏财"):
                    ev.append(f"岁运{_layers_cn(layer)}{st}{br}：干财星坐{name}"
                              f"（{name}头财结构，主因财启争）")
    if ctx.theme_strength.get("比劫", 0) > 0:
        has_cai = any(ten_god(ctx.day_master, s).value in ("正财", "偏财")
                      for _l, s in _temporal_stems(ctx))
        if has_cai:
            ev.append(f"比劫主题增强 ×{ctx.theme_strength['比劫']} 且财星并见：比劫夺财之象")
    return (EventDirection.OPPOSE, ev) if ev else (None, [])


def _ev_wea_cai_ku(ctx: EventContext) -> tuple[EventDirection | None, list[str]]:
    """冲开财库（两说并存：传统喜冲 vs DTZ-35 喜冲极不可靠）→ wealth 支持（DISPUTED 化）。"""
    from tianze.ganzhi.tables import STEM_ELEMENT, Element
    dm_elem = STEM_ELEMENT[ctx.day_master]
    cai_elem = {"WOOD": "EARTH", "FIRE": "METAL", "EARTH": "WATER",
                "METAL": "WOOD", "WATER": "FIRE"}[dm_elem.value]  # 我克者为财
    ku = _ELEMENT_MU.get(cai_elem)
    if not ku:
        return None, []
    natal_ku = [f"{'年月日时'[i]}支{b}" for i, b in enumerate(ctx.natal_branches) if b == ku]
    ev: list[str] = []
    for layer, br in _temporal_branches(ctx):
        for i, nb in enumerate(ctx.natal_branches):
            if nb == ku and _branch_clash(br, nb):
                ev.append(f"岁运{_layers_cn(layer)}支{br}冲原局{'年月日时'[i]}支{nb}"
                          f"（{cai_elem.lower()}财库逢冲）")
    if natal_ku and not ev:
        ev.append(f"原局财库（{'、'.join(natal_ku)}）未被岁运冲动")
        return None, ev
    return (EventDirection.SUPPORT, ev) if ev else (None, [])


def _ev_rel_gong_he(ctx: EventContext) -> tuple[EventDirection | None, list[str]]:
    """夫妻宫（日支）逢岁运六合 → relationship 支持（日支为配偶宫，通说）。"""
    day_br = ctx.natal_branches[2] if len(ctx.natal_branches) > 2 else None
    if not day_br:
        return None, []
    ev = [f"岁运{_layers_cn(l)}支{b}合原局日支{day_br}（夫妻宫逢合）"
          for l, b in _temporal_branches(ctx) if _branch_six_combination(b, day_br)]
    return (EventDirection.SUPPORT, ev) if ev else (None, [])


def _ev_rel_gong_chong(ctx: EventContext) -> tuple[EventDirection | None, list[str]]:
    """夫妻宫逢冲 / 夫星逢冲 → relationship 反对（MLD-18：日支为夫宫…夫星逢冲）。"""
    day_br = ctx.natal_branches[2] if len(ctx.natal_branches) > 2 else None
    if not day_br:
        return None, []
    ev = [f"岁运{_layers_cn(l)}支{b}冲原局日支{day_br}（夫妻宫逢冲）"
          for l, b in _temporal_branches(ctx) if _branch_clash(b, day_br)]
    return (EventDirection.OPPOSE, ev) if ev else (None, [])


def _ev_rel_spouse_star(ctx: EventContext) -> tuple[EventDirection | None, list[str]]:
    """配偶星临岁运（男看财/女看官）→ relationship 支持；性别未知 → UNRESOLVED。"""
    if ctx.gender not in ("male", "female"):
        # 方向 None + 消息 → 聚合层输出 UNRESOLVED 候选（不猜性别）
        return None, ["性别未知：配偶星（男财/女官）无法判定（MLD-18 口径），规则 UNRESOLVED"]
    want = ("正财", "偏财") if ctx.gender == "male" else ("正官", "七杀")
    role = "妻星（财）" if ctx.gender == "male" else "夫星（官）"
    ev = [f"岁运{_layers_cn(l)}干{s}为{ten_god(ctx.day_master, s).value}"
          f"（{role}临岁运）"
          for l, s in _temporal_stems(ctx) if ten_god(ctx.day_master, s).value in want]
    return (EventDirection.SUPPORT, ev) if ev else (None, [])


def _ev_rel_xianchi(ctx: EventContext) -> tuple[EventDirection | None, list[str]]:
    """咸池桃花临岁运 → relationship 支持（shensha 视角，SS-R22 去取从严）。"""
    anchors = {b for b in (ctx.natal_branches[0] if ctx.natal_branches else None,
                           ctx.natal_branches[2] if len(ctx.natal_branches) > 2 else None) if b}
    ev: list[str] = []
    for anchor in anchors:
        xc = _XIANCHI.get(anchor)
        for l, b in _temporal_branches(ctx):
            if xc and b == xc:
                ev.append(f"岁运{_layers_cn(l)}支{b}为原局{'年支' if anchor == ctx.natal_branches[0] else '日支'}{anchor}之咸池桃花")
    return (EventDirection.SUPPORT, ev) if ev else (None, [])


def _ev_stu_yin(ctx: EventContext) -> tuple[EventDirection | None, list[str]]:
    """印星临岁运 + 印主题增强 → study 支持（印主文书/资格，通说+DTZ-33 化杀）。"""
    ev = [f"岁运{_layers_cn(l)}干{s}为{ten_god(ctx.day_master, s).value}（印星透出）"
          for l, s in _temporal_stems(ctx)
          if ten_god(ctx.day_master, s).value in ("正印", "偏印")]
    if ev and ctx.theme_strength.get("印星", 0) > 0:
        ev.append(f"印星主题增强 ×{ctx.theme_strength['印星']}（StructuralTheme）")
        return EventDirection.SUPPORT, ev
    return (None, ev)


def _ev_mob_yima(ctx: EventContext) -> tuple[EventDirection | None, list[str]]:
    """驿马临岁运/驿马逢冲 → mobility 支持（shensha 视角，SS-R22 引滴天髓半推详）。"""
    anchors = {b for b in (ctx.natal_branches[0] if ctx.natal_branches else None,
                           ctx.natal_branches[2] if len(ctx.natal_branches) > 2 else None) if b}
    ev: list[str] = []
    for anchor in anchors:
        ym = _YIMA.get(anchor)
        for l, b in _temporal_branches(ctx):
            if ym and b == ym:
                ev.append(f"岁运{_layers_cn(l)}支{b}临原局{'年支' if anchor == ctx.natal_branches[0] else '日支'}{anchor}之驿马")
            elif ym and _branch_clash(b, ym):
                ev.append(f"岁运{_layers_cn(l)}支{b}冲原局驿马{ym}（驿马逢冲，主迁动）")
    return (EventDirection.SUPPORT, ev) if ev else (None, [])


def _ev_mob_chong_yueling(ctx: EventContext) -> tuple[EventDirection | None, list[str]]:
    """岁运冲提纲（月令）→ mobility 支持（DTZ-09：支神只以冲为重）。"""
    mb = ctx.natal_branches[1] if len(ctx.natal_branches) > 1 else None
    if not mb:
        return None, []
    ev = [f"岁运{_layers_cn(l)}支{b}冲原局月令{mb}（冲提纲，环境根基被引动）"
          for l, b in _temporal_branches(ctx) if _branch_clash(b, mb)]
    return (EventDirection.SUPPORT, ev) if ev else (None, [])


def _ev_fam_tiankedi(ctx: EventContext) -> tuple[EventDirection | None, list[str]]:
    """年柱/月柱被岁运天克地冲 → family 结构变动（宫位映射为通说，PROJECT_REFERENCE）。"""
    ev: list[str] = []
    for s in ctx.structures:
        if s.get("type") in ("fanyin", "tiankedi"):
            positions = "、".join(s.get("positions", []))
            if "natal:year" in positions or "natal:month" in positions:
                ev.append(f"{s.get('label', '')}：{s.get('description', '')}（年柱=祖上/父母宫、月柱=父母兄弟宫，通说映射）")
    return (EventDirection.SUPPORT, ev) if ev else (None, [])


def _ev_soc_bijie(ctx: EventContext) -> tuple[EventDirection | None, list[str]]:
    """比劫临岁运/比劫主题增强 → social 支持（同辈/合作竞争，通说）。"""
    ev = [f"岁运{_layers_cn(l)}干{s}为{ten_god(ctx.day_master, s).value}"
          for l, s in _temporal_stems(ctx)
          if ten_god(ctx.day_master, s).value in ("比肩", "劫财")]
    if ctx.theme_strength.get("比劫", 0) > 0:
        ev.append(f"比劫主题增强 ×{ctx.theme_strength['比劫']}（StructuralTheme）")
    return (EventDirection.SUPPORT, ev) if ev else (None, [])


def _ev_cong_special(ctx: EventContext):
    """从格/专旺岁运破格（两说）→ 命中时返回 (direction, evidence, theme_override)。

    主题按从格类型映射：从财→wealth、从官杀→career、其余→social。
    """
    ev: list[str] = []
    theme_of = {"从财": "wealth", "从官杀": "career", "从儿": "social",
                "从强": "social", "曲直": "social", "炎上": "social",
                "稼穑": "social", "从革": "social", "润下": "social"}
    mapped: str | None = None
    for e in ctx.special_events:
        if e.get("kind") in ("blocked", "status_changed", "removed"):
            t = (e.get("subject") or "")
            for ctype, theme in theme_of.items():
                if ctype in t:
                    mapped = theme
                    ev.append(f"{e.get('subject', '')}：{e.get('trigger', '')}"
                              f"（从格/专旺岁运破格两说：顺势说 vs 破格说，DTZ-04/05/06）")
                    break
    if ev:
        return EventDirection.SUPPORT, ev, mapped
    return None, [], None


def _ev_car_shishenzhisha(ctx: EventContext):
    """食神制杀（条件化）：岁运食神 + 命/岁七杀 → career 支持（制杀成权）。

    条件化边界（SS-R05）：身强煞浅则假煞为权不可制——v1 不判身强弱，
    conflictNote 保留该前提，方向给 support 但注明前提。
    """
    ev: list[str] = []
    shi_layers = [(l, s) for l, s in _temporal_stems(ctx)
                  if ten_god(ctx.day_master, s).value == "食神"]
    sha_present = any(ten_god(ctx.day_master, s).value == "七杀"
                      for s in ctx.natal_stems if s) or         any(ten_god(ctx.day_master, s).value == "七杀" for _l, s in _temporal_stems(ctx))
    if shi_layers and sha_present:
        ev.append("岁运" + "、".join(f"{_layers_cn(l)}干{s}" for l, s in shi_layers)
                  + "（食神）制命/岁七杀：食神制杀结构（DTZ-33：制用食神）")
        ev.append("前提保留（SS-R05）：身强煞浅则煞化为官、假煞为权不可制；v1 不判身强弱")
        return EventDirection.SUPPORT, ev
    return (None, ev)


def _ev_car_sharen(ctx: EventContext):
    """煞刃相合：岁运七杀 + 原局阳刃 → career 支持（DTZ-33：身煞两停最宜煞刃相合）。"""
    from tianze.ganzhi.tables import YANG_STEM_REN, BRANCHES
    ren = YANG_STEM_REN.get(ctx.day_master)
    if not ren:
        return (None, [])
    has_ren = ren in [b for b in ctx.natal_branches if b]
    sha_layers = [(l, s) for l, s in _temporal_stems(ctx)
                  if ten_god(ctx.day_master, s).value == "七杀"]
    if has_ren and sha_layers:
        ev = [f"原局{ren}（阳刃）+ 岁运"
              + "、".join(f"{_layers_cn(l)}干{s}" for l, s in sha_layers)
              + "（七杀）：煞刃相合结构（DTZ-33：身煞两停最宜煞刃相合，不合亦须用印以和之）"]
        return EventDirection.SUPPORT, ev
    return (None, [])


def _ev_wea_shishang_shengcai(ctx: EventContext):
    """食伤生财：岁运食伤 + 岁运/命局财星 → wealth 支持（ZPZ-12 财格用财诸局）。"""
    shi_layers = [(l, s) for l, s in _temporal_stems(ctx)
                  if ten_god(ctx.day_master, s).value in ("食神", "伤官")]
    cai_present = any(ten_god(ctx.day_master, s).value in ("正财", "偏财")
                      for s in ctx.natal_stems if s) or         any(ten_god(ctx.day_master, s).value in ("正财", "偏财")
            for _l, s in _temporal_stems(ctx))
    if shi_layers and cai_present:
        ev = ["岁运" + "、".join(f"{_layers_cn(l)}干{s}（{ten_god(ctx.day_master, s).value}）"
                                for l, s in shi_layers) + " 生财（命/岁财星并见）：食伤生财结构"]
        return EventDirection.SUPPORT, ev
    return (None, [])


def _ev_rel_cai_yin(ctx: EventContext):
    """财印不容（MLD-18）：岁运印星 + 命/岁财星并见 → relationship 反对。"""
    yin_layers = [(l, s) for l, s in _temporal_stems(ctx)
                  if ten_god(ctx.day_master, s).value in ("正印", "偏印")]
    cai_present = any(ten_god(ctx.day_master, s).value in ("正财", "偏财")
                      for s in ctx.natal_stems if s) or         any(ten_god(ctx.day_master, s).value in ("正财", "偏财")
            for _l, s in _temporal_stems(ctx))
    if yin_layers and cai_present:
        ev = ["岁运" + "、".join(f"{_layers_cn(l)}干{s}" for l, s in yin_layers)
              + "（印）与财星并见：财印不相容结构（MLD-18：财印不相容势必分飞）"]
        ev.append("边界保留：MLD-18 原文明言「离婚非不可避免事」——方向仅为关系主题张力")
        return EventDirection.OPPOSE, ev
    return (None, [])


# 本模块只导出评估器注册表；规则元数据（theme/view/label/provenance）在 rules.json
EVALUATORS = {
    "EV-CAR-01": _ev_car_guan,
    "EV-CAR-02": _ev_car_guan_yin,
    "EV-CAR-03": _ev_car_shangguan,
    "EV-WEA-01": _ev_wea_cai,
    "EV-WEA-02": _ev_wea_bijie,
    "EV-WEA-03": _ev_wea_cai_ku,
    "EV-REL-01": _ev_rel_gong_he,
    "EV-REL-02": _ev_rel_gong_chong,
    "EV-REL-03": _ev_rel_spouse_star,
    "EV-REL-04": _ev_rel_xianchi,
    "EV-STU-01": _ev_stu_yin,
    "EV-MOB-01": _ev_mob_yima,
    "EV-MOB-02": _ev_mob_chong_yueling,
    "EV-FAM-01": _ev_fam_tiankedi,
    "EV-SOC-01": _ev_soc_bijie,
    "EV-CON-01": _ev_cong_special,
    "EV-CAR-04": _ev_car_shishenzhisha,
    "EV-CAR-05": _ev_car_sharen,
    "EV-WEA-04": _ev_wea_shishang_shengcai,
    "EV-REL-05": _ev_rel_cai_yin,
}

_UNRESOLVED_RULES = {"EV-REL-03"}   # 性别未知时输出 UNRESOLVED 候选的规则

# confidence 参数（ENGINEERING_HEURISTIC，全透明、随结果输出）
CONFIDENCE_PARAMS = {
    "kind": "ENGINEERING_HEURISTIC",
    "provenanceWeight": {"CLASSICAL_EXPLICIT": 2.0, "PROJECT_REFERENCE": 1.0,
                         "ENGINEERING_HEURISTIC": 0.5},
    "multiViewBonus": 0.25,        # ≥2 个不同 view 同向（原始加权利）
    "opposingPenalty": 0.5,        # 每个 oppose 命中折减（原始加权利）
    "blockPenalty": 0.7,           # block 命中折减（原始加权利）
    "scale": 0.3,                  # 归一尺度：单 CLASSICAL 命中 ≈ 0.6，避免全部触顶
    "cap": 1.0,
    "note": "confidence 为透明加权 heuristic（0..1），不是统计概率；不得以百分比概率口吻输出。",
}


def _conf_of_hit(hit: EventRuleHit) -> float:
    w = CONFIDENCE_PARAMS["provenanceWeight"]
    return max([w.get(lv, 0.5) for lv in hit.provenanceLevels] or [0.5])



# ---- 聚合：规则命中 → School-aware 主题候选 ----

def _load_event_rules() -> list[dict]:
    from tianze.knowledge.event_rules import load_event_rules
    return load_event_rules()


def build_event_context(
    chart: M.BaziChart,
    temporal_ctx: TemporalContext,
    delta_report: TemporalDeltaReport | None,
    relations: Sequence[Any],
    structures: Sequence[Any],
) -> EventContext:
    """从 chart + TemporalContext + Delta 组装 EventContext（只读快照）。"""
    theme_strength: dict[str, int] = {}
    if delta_report:
        for t in delta_report.themes:
            if t.theme in ("财星", "官杀", "印星", "食伤", "比劫") and t.direction == "increased":
                theme_strength[t.theme] = theme_strength.get(t.theme, 0) + 1
    ten_god_counts: dict[str, int] = {}
    for _layer, st in _temporal_stems_or_units(temporal_ctx):
        god = ten_god(chart.day_master.stem, st).value
        ten_god_counts[god] = ten_god_counts.get(god, 0) + 1
    special_events = []
    if delta_report:
        for it in delta_report.items:
            if it.analysis in ("special", "bingYao", "tongGuan"):
                special_events.append({
                    "kind": it.kind.value, "subject": it.subject,
                    "trigger": it.trigger, "refId": it.refId,
                })
    chain = "natal"
    units = temporal_ctx.temporal_units()
    if units:
        chain = "natal->" + "->".join(
            f"{_layers_cn(l)}{(s or '')}{(b or '')}" for l, s, b in units)
    gender = None
    if chart.birth.gender == M.Gender.MALE:
        gender = "male"
    elif chart.birth.gender == M.Gender.FEMALE:
        gender = "female"
    strength_verdict = None
    weighted_score = None
    fuyi_verdict = None
    dimension_de_shi = None
    if chart.strength is not None:
        for m in chart.strength.methods:
            if m.score is not None:
                weighted_score = m.score
            if "weighted" in (m.analyzer_id or "") and m.verdict:
                strength_verdict = m.verdict
            if "fuyi" in (m.analyzer_id or "") and m.verdict:
                fuyi_verdict = m.verdict
            if m.strength_evidence is not None:
                dimension_de_shi = m.strength_evidence.de_shi.result
    return EventContext(
        day_master=chart.day_master.stem,
        gender=gender,
        strength_verdict=strength_verdict,
        fuyi_verdict=fuyi_verdict,
        dimension_de_shi=dimension_de_shi,
        weighted_score=weighted_score,
        natal_stems=[chart.pillars.year.stem, chart.pillars.month.stem,
                     chart.pillars.day.stem,
                     chart.pillars.hour.stem if chart.pillars.hour else None],
        natal_branches=[chart.pillars.year.branch, chart.pillars.month.branch,
                        chart.pillars.day.branch,
                        chart.pillars.hour.branch if chart.pillars.hour else None],
        temporal_units=[{"layer": l, "stem": s, "branch": b} for l, s, b in units],
        ten_god_counts=ten_god_counts,
        theme_strength=theme_strength,
        relations=[r.model_dump(by_alias=True, exclude_none=True) for r in relations],
        structures=[s.model_dump(by_alias=True, exclude_none=True) for s in structures],
        special_events=special_events,
        context_ref=f"temporal:chain:{chain}",
    )


def _temporal_stems_or_units(ctx: TemporalContext):
    for l, s, b in ctx.temporal_units():
        if s:
            yield l, s


def _aggregate(theme_key: str, hits: list[EventRuleHit],
               unresolved: bool,
               unresolved_notes: list[str] | None = None,
               rule_meta: dict[str, dict] | None = None,
               rescue_state: dict | None = None) -> EventThemeCandidate:
    sup = [h for h in hits if h.direction == EventDirection.SUPPORT]
    opp = [h for h in hits if h.direction == EventDirection.OPPOSE]
    blk = [h for h in hits if h.direction == EventDirection.BLOCK]

    views: dict[str, set[str]] = {}
    for h in hits:
        views.setdefault(h.view.value, set()).add(h.direction.value)
    school_views = {v: ("both" if len(ds) > 1 else next(iter(ds)))
                    for v, ds in sorted(views.items())}

    if sup and opp:
        agreement = "CONFLICT"
    elif len({h.view for h in sup}) >= 2:
        agreement = "HIGH"
    elif sup or opp:
        agreement = "PARTIAL" if len(hits) > 1 else None
    else:
        agreement = None

    if unresolved:
        status = EventStatus.UNRESOLVED
    elif blk:
        status = EventStatus.BLOCKED
    elif sup and opp:
        status = EventStatus.DISPUTED
    elif sup and len({h.view for h in sup}) >= 2:
        status = EventStatus.LIKELY
    else:
        status = EventStatus.CANDIDATE

    base = sum(_conf_of_hit(h) for h in sup)
    if len({h.view for h in sup}) >= 2:
        base += CONFIDENCE_PARAMS["multiViewBonus"]
    penalty = (len(opp) * CONFIDENCE_PARAMS["opposingPenalty"]
               + len(blk) * CONFIDENCE_PARAMS["blockPenalty"])
    confidence = round(
        max(0.0, min(CONFIDENCE_PARAMS["cap"],
                     (base - penalty) * CONFIDENCE_PARAMS["scale"])), 3)
    basis = [f"{h.refId}（{h.view.value}/{h.direction.value}，权重 {_conf_of_hit(h)}）"
             for h in hits]

    warnings = ["事件主题是结构层面的「值得关注」提示，不是现实事件预测。",
                "confidence 是 ENGINEERING_HEURISTIC 加权，不是概率。"]
    if agreement == "CONFLICT":
        warnings.append("多体系方向冲突，已保留 disagreement，不做裁决。")

    # M15：方向冲突 → 上下文相关 ConflictExplanation（specific-over-general /
    # school-difference / keep-both，全部透明）
    from tianze.analysis.rule_conflicts import explain_conflicts
    meta = rule_meta or {}
    conflict_explanations = [c.model_dump(by_alias=True, exclude_none=True)
                             for c in explain_conflicts(
        hits,
        view_of_rule={rid: m["view"] for rid, m in meta.items()},
        label_of_rule={rid: m["label"] for rid, m in meta.items()},
        prov_of_rule={rid: m["provenanceLevels"] for rid, m in meta.items()},
        rescue_state=rescue_state or {},
    )]

    return EventThemeCandidate(
        theme=EventTheme(theme_key),
        status=status,
        supportingEvidence=[e for h in sup for e in h.evidence]
        + list(unresolved_notes or []),
        opposingEvidence=[e for h in opp for e in h.evidence]
        + [e for h in blk for e in h.evidence],
        triggeredRules=hits,
        schoolViews=school_views,
        agreement=agreement,
        temporalRefs=sorted({h.refId for h in hits if h.refId}),
        conflictExplanations=conflict_explanations,
        confidence=confidence,
        confidenceBasis=basis,
        warnings=warnings,
    )


def compute_event_themes(
    chart: M.BaziChart,
    luck: tuple[str | None, str | None] | None = None,
    annual: tuple[str | None, str | None] | None = None,
    monthly: tuple[str | None, str | None] | None = None,
    daily: tuple[str | None, str | None] | None = None,
    delta_report: TemporalDeltaReport | None = None,
    temporal_ctx: TemporalContext | None = None,
    relations: Sequence[Any] | None = None,
    structures: Sequence[Any] | None = None,
    with_explanations: bool = False,
) -> EventThemeReport:
    """岁运上下文 → 事件主题候选报告（惰性：只在被选节点调用）。

    复用 TemporalDelta/StructuralTheme 作为证据源（传 None 时内部重算）。
    with_explanations=True 时附带全链路解释（M17 ExplanationChain 产品化）。
    """
    from tianze.analysis.temporal import analyze_temporal
    from tianze.analysis.temporal_delta import compute_temporal_delta

    if delta_report is None or temporal_ctx is None:
        delta_report = compute_temporal_delta(chart, luck=luck, annual=annual,
                                              monthly=monthly, daily=daily)
        temporal_ctx = delta_report.context
    if relations is None or structures is None:
        ta = analyze_temporal(
            natal_stems=temporal_ctx.natal_stems,
            natal_branches=temporal_ctx.natal_branches,
            day_master=chart.day_master.stem,
            luck_stem=temporal_ctx.luck_stem, luck_branch=temporal_ctx.luck_branch,
            annual_stem=temporal_ctx.annual_stem, annual_branch=temporal_ctx.annual_branch,
            monthly_stem=temporal_ctx.monthly_stem, monthly_branch=temporal_ctx.monthly_branch,
            daily_stem=temporal_ctx.daily_stem, daily_branch=temporal_ctx.daily_branch,
        )
        relations, structures = ta.relations, ta.structures

    ectx = build_event_context(chart, temporal_ctx, delta_report, relations, structures)

    # M16：救应谓词一次评估（rescues.json 与 conflicts.json 共用）
    from tianze.analysis.rescues import evaluate_rescues, get_rescue_declarations
    rescue_state = evaluate_rescues(ectx)
    rescue_decls = get_rescue_declarations()

    rules = _load_event_rules()
    hits_by_theme: dict[str, list[EventRuleHit]] = {}
    unresolved_themes: set[str] = set()
    unresolved_notes: dict[str, list[str]] = {}
    unmatched: list[str] = []
    for r in rules:
        rid = r["id"]
        fn = EVALUATORS.get(rid)
        if fn is None:
            raise KeyError(f"事件规则 {rid} 缺少执行器（不静默跳过）")
        result = fn(ectx)
        if len(result) == 3:
            direction, ev, theme_override = result
        else:
            direction, ev = result
            theme_override = None
        if direction is None:
            if rid in _UNRESOLVED_RULES and any("UNRESOLVED" in x for x in ev):
                unresolved_themes.add(r["theme"])
                unresolved_notes.setdefault(r["theme"], []).extend(ev)
            unmatched.append(rid)
            continue
        eff_theme = theme_override or r["theme"]
        hit = EventRuleHit(
            ruleId=rid, label=r.get("label", rid),
            theme=EventTheme(eff_theme), direction=direction,
            view=SchoolView(r.get("view", "traditional")),
            evidence=ev,
            provenanceLevels=[p["level"] for p in r.get("provenance", [])],
        )
        # M16：救应声明应用（对命中命中标记 rescueApplied；效果 weaken 保留方向）
        for d in rescue_decls:
            if d.get("target") != rid:
                continue
            st = rescue_state.get(d.get("predicate", ""), {})
            if st.get("active"):
                hit = hit.model_copy(update={"rescueApplied": {
                    "id": d["id"], "predicate": d["predicate"],
                    "effect": d.get("effect", "weaken"),
                    "evidence": st.get("evidence", []), "note": st.get("note", ""),
                }})
        hits_by_theme.setdefault(eff_theme, []).append(hit)

    rule_meta = {r["id"]: {"view": r.get("view", "traditional"),
                           "label": r.get("label", ""),
                           "provenanceLevels": [p["level"] for p in r.get("provenance", [])]}
                 for r in rules}
    all_themes = sorted(set(hits_by_theme) | set(unresolved_themes))
    themes = [_aggregate(t, hits_by_theme.get(t, []),
                         t in unresolved_themes and not hits_by_theme.get(t),
                         unresolved_notes.get(t, []), rule_meta, rescue_state)
              for t in all_themes]

    units = temporal_ctx.temporal_units()
    ctx_desc: dict[str, Any] = {"chain": ectx.context_ref, "gender": ectx.gender}
    if units:
        ctx_desc["layers"] = [{"layer": l, "stem": s, "branch": b} for l, s, b in units]

    explanations: dict[str, Any] = {}
    if with_explanations:
        from tianze.analysis.explain import build_explanation_chains
        explanations = build_explanation_chains(
            type("ReportShim", (), {"themes": themes}), rescue_state)

    return EventThemeReport(
        eventSchemaVersion=EVENT_THEME_SCHEMA_VERSION,
        context=ctx_desc,
        themes=themes,
        unmatchedRules=unmatched,
        params=dict(CONFIDENCE_PARAMS),
        explanations=explanations,
        warnings=["EventTheme 为结构主题候选，不是现实事件预测；不输出确定性事件结论。",
                  "confidence 为透明 ENGINEERING_HEURISTIC，不是概率。"],
    )
