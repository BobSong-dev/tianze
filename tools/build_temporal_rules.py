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
               source: dict,
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
        "source": source,
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
            source={"sourceKind": "COMMENTARY", "book": "守素室丛谈",
                    "chapter": "日犯岁君", "pages": [2],
                    "sourceFile": "_知识库/_知识库/02-守素室丛谈知识库.md",
                    "confidence": "unverified", "commentator": "徐乐吾（原著）"},
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
            source={"sourceKind": "COMMENTARY", "book": "守素室丛谈",
                    "chapter": "刃头财与禄头财", "pages": [2],
                    "sourceFile": "_知识库/_知识库/02-守素室丛谈知识库.md",
                    "confidence": "unverified", "commentator": "徐乐吾（原著）"},
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
            source={"sourceKind": "COMMENTARY", "book": "守素室丛谈",
                    "chapter": "刃头财与禄头财", "pages": [2],
                    "sourceFile": "_知识库/_知识库/02-守素室丛谈知识库.md",
                    "confidence": "unverified", "commentator": "徐乐吾（原著）"},
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
            source={"sourceKind": "COMMENTARY", "book": "滴天髓补注",
                    "chapter": "杂气财官", "pages": [],
                    "sourceFile": "09p-滴天髓补注/09-滴天髓补注知识库.md",
                    "confidence": "unverified", "commentator": "徐乐吾（补注）"},
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
            source={"sourceKind": "COMMENTARY", "book": "滴天髓补注",
                    "chapter": "支神", "pages": [],
                    "sourceFile": "09p-滴天髓补注/09-滴天髓补注知识库.md",
                    "confidence": "unverified", "commentator": "徐乐吾（补注）"},
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
            "TR-DTZ-11", "DTZ-11", "chong wangshuai", "旺者冲衰衰者拔，衰神冲旺旺者发（旺衰以全局气势言）",
            conditions=[{"field": "temporalBranchClashesNatalBranchFireWater",
                         "operator": "eq", "value": True}],
            effects=[{"kind": "note",
                      "text": "对水火之冲（子午/巳亥）按徐注阵营计数输出旺/衰结构比较；"
                              "吉凶随喜忌（R19 不判喜忌），仅输出旺衰两端"}],
            source={"sourceKind": "COMMENTARY", "book": "滴天髓补注",
                    "chapter": "旺衰", "pages": [],
                    "sourceFile": "09p-滴天髓补注/09-滴天髓补注知识库.md",
                    "confidence": "unverified", "commentator": "徐乐吾（补注）"},
            provenance=[
                {"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库（用户提供 zip）",
                 "concept": "滴天髓补注·旺者冲衰节（DTZ-11）"},
                {"level": "CLASSICAL_EXPLICIT", "project": None,
                 "concept": "古籍原文引文（旺者冲衰衰者拔，衰神冲旺旺者发；徐注例证："
                            "子午冲，原局寅卯巳未戌之神多则午旺子衰，辰申酉亥丑多则子旺午衰）",
                 "note": _quote_note("旺者冲衰衰者拔，衰神冲旺旺者发。……旺衰以全局之气势言。"
                                     "衰者为喜神，则冲而去之为祸；衰者为忌神，冲而去之为吉。"
                                     "旺者为喜神，则冲而发为吉；旺者为忌神，冲而发为祸。")},
                {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
                 "concept": "阵营计数口径（M23）：火营=寅卯巳午未戌、水营=申酉亥子辰丑"
                            "（徐注支持者例证 + 冲端本身入营）；计数含原局+岁运全部可见支，"
                            "平局不裁决；非水火之冲的阵营量化未立——不触发本规则"},
            ],
            quality="B",
            normalization_notes="「衰者为喜冲去为祸……」为喜忌层面的吉凶断语，Tianze 不判喜忌，"
                                "仅输出冲两端的结构旺衰比较（旺者冲衰/衰神冲旺/平局不定）；"
                                "阵营映射只对水火之冲成立（徐注例证范围），其余六冲不量化。",
        ),
        build_rule(
            "TR-SP-08", "DTZ-49", "special-pattern", "假从/假化岁运敏感（行运之别）",
            conditions=[{"field": "jiaCongCandidate", "operator": "exists", "value": None},
                        {"field": "temporalRootOrHelper", "operator": "exists", "value": None}],
            effects=[{"kind": "note",
                      "text": "假从候选 + 岁运根气/印比 → 逆旺气破格风险两说；"
                              "假化候选 + 岁运泄气 → 假化敏感；候选级，不升级"}],
            source={"sourceKind": "COMMENTARY", "book": "滴天髓补注",
                    "chapter": "真从", "pages": [],
                    "sourceFile": "09p-滴天髓补注/09-滴天髓补注知识库.md",
                    "confidence": "unverified", "commentator": "徐乐吾（补注）"},
            provenance=[
                {"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库（用户提供 zip）",
                 "concept": "滴天髓补注·真从之家有几人（DTZ-49）"},
                {"level": "CLASSICAL_EXPLICIT", "project": None,
                 "concept": "古籍原文引文（真从之家有几人？假从亦可发其身；假从=日主有微根"
                            "或有印生助；行运之别：假从行从化旺乡与真从无别，但未交运前"
                            "寒素、运过复初；只要不行逆旺气之乡，无失败之虑）",
                 "note": _quote_note("真从之家有几人？假从亦可发其身；假化之人亦多贵，"
                                     "异姓孤儿能出类。……凡格局纯粹而真者……只要不行逆旺气"
                                     "之乡，无失败之虑。若不纯粹而假……运过之后即回复其"
                                     "原来之状况矣。")},
                {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
                 "concept": "假从判定复用 natal SP-CG-E2 例外注记（微根/印）；岁运根气="
                            "支藏干见日主；印比=十神表；泄气=化神所生五行"},
            ],
            quality="B",
            normalization_notes="「未交运前寒素、运过复初」为行运先后叙事（富贵层面），"
                                "Tianze 仅输出岁运根气/印比/泄气的结构敏感观察；"
                                "逆旺气破格说与顺势说两说并存，不裁决。",
        ),
        build_rule(
            "TR-DTZ-10", "DTZ-10", "an chong an hui", "暗冲暗会/拱夹/暗合/填实（岁运 × 虚神）",
            conditions=[{"field": "temporalXushiInteraction", "operator": "in",
                         "value": ["arch", "arch_fill", "arch_broken", "hidden_combination"]}],
            effects=[{"kind": "note",
                      "text": "岁运与原局虚神的候选级交互观察：成拱/填实/拱位刑冲/暗合；"
                              "非格局不取用（DTZ-26/36），不判吉凶"}],
            source={"sourceKind": "COMMENTARY", "book": "滴天髓补注",
                    "chapter": "暗冲暗会", "pages": [],
                    "sourceFile": "09p-滴天髓补注/09-滴天髓补注知识库.md",
                    "confidence": "unverified", "commentator": "徐乐吾（补注）"},
            provenance=[
                {"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库（用户提供 zip）",
                 "concept": "滴天髓补注·暗冲暗会节（DTZ-10）+ 子平真诠（拱禄拱贵，ZP-05）"
                            "+ 子平粹言（暗合，SPZY-34）"},
                {"level": "CLASSICAL_EXPLICIT", "project": None,
                 "concept": "古籍原文引文（暗冲暗会尤为喜，我冲彼冲皆冲起——拱实不若拱虚；"
                            "拱禄拱贵忌刑冲填实之凶；干与干相遇为明合，地支所藏人元之用"
                            "相遇为暗合）",
                 "note": _quote_note("暗冲暗会尤为喜，我冲彼冲皆冲起。……刑冲破害以冲为重，"
                                     "三会六合以会为重……拱夹包承，为不见之形，即是暗会；"
                                     "拱实不若拱虚，故尤为喜也。")},
                {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
                 "concept": "拱定位 = 地支环隔二缺一且被拱支不见（M24 relation.tables）；"
                            "暗合 = SPZY-34 逐对表（贴邻限制、巳酉会局例外 note）；"
                            "填实 = 岁运支命中拱位虚神；评估器只读关系引擎结果，不重复检测"},
            ],
            quality="B",
            normalization_notes="「忌刑冲填实之凶」为原典禁则语境——Tianze 仅输出填实结构事件，"
                                "不判吉凶；拱夹暗合非格局非用神（DTZ-26/36），永不升格；"
                                "暗合非化（SPZY-34：非以化论也）。",
        ),
        build_rule(
            "TR-SPZY-28", "SPZY-28", "taisui", "流年即太岁（术语框架）",
            conditions=[{"field": "annualStem", "operator": "exists", "value": None}],
            effects=[{"kind": "note",
                      "text": "记录流年干支即太岁的术语框架；Tianze 不做神煞吉凶推断"}],
            source={"sourceKind": "COMMENTARY", "book": "子平粹言",
                    "chapter": "流年太岁", "pages": [],
                    "sourceFile": "_知识库/_知识库/06-子平粹言知识库.md",
                    "confidence": "unverified", "commentator": "徐乐吾"},
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
            "TR-FUYIN-01", "TIANZE-ENGINEERING-01", "fuyin", "伏吟（岁运柱与原局柱相同）",
            conditions=[{"field": "structureType", "operator": "in", "value": ["fuyin"]}],
            effects=[{"kind": "note", "text": "记录伏吟结构（何柱伏吟、来源层）"}],
            source={"sourceKind": "TIANZE_HEURISTIC", "book": "Tianze",
                    "chapter": "temporal.py 结构检测", "pages": [],
                    "confidence": "unverified"},
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
            "TR-FANYIN-01", "TIANZE-ENGINEERING-02", "fanyin", "反吟（岁运柱天克地冲原局柱）",
            conditions=[{"field": "structureType", "operator": "in", "value": ["fanyin"]}],
            effects=[{"kind": "note", "text": "记录反吟结构（何柱被冲克、来源层）"}],
            source={"sourceKind": "TIANZE_HEURISTIC", "book": "Tianze",
                    "chapter": "temporal.py 结构检测", "pages": [],
                    "confidence": "unverified"},
            provenance=[
                {"level": "PROJECT_REFERENCE", "project": "传统命理通说",
                 "concept": "反吟概念（天克地冲；Tianze 知识库暂无原文引文链，如实标注）"},
                {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
                 "concept": "检测口径 v1 = 岁运支与原局支六冲（干克维度暂缺，见 temporal.py 注）"},
            ],
            quality="C",
        ),
        build_rule(
            "TR-BINGLIN-01", "TIANZE-ENGINEERING-03", "binglin", "岁运并临（大运=流年干支）",
            conditions=[{"field": "structureType", "operator": "in", "value": ["binglin"]}],
            effects=[{"kind": "note", "text": "记录岁运并临结构（干支完全相同的岁运层）"}],
            source={"sourceKind": "TIANZE_HEURISTIC", "book": "Tianze",
                    "chapter": "temporal.py 结构检测", "pages": [],
                    "confidence": "unverified"},
            provenance=[
                {"level": "PROJECT_REFERENCE", "project": "传统命理通说",
                 "concept": "岁运并临概念（Tianze 知识库暂无原文引文链，如实标注）"},
                {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
                 "concept": "检测 = 大运干支 == 流年干支"},
            ],
            quality="C",
        ),
        build_rule(
            "TR-TIANKEDI-01", "TIANZE-ENGINEERING-04", "tiankedi", "天克地冲（流年克冲大运）",
            conditions=[{"field": "structureType", "operator": "in", "value": ["tiankedi"]}],
            effects=[{"kind": "note", "text": "记录天克地冲结构（流年天干克大运天干+流年支冲大运支）"}],
            source={"sourceKind": "TIANZE_HEURISTIC", "book": "Tianze",
                    "chapter": "temporal.py 结构检测", "pages": [],
                    "confidence": "unverified"},
            provenance=[
                {"level": "PROJECT_REFERENCE", "project": "传统命理通说",
                 "concept": "天克地冲概念（Tianze 知识库暂无原文引文链，如实标注）"},
                {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
                 "concept": "检测 = 流年干克大运干（五行相克）且流年支冲大运支（六冲）"},
            ],
            quality="C",
        ),
    ]

    _Q_TR_SP_01 = ("阳干性质刚健……虽临死绝而见印相生，仍为绝处逢生，亦不能从；"
                   "若阴干则不然：见四柱财旺则从财、煞旺则从煞。")
    _Q_TR_SP_02 = _Q_TR_SP_01
    _Q_TR_SP_03 = "变格重在形象气势，约分六格：专旺、从强、从财、官煞、从儿、化气。"
    _Q_TR_SP_04 = "天合地者，地旺宜静。……合与化不同，今人见合皆作化论殊误。"
    _DTZ_SOURCE = {"sourceKind": "COMMENTARY", "book": "滴天髓补注",
                   "sourceFile": "09p-滴天髓补注/09-滴天髓补注知识库.md",
                   "confidence": "unverified", "commentator": "徐乐吾（补注）"}

    _Q_TR_SP_05 = ("乙庚化金，不忌甲乙寅卯，而忌丙丁已午；丙辛化水，忌见戊土；"
                   "丁壬化木，忌见庚金；戊葵化火，忌见壬癸，其理一也。")
    _Q_TR_SP_07 = "若克抑则万不能用——盖从化皆以全局气势偏于一方，不能不顺其气势而行。"

    rules += [
        build_rule(
            "TR-SP-01", "DTZ-04", "special-pattern", "从格顺势观察",
            conditions=[{"field": "congCandidate", "operator": "exists", "value": None},
             {"field": "temporalShunGods", "operator": "exists", "value": None}],
            effects=[{"kind": "note", "text": '从格候选 + 岁运顺势之神 → 顺势观察（候选级）'}],
            source={"sourceKind": "COMMENTARY", "book": "滴天髓补注",
                    "sourceFile": "09p-滴天髓补注/09-滴天髓补注知识库.md",
                    "confidence": "unverified", "commentator": "徐乐吾（补注）"},
            provenance=[
                {"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库",
                 "concept": "滴天髓补注（DTZ-04）"},
                {"level": "CLASSICAL_EXPLICIT", "project": None,
                 "concept": "古籍原文（DTZ-04）", "note": _quote_note(_Q_TR_SP_01)},
                {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
                 "concept": "顺势之神映射：从财→财、从官杀→官杀、从儿→食伤（含支藏干）"},
            ],
            quality="B",
        ),

        build_rule(
            "TR-SP-02", "DTZ-04", "special-pattern", "从格岁运印比：破格两说（分阴阳）",
            conditions=[{"field": "congCandidate", "operator": "exists", "value": None},
             {"field": "temporalYinBi", "operator": "exists", "value": None}],
            effects=[{"kind": "note", "text": '阳干→破格说权重更高（绝处逢生不从）；阴干→顺势说权重更高（从势无情义）；两说并存不裁决'}],
            source={"sourceKind": "COMMENTARY", "book": "滴天髓补注",
                    "sourceFile": "09p-滴天髓补注/09-滴天髓补注知识库.md",
                    "confidence": "unverified", "commentator": "徐乐吾（补注）"},
            provenance=[
                {"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库",
                 "concept": "滴天髓补注（DTZ-04）"},
                {"level": "CLASSICAL_EXPLICIT", "project": None,
                 "concept": "古籍原文（DTZ-04）", "note": _quote_note(_Q_TR_SP_02)},
                {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
                 "concept": "按日主阴阳给两说分配权重——上下文相关流派结构，不是全局 A>B"},
            ],
            quality="B",
        ),

        build_rule(
            "TR-SP-03", "DTZ-25", "special-pattern", "专旺岁运：生扶/克神两说",
            conditions=[{"field": "zhuanwangCandidate", "operator": "exists", "value": None},
             {"field": "temporalSupportOrKe", "operator": "exists", "value": None}],
            effects=[{"kind": "note", "text": '专旺生扶→更真观察；岁运官杀克神→顺势/犯旺两说'}],
            source={"sourceKind": "COMMENTARY", "book": "滴天髓补注",
                    "sourceFile": "09p-滴天髓补注/09-滴天髓补注知识库.md",
                    "confidence": "unverified", "commentator": "徐乐吾（补注）"},
            provenance=[
                {"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库",
                 "concept": "滴天髓补注（DTZ-25）"},
                {"level": "CLASSICAL_EXPLICIT", "project": None,
                 "concept": "古籍原文（DTZ-25）", "note": _quote_note(_Q_TR_SP_03)},
                {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
                 "concept": "专旺五行映射（曲直木/炎上火/稼穑土/从革金/润下水）；克神=官杀干"},
            ],
            quality="B",
        ),

        build_rule(
            "TR-SP-04", "DTZ-18", "special-pattern", "化气岁运：引化候选（合≠化）",
            conditions=[{"field": "transformationCandidate", "operator": "exists", "value": None},
             {"field": "temporalHuaSupport", "operator": "exists", "value": None}],
            effects=[{"kind": "note", "text": '合神再现/化神得生扶 → 引化候选；候选永不升级为定论（DTZ-18）'}],
            source={"sourceKind": "COMMENTARY", "book": "滴天髓补注",
                    "sourceFile": "09p-滴天髓补注/09-滴天髓补注知识库.md",
                    "confidence": "unverified", "commentator": "徐乐吾（补注）"},
            provenance=[
                {"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库",
                 "concept": "滴天髓补注（DTZ-18）"},
                {"level": "CLASSICAL_EXPLICIT", "project": None,
                 "concept": "古籍原文（DTZ-18）", "note": _quote_note(_Q_TR_SP_04)},
                {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
                 "concept": "化神五行映射（甲己土/乙庚金/丙辛水/丁壬木/戊癸火）"},
            ],
            quality="B",
        ),

    ]

    rules += [
        build_rule(
            "TR-SP-05", "DTZ-48", "special-pattern", "化神所忌（岁运逆化神旺气）",
            conditions=[{"field": "transformationCandidate", "operator": "exists", "value": None},
                        {"field": "temporalHuaTabooStem", "operator": "exists", "value": None}],
            effects=[{"kind": "note",
                      "text": "岁运遇化神所忌之干 → 化气受阻观察（受阻说/保留两说，候选不改判）"}],
            source=_DTZ_SOURCE,
            provenance=[
                {"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库",
                 "concept": "滴天髓补注·化神所忌（DTZ-48）"},
                {"level": "CLASSICAL_EXPLICIT", "project": None,
                 "concept": "古籍原文（逐干所忌）", "note": _quote_note(_Q_TR_SP_05)},
                {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
                 "concept": "逐干禁忌映射表 _HUA_TABOO_STEMS（直接译自引文）；支藏干仅乙庚取巳午"},
            ],
            quality="B",
        ),
        build_rule(
            "TR-SP-07", "DTZ-48", "special-pattern", "从格所从之神受克（破格两说）",
            conditions=[{"field": "congCandidate", "operator": "exists", "value": None},
                        {"field": "temporalKeShen", "operator": "exists", "value": None}],
            effects=[{"kind": "note",
                      "text": "岁运克所从之神 → 破格说（克抑则万不能用）与顺势说并存，不裁决"}],
            source=_DTZ_SOURCE,
            provenance=[
                {"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库",
                 "concept": "滴天髓补注·从化总纲（DTZ-48）"},
                {"level": "CLASSICAL_EXPLICIT", "project": None,
                 "concept": "古籍原文（克抑不能用）", "note": _quote_note(_Q_TR_SP_07)},
                {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
                 "concept": "所从之神受克映射：从财忌比劫/从官杀忌食伤/从儿忌印（十神表）"},
            ],
            quality="B",
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
