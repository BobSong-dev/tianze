"""M15 · 规则冲突推理（方向级）：同主题规则方向相反时的上下文相关解释。

原则（对齐任务书）：
- 不建立全局 A > B 优先级——解释是**上下文相关**的（当两条规则在同一命盘同时命中）
- 三类解释（全部透明、可审计）：
    SPECIFIC_EXCEPTION  B 是 A 的更具体例外条件 → 当前以 B 为主要解释，同时记录 A
    SCHOOL_DIFFERENCE   两条规则属不同流派 → 不裁决，保持 DISPUTED
    CONDITION_OVERLAP   条件重叠且无例外关系 → 保留双方，status=DISPUTED
- precedence 数据来源：knowledge/rules/event/conflicts.json 的 pairwise 声明
  （resolution 字段），与 tiaohou conflicts.json 同构；未声明的对默认 CONDITION_OVERLAP
- specificity 由声明提供（规则作者显式声明谁更具体），不由引擎启发式猜测
"""

from __future__ import annotations

import json
import os
from functools import lru_cache

from tianze.domain.models import CamelizeModel

__all__ = ["ConflictExplanation", "explain_conflicts", "CONFLICTS_PATH"]

CONFLICTS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "knowledge", "rules", "event", "conflicts.json",
)


class ConflictExplanation(CamelizeModel):
    """一次方向冲突的上下文相关解释。"""
    kind: str                      # SPECIFIC_EXCEPTION / SCHOOL_DIFFERENCE / CONDITION_OVERLAP
    ruleA: str                     # 一般/被限制方（或流派 A）
    ruleB: str                     # 具体/例外方（或流派 B）
    viewA: str = ""
    viewB: str = ""
    directionA: str = ""
    directionB: str = ""
    resolution: str                # 透明处理方式（specific-over-general / keep-both / no-adjudication）
    explanation: str               # 面向解释层的文字
    provenanceLevels: list[str] = []
    refId: str | None = None

    def model_post_init(self, __context) -> None:
        if self.refId is None:
            object.__setattr__(
                self, "refId",
                f"event:conflict:{self.kind}:{self.ruleA}:{self.ruleB}")


@lru_cache(maxsize=1)
def load_conflict_declarations() -> list[dict]:
    """pairwise 冲突声明：{ruleA, ruleB, resolution, note}（A/B 顺序无关）。"""
    if not os.path.exists(CONFLICTS_PATH):
        return []
    payload = json.load(open(CONFLICTS_PATH, encoding="utf-8"))
    return payload.get("conflicts", [])


def _lookup_pair(a: str, b: str) -> dict | None:
    key = frozenset({a, b})
    for c in load_conflict_declarations():
        if frozenset({c.get("ruleA"), c.get("ruleB")}) == key:
            return c
    return None


def explain_conflicts(hits: list, view_of_rule: dict[str, str] | None = None,
                      label_of_rule: dict[str, str] | None = None,
                      prov_of_rule: dict[str, list[str]] | None = None,
                      rescue_state: dict | None = None) -> list[ConflictExplanation]:
    """对同一主题内方向相反的规则命中生成上下文相关解释。

    hits: EventRuleHit 列表（已按主题聚合）；
    *_of_rule: 规则元数据（view/label/provenance），由调用方从 rules.json 提供。
    """
    view_of = view_of_rule or {}
    prov_of = prov_of_rule or {}
    sup = [h for h in hits if h.direction.value == "support"]
    opp = [h for h in hits if h.direction.value in ("oppose", "block")]
    if not sup or not opp:
        return []

    explanations: list[ConflictExplanation] = []
    seen_pairs: set[frozenset] = set()
    for a in sup:
        for b in opp:
            pair = frozenset({a.ruleId, b.ruleId})
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            va, vb = view_of.get(a.ruleId, ""), view_of.get(b.ruleId, "")
            provs = sorted(set(prov_of.get(a.ruleId, []) + prov_of.get(b.ruleId, [])))
            decl = _lookup_pair(a.ruleId, b.ruleId)

            # M16：specificCondition（救应谓词）成立 → SPECIFIC_EXCEPTION 真实启用；
            # 不成立 → 回落 keep-both/no-adjudication（上下文相关优先级，非全局 A>B）
            cond_id = (decl or {}).get("specificCondition")
            cond_active = bool(cond_id) and bool((rescue_state or {}).get(cond_id, {}).get("active"))
            if decl and decl.get("resolution") == "specific-over-general" and cond_id and cond_active:
                specific = decl.get("specific")
                general = decl.get("ruleA") if specific == decl.get("ruleB") else decl.get("ruleB")
                if specific in (a.ruleId, b.ruleId) and general in (a.ruleId, b.ruleId):
                    main = a if a.ruleId == specific else b
                    other = b if main is a else a
                    cond_note = (rescue_state or {}).get(cond_id, {})
                    explanations.append(ConflictExplanation(
                        kind="SPECIFIC_EXCEPTION",
                        ruleA=general, ruleB=specific,
                        viewA=va, viewB=vb,
                        directionA=a.direction.value if a.ruleId == general else b.direction.value,
                        directionB=b.direction.value if b.ruleId == specific else a.direction.value,
                        resolution="specific-over-general",
                        explanation=(
                            f"{general} 命中，但 {specific} 的更具体条件/救应在本上下文成立"
                            f"（{decl.get('specificConditionNote', cond_id)}；"
                            f"依据：{'；'.join(cond_note.get('evidence', [])[:2]) or cond_note.get('note', '')}）"
                            f"——以 {specific} 为主要解释，{general} 保留为背景证据（不删除）"),
                        provenanceLevels=provs,
                    ))
                    continue
            # specificCondition 存在但不成立（或无 condition 的旧式声明）→ 不启用
            # SPECIFIC_EXCEPTION，回落到 SCHOOL_DIFFERENCE / CONDITION_OVERLAP。

            if va and vb and va != vb:
                explanations.append(ConflictExplanation(
                    kind="SCHOOL_DIFFERENCE",
                    ruleA=a.ruleId, ruleB=b.ruleId,
                    viewA=va, viewB=vb,
                    directionA=a.direction.value, directionB=b.direction.value,
                    resolution="no-adjudication",
                    explanation=(f"两条规则属不同流派视角（{va} vs {vb}），方向相反："
                                 f"不裁决，保持 DISPUTED，双方证据全部保留"
                                 + (f"；{decl['note']}" if decl and decl.get("note") else "")),
                    provenanceLevels=provs,
                ))
                continue

            explanations.append(ConflictExplanation(
                kind="CONDITION_OVERLAP",
                ruleA=a.ruleId, ruleB=b.ruleId,
                viewA=va, viewB=vb,
                directionA=a.direction.value, directionB=b.direction.value,
                resolution="keep-both",
                explanation=(f"同一视角（{va or 'traditional'}）下两条规则条件重叠且方向相反："
                             f"保留双方证据，status=DISPUTED（无优先级声明时引擎不做裁决）"
                             + (f"；{decl['note']}" if decl and decl.get("note") else "")),
                provenanceLevels=provs,
            ))
    return explanations
