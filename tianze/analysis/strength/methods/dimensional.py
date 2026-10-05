"""M4.1 维度分析器（dimension）：得令 / 得地 / 得势，纯定性，零评分（R17）。

规则全部显式：
- 得令 = 月令状态为旺（R17；"相"不得令但注明）；
- 得地 = 日主在四支藏干中存在同字之根（R15）；
- 得势 = 年/月/时天干中比劫或印星（比肩/劫财/正印/偏印）出现 ≥2（结构阈值，
  非古籍量化——这是作者口径，公开声明于 R17）。
"""

from __future__ import annotations

from tianze.analysis.strength.base import StrengthFacts
from tianze.domain.models import DimensionResult, DimensionalEvidence, StrengthMethodResult, TenGod
from tianze.ganzhi.tables import ten_god

_POS_CN = {"year": "年", "month": "月", "day": "日", "hour": "时", "luck": "大运", "annual": "流年", "monthly": "流月", "daily": "流日"}
_HELPFUL: frozenset[TenGod] = frozenset({
    TenGod.BI_JIAN, TenGod.JIE_CAI, TenGod.PIAN_YIN, TenGod.ZHENG_YIN,
})
DE_SHI_THRESHOLD = 2  # R17：印比透干 ≥2 判得势（结构规则，非古籍量化）


class DimensionalStrengthAnalyzer:
    analyzer_id = "dimensional_v1"
    name = "dimension"

    def analyze(self, facts: StrengthFacts) -> StrengthMethodResult:
        # —— 得令 ——
        rel = facts.month_command.relation_to_day_master
        de_ling_reasons = [
            rel.rule,
            f"日主{facts.day_master}月令状态【{rel.state.value}】→ "
            + ("得令" if rel.in_command else "不得令（R17：严格 = 旺）"),
        ]
        if not rel.in_command and rel.state.value == "相":
            de_ling_reasons.append("月令生日主为相：受生但不算得令（R17 严格口径）")
        de_ling = DimensionResult(result=rel.in_command, reason=de_ling_reasons)

        # —— 得地 ——
        if facts.day_master_roots:
            de_di = DimensionResult(
                result=True,
                reason=[r.statement for r in facts.day_master_roots],
            )
        else:
            de_di = DimensionResult(
                result=False,
                reason=[f"日主{facts.day_master}在四柱地支藏干中无任何同字之根（R15 遍历）"],
            )

        # —— 得势 ——
        helpers: list[tuple[str, str, TenGod]] = []
        for stem, position in facts.other_stems:
            god = ten_god(facts.day_master, stem)
            if god in _HELPFUL:
                helpers.append((stem, _POS_CN[position], god))
        if len(helpers) >= DE_SHI_THRESHOLD:
            de_shi_reasons = [f"{pos}干{s}（{g.value}）帮身" for s, pos, g in helpers]
            de_shi_reasons.append(f"印比透干 {len(helpers)} 处 ≥ {DE_SHI_THRESHOLD} → 得势（R17）")
            de_shi = DimensionResult(result=True, reason=de_shi_reasons)
        else:
            de_shi_reasons = [f"{pos}干{s}（{g.value}）帮身" for s, pos, g in helpers]
            de_shi_reasons.append(
                f"印比透干仅 {len(helpers)} 处 < {DE_SHI_THRESHOLD} → 不得势"
                f"（R17 阈值={DE_SHI_THRESHOLD}，结构规则非古籍量化）"
            )
            de_shi = DimensionResult(result=False, reason=de_shi_reasons)

        summary = [
            f"得令：{'是' if de_ling.result else '否'}（月令状态【{rel.state.value}】）",
            f"得地：{'是' if de_di.result else '否'}（{len(facts.day_master_roots)} 处通根）",
            f"得势：{'是' if de_shi.result else '否'}（印比透干 {len(helpers)} 处）",
        ]
        return StrengthMethodResult(
            analyzer_id=self.analyzer_id,
            name=self.name,
            verdict=None,
            strength_evidence=DimensionalEvidence(de_ling=de_ling, de_di=de_di, de_shi=de_shi),
            evidence=summary,
            note="M4.1 定性三维，不评分、不输出强弱 verdict（R17/ADR-017）",
        )
