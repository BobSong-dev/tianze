"""M25 · 关系级 ExplanationChain：成立 / 候选 / 阻断 三态统一解释。

知识链路：
    relation.tables（关系事实） + citations.json（引文注册表，机械生成）
        → build_relation_explanations() → RelationExplanation

状态词汇（本模块口径）：
    ESTABLISHED  —— 结构事实：公版表逐对判定（冲/合/刑/害/破/三合三会/干合干冲）
    CANDIDATE    —— 候选关系：拱夹/暗合（成立条件已核，但影响力属候选，永不升格）
    BLOCKED      —— 未成立候选：隔二缺一但靶支在场（只解释「为什么未成立」）

纪律：
- BLOCKED 条目绝不是关系，只用于解释；AI 可以引用但不得描述为成立关系；
- 候选关系永不升级为格局/用神（DTZ-26/36）；
- 引文来自 citations.json 注册表（normalized 候选机械提取），模块内不手写引文。
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any, Sequence

from tianze.domain.models import CamelizeModel
from tianze.relation import tables as T

__all__ = [
    "RelationExplanation", "RelationCondition", "RelationCitation",
    "build_relation_explanations", "explain_relation_generic",
    "RELATION_EXPLAIN_SCHEMA_VERSION",
]

RELATION_EXPLAIN_SCHEMA_VERSION = "1.0.0"

# 候选关系（影响力候选级）；其余已知 kind 视为结构事实；未知 kind → CANDIDATE 保守处理
_CANDIDATE_KINDS = {"arch", "hidden_combination", "arch_fill"}

# kind → 引文注册表键（引用链：关系类型 → 候选 id）
_KIND_CITATIONS: dict[str, list[str]] = {
    "arch": ["DTZ-10", "ZP-05", "SS-R17", "SS-R16", "DTZ-26", "DTZ-36"],
    "arch_fill": ["DTZ-10", "ZP-05", "DTZ-41"],
    "hidden_combination": ["SPZY-34", "DTZ-36"],
    "clash": ["R9"], "harm": ["R9"], "break": ["R9"],
    "punishment_trio": ["R9"], "punishment_pair": ["R9"],
    "self_punishment": ["R9"], "punishment_zimao": ["R9"],
    "three_harmony": ["R10"], "three_harmony_half": ["R10"],
    "three_harmony_completed": ["R10"],
    "three_meeting": ["R9"],
    "six_combination": ["R13"], "stem_combination": ["R13"],
    "combination_state": ["R13", "DTZ-47", "DTZ-18", "DTZ-26", "DTZ-36"],
    "stem_opposition": ["R14"],
}

_KIND_CN: dict[str, str] = {
    "arch": "拱夹/虚神", "arch_fill": "拱位填实", "hidden_combination": "暗合",
    "clash": "六冲", "harm": "六害", "break": "六破",
    "punishment_trio": "三刑全", "punishment_pair": "三刑部分对",
    "self_punishment": "自刑", "punishment_zimao": "子卯相刑",
    "three_harmony": "三合局", "three_harmony_half": "半三合",
    "three_harmony_completed": "三合补齐（岁运）", "three_meeting": "三会方",
    "six_combination": "六合", "stem_combination": "天干五合", "stem_opposition": "天干四冲",
}

_BOUNDARY_CANDIDATE = ("候选关系：非格局、非用神（DTZ-26/36），不参与旺衰/格局/事件推理，"
                       "仅作结构与解释层展示")
_BOUNDARY_BLOCKED = ("未成立候选：本条目不是关系，仅解释「为什么未成立」；"
                     "不得被描述为成立关系（AI Grounding 约束）")
_BOUNDARY_FILL = ("填实为结构事件：ZP-05「忌刑冲填实之凶」为原典禁则语境，"
                  "Tianze 只输出事件，不判吉凶")


class RelationCitation(CamelizeModel):
    candidateId: str
    book: str
    title: str
    quote: str
    sourceFile: str = ""
    quality: str = ""
    ocrRisk: bool = False
    sourceKind: str = "CLASSICAL_EXPLICIT"


class RelationCondition(CamelizeModel):
    text: str
    satisfied: bool


class RelationExplanation(CamelizeModel):
    refId: str
    kind: str
    kindCn: str
    status: str                       # ESTABLISHED / CANDIDATE / BLOCKED
    label: str
    members: list[str] = []
    positions: list[str] = []
    conditions: list[RelationCondition] = []
    schoolNotes: list[str] = []
    exceptions: list[str] = []
    citations: list[RelationCitation] = []
    evidence: list[str] = []
    boundary: str = ""
    relationSchemaVersion: str = RELATION_EXPLAIN_SCHEMA_VERSION


@lru_cache(maxsize=1)
def _load_citations() -> dict[str, dict]:
    """引文注册表：repo knowledge/ 或打包副本（paths.data_root）。"""
    try:
        from tianze.paths import data_root
        path = data_root() / "rules" / "relations" / "citations.json"
        if path.exists():
            return json.load(open(path, encoding="utf-8"))["citations"]
    except Exception:
        pass
    fallback = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "knowledge", "rules", "relations", "citations.json")
    if os.path.exists(fallback):
        return json.load(open(fallback, encoding="utf-8"))["citations"]
    return {}


def _citations_for(kind: str) -> list[RelationCitation]:
    reg = _load_citations()
    out: list[RelationCitation] = []
    for cid in _KIND_CITATIONS.get(kind, []):
        c = reg.get(cid)
        if not c:
            continue
        out.append(RelationCitation(
            candidateId=cid, book=c.get("book", ""), title=c.get("title", ""),
            quote=(c.get("quote", "") or "")[:160],
            sourceFile=c.get("sourceFile", ""), quality=c.get("quality", ""),
            ocrRisk=bool(c.get("ocrRisk", False)), sourceKind=c.get("sourceKind", "CLASSICAL_EXPLICIT"),
        ))
    return out


def _cond(text: str, satisfied: bool = True) -> RelationCondition:
    return RelationCondition(text=text, satisfied=satisfied)


def _explain_arch(note: str, target_in_chart: bool) -> tuple[list[RelationCondition], list[str], list[str]]:
    """拱夹条件与流派注记（由 note 承载的检测层事实转译，不重算）。"""
    conditions = [
        _cond("地支环隔二缺一（关系表 arch_target）"),
        _cond("被拱之支不在场（拱虚；拱实不若拱虚，DTZ-10）", not target_in_chart),
        _cond("「集于一点」强度证据（两柱天干相同或暗合，ZP-05）",
              "集于一点" in note),
    ]
    school = ["暗冲暗会两说并存（DTZ-10：我冲彼冲皆冲起，不必论彼我）"]
    if "亦为日元" in note:
        school.append("拱禄与拱三会方同见——两重身份并存注记（ZP-05）")
    exceptions = []
    return conditions, school, exceptions


def _explain_hidden(note: str) -> tuple[list[RelationCondition], list[str], list[str]]:
    conditions = [
        _cond("逐对命中 SPZY-34 暗合表（两支各取禄旺之气）"),
        _cond("两支毗连（贴邻柱；SPZY-34 原文口径）"),
        _cond("不与六合重叠（六合为明合，另立关系）"),
    ]
    school = []
    if "不以合论" in note:
        school.append("巳酉会局不以合论（SPZY-34 原注）——两读保留")
    exceptions = ["暗合非化（SPZY-34：凡命造之佳者必多合，非以化论也）"]
    return conditions, school, exceptions


def _explain_fill(note: str) -> tuple[list[RelationCondition], list[str], list[str]]:
    conditions = [
        _cond("原局存在拱位虚神（隔二缺一且靶支不见）"),
        _cond("岁运支命中拱位虚神（填实）"),
    ]
    school = ["刑冲与填实均为原典禁则（ZP-05）；是否应凶属喜忌层面，Tianze 不判"]
    return conditions, school, []


def _explain_established(kind: str, note: str) -> tuple[list[RelationCondition], list[str], list[str]]:
    conditions: list[RelationCondition] = []
    if kind == "three_harmony_half":
        conditions.append(_cond("半三合须含中神（R10）"))
    elif kind == "three_harmony":
        conditions.append(_cond("三支全（成局与否留给分析层，R10/R13）"))
    elif kind == "punishment_trio":
        conditions.append(_cond("三刑全组优先（R9；义理派命名互换以 note 保留）"))
    elif kind == "stem_combination":
        conditions.append(_cond("干支五合表命中（R13：只报化气候选，不判化）"))
    elif kind == "six_combination":
        conditions.append(_cond("六合表命中（R13：化气候选）"))
    school = []
    if note and ("两说" in note or "两表并存" in note or "互换" in note or "默认" in note):
        school.append(note)
    return conditions, school, []


def explain_relation_generic(
    kind: str, label: str, members: Sequence[str], positions: Sequence[str],
    note: str | None, blocked: bool = False,
) -> RelationExplanation:
    """统一入口：原局 Interaction 与岁运 TemporalRelation 均可解释。"""
    note = note or ""
    if blocked:
        status = "BLOCKED"
        conditions, school, exceptions = _explain_arch(note, target_in_chart=True)
        boundary = _BOUNDARY_BLOCKED
    elif kind in _CANDIDATE_KINDS:
        status = "CANDIDATE"
        if kind == "hidden_combination":
            conditions, school, exceptions = _explain_hidden(note)
        elif kind == "arch_fill":
            conditions, school, exceptions = _explain_fill(note)
        else:
            conditions, school, exceptions = _explain_arch(note, target_in_chart=False)
        boundary = _BOUNDARY_FILL if kind == "arch_fill" else _BOUNDARY_CANDIDATE
    else:
        status = "ESTABLISHED"
        conditions, school, exceptions = _explain_established(kind, note)
        boundary = ""
    evidence = [f"{label}（{'/'.join(positions) or '岁运'}）"]
    if note:
        evidence.append(note)
    return RelationExplanation(
        refId=f"relation-explain:{kind}:{label}",
        kind=kind, kindCn=_KIND_CN.get(kind, kind), status=status,
        label=label, members=list(members), positions=list(positions),
        conditions=conditions, schoolNotes=school, exceptions=exceptions,
        citations=_citations_for(kind), evidence=evidence, boundary=boundary,
    )


def explain_combination_state(entry: dict) -> RelationExplanation:
    """合化状态解释链（M36）：stem_combination_states 条目 → 三态解释。

    状态候选级：永不判定化成（DTZ-18「合与化不同」）；引文 DTZ-47（真化条件三要素）。
    refId 独立前缀 combination-state:*（不与关系/事件 refId 冲突）。
    """
    state = entry.get("state", "")
    conditions = [
        _cond("五合表命中（R13/SPZY-34 口径）"),
        _cond("邻位（贴邻柱）", bool(entry.get("adjacent"))),
        _cond("月令化神（乘旺秉令，DTZ-47）", bool(entry.get("season"))),
        _cond("无阻化（争合/印比/隔位，DTZ-47）", not entry.get("obstructions")),
    ]
    school = ["合与化不同（DTZ-18：今人见合皆作化论殊误）——状态仅为条件结构"]
    if "近真化" in state:
        school.append("近真化条件满足为候选前提；化成与否永不判定（R13）")
    return RelationExplanation(
        refId=f"combination-state:{entry.get('stem')}:{entry.get('partner')}",
        kind="combination_state", kindCn="合化状态",
        status="CANDIDATE",
        label=f"{entry.get('stem')}{entry.get('partner')}——{state}",
        members=[entry.get("stem", ""), entry.get("partner", "")],
        positions=[f"pos{p}" for p in entry.get("positions", [])],
        conditions=conditions, schoolNotes=school,
        citations=_citations_for("combination_state"),
        evidence=[f"三要素：邻位={entry.get('adjacent')}，月令化神={entry.get('season')}，"
                  f"阻化={len(entry.get('obstructions') or [])}"],
        boundary="合化状态候选：不判定化成，不参与旺衰/事件推理（DTZ-26/36 同口径）",
    )


def build_relation_explanations(chart, combination_states: list[dict] | None = None) -> list[RelationExplanation]:
    """原局关系 + 未成立候选 + 合化状态 → 解释链列表（M36）。

    combination_states：调用方（pipeline）以 stem_combination_states() 产出传入
    （引擎层负责计算，解释层只转译）。
    """
    out: list[RelationExplanation] = []
    for entry in combination_states or []:
        out.append(explain_combination_state(entry))
    for rel in getattr(chart, "relations", None) or []:
        out.append(explain_relation_generic(
            rel.kind.value if hasattr(rel.kind, "value") else str(rel.kind),
            rel.label, rel.members, rel.positions, rel.note, blocked=False))
    for rel in getattr(chart, "blocked_relations", None) or []:
        out.append(explain_relation_generic(
            rel.kind.value if hasattr(rel.kind, "value") else str(rel.kind),
            rel.label, rel.members, rel.positions, rel.note, blocked=True))
    return out
