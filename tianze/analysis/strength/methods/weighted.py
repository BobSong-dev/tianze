"""M4.2 weighted 旺衰分析器（R20）——一种工程量化方法，不是官方唯一真值。

口径（全部参数化，见 WeightedStrengthParams；默认值来源见 provenance()）：
- 计分单位 = 命局每个"字"：可见天干（日主自身除外）+ 各支全部藏干；
- 归类：单位五行 == 日主（比劫）或 生日主（印星）→ support；
  日主所生（食伤）/所克（财）/克日主（官杀）→ drain；
- 月柱全部单位 × month_multiplier（月令当权）；
- score = support / (support + drain)，阈值映射五级 verdict。

防重复计分（ADR-022）：通根、得令**不是**本方法的独立计分项——它们与藏干
单位/月柱乘数是同一批事实，分开计分即重复。本方法只有"逐字单位"一种计分，
贡献明细 contributions 可完整复现总分。
"""

from __future__ import annotations

from tianze.analysis.strength.base import StrengthFacts
from tianze.domain.models import (
    Contribution,
    Element,
    Position,
    Provenance,
    RuleLevel,
    StrengthMethodResult,
)
from tianze.ganzhi.tables import HIDDEN_STEMS, STEM_ELEMENT, stem_index
from tianze.ganzhi.tables import Element as E

_GEN: dict[Element, Element] = {
    Element.WOOD: Element.FIRE, Element.FIRE: Element.EARTH,
    Element.EARTH: Element.METAL, Element.METAL: Element.WATER,
    Element.WATER: Element.WOOD,
}
ELEM_CN: dict[Element, str] = {
    Element.WOOD: "木", Element.FIRE: "火", Element.EARTH: "土",
    Element.METAL: "金", Element.WATER: "水",
}
POS_CN = {"year": "年", "month": "月", "day": "日", "hour": "时", "luck": "大运", "annual": "流年", "monthly": "流月", "daily": "流日"}


class WeightedStrengthParams:
    """weighted-v1 全部权重与阈值（R20）。每个参数：有默认值、有出处、可序列化、随结果输出。

    默认值出处（PROJECT_REFERENCE，均已在 Phase 0 源码核实；见 research/notes/）：
    - visible 1.0 / main 1.0 / middle 0.5 —— bazi-atlas engine.mjs R20（Horosa 为 100/100/60，等比不同）
    - residual 0.25 —— jiwenxu yongshen.py / ruan build_ui（0.25）
    - month_multiplier 1.5 —— Horosa baziWuxing monthMult / ruan 月令×1.5（Atlas 用 ×2）
    - strong/weak 0.55/0.45 —— Atlas engine.mjs:778 与 Horosa baziWuxing:148-149 同值
    - extreme 0.65/0.35 —— ENGINEERING_HEURISTIC（Tianze 扩展五级而设，无上游来源）
    """

    def __init__(
        self,
        visible_stem_weight: float = 1.0,
        main_qi_weight: float = 1.0,
        middle_qi_weight: float = 0.5,
        residual_qi_weight: float = 0.25,
        month_multiplier: float = 1.5,
        strong_threshold: float = 0.55,
        weak_threshold: float = 0.45,
        extreme_strong_threshold: float = 0.65,
        extreme_weak_threshold: float = 0.35,
    ) -> None:
        self.visible_stem_weight = visible_stem_weight
        self.main_qi_weight = main_qi_weight
        self.middle_qi_weight = middle_qi_weight
        self.residual_qi_weight = residual_qi_weight
        self.month_multiplier = month_multiplier
        self.strong_threshold = strong_threshold
        self.weak_threshold = weak_threshold
        self.extreme_strong_threshold = extreme_strong_threshold
        self.extreme_weak_threshold = extreme_weak_threshold
        if not (0 < self.weak_threshold < self.strong_threshold < 1):
            raise ValueError("阈值需满足 0 < weak < strong < 1")
        if not (0 < self.extreme_weak_threshold <= self.weak_threshold):
            raise ValueError("extreme_weak 需在 (0, weak] 内")
        if not (self.strong_threshold <= self.extreme_strong_threshold < 1):
            raise ValueError("extreme_strong 需在 [strong, 1) 内")

    def to_dict(self) -> dict[str, float]:
        return {
            "visibleStemWeight": self.visible_stem_weight,
            "mainQiWeight": self.main_qi_weight,
            "middleQiWeight": self.middle_qi_weight,
            "residualQiWeight": self.residual_qi_weight,
            "monthMultiplier": self.month_multiplier,
            "strongThreshold": self.strong_threshold,
            "weakThreshold": self.weak_threshold,
            "extremeStrongThreshold": self.extreme_strong_threshold,
            "extremeWeakThreshold": self.extreme_weak_threshold,
        }

    def provenance(self) -> list[Provenance]:
        return [
            Provenance(level=RuleLevel.PROJECT_REFERENCE, project="bazi-atlas",
                       concept="visible stem / main qi / middle qi weights (engine.mjs R20)",
                       note="Horosa 同类权重为 100/100/60，等比不同，未采用"),
            Provenance(level=RuleLevel.PROJECT_REFERENCE, project="jiwenxu/ruan",
                       concept="residual qi weight 0.25"),
            Provenance(level=RuleLevel.PROJECT_REFERENCE, project="Horosa/ruan",
                       concept="month multiplier 1.5（Atlas 为 ×2，未采用）"),
            Provenance(level=RuleLevel.PROJECT_REFERENCE, project="bazi-atlas/Horosa",
                       concept="strong/weak thresholds 0.55/0.45"),
            Provenance(level=RuleLevel.ENGINEERING_HEURISTIC, project="Tianze",
                       concept="extreme strong/weak thresholds 0.65/0.35（五级 verdict 扩展，无上游来源）"),
            Provenance(level=RuleLevel.ENGINEERING_HEURISTIC, project="Tianze",
                       concept="加权 ratio 模型整体（工程量化，非传统命理公认算法）"),
        ]


