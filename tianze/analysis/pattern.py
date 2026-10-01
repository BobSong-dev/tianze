"""M5 格局引擎：候选识别（R23/R24）+ 证据化评估（R25）。

取格口径（PROJECT_REFERENCE：Horosa baziGejuYongShen / jiwenxu pattern.py 的
月令取格骨架；未见古籍原文前不标 CLASSICAL_EXPLICIT）：
1. 禄刃优先：月支 == 日主禄位 → 建禄格；月支 == 阳干帝旺位 → 阳刃格（R24）。
2. 否则按月支藏干本气→中气→余气顺序，取第一个"透出（年/月/时干同字）且
   十神非比劫"者为首选候选；其后透出者依次保留为次候选（中余同时透场景）。
3. 皆不透 → 取月令本气十神为格（本气为比劫时无正格候选，记 note）。
4. 比肩/劫财不立正格；特殊格（从/专旺/化气）M5 不支持，见 docs/PATTERN.md。

评估（R25）：每条 support/damage/rescue 都是显式规则（rule_id + 事实描述 +
provenance），status 仅是摘要；证据不足或候选缺失 → 待定。
"""

from __future__ import annotations

from typing import Literal, Sequence

from tianze.domain.models import (
    PatternAnalysis,
    PatternCandidate,
    PatternEvaluation,
    PatternFactor,
    Position,
    Provenance,
    RuleLevel,
    TenGod,
)
from tianze.ganzhi.tables import (
    HIDDEN_STEMS,
    STEM_LU,
    YANG_STEM_REN,
    ten_god,
)

GE_NAME: dict[TenGod, str] = {
    TenGod.ZHENG_GUAN: "正官格",
    TenGod.QI_SHA: "七杀格",
    TenGod.ZHENG_CAI: "正财格",
    TenGod.PIAN_CAI: "偏财格",
    TenGod.ZHENG_YIN: "正印格",
    TenGod.PIAN_YIN: "偏印格",
    TenGod.SHI_SHEN: "食神格",
    TenGod.SHANG_GUAN: "伤官格",
}

_TAKEN_FROM_MONTH_PROV = Provenance(
    level=RuleLevel.PROJECT_REFERENCE,
    project="Horosa/jiwenxu",
    concept="月令取格：禄刃优先；本气→中气→余气透干优先；皆不透取本气",
    note="子平通说骨架，古籍原文核校留待 Classical Knowledge Integration",
)

_RULE_PROV = Provenance(
    level=RuleLevel.PROJECT_REFERENCE,
    project="jiwenxu(pattern.validate)/Horosa(GE_JI)",
    concept="格局成败救应规则（支持/破坏/救应条件）",
    note="规则条件为工程化转写，古籍原文核校留待知识库接入",
)

_POS_CN = {"year": "年", "month": "月", "day": "日", "hour": "时"}

_BI_JIE = {TenGod.BI_JIAN, TenGod.JIE_CAI}
_YIN = {TenGod.ZHENG_YIN, TenGod.PIAN_YIN}
_CAI = {TenGod.ZHENG_CAI, TenGod.PIAN_CAI}
_GUAN = {TenGod.ZHENG_GUAN}
_SHA = {TenGod.QI_SHA}


