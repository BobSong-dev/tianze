"""M14 · 事件规则知识构建：RuleCandidate（normalized）→ ExecutableRule(domain=event)。

与 build_temporal_rules.py 同一纪律：
- 有原文引文链 → provenance 带 CLASSICAL_EXPLICIT（如 MLD-18 夫妻宫/夫星、
  DTZ-39 伤官见官、SS-R10 刃头财、SS-R22 神煞去取、DTZ-09 冲重、DTZ-04/05/06 从格两说）
- 通说概念无引文链 → PROJECT_REFERENCE（如实注明）
- 检测口径 → ENGINEERING_HEURISTIC
- 每条规则带 view（schoolView）：traditional/pattern/strength/tiaohou/special_pattern/
  shensha/temporal_rule——流派差异显式保留，不合并成唯一答案
- effects 只输出主题方向（support/oppose/block），绝不输出现实事件断言

输出：knowledge/rules/event/rules.json
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tianze.analysis.event_themes import EVENT_THEME_SCHEMA_VERSION  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "knowledge", "rules", "event")

_SS = {"sourceKind": "COMMENTARY", "book": "守素室丛谈",
       "sourceFile": "_知识库/_知识库/02-守素室丛谈知识库.md",
       "confidence": "unverified", "commentator": "徐乐吾（原著）"}
_MLD = {"sourceKind": "COMMENTARY", "book": "命理一得",
        "sourceFile": "_知识库/_知识库/04-命理一得知识库.md",
        "confidence": "unverified", "commentator": "徐乐吾"}
_DTZ = {"sourceKind": "COMMENTARY", "book": "滴天髓补注",
        "sourceFile": "09p-滴天髓补注/09-滴天髓补注知识库.md",
        "confidence": "unverified", "commentator": "徐乐吾（补注）"}
_TZ = {"sourceKind": "TIANZE_HEURISTIC", "book": "Tianze",
       "chapter": "event_themes.py 结构检测", "confidence": "unverified"}


def _q(quote: str) -> str:
    return (quote[:60] + "…") if len(quote) > 60 else quote


def build_rule(rid: str, candidate_id: str, theme: str, view: str, label: str,
               conditions: list[dict], provenance: list[dict], source: dict,
               quality: str, normalization_notes: str | None = None,
               conflict_note: str | None = None) -> dict:
    return {
        "id": rid,
        "candidateId": candidate_id,
        "domain": "event",
        "theme": theme,
        "view": view,
        "label": label,
        "conditions": conditions,
        "effects": [{"kind": "eventTheme", "theme": theme}],
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
            "verifiedBy": "tianze-pipeline:build_event_rules.py",
            "verifiedAt": None,
            "method": "ai_curation",
            "sourceChecked": True,
            "notes": "M14 事件规则 curation 由 AI 依候选原文完成（非人工）；"
                     "升级需真人对照扫描件；效果只输出主题方向，不输出事件断言",
        },
        "accuracyMatrix": {
            "traceability": "PASS",
            "textAccuracy": "UNVERIFIED",
            "interpretationAccuracy": "MACHINE_CURATED",
            "engineAccuracy": "TESTED",
        },
    }


def main() -> int:
    rules = [
        build_rule(
            "EV-CAR-01", "DTZ-33", "career", "traditional", "官星透岁运+官杀主题增强",
            [{"field": "temporalStemTenGod", "operator": "in", "value": ["正官", "七杀"]},
             {"field": "themeStrength.官杀", "operator": "exists", "value": None}],
            [{"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库",
              "concept": "滴天髓补注·偏官七煞制化（DTZ-33：假煞为权/食神制煞/印化）"},
             {"level": "CLASSICAL_EXPLICIT", "project": None,
              "concept": "古籍原文（官杀制化框架）",
              "note": _q("偏官，即七煞也——一位而清名偏官，多而杂名七煞。用煞之法不外制与化：制用食神，化用印绶。")},
             {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
              "concept": "「官杀主题增强」= StructuralTheme 增量（temporal delta 十神主题）"}],
            _DTZ, "B",
            normalization_notes="官星透干本身只是结构事实；与主题增强同时出现才给 support。",
        ),
        build_rule(
            "EV-CAR-02", "DTZ-33", "career", "traditional", "官印相生（印化官杀）",
            [{"field": "temporalStemTenGod", "operator": "in", "value": ["正印", "偏印"]},
             {"field": "guanPresent", "operator": "eq", "value": True}],
            [{"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库",
              "concept": "滴天髓补注·化煞用印（DTZ-33）"},
             {"level": "CLASSICAL_EXPLICIT", "project": None,
              "concept": "古籍原文（化煞用印绶）",
              "note": _q("用煞之法不外制与化：制用食神，化用印绶。")}],
            _DTZ, "B",
        ),
        build_rule(
            "EV-CAR-03", "DTZ-39", "career", "traditional", "伤官见官（岁运伤官克官）",
            [{"field": "temporalStemTenGod", "operator": "eq", "value": "伤官"},
             {"field": "guanClashed", "operator": "eq", "value": True}],
            [{"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库",
              "concept": "滴天髓补注·伤官见官（DTZ-39/43：以财化伤生官、以印制伤护官）"},
             {"level": "CLASSICAL_EXPLICIT", "project": None,
              "concept": "古籍原文（伤官见官之辨）",
              "note": _q("原文口诀「伤官见官最难辨，官有可见不可见」。")},
             {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
              "concept": "只判「岁运伤官干克官星干」的最简结构；救应（财/印并见）v1 不展开，"
                         "在 evidence 中如实说明"}],
            _DTZ, "B",
            conflict_note="伤官见官有「可见/不可见」之辨（有财则可见官）；v1 规则不判救应，"
                          "因此输出为 oppose 方向但保留该 conflictNote，不伪装成定论。",
        ),
        build_rule(
            "EV-WEA-01", "ZPZ-12", "wealth", "traditional", "财星透岁运+财主题增强",
            [{"field": "temporalStemTenGod", "operator": "in", "value": ["正财", "偏财"]},
             {"field": "themeStrength.财星", "operator": "exists", "value": None}],
            [{"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库",
              "concept": "子平真诠·财格（ZPZ-12：身强方能任财；喜根深不宜太露）"},
             {"level": "CLASSICAL_EXPLICIT", "project": None,
              "concept": "古籍原文（财格框架）",
              "note": _q("财格——身强方能任财；喜根深不宜太露；用财诸局。")},
             {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
              "concept": "「财星主题增强」= StructuralTheme 增量"}],
            {"sourceKind": "COMMENTARY", "book": "子平真诠评注",
             "sourceFile": "_知识库/_知识库/03-子平真诠评注知识库.md",
             "confidence": "unverified", "commentator": "徐乐吾（评注）"}, "B",
        ),
        build_rule(
            "EV-WEA-02", "SS-R10", "wealth", "traditional", "刃头财/比劫夺财（因财启争）",
            [{"field": "renOrLuHeadCai", "operator": "eq", "value": True},
             {"field": "orBijiePlusCai", "operator": "eq", "value": True}],
            [{"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库",
              "concept": "守素室丛谈·刃头财/禄头财（SS-R10）"},
             {"level": "CLASSICAL_EXPLICIT", "project": None,
              "concept": "古籍原文（刃头财/禄头财流年断）",
              "note": _q("刃头财者，支逢阳刃、干见财星也，名销镕煞……流年遇之，皆主因财启争。")},
             {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
              "concept": "比劫主题增强+财星并见 的组合判定"}],
            _SS, "B",
            conflict_note="SS-R10 原书即注明「须察其配合，非可一例以推」；oppose 方向是结构提示，"
                          "不是破财断言。",
        ),
        build_rule(
            "EV-WEA-03", "DTZ-35", "wealth", "traditional", "财库逢冲（两说并存）",
            [{"field": "caiKuClashed", "operator": "eq", "value": True}],
            [{"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库",
              "concept": "滴天髓补注·杂气财官（DTZ-35）"},
             {"level": "CLASSICAL_EXPLICIT", "project": None,
              "concept": "古籍原文（喜冲不可靠之辨）",
              "note": _q("至于杂气财官喜冲之说极不可靠……用神所在必不可损伤，冲而损伤岂不为害？")},
             {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
              "concept": "财库 = 我克五行之墓库（木未/火戌/金丑/水辰）；冲 = 六冲表"}],
            _DTZ, "B",
            conflict_note="「冲开财库得财」与「冲不可靠（DTZ-35）」两说并存：规则给 support 方向"
                          "但 conflictNote 强制保留两说，聚合层因此可能出 DISPUTED。",
        ),
        build_rule(
            "EV-REL-01", "TIANZE-ENGINEERING-11", "relationship", "traditional",
            "夫妻宫（日支）逢岁运六合",
            [{"field": "dayBranchSixCombined", "operator": "eq", "value": True}],
            [{"level": "PROJECT_REFERENCE", "project": "传统命理通说",
              "concept": "日支为夫妻宫；合主结合/引动（Tianze 知识库无直接引文，如实标注）"},
             {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
              "concept": "六合表判定（R10 相关口径）"}],
            _TZ, "C",
        ),
        build_rule(
            "EV-REL-02", "MLD-18", "relationship", "traditional", "夫妻宫逢冲/夫星逢冲",
            [{"field": "dayBranchClashed", "operator": "eq", "value": True}],
            [{"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库",
              "concept": "命理一得·离婚之微象（MLD-18：财为妻星、日支为夫宫）"},
             {"level": "CLASSICAL_EXPLICIT", "project": None,
              "concept": "古籍原文（夫宫/夫星逢冲）",
              "note": _q("财为妻星、日支为夫宫……盖女命以官为夫星……更见财星冲之，决然合（离）。")},
             {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
              "concept": "宫位映射（日支=配偶宫）为通行口径"}],
            _MLD, "B",
            conflict_note="MLD-18 原文明言「离婚非不可避免事」且随时代变迁——oppose 方向只是"
                          "「关系主题有冲突结构」，绝不可输出关系破裂断言。",
        ),
        build_rule(
            "EV-REL-03", "MLD-18", "relationship", "traditional", "配偶星临岁运（男财/女官）",
            [{"field": "gender", "operator": "in", "value": ["male", "female"]},
             {"field": "temporalStemTenGod", "operator": "in",
              "value": ["__GENDER_CONDITIONAL__"]}],
            [{"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库",
              "concept": "命理一得（MLD-18：财为妻星、女命以官为夫星）"},
             {"level": "CLASSICAL_EXPLICIT", "project": None,
              "concept": "古籍原文（妻星/夫星定义）",
              "note": _q("财为妻星，日支为夫宫……女命以官为夫星。")},
             {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
              "concept": "性别未知 → 规则 UNRESOLVED（不猜）"}],
            _MLD, "B",
            normalization_notes="value __GENDER_CONDITIONAL__ 由执行器按性别解析为 "
                                "[正财,偏财]（男）或 [正官,七杀]（女）；性别未知时输出 UNRESOLVED。",
        ),
        build_rule(
            "EV-REL-04", "MLD-21", "relationship", "shensha", "咸池桃花临岁运",
            [{"field": "xianchiBranchHit", "operator": "eq", "value": True}],
            [{"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库",
              "concept": "命理一得·桃花名目（MLD-21）+ 守素室丛谈·神煞去取（SS-R22）"},
             {"level": "CLASSICAL_EXPLICIT", "project": None,
              "concept": "古籍原文（桃花名目与四时起例）",
              "note": _q("桃花名目甚多……正桃花-巳亥，咸池桃花，红艳桃花，桃花马……")},
             {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
              "concept": "v1 只用通行咸池起例（三合沐浴位）；MLD-21 名目繁多且有分歧"}],
            _MLD, "C",
            conflict_note="SS-R22 引滴天髓「咸池驿马半推详」、子平法尽删神煞——神煞视角的"
                          "support 必须带该反对声音（shensha view 单独记录，不与传统 view 合并）。",
        ),
        build_rule(
            "EV-STU-01", "DTZ-33", "study", "traditional", "印星临岁运+印主题增强",
            [{"field": "temporalStemTenGod", "operator": "in", "value": ["正印", "偏印"]},
             {"field": "themeStrength.印星", "operator": "exists", "value": None}],
            [{"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库",
              "concept": "滴天髓补注·印绶（DTZ-33 化煞）+ 印主文书/资格（通说）"},
             {"level": "CLASSICAL_EXPLICIT", "project": None,
              "concept": "古籍原文（印绶化煞）",
              "note": _q("身弱煞强则宜用印以化之。")},
             {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
              "concept": "「印=学习/考试/资格」为通说映射（Tianze 知识库无直接考试引文）"}],
            _DTZ, "C",
        ),
        build_rule(
            "EV-MOB-01", "SS-R22", "mobility", "shensha", "驿马临岁运/驿马逢冲",
            [{"field": "yimaBranchHitOrClash", "operator": "eq", "value": True}],
            [{"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库",
              "concept": "守素室丛谈·神煞去取（SS-R22 引滴天髓）"},
             {"level": "CLASSICAL_EXPLICIT", "project": None,
              "concept": "古籍原文（神煞去取原则）",
              "note": _q("神煞之名盈千，重复伪造者十居七八……即驿马咸池亦不能尽验。")},
             {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
              "concept": "驿马起例 = 年支/日支三合马位；逢冲为「马逢冲则动」通说"}],
            _SS, "C",
            conflict_note="SS-R22 明言驿马「不能尽验」且子平法尽删神煞——本规则属 shensha "
                          "view，confidence 权重低，且不得与其他 view 合并成强结论。",
        ),
        build_rule(
            "EV-MOB-02", "DTZ-09", "mobility", "traditional", "岁运冲提纲（月令）",
            [{"field": "monthBranchClashed", "operator": "eq", "value": True}],
            [{"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库",
              "concept": "滴天髓补注·支神只以冲为重（DTZ-09）"},
             {"level": "CLASSICAL_EXPLICIT", "project": None,
              "concept": "古籍原文（冲为重）",
              "note": _q("支神只以冲为重，刑与穿兮动不动。……刑、冲、害三者之中以冲为重。")},
             {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
              "concept": "冲提纲→环境/根基引动为通说映射（TR-DTZ-09 同源）"}],
            _DTZ, "B",
        ),
        build_rule(
            "EV-FAM-01", "DTZ-09", "family", "traditional",
            "年柱/月柱被天克地冲（宫位引动）",
            [{"field": "familyPalaceTiankedi", "operator": "eq", "value": True}],
            [{"level": "PROJECT_REFERENCE", "project": "传统命理通说",
              "concept": "年柱=祖上/父母宫、月柱=父母兄弟宫（通说映射，知识库无直接引文）"},
             {"level": "CLASSICAL_EXPLICIT", "project": None,
              "concept": "古籍原文（冲重框架，来自 DTZ-09）",
              "note": _q("支神只以冲为重，刑与穿兮动不动。")},
             {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
              "concept": "复用 temporal structures（fanyin/tiankedi）中涉及 natal:year/month 者"}],
            _TZ, "C",
        ),
        build_rule(
            "EV-SOC-01", "MLD-06", "social", "traditional",
            "比劫临岁运/比劫主题增强",
            [{"field": "temporalStemTenGod", "operator": "in", "value": ["比肩", "劫财"]},
             {"field": "orThemeStrength.比劫", "operator": "exists", "value": None}],
            [{"level": "PROJECT_REFERENCE", "project": "传统命理通说",
              "concept": "比劫=同辈/朋友/竞争（MLD-06 六神框架）"},
             {"level": "CLASSICAL_EXPLICIT", "project": None,
              "concept": "古籍原文（六神框架）",
              "note": _q("神煞者：天干六神（财官食印比劫及本身为六），地支会合刑冲。")},
             {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
              "concept": "主题增强 = StructuralTheme 增量"}],
            {"sourceKind": "COMMENTARY", "book": "命理一得",
             "sourceFile": "_知识库/_知识库/04-命理一得知识库.md",
             "confidence": "unverified", "commentator": "徐乐吾"}, "C",
        ),
        build_rule(
            "EV-CON-01", "DTZ-04", "social", "special_pattern",
            "从格/专旺岁运破格（顺势 vs 破格两说）",
            [{"field": "specialCandidateBlocked", "operator": "exists", "value": None}],
            [{"level": "PROJECT_REFERENCE", "project": "徐乐吾八字知识库",
              "concept": "滴天髓补注·从格（DTZ-04/05/06：阳干从气不从势、阴干从势无情义、"
                         "绝处逢生/有印不从）"},
             {"level": "CLASSICAL_EXPLICIT", "project": None,
              "concept": "古籍原文（从与不从之辨）",
              "note": _q("阳干性质刚健……非至本气休囚死绝之地不能言从；或虽临死绝而见印相生，"
                         "仍为绝处逢生，亦不能从。")},
             {"level": "ENGINEERING_HEURISTIC", "project": "Tianze",
              "concept": "岁运引入印比 → 从格 candidate BLOCKED（复用 M13 special delta）；"
                         "主题归属按从格类型映射（从财→wealth 等）"}],
            _DTZ, "B",
            conflict_note="岁运破从格：顺势说（岁运助从）与破格说（印比生扶不从）并存；"
                          "本规则只记录 blocked 事件并给出两说，不裁决。",
        ),
    ]

    conflicts = [
        {"ruleA": "EV-CAR-01", "ruleB": "EV-CAR-03",
         "resolution": "keep-both",
         "note": "DTZ-39：伤官见官有「可见/不可见」之辨（有财化伤则可见官）；"
                 "v1 执行器未判救应，因此两条规则可同盘反向命中——保留双方，status=DISPUTED"},
        {"ruleA": "EV-WEA-01", "ruleB": "EV-WEA-02",
         "resolution": "keep-both",
         "note": "SS-R10 原书自注「须察其配合，非可一例以推」：财星支持与因财启争同盘并存"},
        {"ruleA": "EV-REL-02", "ruleB": "EV-REL-03",
         "resolution": "keep-both",
         "note": "MLD-18：配偶星临岁运（support）与夫妻宫逢冲（oppose）可同时成立；"
                 "原文并注明「离婚非不可避免事」，方向相反只表示主题内张力"},
        {"ruleA": "EV-CON-01", "ruleB": "EV-WEA-02",
         "resolution": "no-adjudication",
         "note": "special_pattern 视角（从格顺势/破格两说）与 traditional 视角（比劫夺财）"
                 "方向相反时属流派差异，不裁决"},
    ]
    with open(os.path.join(OUT, "conflicts.json"), "w", encoding="utf-8") as f:
        json.dump({"schemaVersion": "1.0.0", "count": len(conflicts),
                   "conflicts": conflicts}, f, ensure_ascii=False, indent=1)

    os.makedirs(OUT, exist_ok=True)
    payload = {
        "domain": "event",
        "schemaVersion": EVENT_THEME_SCHEMA_VERSION,
        "count": len(rules),
        "description": "事件主题规则（M14）：Source→Quote→RuleCandidate→ExecutableRule(domain=event)"
                       "→EventThemeCandidate；view（流派视角）显式保留，效果只输出主题方向",
        "rules": rules,
    }
    with open(os.path.join(OUT, "rules.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"事件规则构建完成：{len(rules)} 条 → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
