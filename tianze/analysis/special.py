"""M8 · 特殊格局与结构分析：从格 / 专旺 / 化气 / 病药 / 通关。

第一原则（R29）：高争议、高流派差异区域——禁止 `if condition: return "从财格"`
式结论代码。统一遵循：事实 → 候选 → 支持证据 → 阻断证据 → 例外 → 冲突 → 评估状态。
状态永不出现 CONFIRMED（CANDIDATE/LIKELY/BLOCKED/DISPUTED/UNRESOLVED）。

- 从格复用 M4 三分析器结果（weighted/fuyi 分歧即 DISPUTED，不复制旺衰算法）；
- 病药命名为 StructuralProblem/MedicineCandidate（避免医学误解，ADR-033）；
- 通关基于五行生克图（A→bridge→B 路径检索，非字符串规则）；
- 化气默认"干合 ≠ 化"，只报候选（R13 延伸）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from tianze.domain.models import Element, ProvenanceRef, RuleLevel, TenGod
from tianze.ganzhi.tables import  (
    BRANCHES,
    BRANCH_ELEMENT,
    STEMS,
    STEM_ELEMENT,
    branch_index,
    stem_index,
    ten_god,
)

ELEM_CN = {"WOOD": "木", "FIRE": "火", "EARTH": "土", "METAL": "金", "WATER": "水"}
_GEN = {Element.WOOD: Element.FIRE, Element.FIRE: Element.EARTH, Element.EARTH: Element.METAL,
        Element.METAL: Element.WATER, Element.WATER: Element.WOOD}
_CTL = {Element.WOOD: Element.EARTH, Element.EARTH: Element.WATER, Element.WATER: Element.FIRE,
        Element.FIRE: Element.METAL, Element.METAL: Element.WOOD}


class SpecialStatus(str, Enum):
    CANDIDATE = "CANDIDATE"    # 满足前置，尚需复核
    LIKELY = "LIKELY"          # 支持>阻断且多分析器一致
    BLOCKED = "BLOCKED"        # 阻断证据占优（有根/印比/克破等）
    DISPUTED = "DISPUTED"      # 分析器之间或规则之间冲突
    UNRESOLVED = "UNRESOLVED"  # 证据不足


_PROV_HOROSA = ProvenanceRef(level=RuleLevel.PROJECT_REFERENCE, project="Horosa",
                             concept="专旺/从格结构条件（baziGejuYongShen 变格候选）")
_PROV_JIWENXU = ProvenanceRef(level=RuleLevel.PROJECT_REFERENCE, project="jiwenxu",
                              concept="从格反条件：有明根/暗根即不从（yongshen._detect_cong_ge）")
_PROV_RUAN = ProvenanceRef(level=RuleLevel.PROJECT_REFERENCE, project="ruan",
                           concept="专旺五格划分（曲直/炎上/稼穑/从革/润下）")
_PROV_TIANZE = ProvenanceRef(level=RuleLevel.ENGINEERING_HEURISTIC, project="Tianze",
                             concept="候选阈值与状态映射（工程化口径，PROJECT_HEURISTIC）")


@dataclass
class Factor:
    """候选的单条证据（支持或阻断）。"""

    kind: str            # support / blocker / exception / conflict
    rule_id: str         # 如 SP-CG-01
    text: str

    def as_dict(self) -> dict:
        return {"kind": self.kind, "ruleId": self.rule_id, "text": self.text}


@dataclass
class SpecialPatternCandidate:
    """特殊格局候选（M8.1/M8.2）：候选与成立严格分离。"""

    type: str                              # 从财/从官杀/从儿/从强/曲直/炎上/稼穑/从革/润下
    school: str = "tianze-v1"              # 口径标识
    status: SpecialStatus = SpecialStatus.CANDIDATE
    prerequisites: list[str] = field(default_factory=list)
    supports: list[dict] = field(default_factory=list)
    blockers: list[dict] = field(default_factory=list)
    exceptions: list[dict] = field(default_factory=list)
    conflicts: list[dict] = field(default_factory=list)
    schoolVariants: dict[str, str] = field(default_factory=dict)
    provenance: list[ProvenanceRef] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "type": self.type, "school": self.school, "status": self.status.value,
            "prerequisites": self.prerequisites, "supports": [f.as_dict() for f in self.supports],
            "blockers": [f.as_dict() for f in self.blockers],
            "exceptions": [f.as_dict() for f in self.exceptions],
            "conflicts": [f.as_dict() for f in self.conflicts],
            "schoolVariants": self.schoolVariants,
            "provenance": [p.model_dump(by_alias=True) for p in self.provenance],
        }


# ---------- M8.1 从格 ----------

def analyze_cong(
    day_master: str,
    month_branch: str,
    stems: list[str | None],
    branches: list[str | None],
    strength_verdicts: dict[str, str | None],
    weighted_score: float | None,
    day_master_roots: int,
    helper_stems: list[str],
) -> list[SpecialPatternCandidate]:
    """从格候选：从财/从官杀/从儿/从强。输入复用 M4 StrengthResult 与 M3 根事实。

    从强 = 日主一方极旺（专旺的宽松形态），与从财/从官杀/从儿（日主极弱顺从异党）相反。
    规则来源：jiwenxu 反条件（有根不从）+ Horosa 阈值口径 + Tianze 状态映射。
    """
    dm_elem = STEM_ELEMENT[day_master]
    out: list[SpecialPatternCandidate] = []
    weak_verdicts = {m: strength_verdicts.get(m) for m in ("weighted", "fuyi")}
    both_extremely_weak = all(v in ("极弱", "偏弱") for v in weak_verdicts.values()) and any(
        v == "极弱" for v in weak_verdicts.values()
    )
    analyzer_conflict = (weak_verdicts.get("weighted") in ("极弱", "偏弱") and
                         weak_verdicts.get("fuyi") in ("偏强", "极强"))
    has_root = day_master_roots >= 1
    strong_root = day_master_roots >= 2
    has_helper = bool(helper_stems)

    # 结构统计：异党（财/官杀/食伤）占比与主导异党
    other_elems: list[Element] = []
    for s in stems:
        if s and s != day_master:
            other_elems.append(STEM_ELEMENT[s])
    drain_map = {"从财": lambda e: _CTL[dm_elem] == e,        # 我克者=财
                 "从官杀": lambda e: _CTL[e] == dm_elem,      # 克我者=官杀
                 "从儿": lambda e: _GEN[dm_elem] == e}        # 我生者=食伤
    counters = Counter(ELEM_CN[e] for e in other_elems)

    for cong_type, cond in drain_map.items():
        dominant = max((e for e in set(other_elems) if cond(e)),
                       key=lambda e: counters[ELEM_CN[e]], default=None)
        if dominant is None:
            continue
        cand = SpecialPatternCandidate(type=cong_type)
        cand.prerequisites = [
            "日主极弱（weighted/fuyi 至少一项极弱，另一项不高于偏弱）",
            "日主无根或仅余气微根（jiwenxu 反条件：明根/暗根即不从）",
            "异党（财/官杀/食伤）当令且透干成势",
            f"{cong_type}目标五行 {ELEM_CN[dominant]} 在异党中占主导",
        ]
        cand.provenance = [_PROV_JIWENXU, _PROV_HOROSA, _PROV_TIANZE]
        if month_branch and BRANCH_ELEMENT.get(month_branch) == dominant:
            cand.supports.append(Factor("support", "SP-CG-S1",
                                        f"月支{month_branch}为本气 {ELEM_CN[dominant]}，异党当令"))
        cand.supports.append(Factor(
            "support", "SP-CG-S2",
            f"旺衰分析：weighted={weak_verdicts['weighted']}，fuyi={weak_verdicts['fuyi']}"
            + (f"，score={weighted_score}" if weighted_score is not None else ""),
        ))
        if not has_root:
            cand.supports.append(Factor("support", "SP-CG-S3", "日主四支无根（虚浮无依）"))
        else:
            cand.blockers.append(Factor(
                "blocker", "SP-CG-B1",
                f"日主有根（{day_master_roots} 处）——jiwenxu 反条件：有根不从" +
                ("（强根，阻断力度大）" if strong_root else ""),
            ))
        if has_helper:
            cand.blockers.append(Factor(
                "blocker", "SP-CG-B2",
                f"印比透干（{'、'.join(helper_stems)}）——逆从格之势",
            ))
            # M24 · 印比合去/合绊两说（伍庭芳造口径：丁壬合，徐断「弃命相从」）——
            # 印比与**非印比**之干天干相合 → 真从说（合去不能生身，从势成立）与
            # 保留说（合而不化仍有意）并存；只加证据，不改状态映射（不调参）。
            helper_set = set(helper_stems)
            for h in helper_stems:
                for s2 in stems:
                    if not s2 or s2 == day_master or s2 == h or s2 in helper_set:
                        continue
                    if tuple(sorted((h, s2), key=stem_index)) in _STEM_PAIR_TRANSFORM:
                        cand.exceptions.append(Factor(
                            "exception", "SP-CG-E1",
                            f"印比{h}与{s2}天干相合——合去（不能生身，真从说，"
                            "伍庭芳造丁壬合丁印而弃命相从）vs 合绊（合而不化仍有意，"
                            "保留说）两说并存（DTZ-06：能从与否须察干支配合之趋向）",
                        ))
                        break
        if analyzer_conflict:
            cand.conflicts.append(Factor(
                "conflict", "SP-CG-C1",
                "旺衰分析器冲突：weighted 与 fuyi 方向相反——DISPUTED，不判从",
            ))
        # M26 · 真从/假从两说（DTZ-49 逐条定义；证据层注记，不改状态映射）
        if not has_root and not has_helper and both_extremely_weak:
            cand.exceptions.append(Factor(
                "exception", "SP-CG-E2",
                "真从说：日主孤弱、无根无印（DTZ-49「真从之家有几人」）——格局纯粹，"
                "行运只要不逆旺气即无失败之虑"))
        elif has_root or has_helper:
            cand.exceptions.append(Factor(
                "exception", "SP-CG-E2",
                "假从说：日主有微根或印生助（DTZ-49 假从定义）——从势可成但岁运敏感"
                "（「未交运前寒素、运过复初」；从财食伤不透/从官煞官煞不透亦假从）"))
        # 状态映射（永不 CONFIRMED）
        if analyzer_conflict:
            cand.status = SpecialStatus.DISPUTED
        elif strong_root or (has_root and has_helper):
            cand.status = SpecialStatus.BLOCKED
        elif both_extremely_weak and not has_helper:
            cand.status = SpecialStatus.LIKELY
        elif has_root or has_helper:
            cand.status = SpecialStatus.CANDIDATE
        else:
            cand.status = SpecialStatus.UNRESOLVED
        out.append(cand)

    # 从强（同党极旺，日主旺极顺从同党）——与"从弱系"相反
    same_party = sum(1 for e in other_elems if e == dm_elem or _GEN[e] == dm_elem)
    both_strong = all(v in ("极强", "偏强") for v in weak_verdicts.values()) and any(
        v == "极强" for v in weak_verdicts.values()
    )
    if both_strong and same_party >= 2:
        cand = SpecialPatternCandidate(type="从强")
        cand.prerequisites = ["日主极旺（weighted/fuyi 一致偏强以上）", "印比成势", "异党衰微"]
        cand.provenance = [_PROV_HOROSA, _PROV_TIANZE]
        cand.supports.append(Factor("support", "SP-CQ-S1",
                                    f"旺衰分析：weighted={weak_verdicts['weighted']}，"
                                    f"fuyi={weak_verdicts['fuyi']}；同党干 {same_party} 处"))
        if day_master_roots >= 2:
            cand.supports.append(Factor("support", "SP-CQ-S2", f"日主多根（{day_master_roots} 处）"))
        if any(_CTL[STEM_ELEMENT[s]] == dm_elem or _CTL[dm_elem] == STEM_ELEMENT[s]
               for s in stems if s and s != day_master):
            cand.blockers.append(Factor("blocker", "SP-CQ-B1", "存在官杀或财星透干（异党制耗）"))
        cand.status = SpecialStatus.CANDIDATE
        out.append(cand)
    return out


# ---------- M8.2 专旺 ----------

_ZHUANGWANG: dict[str, dict] = {
    "曲直": {"element": Element.WOOD, "stems": "甲乙", "branches": "寅卯辰", "trio": "亥卯未"},
    "炎上": {"element": Element.FIRE, "stems": "丙丁", "branches": "巳午未", "trio": "寅午戌"},
    "稼穑": {"element": Element.EARTH, "stems": "戊己", "branches": "辰戌丑未", "trio": None},
    "从革": {"element": Element.METAL, "stems": "庚辛", "branches": "申酉戌", "trio": "巳酉丑"},
    "润下": {"element": Element.WATER, "stems": "壬癸", "branches": "亥子丑", "trio": "申子辰"},
}


def analyze_zhuanwang(
    day_master: str,
    month_branch: str,
    stems: list[str | None],
    branches: list[str | None],
    element_counts: dict[str, dict[str, int]],
    strength_verdicts: dict[str, str | None],
) -> list[SpecialPatternCandidate]:
    """专旺格候选：曲直/炎上/稼穑/从革/润下。

    结构条件（非"某五行多就行"）：日干五行 == 格局五行；三会/三合成局或同类占优；
    天干透出；异党衰微。schoolVariants 保留 Horosa（同党≥85% 且有本气根）与
    ruan（主导行>0.75×总量 且 最强他行≤0.15）差异。
    """
    out: list[SpecialPatternCandidate] = []
    dm_elem = STEM_ELEMENT[day_master]
    spec = _ZHUANGWANG.get(ELEM_CN[dm_elem] and {v: k for k, v in
                                                  (("曲直", "WOOD"), ("炎上", "FIRE"),
                                                   ("稼穑", "EARTH"), ("从革", "METAL"),
                                                   ("润下", "WATER"))}.get(dm_elem.value, ""))
    if spec is None:
        return out
    name = {"WOOD": "曲直", "FIRE": "炎上", "EARTH": "稼穑", "METAL": "从革", "WATER": "润下"}[dm_elem.value]
    key = dm_elem.value.lower()
    visible = element_counts.get(key, {"visible": 0, "hidden": 0})
    total_visible = sum(v["visible"] for v in element_counts.values()) or 1
    share = visible["visible"] / total_visible
    cand = SpecialPatternCandidate(type=name)
    cand.prerequisites = [
        f"日干{day_master}五行与格局五行（{ELEM_CN[dm_elem]}）一致",
        "地支三会/三合成局 或 同类干支占绝对优势",
        "天干透出本气",
        "异党（克泄耗）衰微且无强根克破",
    ]
    cand.provenance = [_PROV_RUAN, _PROV_HOROSA, _PROV_TIANZE]
    # 支持证据
    branch_same = sum(1 for b in branches if b and BRANCH_ELEMENT.get(b) == dm_elem)
    if branch_same >= 3:
        cand.supports.append(Factor("support", "SP-ZW-S1", f"地支 {branch_same} 支同为 {ELEM_CN[dm_elem]}（会局/方局之势）"))
    trio_chars = spec.get("trio") or spec["branches"]
    if all(any(b == ch for b in branches if b) for ch in trio_chars):
        cand.supports.append(Factor("support", "SP-ZW-S2", f"地支俱备（{''.join(trio_chars)} 成局/方）"))
    if share >= 0.6:
        cand.supports.append(Factor("support", "SP-ZW-S3",
                                    f"同党可见占比 {share:.0%}（Horosa 口径 ≥85%、ruan 主导行 ≥75% 为参考阈值）"))
    if month_branch and BRANCH_ELEMENT.get(month_branch) == dm_elem:
        cand.supports.append(Factor("support", "SP-ZW-S4", f"月令 {month_branch} 本气当权"))
    # 阻断：异党存在（尤其官杀克破）
    opposite = _CTL[dm_elem]  # 克我者（官杀五行）
    for s in stems:
        if s and STEM_ELEMENT[s] == opposite:
            cand.blockers.append(Factor("blocker", "SP-ZW-B1",
                                        f"官杀 {s}（{ELEM_CN[opposite]}）透干克破——专旺最忌"))
    weak_opposite = sum(v for k, v in element_counts.get(opposite.value.lower(), {"visible": 0, "hidden": 0}).items())
    if weak_opposite == 0 and share < 0.6:
        cand.blockers.append(Factor("blocker", "SP-ZW-B2",
                                    f"同党占比仅 {share:.0%}（<60%），不足以成专旺之势"))
    if strength_verdicts.get("weighted") not in ("极强", "偏强"):
        cand.blockers.append(Factor("blocker", "SP-ZW-B3",
                                    f"旺衰分析不支持极旺（weighted={strength_verdicts.get('weighted')}）"))
    if share >= 0.6 and branch_same >= 3 and not any(b.kind == "blocker" and "官杀" in b.text for b in cand.blockers):
        cand.status = SpecialStatus.LIKELY
    elif cand.blockers and any("透干克破" in b.text for b in cand.blockers):
        cand.status = SpecialStatus.BLOCKED
    elif share >= 0.5 or branch_same >= 2:
        cand.status = SpecialStatus.CANDIDATE
    else:
        cand.status = SpecialStatus.UNRESOLVED
    out.append(cand)
    return out


# ---------- M8.3 化气 ----------

_STEM_PAIR_TRANSFORM = {("甲", "己"): Element.EARTH, ("乙", "庚"): Element.METAL,
                        ("丙", "辛"): Element.WATER, ("丁", "壬"): Element.WOOD,
                        ("戊", "癸"): Element.FIRE}


@dataclass
class TransformationCandidate:
    stem_pair: tuple[str, str]
    target_element: Element
    season_support: bool | None
    root_support: bool | None
    obstructions: list[str]
    competing_relations: list[str]
    status: SpecialStatus
    provenance: list[ProvenanceRef] = field(default_factory=list)
    # DTZ-47 真化条件结构化（M23）：逢龙而运（原局见辰）与日主邻位合
    chen_present: bool = False
    adjacent_to_day_master: bool | None = None

    def to_dict(self) -> dict:
        return {
            "stemPair": list(self.stem_pair), "targetElement": self.target_element.value,
            "seasonSupport": self.season_support, "rootSupport": self.root_support,
            "obstructions": self.obstructions,
            "competingRelations": self.competing_relations,
            "status": self.status.value,
            "chenPresent": self.chen_present,
            "adjacentToDayMaster": self.adjacent_to_day_master,
            "provenance": [p.model_dump(by_alias=True) for p in self.provenance],
        }


# DTZ-47（真化条件）——化格以日干与月/时之干相合为正：
# 「须月时之干相合（若年干己土相隔太远不能合化）」——年干与日干之间隔月干，不相邻。
_DAY_POS = 2          # stems 固定 year,month,day,hour 序（岁运扩展干附加其后）
_NATAL_LEN = 4

# DTZ-47：「壬癸印绶也、甲乙比劫也，均不可见」——印生身、比劫帮身，
# 日干气势不衰绝则不能真化。泛化：日主之印/比劫透干即阻化。
_HELPER_GODS_HUA = ("正印", "偏印", "比肩", "劫财")


def analyze_transformation(
    day_master: str,
    month_branch: str,
    stems: list[str | None],
    branches: list[str | None],
) -> list[TransformationCandidate]:
    """化气候选框架（M8.3）：默认"干合 ≠ 化"，只报候选；大量 UNRESOLVED 是正确行为。

    M23 真化条件精细化（DTZ-47，CLASSICAL_EXPLICIT）：
    - 位置约束：化格以日干与月/时之干相合为正；年干与日干相隔太远不能合化；
      非日主参与之干合（如年月合）不构成化格候选。岁运扩展干（位置 ≥4）不受
      原局邻位约束（岁运与日干之合不因距离失效），仅记录。
    - 印比阻化：日主之印绶/比劫透干 → 日干气势不衰绝，阻化（原注引文逐神）。
    - 争合：他干与合干争合 → 阻化（既有口径保留）。
    - 逢龙而运：原局见辰 → 记录 chenPresent（化气元神之地的柱位遁干判定
      属工程未实现部分，仅如实记录辰之有无）。
    """
    from tianze.ganzhi.tables import  HIDDEN_STEMS
    out: list[TransformationCandidate] = []
    present = [(i, s_) for i, s_ in enumerate(stems) if s_]
    chen_present = any(b == "辰" for b in branches if b)
    for a in range(len(present)):
        for b in range(a + 1, len(present)):
            ia, s1 = present[a]
            ib, s2 = present[b]
            pair = (s1, s2) if stem_index(s1) < stem_index(s2) else (s2, s1)
            target = _STEM_PAIR_TRANSFORM.get(pair)
            if target is None:
                continue
            season_support = bool(month_branch and BRANCH_ELEMENT.get(month_branch) == target)
            root_support = any(
                any(STEM_ELEMENT[h] == target for h, _r in HIDDEN_STEMS.get(br, []))
                for br in branches if br)
            obstructions = []
            others = [(idx, st) for idx, st in present
                      if idx not in (ia, ib)]
            day_idx = _DAY_POS if stems[_DAY_POS] == day_master else None
            pair_has_day_natal = (
                day_idx is not None and day_idx in (ia, ib)
                and ia < _NATAL_LEN and ib < _NATAL_LEN)
            adjacent = bool(pair_has_day_natal and abs(ia - ib) == 1)
            # 争合（DTZ-47）：只计原局争合——岁运再遇合神不破真化
            # （DTZ-48：烈女不事二夫；岁运争合由 TR-SP-04 合神再现另行观察）
            natal_others = [(idx, st) for idx, st in others if idx < _NATAL_LEN]
            for _idx, st in natal_others:
                for partner in pair:
                    op = tuple(sorted((st, partner), key=stem_index))
                    if op in _STEM_PAIR_TRANSFORM:
                        obstructions.append(f"{st} 与合干 {partner} 争合")
            # 位置约束（DTZ-47）：仅对原局位置（0-3）判定
            if day_idx is not None and ia < _NATAL_LEN and ib < _NATAL_LEN:
                if not pair_has_day_natal:
                    obstructions.append(
                        "非日主之合（DTZ-47：化格以日干与月/时之干相合为正）——隔位不合")
                elif not adjacent:
                    obstructions.append(
                        "合干与日干相隔太远（DTZ-47：年干相隔太远不能合化）")
            # 印比阻化（DTZ-47 原注：印绶/比劫均不可见；日干本身不计）。
            # 与争合同口径：只计原局印比——岁运再遇不破原局真化（DTZ-48 烈女不事二夫）；
            # 岁运印比之阻由岁运专题（TR-SP-02/05/07）另行观察。
            helper_hits = [st for idx, st in natal_others
                           if idx != _DAY_POS and ten_god(day_master, st).value in _HELPER_GODS_HUA]
            if helper_hits:
                obstructions.append(
                    f"印绶/比劫透干（{'、'.join(helper_hits)}）——日干气势不衰绝，"
                    "不能真化（DTZ-47：印绶比劫均不可见）")
            status = (SpecialStatus.CANDIDATE if season_support and not obstructions
                      else SpecialStatus.UNRESOLVED)
            out.append(TransformationCandidate(
                stem_pair=pair, target_element=target, season_support=season_support,
                root_support=root_support, obstructions=obstructions,
                competing_relations=[f"{pair[0]}{pair[1]}合（化{ELEM_CN[target]}候选）"],
                status=status,
                chen_present=chen_present,
                adjacent_to_day_master=(adjacent if pair_has_day_natal else None),
                provenance=[
                    ProvenanceRef(level=RuleLevel.PROJECT_REFERENCE, project="Tianze/jiwenxu",
                                  concept="化气候选框架；干合≠化"),
                    ProvenanceRef(level=RuleLevel.CLASSICAL_EXPLICIT,
                                  project="滴天髓·化得真者只论化（DTZ-47，徐注）",
                                  concept="真化条件：乘旺秉令/日干衰绝/逢龙而运/月时相合/"
                                          "印比不见/重见争合"),
                    ProvenanceRef(level=RuleLevel.ENGINEERING_HEURISTIC, project="Tianze",
                                  concept="状态映射，不裁决真化"),
                ],
            ))
    return out




# ---------- M25 · 外格虚神候选（ZP-05/07/11/12 + DTZ-41） ----------

def analyze_xushi_outer(
    day_master: str,
    month_branch: str,
    stems: list[str | None],
    branches: list[str | None],
) -> list[SpecialPatternCandidate]:
    """外格虚神候选：飞天禄马/井栏叉（拱刃）/刑合/子邀巳。

    纪律（ZP-05「忌刑冲填实之凶」、DTZ-41「遇官星填实破格」、DTZ-26/36「不成为格」）：
    - 只产候选（CANDIDATE/BLOCKED/UNRESOLVED），永不认定成格；
    - 填实/官星透干 = 阻断证据而非吉凶断语；
    - 每条带「外格说 vs 徐辨伤官变格说」流派注记（schoolVariants）。
    """
    from tianze.ganzhi.tables import YANG_STEM_REN
    from tianze.relation.tables import arch_target
    out: list[SpecialPatternCandidate] = []
    present = [b for b in branches if b]
    visible_stems = [s for s in stems if s]
    prov = [
        ProvenanceRef(level=RuleLevel.PROJECT_REFERENCE,
                      project="子平真诠（ZP-05/07/11/12）+ 滴天髓补注（DTZ-41）",
                      concept="拱禄拱贵/刑合/子邀巳/井栏叉倒冲——外格虚神"),
        ProvenanceRef(level=RuleLevel.ENGINEERING_HEURISTIC, project="Tianze",
                      concept="起例结构化与阻断判定（M25）；OCR 残缺处以争议注记保留"),
    ]
    guansha_gods = ("正官", "七杀")

    # 井栏叉（拱刃类，ZP-12：庚日地支辰申拱酉）——由 arch 检测派生：拱位 = 日主阳刃
    ren = YANG_STEM_REN.get(day_master)
    for x in range(len(present)):
        for y in range(x + 1, len(present)):
            tgt = arch_target(present[x], present[y])
            if (tgt and tgt not in present and ren and tgt == ren
                    and day_master == "庚"):  # ZP-12 起例：井栏叉专指庚日（辰申拱酉之属）
                cand = SpecialPatternCandidate(type=f"井栏叉（拱刃{ren}）")
                cand.prerequisites = [f"日主{day_master}之阳刃{ren}为拱位虚神",
                                      "拱位支原局不见（拱虚）"]
                cand.provenance = prov
                cand.supports.append(Factor("support", "SP-XO-S1",
                                            f"{present[x]}{present[y]}隔二缺一拱{ren}（刃位虚神）"))
                for st in visible_stems:
                    if st != day_master and ten_god(day_master, st).value in guansha_gods:
                        cand.blockers.append(Factor(
                            "blocker", "SP-XO-B1",
                            f"官杀{st}透干——填实/官星现（DTZ-41：遇官星填实破格）"))
                cand.schoolVariants = {
                    "外格说": "井栏叉以拱邀刃，虚神得用（ZP-12）",
                    "徐辨（伤官变格说）": "DTZ-41：其实为伤官变格，不必以外格附会",
                }
                cand.status = (SpecialStatus.BLOCKED if cand.blockers
                               else SpecialStatus.CANDIDATE)
                out.append(cand)

    # 飞天禄马/倒冲（ZP-12：以冲邀虚神；DTZ-41 张勋/曹锟造辨正）——庚日之子暗冲午
    if day_master == "庚":
        zi_count = sum(1 for b in present if b == "子")
        if zi_count >= 2 and "午" not in present:
            cand = SpecialPatternCandidate(type="飞天禄马（子暗冲午）")
            cand.prerequisites = ["庚日地支多子（暗冲午中丁己官星）", "午不见（填实则破）"]
            cand.provenance = prov
            cand.supports.append(Factor("support", "SP-XO-S2",
                                        f"子×{zi_count}（虚神邀合之冲势）"))
            cand.blockers.append(Factor(
                "blocker", "SP-XO-B2",
                f"子数门槛二/三两说（现 {zi_count} 子）——传统起例多以三子，二子说保留"))
            for st in visible_stems:
                if st != day_master and ten_god(day_master, st).value in guansha_gods:
                    cand.blockers.append(Factor(
                        "blocker", "SP-XO-B3",
                        f"官星{st}透干——填实破格（DTZ-41）"))
            cand.schoolVariants = {
                "外格说": "倒冲格：以冲邀虚官（ZP-12）",
                "徐辨（伤官变格说）": "DTZ-41：曹锟造「其实亦是伤官变格」——金水伤官喜见官",
            }
            cand.status = (SpecialStatus.BLOCKED
                           if any("官星" in b.text for b in cand.blockers)
                           else SpecialStatus.CANDIDATE)
            out.append(cand)

    # 六乙鼠贵（ZP-06：乙日子时，印煞临天乙贵人；忌官煞刑冲；ocrRisk=True）
    if day_master == "乙" and len(branches) >= 4 and branches[3] == "子":
        cand = SpecialPatternCandidate(type="六乙鼠贵（乙日子时）")
        cand.prerequisites = ["乙日子时（子为乙之天乙贵人，六乙遁干丙子）",
                              "忌官煞刑冲（喜忌篇：乙木独遇子时不见官煞）"]
        cand.provenance = prov + [
            ProvenanceRef(level=RuleLevel.PROJECT_REFERENCE, project="守素室丛谈（SS-R16/17）",
                          concept="天乙贵人起例与成格三要件（见合/交互得/生旺无冲破）")]
        cand.supports.append(Factor("support", "SP-XO-S6",
                                    "时支子为日元乙之天乙贵人（SS-R17 起例），印煞滋生之地"))
        for st in visible_stems:
            if st != day_master and ten_god(day_master, st).value in guansha_gods:
                cand.blockers.append(Factor(
                    "blocker", "SP-XO-B6",
                    f"官煞{st}透干——ZP-06：柱有官煞不喜（泥途说，OCR 残缺）"))
        cand.schoolVariants = {
            "外格说": "六乙鼠贵：印煞临天乙（ZP-06，quality B / ocrRisk）",
            "SS-R16 三要件口径": "贵人须见合、交互得、生旺无冲破方为有用——"
                              "单取时支贵人属窄口径，两说并存",
        }
        cand.status = (SpecialStatus.BLOCKED if cand.blockers
                       else SpecialStatus.CANDIDATE)
        out.append(cand)

    # 刑合（ZP-07：癸日暗合戊，时甲寅以寅刑巳邀戊禄——OCR 残缺，重争议）
    if day_master == "癸" and len(branches) >= 4 and branches[3] == "寅"             and "巳" not in present:
        cand = SpecialPatternCandidate(type="刑合（寅刑巳邀戊禄）")
        cand.prerequisites = ["癸日时柱寅", "巳不见（虚邀戊禄之地）",
                              "岁运/原局忌戊己透（喜忌篇：岁月怕戊己二方）"]
        cand.provenance = prov
        cand.supports.append(Factor("support", "SP-XO-S3", "癸日甲寅时，寅刑巳虚邀戊土官星"))
        for st in visible_stems:
            if st != day_master and ten_god(day_master, st).value in ("正官", "七杀", "正印", "偏印"):
                cand.blockers.append(Factor(
                    "blocker", "SP-XO-B4",
                    f"{st}（{ten_god(day_master, st).value}）透干——喜忌篇忌戊己官煞及枭印"))
        cand.schoolVariants = {
            "外格说": "刑合格：寅刑巳邀戊（ZP-07）",
            "神峰通考辨（伤官说）": "「假名刑合亦非真」——月令子位实为伤官格（ZP-07 徐按）",
        }
        cand.status = (SpecialStatus.BLOCKED if cand.blockers
                       else SpecialStatus.CANDIDATE)
        out.append(cand)

    # 子邀巳（ZP-11）：OCR 残缺（取印为用口径缺失）且子在场巳不在场覆盖 ~27% 命例——
    # 泛化过高，不落地为引擎候选（M25 审计结论）；ZP-11 保留在引文注册表与知识层，
    # 结构上的子巳邀合方向已由 SPZY-34 暗合关系层承载。
    return out


# ---------- M8.4 病药 ----------

def analyze_bingyao(element_counts: dict[str, dict[str, int]]) -> dict:
    """病药 = 命局结构矛盾 + 制衡因素（StructuralProblem/MedicineCandidate）。

    口径（PROJECT_HEURISTIC）：某五行 visible 占比 ≥ 1/2 且为日主异党 → 结构失衡病；
    制（克病者）/化（泄病者）两行若有可见单位 → 药。药必须关联具体病，不接受"喜某五行"。
    """
    problems: list[dict] = []
    medicines: list[dict] = []
    total = sum(v["visible"] for v in element_counts.values()) or 1
    for key, view in element_counts.items():
        if view["visible"] >= total / 2 and view["visible"] >= 3:
            elem = Element(key.upper())
            problems.append({
                "type": "OVERPOWERED_FACTOR", "target": key,
                "evidence": [f"{ELEM_CN[elem]}可见 {view['visible']}/{total}（≥1/2 且 ≥3 字）"],
            })
    for prob in problems:
        elem = Element(prob["target"].upper())
        control = _CTL[elem]       # 克病者=制
        drain = _GEN[elem]         # 病所生=泄
        for kind, helper in (("制", control), ("泄", drain)):
            view = element_counts[helper.value.lower()]
            if view["visible"] > 0:
                medicines.append({
                    "problem": prob["target"], "kind": kind,
                    "target": helper.value.lower(),
                    "evidence": [f"{ELEM_CN[helper]}可见 {view['visible']} 字，"
                                 f"{'克制' if kind == '制' else '宣泄'}病神 {ELEM_CN[elem]}"],
                })
    provenance = [ProvenanceRef(level=RuleLevel.ENGINEERING_HEURISTIC, project="Tianze",
                                concept="结构失衡病+制/泄药口径（占比阈值 ≥1/2 且 ≥3 字，PROJECT_HEURISTIC）"),
                  ProvenanceRef(level=RuleLevel.PROJECT_REFERENCE, project="jiwenxu(bingyao 概念)/Horosa(病药派)",
                                concept="病药为结构矛盾与制衡，非医学疾病")]
    return {"problems": problems, "medicines": medicines, "provenance": [p.model_dump(by_alias=True) for p in provenance]}


# ---------- M8.5 通关 ----------

def analyze_tongguan(element_counts: dict[str, dict[str, int]]) -> dict:
    """通关：识别 A 克 B 对峙 + A→C→B 桥接（C 生 B 且 A 生 C）。基于五行生克图检索。

    对峙定义（PROJECT_HEURISTIC）：A 与 B 均有可见单位、A 克 B、且 A 的可见数 ≥ B 的 2 倍
    或 B ≥ A 的 2 倍（力量显著不均形成"对峙"）。桥 = A 生 C 且 C 生 B，C 可见。
    """
    pairs: list[dict] = []
    bridges: list[dict] = []
    total = sum(v["visible"] for v in element_counts.values()) or 1
    elems = {e: element_counts[e.lower()]["visible"] for e in Element}
    provenance = [ProvenanceRef(level=RuleLevel.ENGINEERING_HEURISTIC, project="Tianze",
                                concept="对峙阈值（一方 ≥ 另一方 2 倍）与桥检索（A→C→B 生链），基于五行图"),
                  ProvenanceRef(level=RuleLevel.PROJECT_REFERENCE, project="jiwenxu(interactions 贪生忘克)/Horosa(通关派)",
                                concept="通关概念")]
    for a in Element:
        for b in Element:
            if a == b or _CTL[a] != b:
                continue
            va, vb = elems[a.value], elems[b.value]
            if va == 0 or vb == 0:
                continue
            if not (va >= 2 * vb or vb >= 2 * va):
                continue
            strong, weak = (a, b) if va >= 2 * vb else (b, a)
            pair = {"conflict": {"from": strong.value, "to": weak.value},
                    "evidence": [f"{ELEM_CN[strong]} {elems[strong.value]} 字 vs {ELEM_CN[weak]} {elems[weak.value]} 字（≥2 倍对峙）"]}
            pairs.append(pair)
            bridge = _GEN[strong]  # strong 所生
            if bridge == weak:
                continue  # strong 生 weak 不构成通关（无克）
            bview = element_counts[bridge.value.lower()]
            present = bview["visible"] > 0
            positions = [f"{i}" for i, s in enumerate(STEMS)
                         if STEM_ELEMENT[s] == bridge]  # 理论位置；命例由调用方细化
            bridges.append({
                "conflict": pair["conflict"], "bridge": bridge.value,
                "present": present, "positions": positions if present else [],
                "evidence": [f"通关路径 {ELEM_CN[strong]} → {ELEM_CN[bridge]} → {ELEM_CN[weak]}"
                             f"（{'桥已存在 ' + str(bview['visible']) + ' 字' if present else '桥未出现，行运遇之则通'}）"],
            })
    return {"conflictPairs": pairs, "bridges": bridges, "provenance": [p.model_dump(by_alias=True) for p in provenance]}


from collections import Counter  # noqa: E402  （analyze_cong 使用）


def analyze_all_special(
    day_master: str,
    month_branch: str,
    stems: list[str | None],
    branches: list[str | None],
    strength_verdicts: dict[str, str | None],
    weighted_score: float | None,
    day_master_roots: int,
    helper_stems: list[str],
    element_counts: dict[str, dict[str, int]],
) -> dict:
    """M8 总入口：specialPattern / bingYao / tongGuan 三组结果。"""
    cong = analyze_cong(day_master, month_branch, stems, branches, strength_verdicts,
                        weighted_score, day_master_roots, helper_stems)
    zhuanwang = analyze_zhuanwang(day_master, month_branch, stems, branches, element_counts,
                                  strength_verdicts)
    transformation = analyze_transformation(day_master, month_branch, stems, branches)
    xushi_outer = analyze_xushi_outer(day_master, month_branch, stems, branches)
    bingyao = analyze_bingyao(element_counts)
    tongguan = analyze_tongguan(element_counts)
    return {
        "specialPattern": {
            "cong": [c.to_dict() for c in cong],
            "zhuanwang": [c.to_dict() for c in zhuanwang],
            "transformation": [c.to_dict() for c in transformation],
            "xushiOuter": [c.to_dict() for c in xushi_outer],
        },
        "bingYao": bingyao,
        "tongGuan": tongguan,
    }