def derive_pattern_candidates(
    day_master: str,
    month_branch: str,
    stems: Sequence[str | None],
    positions: Sequence[Position],
) -> tuple[list[PatternCandidate], list[str]]:
    """返回（候选列表[按优先级排序]，说明性 note 列表）。"""
    if len(stems) != len(positions):
        raise ValueError("stems/positions 长度不一致")
    notes: list[str] = []
    visible: dict[str, Position] = {}
    for s, p in zip(stems, positions):
        if s and p != "day":
            visible.setdefault(s, p)  # 首次出现位置（年<月<时）

    # —— 禄刃优先（R24）——
    if STEM_LU[day_master] == month_branch:
        cand = PatternCandidate(
            name="建禄格",
            category="regular",
            month_branch=month_branch,
            source_stem=day_master,
            ten_god=TenGod.BI_JIAN,
            via="禄位",
            evidence=[
                f"月支{month_branch}为日主{day_master}之禄（临官位，R24 禄位表）",
                "禄位表口径：不要求月令本气为比劫（Horosa 口径以本气比劫为准，如戊日巳月，两派差异已记录）",
            ],
            provenance=[_TAKEN_FROM_MONTH_PROV],
        )
        return [cand], notes
    if day_master in YANG_STEM_REN and YANG_STEM_REN[day_master] == month_branch:
        cand = PatternCandidate(
            name="阳刃格",
            category="regular",
            month_branch=month_branch,
            source_stem=day_master,
            ten_god=TenGod.JIE_CAI,
            via="阳刃位",
            evidence=[
                f"月支{month_branch}为阳干日主{day_master}之刃（帝旺位，R24）",
                "阴干无刃为通行口径（阴干刃派别争议见 R24，本引擎不立阴干刃）",
            ],
            provenance=[_TAKEN_FROM_MONTH_PROV],
        )
        return [cand], notes

    # —— 月令藏干取格（本气→中气→余气）——
    candidates: list[PatternCandidate] = []
    for hidden, role in HIDDEN_STEMS[month_branch]:
        god = ten_god(day_master, hidden)
        if god in _BI_JIE:
            notes.append(
                f"月令藏{hidden}为日主之{god.value}，不立正格；"
                f"月支{month_branch}非{day_master}之禄刃位（R24），正格候选缺失"
            )
            continue
        if hidden in visible:
            pos = visible[hidden]
            candidates.append(PatternCandidate(
                name=GE_NAME[god],
                category="regular",
                month_branch=month_branch,
                source_stem=hidden,
                ten_god=god,
                via=f"{role}透干",
                evidence=[
                    f"月支{month_branch}藏{hidden}（{role}）",
                    f"{hidden}为日主{day_master}之{god.value}",
                    f"{hidden}透出于{_POS_CN[pos]}干",
                ],
                provenance=[_TAKEN_FROM_MONTH_PROV],
            ))
    if not candidates:
        main_hidden, main_role = HIDDEN_STEMS[month_branch][0]
        main_god = ten_god(day_master, main_hidden)
        if main_god not in _BI_JIE:
            candidates.append(PatternCandidate(
                name=GE_NAME[main_god],
                category="regular",
                month_branch=month_branch,
                source_stem=main_hidden,
                ten_god=main_god,
                via="本气不透取本气",
                evidence=[
                    f"月支{month_branch}藏{main_hidden}（{main_role}）",
                    f"{main_hidden}为日主{day_master}之{main_god.value}",
                    "月令藏干均不透出干，按回退口径取月令本气为格（R23）",
                ],
                provenance=[_TAKEN_FROM_MONTH_PROV],
            ))
        else:
            notes.append("月令本气为比劫且不透、非禄刃位：无正格候选（特殊格未支持，见 docs/PATTERN.md）")
    return candidates, notes


# ---------------- M5.2 评估规则表（R25） ----------------

