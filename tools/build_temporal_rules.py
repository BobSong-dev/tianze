"""M13 · 岁运知识规则构建：RuleCandidate（normalized）→ ExecutableRule(domain=temporal)。

CURATION 表逐条人工指定（AI 整理，MACHINE_CURATED——升级需真人对照扫描件）：
- 有原文引文的候选（SS-R09/SS-R10/DTZ-35/DTZ-09/SPZY-28）→ provenance 带 CLASSICAL_EXPLICIT
- 概念通说（伏吟/反吟/岁运并临/天克地冲）→ PROJECT_REFERENCE，如实注明"知识库暂无引文链"
- 检测口径（位置/阈值判定）→ ENGINEERING_HEURISTIC

输出：knowledge/rules/temporal/rules.json
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tianze.knowledge.temporal_rules import TEMPORAL_RULES_PATH  # noqa: E402

OUT = os.path.dirname(TEMPORAL_RULES_PATH)


def _quote_note(quote: str) -> str:
    return (quote[:60] + "…") if len(quote) > 60 else quote


def build_rule(rid: str, candidate_id: str, category: str, label: str,
               conditions: list[dict], effects: list[dict],
               provenance: list[dict], quality: str,
               normalization_notes: str | None = None,
               conflict_note: str | None = None) -> dict:
    return {
        "id": rid,
        "candidateId": candidate_id,
        "domain": "temporal",
        "category": category,
        "label": label,
        "conditions": conditions,
        "effects": effects,
        "exceptions": [],
        "modifiers": [],
        "normalizationNotes": normalization_notes,
        "conflictNote": conflict_note,
        "provenance": provenance,
        "quality": quality,
        "status": "active",
        "verification": {
            "status": "MACHINE_CURATED",
            "verifiedBy": "tianze-pipeline:build_temporal_rules.py",
            "verifiedAt": None,
            "method": "ai_curation",
            "sourceChecked": True,
            "notes": "M13 岁运规则 curation 由 AI 依候选原文完成（非人工）；"
                     "升级 SOURCE_ALIGNED/HUMAN_VERIFIED 需真人对照扫描件",
        },
        "accuracyMatrix": {
            "traceability": "PASS",
            "textAccuracy": "UNVERIFIED",
            "interpretationAccuracy": "MACHINE_CURATED",
            "engineAccuracy": "TESTED",
        },
    }


def main() -> int:
    # 引文取自 normalized 候选（原文链）
    ss_r09_quote = ("《继善篇》云，'日犯岁君，灾殃必重，五行有救，其年反必为财，四柱无情，故论名为克岁'，"
                    "克岁总非吉朕，然有有情无情之别。")
    ss_r10_quote = "刃头财者，支逢阳刃、干见财星也，名销镕煞……禄头财者，支逢临官、干带财星也，名捆缛煞……流年遇之。"
    dtz_35_quote = "杂气财官……必须财官为用，而干不透出、支不会合，见运程引出，方为真正之杂气财官格也。"
    dtz_09_quote = "支神只以冲为重，刑与穿兮动不动。……刑、冲、害三者之中以冲为重，刑害为轻。"
    spzy_28_quote = "流年者，本年之太岁也……太岁为一岁之尊神，管一年之吉凶，又名游行太岁。"

    rules = [
        build_rule(
            "TR-SS-R09", "SS-R09", "suijun", "日犯岁君（流年干为日主所克）",
            conditions=[{"field": "dayMasterKeAnnualStem", "operator": "eq", "value": True}],
            effects=[{"kind": "note",
                      "text": "日犯岁君结构：检查继善篇救应法（克者→救神映射），输出有救/无救观察"}],
            provenance=[
                {"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库（用户提供 zip）",
                 "concept": "守素室丛谈·日犯岁君节（SS-R09）"},
                {"level": "CLASSICAL_EXPLICIT", "project": None,
                 "concept": "古籍原文引文（《继善篇》救应之法，经守素室丛谈页码定位）",
                 "note": _quote_note(ss_r09_quote)},
                {"level": "TIANZE_NORMALIZATION", "project": "Tianze",
                 "concept": "救应映射结构化（克者干→救神干集合）；效果仅输出结构观察，不输出吉凶"},
            ],
            quality="B",
            normalization_notes="「灾殃必重/反必为财」为原书吉凶断语，Tianze 仅执行结构条件与救应观察；"
                                "岁君干头为财的判定 = 日主克流年天干（五行相克）。",
        ),
        build_rule(
            "TR-SS-R10A", "SS-R10", "ren tou cai", "刃头财（流年支阳刃+干财星）",
            conditions=[{"field": "annualBranch", "operator": "eq", "value": "YANG_STEM_REN[dayMaster]"},
                        {"field": "annualStemTenGod", "operator": "in", "value": ["正财", "偏财"]}],
            effects=[{"kind": "note", "text": "流年构成刃头财结构（销镕煞）；记录组合与十神"}],
            provenance=[
                {"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库（用户提供 zip）",
                 "concept": "守素室丛谈·刃头财/禄头财节（SS-R10）"},
                {"level": "CLASSICAL_EXPLICIT", "project": None,
                 "concept": "古籍原文引文（刃头财定义，经守素室丛谈页码定位）",
                 "note": _quote_note(ss_r10_quote)},
                {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
                 "concept": "阳刃取 YANG_STEM_REN 表（阴干无刃口径 R24）；财星 = ten_god∈{正财,偏财}"},
            ],
            quality="B",
        ),
        build_rule(
            "TR-SS-R10B", "SS-R10", "lu tou cai", "禄头财（流年支禄位+干财星）",
            conditions=[{"field": "annualBranch", "operator": "eq", "value": "STEM_LU[dayMaster]"},
                        {"field": "annualStemTenGod", "operator": "in", "value": ["正财", "偏财"]}],
            effects=[{"kind": "note", "text": "流年构成禄头财结构（捆缛煞）；记录组合与十神"}],
            provenance=[
                {"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库（用户提供 zip）",
                 "concept": "守素室丛谈·刃头财/禄头财节（SS-R10）"},
                {"level": "CLASSICAL_EXPLICIT", "project": None,
                 "concept": "古籍原文引文（禄头财定义，经守素室丛谈页码定位）",
                 "note": _quote_note(ss_r10_quote)},
                {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
                 "concept": "禄位取 STEM_LU 表（R24）；财星 = ten_god∈{正财,偏财}"},
            ],
            quality="B",
        ),
        build_rule(
            "TR-DTZ-35", "DTZ-35", "chong yue ling", "杂气财官运程引出候选",
            conditions=[{"field": "monthBranch", "operator": "in", "value": ["辰", "戌", "丑", "未"]},
                        {"field": "temporalCombinesMonthBranch", "operator": "exists", "value": None}],
            effects=[{"kind": "note",
                      "text": "月支墓库 + 岁运支三合/六合会合 → 杂气引出候选（观察项，不判格局成败）"}],
            provenance=[
                {"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库（用户提供 zip）",
                 "concept": "滴天髓补注·杂气财官须运程引出（DTZ-35）"},
                {"level": "CLASSICAL_EXPLICIT", "project": None,
                 "concept": "古籍原文引文（杂气财官引出，经补注本定位）",
                 "note": _quote_note(dtz_35_quote)},
                {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
                 "concept": "「引出」判定 = 岁运支与月支三合补齐/六合（复用 TemporalRelation），"
                            "不含冲开墓库（原书明言喜冲之说极不可靠）"},
            ],
            quality="B",
        ),
        build_rule(
            "TR-DTZ-09", "DTZ-09", "chong yue ling", "岁运冲提纲/三刑全备观察",
            conditions=[{"field": "temporalBranchClashesMonthBranch", "operator": "eq", "value": True},
                        {"field": "temporalCompletesSanXing", "operator": "eq", "value": True}],
            effects=[{"kind": "note",
                      "text": "记录岁运支冲月令提纲、三刑因岁运全备的结构观察（冲为重、刑害为轻）"}],
            provenance=[
                {"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库（用户提供 zip）",
                 "concept": "滴天髓补注·支神只以冲为重（DTZ-09）"},
                {"level": "CLASSICAL_EXPLICIT", "project": None,
                 "concept": "古籍原文引文（支神冲重口诀，经补注本定位）",
                 "note": _quote_note(dtz_09_quote)},
                {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
                 "concept": "三刑集 = {寅巳申, 丑戌未, 子卯}；冲 = 六冲表（R9 刑冲命名口径）"},
            ],
            quality="B",
        ),
        build_rule(
            "TR-SPZY-28", "SPZY-28", "taisui", "流年即太岁（术语框架）",
            conditions=[{"field": "annualStem", "operator": "exists", "value": None}],
            effects=[{"kind": "note",
                      "text": "记录流年干支即太岁的术语框架；Tianze 不做神煞吉凶推断"}],
            provenance=[
                {"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库（用户提供 zip）",
                 "concept": "子平粹言·流年太岁定义（SPZY-28）"},
                {"level": "CLASSICAL_EXPLICIT", "project": None,
                 "concept": "古籍原文引文（流年太岁定义，经子平粹言评注本定位）",
                 "note": _quote_note(spzy_28_quote)},
            ],
            quality="B",
        ),
        build_rule(
            "TR-FUYIN-01", "TIANZE-TEMPORAL-01", "fuyin", "伏吟（岁运柱与原局柱相同）",
            conditions=[{"field": "structureType", "operator": "in", "value": ["fuyin"]}],
            effects=[{"kind": "note", "text": "记录伏吟结构（何柱伏吟、来源层）"}],
            provenance=[
                {"level": "PROJECT_REFERENCE", "project": "传统命理通说",
                 "concept": "伏吟概念（反吟伏吟，泪吟吟吟；Tianze 知识库暂无原文引文链，如实标注）"},
                {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
                 "concept": "检测 = 岁运干支与原局四柱干支完全相同（temporal.py structures.type=fuyin）"},
            ],
            quality="C",
            conflict_note="伏吟古有「反吟伏吟、泣哭淋淋」之说，属吉凶断语，Tianze 不执行；"
                          "仅输出相同柱位结构。",
        ),
        build_rule(
            "TR-FANYIN-01", "TIANZE-TEMPORAL-02", "fanyin", "反吟（岁运柱天克地冲原局柱）",
            conditions=[{"field": "structureType", "operator": "in", "value": ["fanyin"]}],
            effects=[{"kind": "note", "text": "记录反吟结构（何柱被冲克、来源层）"}],
            provenance=[
                {"level": "PROJECT_REFERENCE", "project": "传统命理通说",
                 "concept": "反吟概念（天克地冲；Tianze 知识库暂无原文引文链，如实标注）"},
                {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
                 "concept": "检测口径 v1 = 岁运支与原局支六冲（干克维度暂缺，见 temporal.py 注）"},
            ],
            quality="C",
        ),
        build_rule(
            "TR-BINGLIN-01", "TIANZE-TEMPORAL-03", "binglin", "岁运并临（大运=流年干支）",
            conditions=[{"field": "structureType", "operator": "in", "value": ["binglin"]}],
            effects=[{"kind": "note", "text": "记录岁运并临结构（干支完全相同的岁运层）"}],
            provenance=[
                {"level": "PROJECT_REFERENCE", "project": "传统命理通说",
                 "concept": "岁运并临概念（Tianze 知识库暂无原文引文链，如实标注）"},
                {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
                 "concept": "检测 = 大运干支 == 流年干支"},
            ],
            quality="C",
        ),
        build_rule(
            "TR-TIANKEDI-01", "TIANZE-TEMPORAL-04", "tiankedi", "天克地冲（流年克冲大运）",
            conditions=[{"field": "structureType", "operator": "in", "value": ["tiankedi"]}],
            effects=[{"kind": "note", "text": "记录天克地冲结构（流年天干克大运天干+流年支冲大运支）"}],
            provenance=[
                {"level": "PROJECT_REFERENCE", "project": "传统命理通说",
                 "concept": "天克地冲概念（Tianze 知识库暂无原文引文链，如实标注）"},
                {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
                 "concept": "检测 = 流年干克大运干（五行相克）且流年支冲大运支（六冲）"},
            ],
            quality="C",
        ),
    ]

    os.makedirs(OUT, exist_ok=True)
    payload = {
        "domain": "temporal",
        "schemaVersion": "1.1.0",
        "count": len(rules),
        "description": "岁运规则（M13）：Source→Quote→RuleCandidate→ExecutableRule(domain=temporal)→TemporalEvidence",
        "rules": rules,
    }
    with open(TEMPORAL_RULES_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"岁运规则构建完成：{len(rules)} 条 → {TEMPORAL_RULES_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
