"""M15 · 特殊格局岁运专题（从格/专旺/化气）。

规则链：Source → Quote(RuleCandidate) → ExecutableRule(domain=temporal, category=special-pattern)
→ analyze_special_temporal() → SpecialTemporalFinding

流派结构（上下文相关，不做全局裁决）：
- 阳日主：DTZ-04「阳干从气不从势……虽临死绝而见印相生，仍为绝处逢生，亦不能从」
  → 岁运印比时「破格说」权重更高
- 阴日主：DTZ-04「阴干则不然：见四柱财旺则从财……亦所不论」
  → 岁运财官时「顺势说」权重更高
- 化气：DTZ-18「合与化不同，今人见合皆作化论殊误」→ 引化候选永远不升级为定论

状态词汇保持 CANDIDATE/LIKELY/BLOCKED/DISPUTED/UNRESOLVED；绝不输出 CONFIRMED。
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

from tianze.ganzhi.tables import STEM_ELEMENT, Element, ten_god
from tianze.domain.models import CamelizeModel
from tianze.analysis.temporal import AnalysisSupport

__all__ = [
    "SpecialTemporalFinding", "analyze_special_temporal",
    "SPECIAL_TEMPORAL_SCHEMA_VERSION",
]

SPECIAL_TEMPORAL_SCHEMA_VERSION = "1.0.0"

_SPECIAL_RULES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "knowledge", "rules", "temporal", "rules.json",
)

# 从格类型 → 顺势之神（十神集合）
_CONG_GODS: dict[str, set[str]] = {
    "从财": {"正财", "偏财"},
    "从官杀": {"正官", "七杀"},
    "从儿": {"食神", "伤官"},
    "从强": {"比肩", "劫财"},
}

# 专旺类型 → 专旺五行
_ZW_ELEMENT: dict[str, str] = {
    "曲直": "WOOD", "炎上": "FIRE", "稼穑": "EARTH",
    "从革": "METAL", "润下": "WATER",
}

# 化气 stemPair → 化神五行
_HUA_ELEMENT: dict[str, str] = {
    "甲己": "EARTH", "乙庚": "METAL", "丙辛": "WATER",
    "丁壬": "WOOD", "戊癸": "FIRE",
}

# 化神所忌（DTZ-48 逐干引文）：逆化神旺气之岁运干
# 甲己化土→忌甲乙寅卯（逆土旺气，还原非大忌）；乙庚化金→忌丙丁巳午；
# 丙辛化水→忌戊土；丁壬化木→忌庚金；戊癸化火→忌壬癸
_HUA_TABOO_STEMS: dict[str, set[str]] = {
    "甲己": {"甲", "乙"},
    "乙庚": {"丙", "丁"},
    "丙辛": {"戊"},
    "丁壬": {"庚"},
    "戊癸": {"壬", "癸"},
}
_HUA_TABOO_BRANCH_STEMS: dict[str, set[str]] = {   # 支藏干引申（巳午藏丙丁等）
    "乙庚": {"丙", "丁"},
}


class SpecialTemporalFinding(CamelizeModel):
    """特殊格局候选在岁运中的状态变化 + 流派观察（候选级，非定论）。"""
    ruleId: str
    candidateType: str                    # 从财 / 曲直 / 甲己 …
    group: str                            # cong / zhuanwang / transformation
    natalStatus: str | None = None
    temporalStatus: str | None = None
    transition: str                       # unchanged / appeared / disappeared / blocked / unblocked / regraded
    schoolSplit: dict[str, str] = {}      # 顺势说/破格说/… → 依据（上下文相关）
    status: str = "CANDIDATE"             # 候选级状态词汇
    evidence: list[str] = []
    provenanceLevels: list[str] = []
    refId: str | None = None

    def model_post_init(self, __context: Any) -> None:
        if self.refId is None:
            object.__setattr__(
                self, "refId",
                f"temporal:special:{self.group}:{self.candidateType}:{self.ruleId}")


@lru_cache(maxsize=1)
def _load_special_rules() -> list[dict]:
    payload = json.load(open(_SPECIAL_RULES_PATH, encoding="utf-8"))
    return [r for r in payload["rules"] if r.get("category") == "special-pattern"]


def _natal_candidates(chart) -> dict[str, dict]:
    """原局特殊格局候选：{(group, type): status}。"""
    out: dict[str, dict] = {}
    adv = chart.advancedAnalysis
    if not adv:
        return out
    for c in adv.get("specialPattern", {}).get("cong", []):
        out[("cong", c["type"])] = {"status": c["status"], "entry": c}
    for z in adv.get("specialPattern", {}).get("zhuanwang", []):
        out[("zhuanwang", z["type"])] = {"status": z["status"], "entry": z}
    for t in adv.get("specialPattern", {}).get("transformation", []):
        out[("transformation", "".join(t.get("stemPair", [])))] = {
            "status": t["status"], "entry": t}
    return out


def _transitions(delta_report) -> dict[tuple[str, str], dict]:
    """M13 special delta 的状态迁移事件：{(group-ish, type): item}。"""
    out: dict[tuple[str, str], dict] = {}
    for it in delta_report.items:
        if it.analysis != "special":
            continue
        subject = it.subject or ""
        for gname, gkey in (("从格候选·", "cong"), ("专旺候选·", "zhuanwang"),
                            ("化气候选·", "transformation")):
            if subject.startswith(gname):
                out[(gkey, subject[len(gname):])] = {
                    "kind": it.kind.value, "natal": it.natalValue,
                    "temporal": it.temporalValue, "trigger": it.trigger,
                }
    return out


# ---- 评估器（每条 TR-SP-* 规则一个；规则元数据在 rules.json） ----

def _sp_cong_shunshi(chart, ctx, candidates):
    """TR-SP-01 从格顺势：从格候选 + 岁运干支为顺势之神 → 顺势观察。"""
    out = []
    dm = chart.day_master.stem
    for (group, ctype), info in candidates.items():
        if group != "cong" or ctype not in _CONG_GODS:
            continue
        if info["status"] in ("BLOCKED", "UNRESOLVED"):
            continue
        note_suffix = "" if not info.get("temporal_only") else "（岁运上下文新增候选）"
        gods = _CONG_GODS[ctype]
        hits = [(l, s) for l, s in _temporal_stems(ctx)
                if ten_god(dm, s).value in gods]
        branch_hits = [(l, b) for l, b in _temporal_branches(ctx)
                       if any(STEM_ELEMENT.get(h) and ten_god(dm, h).value in gods
                              for h in _hidden_of(b))]
        if hits or branch_hits:
            layers = "、".join(f"{_cn(l)}干{s}" for l, s in hits) or \
                "、".join(f"{_cn(l)}支{b}藏顺势之神" for l, b in branch_hits)
            out.append((ctype, "cong", info["status"], "顺势观察", hits and "stem" or "hidden",
                        f"{ctype}候选（natal={info['status']}{note_suffix}）："
                        f"岁运{layers}为顺势之神"
                        f"（阴干「从势无情义」顺势说，DTZ-04）"))
    return out


def _sp_cong_break(chart, ctx, candidates):
    """TR-SP-02 从格破格两说：从格候选 + 岁运印比 → 阳干破格说 / 阴干顺势说并存。"""
    out = []
    dm = chart.day_master.stem
    yang = dm in "甲丙戊庚壬"
    for (group, ctype), info in candidates.items():
        if group != "cong" or ctype not in _CONG_GODS:
            continue
        if info["status"] in ("BLOCKED", "UNRESOLVED"):
            continue
        note_suffix = "" if not info.get("temporal_only") else "（岁运上下文新增候选）"
        hits = [(l, s) for l, s in _temporal_stems(ctx)
                if ten_god(dm, s).value in ("正印", "偏印", "比肩", "劫财")]
        if not hits:
            continue
        layers = "、".join(f"{_cn(l)}干{s}（{ten_god(dm, s).value}）" for l, s in hits)
        if yang:
            school = {
                "破格说（权重更高）": f"阳干{dm}：DTZ-04「阳干性质刚健……虽临死绝而见印相生，"
                                     "仍为绝处逢生，亦不能从」",
                "顺势说（保留）": f"岁运{layers}是否足以生扶，须察全局（两说并存不裁决）",
            }
        else:
            school = {
                "顺势说（权重更高）": f"阴干{dm}：DTZ-04「见四柱财旺则从财、煞旺则从煞……"
                                     "亦所不论」（从势无情义）",
                "破格说（保留）": f"岁运{layers}印比并见，破格说仍成立（不裁决）",
            }
        out.append((ctype, "cong", info["status"], "破格两说", "school-split",
                    f"{ctype}候选（natal={info['status']}{note_suffix}）：岁运{layers}",
                    school))
    return out


def _sp_zw(chart, ctx, candidates):
    """TR-SP-03 专旺岁运：生扶（比劫/印）→ 专旺更真；官杀克神 → 破格两说。"""
    out = []
    dm = chart.day_master.stem
    for (group, ctype), info in candidates.items():
        if group != "zhuanwang":
            continue
        if info["status"] in ("BLOCKED", "UNRESOLVED"):
            continue
        elem = _ZW_ELEMENT.get(ctype)
        if not elem:
            continue
        elem_enum = Element(elem)
        support = [(l, s) for l, s in _temporal_stems(ctx)
                   if STEM_ELEMENT.get(s, elem_enum) == elem_enum
                   or ten_god(dm, s).value in ("正印", "偏印", "比肩", "劫财")]
        ke = [(l, s) for l, s in _temporal_stems(ctx)
              if ten_god(dm, s).value in ("正官", "七杀")]
        if support:
            out.append((ctype, "zhuanwang", info["status"], "生扶观察", "support",
                        f"{ctype}（专旺{elem.lower()}）候选：岁运"
                        + "、".join(f"{_cn(l)}干{s}" for l, s in support)
                        + "生扶专旺之气（变格重在形象气势，DTZ-25）"))
        if ke:
            out.append((ctype, "zhuanwang", info["status"], "破格两说", "school-split",
                        f"{ctype}候选：岁运"
                        + "、".join(f"{_cn(l)}干{s}（{ten_god(dm, s).value}）" for l, s in ke)
                        + "为专旺之克神——「顺势」与「犯旺」两说并存（不裁决）",
                        {"顺势说": "从其旺势，岁运宜顺不宜逆",
                         "破格说": "克神引动，专旺格破（两说权重随岁运强弱而定，v1 不量化）"}))
    return out


def _sp_hua(chart, ctx, candidates):
    """TR-SP-04 化气岁运：合神再现/化神得岁运生扶 → 引化候选（永远不升级）。"""
    out = []
    dm = chart.day_master.stem
    for (group, ctype), info in candidates.items():
        if info["status"] in ("BLOCKED", "UNRESOLVED"):
            continue
        if group != "transformation" or ctype not in _HUA_ELEMENT:
            continue
        hua_elem = _HUA_ELEMENT[ctype]
        notes = []
        for l, s in _temporal_stems(ctx):
            pair = frozenset({ctype[0], ctype[1]})
            if s in (ctype[0], ctype[1]):
                notes.append(f"岁运{_cn(l)}干{s}为原局合神{ctype}之一（合神再现）")
            if STEM_ELEMENT.get(s, Element.WOOD).value == hua_elem:
                notes.append(f"岁运{_cn(l)}干{s}生扶化神（{hua_elem.lower()}）")
        if notes:
            out.append((ctype, "transformation", info["status"], "引化候选", "candidate",
                        f"化气候选 {ctype}（natal={info['status']}）：" + "；".join(notes)
                        + "。DTZ-18「合与化不同，今人见合皆作化论殊误」——"
                          "候选保持 UNRESOLVED/CANDIDATE，不升级"))
    return out


def _sp_hua_taboo(chart, ctx, candidates):
    """TR-SP-05 化神所忌（DTZ-48 逐干引文）：岁运遇禁忌之干/支藏干 → 化气受阻观察。"""
    out = []
    dm = chart.day_master.stem
    for (group, ctype), info in candidates.items():
        if group != "transformation" or ctype not in _HUA_TABOO_STEMS:
            continue
        if info["status"] in ("BLOCKED",):
            continue
        note_suffix = "" if not info.get("temporal_only") else "（岁运上下文新增候选）"
        ev = []
        for l, st in _temporal_stems(ctx):
            if st in _HUA_TABOO_STEMS[ctype]:
                ev.append(f"岁运{_cn(l)}干{st}为化神所忌"
                          f"（DTZ-48 逐干引文；逆旺气，非还原之忌）")
        for l, br in _temporal_branches(ctx):
            for h in _hidden_of(br):
                if h in _HUA_TABOO_STEMS[ctype] and br in _HUA_TABOO_BRANCH_STEMS.get(ctype, set()):
                    ev.append(f"岁运{_cn(l)}支{br}（藏{h}）为化神所忌")
                    break
        if ev:
            out.append((ctype, "transformation", info["status"], "化神所忌", "school-split",
                        f"化气候选 {ctype}（natal={info['status']}{note_suffix}）："
                        + "；".join(ev), {"受阻说": "逆化神旺气（DTZ-48）",
                                          "保留": "候选状态不因单条岁运引文改判"}))
    return out


def _sp_cong_ke(  chart, ctx, candidates):
    """TR-SP-07 从格所从之神受克（DTZ-48：克抑则万不能用）→ 破格观察两说。"""
    out = []
    dm = chart.day_master.stem
    for (group, ctype), info in candidates.items():
        if group != "cong" or ctype not in _CONG_GODS:
            continue
        if info["status"] in ("BLOCKED", "UNRESOLVED"):
            continue
        note_suffix = "" if not info.get("temporal_only") else "（岁运上下文新增候选）"
        gods = _CONG_GODS[ctype]
        ke_hits = []
        for l, s_ in _temporal_stems(ctx):
            god = ten_god(dm, s_).value
            # 岁运干为官杀而所从为财 → 官杀克身破从？口径：克「所从之神」——
            # 从财（所从=财）忌比劫克财；从官杀忌食伤克官杀；从儿忌印克食伤
            if ctype == "从财" and god in ("比肩", "劫财"):
                ke_hits.append(f"{_cn(l)}干{s_}（{god}）克所从之财")
            elif ctype == "从官杀" and god in ("食神", "伤官"):
                ke_hits.append(f"{_cn(l)}干{s_}（{god}）克所从之官杀")
            elif ctype == "从儿" and god in ("正印", "偏印"):
                ke_hits.append(f"{_cn(l)}干{s_}（{god}）克所从之食伤")
        if ke_hits:
            out.append((ctype, "cong", info["status"], "所从受克", "school-split",
                        f"{ctype}候选（natal={info['status']}{note_suffix}）："
                        + "；".join(ke_hits)
                        + "（DTZ-48：克抑则万不能用——破格说；顺势说仍保留）",
                        {"破格说": "DTZ-48「若克抑则万不能用」（逆所从旺势）",
                         "顺势说（保留）": "岁运克神力量与全局气势须并察，不单条裁决"}))
    return out


def _sp_jia_cong_hua_sensitive(chart, ctx, candidates):
    """TR-SP-08 假从/假化岁运敏感（DTZ-49 行运之别）：假从候选 + 岁运根气/印比
    → 逆旺气破格风险 vs 顺势与真从无别，两说；假化同理（化神见克泄）。

    假从判定复用 natal 候选的 SP-CG-E2 例外注记（微根/印生助）——本评估器只读
    natal 证据，不重复判定。候选级观察，永不升级。
    """
    out = []
    dm = chart.day_master.stem
    # natal cong 候选是否带假从说（SP-CG-E2 文本特征）
    natal_cong = {c["type"]: c for c in
                  (chart.advancedAnalysis or {}).get("specialPattern", {}).get("cong", [])}
    jia_cong_types = {t for t, c in natal_cong.items()
                      if any("假从说" in (e.get("text") or "") for e in c.get("exceptions", []))}
    for (group, ctype), info in candidates.items():
        note_suffix = "" if not info.get("temporal_only") else "（岁运上下文新增候选）"
        if group == "cong" and ctype in jia_cong_types and info["status"] not in ("BLOCKED", "UNRESOLVED"):
            # 岁运根气（支藏干见日主）或印比 → 逆旺气风险
            root_hits = [f"{_cn(l)}支{b}藏{h}" for l, b in _temporal_branches(ctx)
                         for h in _hidden_of(b) if h == dm]
            helper_hits = [f"{_cn(l)}干{s}（{ten_god(dm, s).value}）" for l, s in _temporal_stems(ctx)
                           if ten_god(dm, s).value in ("正印", "偏印", "比肩", "劫财")]
            if root_hits or helper_hits:
                det = "；".join(root_hits + helper_hits)
                out.append((ctype, "cong", info["status"], "假从岁运敏感", "school-split",
                            f"假从候选 {ctype}（natal={info['status']}{note_suffix}）："
                            f"岁运{det}为日主根气/印比",
                            {"逆旺气破格说（权重更高）": "DTZ-49：假从行逆旺气之乡有失败之虑",
                             "顺势说（保留）": "行从化旺乡与真从无别，一样取富贵——"
                                              "「未交运前寒素、运过复初」属行运先后叙事，"
                                              "不构成结构判定"}))
        if group == "transformation" and info["status"] not in ("BLOCKED", "UNRESOLVED"):
            # 假化：岁运见化神之克/泄（克神=所忌已在 TR-SP-05；此处补「泄气」半边）
            ctype_str = ctype
            if ctype_str in _HUA_ELEMENT:
                from tianze.ganzhi.tables import Element as _E
                hua = _HUA_ELEMENT[ctype_str]
                hua_enum = _E(hua)
                drain = {"WOOD": "FIRE", "FIRE": "EARTH", "EARTH": "METAL",
                         "METAL": "WATER", "WATER": "WOOD"}[hua]
                drain_enum = _E(drain)
                hits = [f"{_cn(l)}干{s}" for l, s in _temporal_stems(ctx)
                        if STEM_ELEMENT.get(s) == drain_enum]
                if hits:
                    out.append((ctype_str, "transformation", info["status"], "假化岁运敏感",
                                "school-split",
                                f"化气候选 {ctype_str}（natal={info['status']}{note_suffix}）："
                                f"岁运{'、'.join(hits)}泄化神之气",
                                {"假化说": "DTZ-49：化神见克泄便是假化——岁运敏感",
                                 "保留": "候选不因单条岁运引文改判"}))
    return out


_SPECIAL_EVALUATORS = {
    "TR-SP-01": _sp_cong_shunshi,
    "TR-SP-02": _sp_cong_break,
    "TR-SP-03": _sp_zw,
    "TR-SP-04": _sp_hua,
    "TR-SP-05": _sp_hua_taboo,
    "TR-SP-07": _sp_cong_ke,
    "TR-SP-08": _sp_jia_cong_hua_sensitive,
}


def _temporal_stems(ctx):
    for l, s, b in ctx.temporal_units():
        if s:
            yield l, s


def _temporal_branches(ctx):
    for l, s, b in ctx.temporal_units():
        if b:
            yield l, b


def _hidden_of(branch: str) -> list[str]:
    from tianze.ganzhi.tables import HIDDEN_STEMS
    return [h for h, _r in HIDDEN_STEMS.get(branch, [])]


def _cn(layer: str) -> str:
    return {"luck": "大运", "annual": "流年", "monthly": "流月", "daily": "流日"}.get(layer, layer)


def _dm_elem(dm: str) -> str:
    return STEM_ELEMENT[dm].value


def _merged_candidates(chart, transitions: dict) -> dict:
    """natal 候选 + 岁运新出现（added）候选的合并视图。

    值：{"status": natal 状态或 "APPEARED", "temporal_only": bool}
    """
    merged = {}
    for (group, ctype), info in _natal_candidates(chart).items():
        merged[(group, ctype)] = {"status": info["status"], "temporal_only": False}
    for (group, ctype), tr in transitions.items():
        if tr["kind"] == "added" and (group, ctype) not in merged:
            merged[(group, ctype)] = {"status": None, "temporal_only": True}
    return merged


def analyze_special_temporal(chart, delta_report) -> list[SpecialTemporalFinding]:
    """原局特殊格局候选 × 岁运 → 专题 findings（规则驱动，缺执行器抛错）。"""
    rules = _load_special_rules()
    transitions = _transitions(delta_report)
    ctx = delta_report.context
    findings: list[SpecialTemporalFinding] = []

    transition_map = {
        "added": "appeared", "removed": "disappeared",
        "blocked": "blocked", "unblocked": "unblocked",
        "status_changed": "regraded",
    }

    candidates = _merged_candidates(chart, transitions)
    for r in rules:
        rid = r["id"]
        fn = _SPECIAL_EVALUATORS.get(rid)
        if fn is None:
            raise KeyError(f"特殊格局岁运规则 {rid} 缺少执行器（不静默跳过）")
        results = fn(chart, ctx, candidates)
        for item in results:
            ctype, group, natal_status, label, _kind, evidence = item[:6]
            school = item[6] if len(item) > 6 else {}
            tr = transitions.get((group, ctype))
            transition = transition_map.get(tr["kind"], "unchanged") if tr else "unchanged"
            temporal_status = tr.get("temporal") if tr else None
            findings.append(SpecialTemporalFinding(
                ruleId=rid, candidateType=ctype, group=group,
                natalStatus=natal_status, temporalStatus=temporal_status,
                transition=transition,
                schoolSplit=school,
                status="CANDIDATE",
                evidence=[evidence] if isinstance(evidence, str) else list(evidence),
                provenanceLevels=[p["level"] for p in r.get("provenance", [])],
            ))
    return findings