# (rule_id, name, 触及十神集合, detail 模板)
_SUPPORT_RULES: dict[str, list[tuple[str, str, set[TenGod], str]]] = {
    "正官格": [
        ("PAT-GUAN-S1", "财生官", _CAI, "财星透干，生扶正官"),
        ("PAT-GUAN-S2", "印护官", _YIN, "印星透干，护官化伤"),
    ],
    "七杀格": [
        ("PAT-SHA-S1", "食神制杀", {TenGod.SHI_SHEN}, "食神透干，制衡七杀"),
        ("PAT-SHA-S2", "杀印相生", _YIN, "印星透干，化杀生身"),
    ],
    "正财格": [
        ("PAT-CAI-S1", "食神生财", {TenGod.SHI_SHEN}, "食神透干，生扶财星"),
        ("PAT-CAI-S2", "财旺生官", _GUAN, "正官透干，财气流通"),
    ],
    "偏财格": [
        ("PAT-CAI2-S1", "食神生财", {TenGod.SHI_SHEN}, "食神透干，生扶财星"),
        ("PAT-CAI2-S2", "财旺生官", _GUAN, "正官透干，财气流通"),
    ],
    "正印格": [
        ("PAT-YIN-S1", "官印相生", _GUAN, "正官透干，生扶印星"),
    ],
    "偏印格": [
        ("PAT-YIN2-S1", "杀印相生", _SHA, "七杀透干，生扶偏印"),
    ],
    "食神格": [
        ("PAT-SS-S1", "食神生财", _CAI, "财星透干，食神有所生"),
    ],
    "伤官格": [
        ("PAT-SG-S1", "伤官生财", _CAI, "财星透干，伤官有所生"),
        ("PAT-SG-S2", "伤官佩印", _YIN, "印星透干，调济伤官"),
    ],
}

# (rule_id, name, 触及十神集合, 附加条件, detail, 救应条件, 救应名, 救应 detail)
_DAMAGE_RULES: dict[str, list[tuple]] = {
    "正官格": [
        ("PAT-GUAN-D1", "伤官见官", {TenGod.SHANG_GUAN}, None,
         "伤官透干，直克正官", _YIN, "印制伤护官", "印星透干，制伤护官（有救应）"),
        ("PAT-GUAN-D2", "官杀混杂", _SHA, None,
         "七杀透干，官杀混杂", None, None, None),
    ],
    "七杀格": [
        ("PAT-SHA-D1", "官杀混杂", _GUAN, None,
         "正官透干，官杀混杂", None, None, None),
        ("PAT-SHA-D2", "财生杀攻身", _CAI,
         lambda gods: TenGod.SHI_SHEN not in gods and not (gods & _YIN),
         "财星透干且无食神制、无印化，财党生杀攻身", None, None, None),
    ],
    "正财格": [
        ("PAT-CAI-D1", "比劫夺财", _BI_JIE, None,
         "比劫透干，争夺财星", _GUAN | _SHA, "官杀制比劫护财", "官杀透干，制比劫而护财（有救应）"),
    ],
    "偏财格": [
        ("PAT-CAI2-D1", "比劫夺财", _BI_JIE, None,
         "比劫透干，争夺财星", _GUAN | _SHA, "官杀制比劫护财", "官杀透干，制比劫而护财（有救应）"),
    ],
    "正印格": [
        ("PAT-YIN-D1", "财破印", _CAI, None,
         "财星透干，克破印星", _GUAN | _SHA, "官杀通关化财生印", "官杀透干，通关化财生印（有救应）"),
    ],
    "偏印格": [
        ("PAT-YIN2-D1", "财破印", _CAI, None,
         "财星透干，克破偏印", _GUAN | _SHA, "官杀通关化财生印", "官杀透干，通关化财生印（有救应）"),
    ],
    "食神格": [
        ("PAT-SS-D1", "枭神夺食", {TenGod.PIAN_YIN}, None,
         "偏印（枭神）透干，夺食", _CAI, "财能制枭护食", "财星透干，制枭护食（有救应）"),
    ],
    "伤官格": [
        ("PAT-SG-D1", "伤官见官", _GUAN, None,
         "正官透干，伤官见官", _YIN, "印制伤", "印星透干，制伤（有救应）"),
    ],
}

_CONFLICT_MULTI = ("PAT-MULTI", "多候选并存", "月令多藏干同时透出：本评估仅针对首选候选（R23 优先级），其余候选保留未评")


