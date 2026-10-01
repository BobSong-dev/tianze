"""M6 · 调候分析器（TiaoHou）——独立于旺衰的分析方法。

只回答：调候体系认为需要什么（desired）、命局是否已有（present）、
有哪些条件与例外、依据是什么（规则 → 候选 → 原文 → 页码）。
禁止输出吉凶（"因此富贵"一类结论不存在于本模块）。

规则来源：knowledge/rules/tiaohou/rules.json（穷通宝鉴评注逐月调候，
人工复核 curation → ExecutableRule，120 格全覆盖）。
"""

from __future__ import annotations

from tianze.domain.models import (
    KnowledgeSource,
    Position,
    ProvenanceRef,
    TiaoHouRecommendation,
    TiaoHouResult,
)
from tianze.knowledge.loader import load_tiaohou_conflicts, load_tiaohou_rules

_EVIDENCE_HEADER = "调候口径：穷通宝鉴评注逐月取用（原文/徐注分层，页码可回查）"


def _stem_positions(stems: dict[Position, str | None], target: str) -> list[Position]:
    return [pos for pos, s in stems.items() if s == target]


def analyze_tiaohou(
    day_master: str,
    month_branch: str,
    stems: dict[Position, str | None],
    season_phase: str | None = None,
) -> TiaoHouResult:
    """stems: 四柱天干映射（含 day）；season_phase: 节气深浅（如 雨水后/清明后，可选）。"""
    all_rules = load_tiaohou_rules()
    matched = [
        r for r in all_rules
        if any(c.field == "dayMaster" and c.value == day_master for c in r.conditions)
        and any(c.field == "monthBranch" and c.value == month_branch for c in r.conditions)
    ]
    if not matched:
        return TiaoHouResult(
            day_master=day_master,
            month_branch=month_branch,
            resolved=False,
            evidence=["该（日主×月支）组合在调候知识库中无规则：UNRESOLVED（不编造）"],
            note="资料不足，显式标记 UNRESOLVED。",
        )

    context: dict[str, str] = {"dayMaster": day_master, "monthBranch": month_branch}
    if season_phase:
        context["seasonPhase"] = season_phase

    def _conditions_met(conds: list[RuleCondition]) -> bool:
        for c in conds:
            field, op, value = c.field, c.operator, c.value
            if field in ("dayMaster", "monthBranch"):
                continue  # 匹配条件已过滤
            actual = context.get(field)
            if op == "eq" and actual != value:
                return False
            if op == "ne" and actual == value:
                return False
            if op == "in" and actual not in (value or []):
                return False
            if op == "not_in" and actual in (value or []):
                return False
            if op == "exists" and not actual:
                return False
            if op == "not_exists" and actual:
                return False
        return True

    conditions: list[RuleCondition] = []
    exceptions: list[RuleCondition] = []
    conflicts: list[str] = []
    evidence: list[str] = [_EVIDENCE_HEADER]
    rec_map: dict[tuple[str, str], dict] = {}  # (stem, priority) → data

    for rule in matched:
        active = _conditions_met(rule.conditions)
        if not active:
            conditions.extend(c.model_dump(by_alias=True) for c in rule.conditions)
            evidence.append(f"{rule.id}：条件未满足（{'；'.join(c.field + '=' + str(c.value) for c in rule.conditions if c.field not in ('dayMaster', 'monthBranch')) or '节气/结构条件'}），本规则休眠")
            continue
        rule_conflicts = [c for c in load_tiaohou_conflicts() if rule.id in c["ruleIds"]]
        for c in rule_conflicts:
            line = f"{c['conditionOverlap']}：{c['description']}（处理：{c['resolution']}）"
            if line not in conflicts:
                conflicts.append(line)
        if rule.conflict_note and rule.conflict_note not in conflicts:
            conflicts.append(f"{rule.id}：{rule.conflict_note}")
        exceptions.extend(x.model_dump(by_alias=True) for x in rule.exceptions)
        conditions.extend(
            c.model_dump(by_alias=True) for c in rule.conditions
            if c.field not in ("dayMaster", "monthBranch")
        )
        for eff in rule.effects:
            if eff.kind == "avoidStem":
                avoid_stem = eff.target_stem
                positions = _stem_positions(stems, avoid_stem)
                if positions:
                    evidence.append(
                        f"{rule.id}：例外命中——忌 {avoid_stem} 而命局{'、'.join(positions)}见之"
                        f"（{eff.condition_note or ''}）"
                    )
                continue
            if eff.kind != "needStem" or not eff.target_stem:
                continue
            key = (eff.target_stem, eff.priority or "secondary")
            if key not in rec_map:
                positions = _stem_positions(stems, eff.target_stem)
                rec_map[key] = {
                    "targetStem": eff.target_stem,
                    "element": eff.element,
                    "priority": eff.priority or "secondary",
                    "present": bool(positions),
                    "positions": positions,
                    "ruleIds": [rule.id],
                    # 推荐级 provenance 不携带 TIANZE_NORMALIZATION 的整理注释
                    # （那是规则层的机器化痕迹，避免 AI 摘要语混入结论字段）
                    "provenance": [
                        p_ref.model_copy(update={"note": None})
                        if p_ref.level == "TIANZE_NORMALIZATION" else p_ref
                        for p_ref in rule.provenance
                    ],
                    "quality": rule.quality,
                    "quote": next((p.note for p in rule.provenance if p.level == "CLASSICAL_EXPLICIT"), None),
                    "source": rule.source,
                }
            else:
                rec_map[key]["ruleIds"].append(rule.id)

    order = {"primary": 0, "secondary": 1, "tertiary": 2}
    recommendations = sorted(
        (TiaoHouRecommendation(**data) for data in rec_map.values()),
        key=lambda r: (order.get(r.priority, 9), r.target_stem),
    )
    for r in recommendations:
        pos_txt = "、".join(r.positions) if r.positions else "未见"
        evidence.append(
            f"{'、'.join(r.rule_ids)}：需要 {r.target_stem}（{r.element}·{r.priority}）"
            f"— 命局{'已见（' + pos_txt + '）' if r.present else '未见'}"
        )

    return TiaoHouResult(
        day_master=day_master,
        month_branch=month_branch,
        resolved=True,
        recommendations=recommendations,
        evidence=evidence,
        conflicts=conflicts,
        conditions=conditions,
        exceptions=exceptions,
        rule_ids=[r.id for r in matched],
        note="调候结论仅为体系内需要/有无判断，不构成任何命运断语（M6 边界）。",
    )