_ROLE_WEIGHT_ATTR = {"本气": "main_qi_weight", "中气": "middle_qi_weight", "余气": "residual_qi_weight"}


class WeightedStrengthAnalyzer:
    analyzer_id = "weighted-v1"
    name = "weighted"

    def __init__(self, params: WeightedStrengthParams | None = None) -> None:
        self.params = params or WeightedStrengthParams()

    def _effect(self, unit_elem: Element, dm_elem: Element) -> str:
        if unit_elem == dm_elem or _GEN[unit_elem] == dm_elem:
            return "support"
        return "drain"

    def analyze(self, facts: StrengthFacts) -> StrengthMethodResult:
        p = self.params
        dm_elem = facts.day_master_element
        contributions: list[Contribution] = []
        support_total = 0.0
        drain_total = 0.0

        for position, stem, branch in facts.pillar_units:
            mult = p.month_multiplier if position == "month" else 1.0
            if stem and position != "day":
                # 日主自身的天干不是计分单位（它是分类主体，ADR-022）
                elem = STEM_ELEMENT[stem]
                effect = self._effect(elem, dm_elem)
                value = round(p.visible_stem_weight * mult, 4)
                contributions.append(Contribution(
                    factor=f"stem:{position}",
                    effect=effect,  # type: ignore[arg-type]
                    value=value,
                    reason=(
                        f"{POS_CN[position]}干{stem}（{ELEM_CN[elem]}）"
                        f"{'与日主同类/生日主，归帮扶' if effect == 'support' else '泄耗克日主，归克泄耗'}"
                        f" × {p.visible_stem_weight}" + (f" × {mult}（月令乘数）" if mult != 1.0 else "")
                    ),
                ))
                if effect == "support":
                    support_total += value
                else:
                    drain_total += value
            if branch:
                for hidden, role in HIDDEN_STEMS[branch]:
                    elem = STEM_ELEMENT[hidden]
                    effect = self._effect(elem, dm_elem)
                    base = getattr(p, _ROLE_WEIGHT_ATTR[role])
                    value = round(base * mult, 4)
                    contributions.append(Contribution(
                        factor=f"hidden:{position}:{role}",
                        effect=effect,  # type: ignore[arg-type]
                        value=value,
                        reason=(
                            f"{POS_CN[position]}支{branch}藏{hidden}（{ELEM_CN[elem]}·{role}）"
                            f"{'归帮扶' if effect == 'support' else '归克泄耗'} × {base}"
                            + (f" × {mult}（月令乘数）" if mult != 1.0 else "")
                        ),
                    ))
                    if effect == "support":
                        support_total += value
                    else:
                        drain_total += value

        support_total = round(support_total, 4)
        drain_total = round(drain_total, 4)
        total = round(support_total + drain_total, 4)
        note_parts = ["工程量化方法之一，非官方唯一真值（R20）；通根/得令不重复计分（ADR-022）。"]

        if total == 0:
            return StrengthMethodResult(
                analyzer_id=self.analyzer_id,
                name=self.name,
                verdict=None,
                score=None,
                params=p.to_dict(),
                contributions=contributions,
                provenance=p.provenance(),
                evidence=["命局无任何可计分单位（未知时辰且无干支？）"],
                note="；".join(note_parts + ["总分为 0，无法给出 verdict。"]),
            )

        score = round(support_total / total, 4)
        if score >= p.extreme_strong_threshold:
            verdict = "极强"
        elif score >= p.strong_threshold:
            verdict = "偏强"
        elif score <= p.extreme_weak_threshold:
            verdict = "极弱"
        elif score <= p.weak_threshold:
            verdict = "偏弱"
        else:
            verdict = "中和"

        evidence = [
            f"support 总分 {support_total} / drain 总分 {drain_total}（明细见 contributions）",
            f"score = {support_total} / {total} = {score}",
            f"verdict 规则：≥{p.extreme_strong_threshold} 极强；≥{p.strong_threshold} 偏强；"
            f"≤{p.extreme_weak_threshold} 极弱；≤{p.weak_threshold} 偏弱；其余中和",
            f"本次判定：{verdict}",
        ]
        return StrengthMethodResult(
            analyzer_id=self.analyzer_id,
            name=self.name,
            verdict=verdict,
            score=score,
            params=p.to_dict(),
            contributions=contributions,
            provenance=p.provenance(),
            evidence=evidence,
            note="；".join(note_parts),
        )