def evaluate_pattern(
    candidate: PatternCandidate,
    day_master: str,
    other_stems: Sequence[tuple[str, Position]],
) -> PatternEvaluation:
    """对单个候选做证据化评估。other_stems = 年/月/时干（日主除外）。"""
    visible_gods: set[TenGod] = set()
    details: list[str] = []
    for stem, position in other_stems:
        god = ten_god(day_master, stem)
        visible_gods.add(god)
        details.append(f"{_POS_CN[position]}干{stem}（{god.value}）")

    supports: list[PatternFactor] = []
    for rule_id, name, gods, detail in _SUPPORT_RULES.get(candidate.name, []):
        if gods & visible_gods:
            hit = [d for d in details if any(t.value in d for t in gods)]
            supports.append(PatternFactor(
                kind="support", rule_id=rule_id, name=name,
                detail=f"{detail}（{'、'.join(hit)}）", provenance=_RULE_PROV,
            ))

    damages: list[PatternFactor] = []
    rescues: list[PatternFactor] = []
    for rule_id, name, gods, extra, detail, r_gods, r_name, r_detail in _DAMAGE_RULES.get(candidate.name, []):
        if not (gods & visible_gods):
            continue
        if extra is not None and not extra(visible_gods):
            continue
        damages.append(PatternFactor(
            kind="damage", rule_id=rule_id, name=name,
            detail=f"{detail}（{'、'.join(d for d in details if any(t.value in d for t in gods))}）",
            provenance=_RULE_PROV,
        ))
        if r_gods and (r_gods & visible_gods):
            rescues.append(PatternFactor(
                kind="rescue", rule_id=rule_id + "-R", name=r_name,
                detail=r_detail, provenance=_RULE_PROV, related=[rule_id],
            ))

    conflicts: list[PatternFactor] = []
    if TenGod.SHI_SHEN in visible_gods and (visible_gods & _YIN) and candidate.name == "七杀格":
        conflicts.append(PatternFactor(
            kind="conflict", rule_id="PAT-SHA-C1", name="制化两立",
            detail="食神制杀与印星化杀并见：jiwenxu 判破、Horosa 记瑕，Tianze 仅记录冲突不裁决（R25）",
            provenance=_RULE_PROV,
        ))

    rescued_ids = {rid for f in rescues for rid in f.related}
    unrescued = [d for d in damages if d.rule_id not in rescued_ids]
    if candidate.name not in _DAMAGE_RULES:  # 建禄/阳刃：v1 未配置评估规则
        status: Literal["成立", "有瑕", "受损", "破格", "待定"] = "待定"
        note = "禄刃格的成败评估规则 M5.2 v1 未配置（见 docs/PATTERN.md），仅保留候选证据。"
    elif not unrescued:
        status = "有瑕" if damages else "成立"
        note = None if damages else ("无支持因素亦无破坏因素。" if not supports else None)
    elif len(unrescued) == 1:
        status = "受损"
        note = f"未获救应的破坏因素：{unrescued[0].name}。"
    else:
        status = "破格"
        note = "未获救应的破坏因素 ≥2：" + "、".join(d.name for d in unrescued) + "。"
    return PatternEvaluation(
        candidate=candidate,
        supports=supports,
        damages=damages,
        rescues=rescues,
        conflicts=conflicts,
        status=status,
        note=note,
    )


def analyze_pattern(
    day_master: str,
    month_branch: str,
    stems: Sequence[str | None],
    positions: Sequence[Position],
) -> PatternAnalysis:
    candidates, notes = derive_pattern_candidates(day_master, month_branch, stems, positions)
    other_stems = [(s, p) for s, p in zip(stems, positions) if s and p != "day"]
    evaluation = None
    if candidates:
        evaluation = evaluate_pattern(candidates[0], day_master, other_stems)
        if len(candidates) > 1:
            evaluation = evaluation.model_copy(update={
                "conflicts": list(evaluation.conflicts) + [PatternFactor(
                    kind="conflict", rule_id=_CONFLICT_MULTI[0], name=_CONFLICT_MULTI[1],
                    detail=_CONFLICT_MULTI[2] + f"（共 {len(candidates)} 个候选）",
                    provenance=_RULE_PROV,
                )],
            })
    return PatternAnalysis(
        candidates=candidates,
        primary_index=0 if candidates else None,
        evaluation=evaluation,
        note="；".join(notes) if notes else None,
    )
