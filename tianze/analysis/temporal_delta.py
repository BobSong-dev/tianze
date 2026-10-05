"""M13 · 完整 Temporal Delta：原局 vs 岁运扩展上下文的状态差异分析。

设计原则（对齐任务书边界）：
- 复用现有引擎（strength/pattern/tiaohou/special/bingyao/tongguan），不重写算法
- 月令保持原局：格局候选、调候取用规则匹配、旺衰月令维度均不允许被岁运替换
- 每条 Delta 标注 supportLevel：
    SUPPORTED    —— 规则驱动的确定比较（如调候用神到位、格局评估证据增减）
    EXPERIMENTAL —— 岁运参与该计算存在流派分歧（如岁运字入旺衰计分、岁运阻断从格）
    UNSUPPORTED  —— 理论上不应随岁运变化（格局候选重推导）——明确不计算，只给 note
- 不输出吉凶：Delta 只描述结构状态迁移，不做事件预测
- refId：确定性引用串，供 AI 解释层绑定（禁止 AI 自由发挥）
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Sequence

from tianze.domain import models as M
from tianze.domain.models import CamelizeModel
from tianze.analysis.strength import StrengthFacts, default_run
from tianze.analysis.strength.base import VERDICT_SCALE
from tianze.analysis.pattern import evaluate_pattern
from tianze.analysis.tiaohou import analyze_tiaohou
from tianze.analysis.special import analyze_all_special
from tianze.analysis.element_counts import count_elements
from tianze.ganzhi import tables as G
from tianze.ganzhi.tables import ten_god
from tianze.analysis.temporal import (
    AnalysisSupport,
    TemporalContext,
    TemporalSource,
)

__all__ = [
    "DeltaKind", "DeltaItem", "TemporalDeltaReport", "compute_temporal_delta",
    "DELTA_SCHEMA_VERSION",
]

DELTA_SCHEMA_VERSION = "1.0.0"

_LAYER_CN = {"luck": "大运", "annual": "流年", "monthly": "流月", "daily": "流日"}

_HELPER_GODS = ("比肩", "劫财", "正印", "偏印")

_ELEM_CN = {"WOOD": "木", "FIRE": "火", "EARTH": "土", "METAL": "金", "WATER": "水"}


class DeltaKind(str, Enum):
    ADDED = "added"                              # 新出现
    REMOVED = "removed"                          # 消失
    STRENGTHENED = "strengthened"                # 增强
    WEAKENED = "weakened"                        # 减弱
    STATUS_CHANGED = "status_changed"            # status 迁移
    BLOCKED = "blocked"                          # 候选被阻断
    UNBLOCKED = "unblocked"                      # 阻断解除 / 条件由休眠转满足
    DISAGREEMENT_CHANGED = "disagreement_changed"  # 多方法一致性变化


class DeltaItem(CamelizeModel):
    """统一 Delta 条目：一条结构状态迁移。"""
    analysis: str                        # strength / pattern / tiaohou / special / bingYao / tongGuan / tenGodTheme
    kind: DeltaKind
    subject: str                         # 变化主体（如 "从财"、"调候用神丙"、"旺衰 weighted"）
    supportLevel: AnalysisSupport = AnalysisSupport.EXPERIMENTAL
    natalValue: Any = None
    temporalValue: Any = None
    trigger: str | None = None           # 触发来源（如 "大运甲子"、"流年丙寅"）
    evidence: list[str] = []
    refId: str | None = None             # 确定性 claim ref（供 AI 绑定）


class TemporalDeltaReport(CamelizeModel):
    """完整岁运 Delta 报告。"""
    context: TemporalContext
    deltaSchemaVersion: str = DELTA_SCHEMA_VERSION
    items: list[DeltaItem] = []
    unsupportedNotes: list[str] = []     # 明示未计算/不适用的部分
    warnings: list[str] = []


def _trigger_label(label: str, stem: str | None, branch: str | None) -> str:
    gz = (stem or "") + (branch or "")
    return f"{_LAYER_CN[label]}{gz}" if gz else _LAYER_CN[label]


def _layers_str(units: Sequence[tuple[str, str | None, str | None]]) -> str:
    return "、".join(_trigger_label(l, s, b) for l, s, b in units) or "（无岁运）"


# ---------- 旺衰 Delta ----------

def _strength_delta(chart: M.BaziChart, ctx: TemporalContext,
                    units: list[tuple[str, str | None, str | None]],
                    items: list[DeltaItem]) -> dict | None:
    """岁运扩展上下文重跑旺衰（EXPERIMENTAL），返回 temporal 方法表供 special 复用。"""
    if chart.strength is None:
        return None
    natal_report = chart.strength
    positions = ["year", "month", "day", "hour"]
    natal_stems = [chart.pillars.year.stem, chart.pillars.month.stem,
                   chart.pillars.day.stem,
                   chart.pillars.hour.stem if chart.pillars.hour else None]
    natal_branches = [chart.pillars.year.branch, chart.pillars.month.branch,
                      chart.pillars.day.branch,
                      chart.pillars.hour.branch if chart.pillars.hour else None]

    other_stems: list[tuple[str, str]] = [
        (s, p) for s, p in zip(natal_stems, positions) if s and p != "day"
    ]
    pillar_units: list[tuple[str, str | None, str | None]] = list(
        zip(positions, natal_stems, natal_branches)
    )
    for label, st, br in units:
        if st:
            other_stems.append((st, label))
        pillar_units.append((label, st, br))

    dm = chart.day_master.stem
    facts = StrengthFacts(
        day_master=dm,
        day_master_element=G.STEM_ELEMENT[dm],
        month_command=chart.month_command,          # 原局月令：岁运不替换
        day_master_roots=tuple(r for r in chart.roots if r.is_day_master),
        other_stems=tuple(other_stems),
        pillar_units=tuple(pillar_units),
    )
    temporal_report = default_run(facts)

    for n_m, t_m in zip(natal_report.methods, temporal_report.methods):
        mid = getattr(n_m, "analyzer_id", n_m.name)
        if n_m.verdict and t_m.verdict and n_m.verdict != t_m.verdict:
            if n_m.verdict == "UNCERTAIN" or t_m.verdict == "UNCERTAIN":
                kind = DeltaKind.STATUS_CHANGED
            else:
                ni, ti = VERDICT_SCALE.index(n_m.verdict), VERDICT_SCALE.index(t_m.verdict)
                kind = DeltaKind.STRENGTHENED if ti < ni else DeltaKind.WEAKENED
            items.append(DeltaItem(
                analysis="strength", kind=kind,
                subject=f"旺衰·{n_m.name}", supportLevel=AnalysisSupport.EXPERIMENTAL,
                natalValue=n_m.verdict, temporalValue=t_m.verdict,
                trigger=_layers_str(units),
                evidence=[
                    f"原局 {n_m.name} 判定 {n_m.verdict}，岁运扩展上下文判定 {t_m.verdict}",
                    "岁运字按显式规则入/不入计分存在流派分歧：本结果仅描述扩展口径下的变化（EXPERIMENTAL）",
                ],
                refId=f"temporal:strength:{mid}",
            ))
        elif n_m.verdict is None and t_m.verdict is None and n_m.strength_evidence and t_m.strength_evidence:
            # dimension 定性三维对比
            for dim, cn in ((("de_ling"), "得令"), (("de_di"), "得地"), (("de_shi"), "得势")):
                nd = getattr(n_m.strength_evidence, dim)
                td = getattr(t_m.strength_evidence, dim)
                if nd.result != td.result:
                    items.append(DeltaItem(
                        analysis="strength", kind=DeltaKind.STATUS_CHANGED,
                        subject=f"旺衰·{n_m.name}·{cn}",
                        supportLevel=AnalysisSupport.EXPERIMENTAL,
                        natalValue=nd.result, temporalValue=td.result,
                        trigger=_layers_str(units),
                        evidence=td.reason or [f"{cn}状态由 {nd.result} 变为 {td.result}"],
                        refId=f"temporal:strength:{mid}:{dim}",
                    ))
        if n_m.score is not None and t_m.score is not None and abs(n_m.score - t_m.score) > 1e-9:
            new_factors = [c for c in (t_m.contributions or [])
                           if any(c.factor.endswith(f":{l}") for l, _, _ in units)]
            items.append(DeltaItem(
                analysis="strength", kind=DeltaKind.STATUS_CHANGED,
                subject=f"旺衰·{n_m.name}·score", supportLevel=AnalysisSupport.EXPERIMENTAL,
                natalValue=round(n_m.score, 4), temporalValue=round(t_m.score, 4),
                trigger=_layers_str(units),
                evidence=[f"support/drain 比 {n_m.score:.4f} → {t_m.score:.4f}（公开公式，参数随结果输出）"]
                + [f"岁运计分单位：{c.factor} {c.effect} {c.value}（{c.reason}）" for c in new_factors],
                refId=f"temporal:strength:{mid}:score",
            ))

    if natal_report.agreement != temporal_report.agreement:
        items.append(DeltaItem(
            analysis="strength", kind=DeltaKind.DISAGREEMENT_CHANGED,
            subject="旺衰·多方法一致性", supportLevel=AnalysisSupport.EXPERIMENTAL,
            natalValue=natal_report.agreement, temporalValue=temporal_report.agreement,
            trigger=_layers_str(units),
            evidence=[f"agreement（R22）：{natal_report.agreement} → {temporal_report.agreement}；"
                      "多方法并列、不裁决，一致性变化仅作提示"],
            refId="temporal:strength:agreement",
        ))

    return {
        "report": temporal_report,
        "verdicts": {
            ("dimension" if "dimension" in m.analyzer_id else
             "weighted" if "weighted" in m.analyzer_id else "fuyi"): m.verdict
            for m in temporal_report.methods
        },
        "weighted_score": next((m.score for m in temporal_report.methods if m.score is not None), None),
    }


# ---------- 格局 Delta ----------

def _pattern_delta(chart: M.BaziChart, ctx: TemporalContext,
                   units: list[tuple[str, str | None, str | None]],
                   items: list[DeltaItem],
                   unsupported: list[str]) -> None:
    pa = chart.pattern
    if pa is None or not pa.candidates or pa.evaluation is None:
        return
    unsupported.append(
        "pattern：格局候选与取格依据由月令推导，岁运不改变格局候选（月令保持原局）。"
        "以下仅评估岁运干对既有候选证据（支持/破坏/救应）的影响（SUPPORTED）。"
    )
    cand = pa.candidates[pa.primary_index or 0]
    dm = chart.day_master.stem
    positions = ["year", "month", "day", "hour"]
    natal_stems = [chart.pillars.year.stem, chart.pillars.month.stem,
                   chart.pillars.day.stem,
                   chart.pillars.hour.stem if chart.pillars.hour else None]
    ext_other = [(s, p) for s, p in zip(natal_stems, positions) if s and p != "day"]
    ext_other += [(st, label) for label, st, _ in units if st]

    natal_eval = pa.evaluation
    temp_eval = evaluate_pattern(cand, dm, ext_other)

    natal_sup = {f.rule_id for f in natal_eval.supports}
    natal_dmg = {f.rule_id for f in natal_eval.damages}
    natal_res = {f.rule_id for f in natal_eval.rescues}
    for f in temp_eval.supports:
        if f.rule_id not in natal_sup:
            items.append(DeltaItem(
                analysis="pattern", kind=DeltaKind.ADDED, subject=f"格局支持·{cand.name}",
                supportLevel=AnalysisSupport.SUPPORTED,
                natalValue=None, temporalValue=f.detail,
                trigger=_layers_str(units),
                evidence=[f"{f.rule_id} {f.name}：{f.detail}"],
                refId=f"temporal:pattern:support:{f.rule_id}",
            ))
    for f in temp_eval.damages:
        if f.rule_id not in natal_dmg:
            items.append(DeltaItem(
                analysis="pattern", kind=DeltaKind.ADDED, subject=f"格局破坏·{cand.name}",
                supportLevel=AnalysisSupport.SUPPORTED,
                natalValue=None, temporalValue=f.detail,
                trigger=_layers_str(units),
                evidence=[f"{f.rule_id} {f.name}：{f.detail}"],
                refId=f"temporal:pattern:damage:{f.rule_id}",
            ))
    for f in temp_eval.rescues:
        if f.rule_id not in natal_res:
            items.append(DeltaItem(
                analysis="pattern", kind=DeltaKind.ADDED, subject=f"格局救应·{cand.name}",
                supportLevel=AnalysisSupport.SUPPORTED,
                natalValue=None, temporalValue=f.detail,
                trigger=_layers_str(units),
                evidence=[f"{f.rule_id} {f.name}：{f.detail}"],
                refId=f"temporal:pattern:rescue:{f.rule_id}",
            ))
    if temp_eval.status != natal_eval.status:
        items.append(DeltaItem(
            analysis="pattern", kind=DeltaKind.STATUS_CHANGED, subject=f"格局评估·{cand.name}",
            supportLevel=AnalysisSupport.SUPPORTED,
            natalValue=natal_eval.status, temporalValue=temp_eval.status,
            trigger=_layers_str(units),
            evidence=[f"评估状态（R25）：{natal_eval.status} → {temp_eval.status}"
                      + (f"；{temp_eval.note}" if temp_eval.note else "")],
            refId="temporal:pattern:status",
        ))


# ---------- 调候 Delta ----------

def _tiaohou_delta(chart: M.BaziChart, ctx: TemporalContext,
                   units: list[tuple[str, str | None, str | None]],
                   items: list[DeltaItem]) -> None:
    tr = chart.tiaohou
    if tr is None or not tr.resolved:
        return
    for rec in tr.recommendations:
        layers_with = [l for l, st, _ in units if st == rec.target_stem]
        if not layers_with:
            continue
        trig = "、".join(_trigger_label(l, st, br)
                         for l, st, br in units if st == rec.target_stem)
        if rec.present:
            items.append(DeltaItem(
                analysis="tiaohou", kind=DeltaKind.STRENGTHENED,
                subject=f"调候用神{rec.target_stem}（{rec.priority}）重见",
                supportLevel=AnalysisSupport.SUPPORTED,
                natalValue={"present": True, "positions": rec.positions},
                temporalValue={"present": True,
                               "positions": list(rec.positions) + layers_with},
                trigger=trig,
                evidence=[f"原局已见调候用神 {rec.target_stem}（{'、'.join(rec.positions) or '日主'}），"
                          f"岁运{trig}重见；rule_ids={rec.rule_ids}"],
                refId=f"temporal:tiaohou:{rec.target_stem}",
            ))
        else:
            items.append(DeltaItem(
                analysis="tiaohou", kind=DeltaKind.UNBLOCKED,
                subject=f"调候用神{rec.target_stem}（{rec.priority}）到位",
                supportLevel=AnalysisSupport.SUPPORTED,
                natalValue={"present": False},
                temporalValue={"present": True, "via": [f"{_LAYER_CN[l]}干{rec.target_stem}" for l in layers_with]},
                trigger=trig,
                evidence=[f"原局未见调候用神 {rec.target_stem}，岁运{trig}带来；"
                          f"rule_ids={rec.rule_ids}；desired/present 分离口径不变（M6）"],
                refId=f"temporal:tiaohou:{rec.target_stem}",
            ))


# ---------- 特殊格局 / 病药 / 通关 Delta ----------

def _special_delta(chart: M.BaziChart, ctx: TemporalContext,
                   units: list[tuple[str, str | None, str | None]],
                   items: list[DeltaItem],
                   strength_ctx: dict | None) -> None:
    natal = chart.advancedAnalysis
    if not natal:
        return
    dm = chart.day_master.stem
    positions = ["year", "month", "day", "hour"]
    natal_stems = [chart.pillars.year.stem, chart.pillars.month.stem,
                   chart.pillars.day.stem,
                   chart.pillars.hour.stem if chart.pillars.hour else None]
    natal_branches = [chart.pillars.year.branch, chart.pillars.month.branch,
                      chart.pillars.day.branch,
                      chart.pillars.hour.branch if chart.pillars.hour else None]
    ext_stems = natal_stems + [st for _, st, _ in units if st]
    ext_branches = natal_branches + [br for _, _, br in units if br]

    ext_ec = count_elements(ext_stems, ext_branches)
    ext_ec_dict = {k: {"visible": v.visible, "hidden": v.hidden}
                   for k, v in ext_ec.elements.items()}
    # 与原局口径一致：hidden 计数结构对齐 analyze_all_special 的入参
    natal_ec = chart.element_counts
    _ = natal_ec  # natal 已算好，扩展口径重算

    verdicts = (strength_ctx or {}).get("verdicts") or {}
    # pipeline 口径：dimension/weighted/fuyi 键名
    sv = {
        "dimension": verdicts.get("dimension"),
        "weighted": verdicts.get("weighted"),
        "fuyi": verdicts.get("fuyi"),
    }
    weighted_score = (strength_ctx or {}).get("weighted_score")
    helper_stems = [s for s in ext_stems if s and s != dm and
                    ten_god(dm, s).value in _HELPER_GODS]
    ext = analyze_all_special(
        day_master=dm, month_branch=chart.pillars.month.branch,
        stems=ext_stems, branches=ext_branches,
        strength_verdicts=sv, weighted_score=weighted_score,
        day_master_roots=len([r for r in chart.roots if r.is_day_master]),
        helper_stems=helper_stems,
        element_counts=ext_ec_dict,
    )

    for group, cn in (("cong", "从格"), ("zhuanwang", "专旺"), ("transformation", "化气")):
        def key_of(c: dict) -> str:
            return c.get("type") or "-".join(c.get("stemPair") or [])

        natal_map = {key_of(c): c for c in natal["specialPattern"][group]}
        ext_map = {key_of(c): c for c in ext["specialPattern"][group]}
        for t, c in ext_map.items():
            trig = _layers_str(units)
            if t not in natal_map:
                items.append(DeltaItem(
                    analysis="special", kind=DeltaKind.ADDED,
                    subject=f"{cn}候选·{t}", supportLevel=AnalysisSupport.EXPERIMENTAL,
                    natalValue=None, temporalValue=c["status"],
                    trigger=trig,
                    evidence=[f"岁运扩展上下文中出现 {cn}候选 {t}（status={c['status']}）",
                              "特殊格局候选永远不是定论；岁运是否参与从格/化气判定存在流派分歧（EXPERIMENTAL）"],
                    refId=f"temporal:special:{group}:{t}",
                ))
            elif c["status"] != natal_map[t]["status"]:
                ns, ts = natal_map[t]["status"], c["status"]
                kind = (DeltaKind.BLOCKED if ts == "BLOCKED" and ns != "BLOCKED"
                        else DeltaKind.UNBLOCKED if ns == "BLOCKED" and ts != "BLOCKED"
                        else DeltaKind.STATUS_CHANGED)
                new_blockers = [b for b in c["blockers"]
                                if b not in natal_map[t]["blockers"]]
                ev = [f"{cn}候选 {t}：{ns} → {ts}"]
                for b in new_blockers:
                    ev.append(f"岁运引入阻断因素：{b.get('description') or b.get('name') or b}")
                items.append(DeltaItem(
                    analysis="special", kind=kind, subject=f"{cn}候选·{t}",
                    supportLevel=AnalysisSupport.EXPERIMENTAL,
                    natalValue=ns, temporalValue=ts, trigger=trig,
                    evidence=ev, refId=f"temporal:special:{group}:{t}",
                ))
        for t, c in natal_map.items():
            if t not in ext_map:
                items.append(DeltaItem(
                    analysis="special", kind=DeltaKind.REMOVED,
                    subject=f"{cn}候选·{t}", supportLevel=AnalysisSupport.EXPERIMENTAL,
                    natalValue=c["status"], temporalValue=None,
                    trigger=trig,
                    evidence=[f"原局候选 {t}（{c['status']}）在岁运扩展上下文中不再成立"],
                    refId=f"temporal:special:{group}:{t}",
                ))

    # 病药
    natal_probs = {p["target"]: p for p in natal["bingYao"]["problems"]}
    ext_probs = {p["target"]: p for p in ext["bingYao"]["problems"]}
    for t, p in ext_probs.items():
        if t not in natal_probs:
            items.append(DeltaItem(
                analysis="bingYao", kind=DeltaKind.ADDED, subject=f"结构失衡病·{t}",
                supportLevel=AnalysisSupport.EXPERIMENTAL,
                natalValue=None, temporalValue=p["evidence"],
                trigger=_layers_str(units),
                evidence=[f"岁运扩展上下文出现失衡病：{'；'.join(p['evidence'])}（ENGINEERING_HEURISTIC 口径）"],
                refId=f"temporal:bingyao:problem:{t}",
            ))
    for t, p in natal_probs.items():
        if t not in ext_probs:
            items.append(DeltaItem(
                analysis="bingYao", kind=DeltaKind.REMOVED, subject=f"结构失衡病·{t}",
                supportLevel=AnalysisSupport.EXPERIMENTAL,
                natalValue=p["evidence"], temporalValue=None,
                trigger=_layers_str(units),
                evidence=["岁运扩展上下文中该失衡病不再成立（占比口径随上下文字数变化）"],
                refId=f"temporal:bingyao:problem:{t}",
            ))
    natal_med = {(m["problem"], m["kind"]): m for m in natal["bingYao"]["medicines"]}
    ext_med = {(m["problem"], m["kind"]): m for m in ext["bingYao"]["medicines"]}
    for k, m in ext_med.items():
        if k not in natal_med:
            items.append(DeltaItem(
                analysis="bingYao", kind=DeltaKind.ADDED,
                subject=f"药·{m['target']}（{m['kind']}病 {k[0]}）",
                supportLevel=AnalysisSupport.EXPERIMENTAL,
                natalValue=None, temporalValue=m["evidence"],
                trigger=_layers_str(units),
                evidence=[f"岁运带来制/泄药：{'；'.join(m['evidence'])}"],
                refId=f"temporal:bingyao:medicine:{m['target']}:{m['kind']}",
            ))
    for k, m in natal_med.items():
        if k not in ext_med:
            items.append(DeltaItem(
                analysis="bingYao", kind=DeltaKind.REMOVED,
                subject=f"药·{m['target']}（{m['kind']}病 {k[0]}）",
                supportLevel=AnalysisSupport.EXPERIMENTAL,
                natalValue=m["evidence"], temporalValue=None,
                trigger=_layers_str(units),
                evidence=["岁运扩展上下文中该药不再满足口径（ENGINEERING_HEURISTIC）"],
                refId=f"temporal:bingyao:medicine:{m['target']}:{m['kind']}",
            ))

    # 通关
    natal_pairs = {(p["conflict"]["from"], p["conflict"]["to"]): p
                   for p in natal["tongGuan"]["conflictPairs"]}
    ext_pairs = {(p["conflict"]["from"], p["conflict"]["to"]): p
                 for p in ext["tongGuan"]["conflictPairs"]}
    natal_bridges = {(b["conflict"]["from"], b["conflict"]["to"]): b
                     for b in natal["tongGuan"]["bridges"]}
    ext_bridges = {(b["conflict"]["from"], b["conflict"]["to"]): b
                   for b in ext["tongGuan"]["bridges"]}
    for k, b in ext_bridges.items():
        nb = natal_bridges.get(k)
        if nb is None:
            items.append(DeltaItem(
                analysis="tongGuan", kind=DeltaKind.ADDED,
                subject=f"通关桥·{_ELEM_CN[b['bridge']]}（{k[0]}→{k[1]}）",
                supportLevel=AnalysisSupport.EXPERIMENTAL,
                natalValue=None, temporalValue=b["evidence"],
                trigger=_layers_str(units),
                evidence=[f"岁运扩展上下文出现对峙+桥：{'；'.join(b['evidence'])}"],
                # 桥五行展示用中文名
                refId=f"temporal:tongguan:bridge:{b['bridge']}",
            ))
        elif not nb["present"] and b["present"]:
            items.append(DeltaItem(
                analysis="tongGuan", kind=DeltaKind.UNBLOCKED,
                subject=f"通关桥·{_ELEM_CN[b['bridge']]}（{k[0]}→{k[1]}）",
                supportLevel=AnalysisSupport.EXPERIMENTAL,
                natalValue=False, temporalValue=True,
                trigger=_layers_str(units),
                evidence=[f"原局桥未出现（{'；'.join(nb['evidence'])}），岁运遇桥则通："
                          f"{_layers_str(units)}补 {_ELEM_CN[b['bridge']]}"],
                refId=f"temporal:tongguan:bridge:{b['bridge']}",
            ))
    for k, b in natal_bridges.items():
        if k not in ext_bridges:
            items.append(DeltaItem(
                analysis="tongGuan", kind=DeltaKind.REMOVED,
                subject=f"通关桥·{_ELEM_CN[b['bridge']]}（{k[0]}→{k[1]}）",
                supportLevel=AnalysisSupport.EXPERIMENTAL,
                natalValue=b["evidence"], temporalValue=None,
                trigger=_layers_str(units),
                evidence=["岁运扩展上下文中该对峙不再满足 ≥2 倍口径"],
                refId=f"temporal:tongguan:bridge:{b['bridge']}",
            ))


# ---------- 十神主题 Delta ----------

def _tengod_delta(chart: M.BaziChart, ctx: TemporalContext,
                  units: list[tuple[str, str | None, str | None]],
                  items: list[DeltaItem]) -> None:
    dm = chart.day_master.stem
    natal_counts: dict[str, int] = {}
    for p in (chart.pillars.year, chart.pillars.month, chart.pillars.day, chart.pillars.hour):
        if p and p.stem and p.position != "day":
            god = ten_god(dm, p.stem).value
            natal_counts[god] = natal_counts.get(god, 0) + 1
    temporal_counts: dict[str, int] = {}
    for label, st, _br in units:
        if st:
            god = ten_god(dm, st).value
            temporal_counts[god] = temporal_counts.get(god, 0) + 1
    for god in sorted(set(natal_counts) | set(temporal_counts)):
        nc = natal_counts.get(god, 0)
        tc = temporal_counts.get(god, 0)
        if tc == 0:
            continue  # 岁运只增不减：原局主题不会因岁运消失
        if nc == 0:
            kind = DeltaKind.ADDED
        else:
            kind = DeltaKind.STRENGTHENED
        items.append(DeltaItem(
            analysis="tenGodTheme", kind=kind, subject=f"十神主题·{god}",
            supportLevel=AnalysisSupport.SUPPORTED,
            natalValue=nc, temporalValue=nc + tc,
            trigger=_layers_str(units),
            evidence=[f"岁运{_layers_str(units)}为日主带来 {god} ×{tc}："
                      f"原局透干计数 {nc} → 岁运主题计数 {nc + tc}（结构主题，非事件预测）"],
            refId=f"temporal:tengod:{god}",
        ))


# ---------- 主入口 ----------

def compute_temporal_delta(
    chart: M.BaziChart,
    luck: tuple[str | None, str | None] | None = None,
    annual: tuple[str | None, str | None] | None = None,
    monthly: tuple[str | None, str | None] | None = None,
    daily: tuple[str | None, str | None] | None = None,
    luck_index: int | None = None,
    annual_year: int | None = None,
) -> TemporalDeltaReport:
    """原局分析 vs 岁运扩展上下文：统一状态差异报告。

    - 月令保持原局（格局候选/调候规则匹配/旺衰月令维度均不被替换）
    - strength/special/bingyao/tongguan 的岁运口径标记 EXPERIMENTAL
    - 不做任何吉凶预测
    """
    units: list[tuple[str, str | None, str | None]] = []
    for label, pair in (("luck", luck), ("annual", annual),
                        ("monthly", monthly), ("daily", daily)):
        if pair and (pair[0] or pair[1]):
            units.append((label, pair[0], pair[1]))

    natal_stems = [chart.pillars.year.stem, chart.pillars.month.stem,
                   chart.pillars.day.stem,
                   chart.pillars.hour.stem if chart.pillars.hour else None]
    natal_branches = [chart.pillars.year.branch, chart.pillars.month.branch,
                      chart.pillars.day.branch,
                      chart.pillars.hour.branch if chart.pillars.hour else None]
    ctx = TemporalContext(
        natal_stems=natal_stems, natal_branches=natal_branches,
        luck_stem=(luck or (None, None))[0], luck_branch=(luck or (None, None))[1],
        annual_stem=(annual or (None, None))[0], annual_branch=(annual or (None, None))[1],
        monthly_stem=(monthly or (None, None))[0], monthly_branch=(monthly or (None, None))[1],
        daily_stem=(daily or (None, None))[0], daily_branch=(daily or (None, None))[1],
        luck_index=luck_index, annual_year=annual_year,
        day_master=chart.day_master.stem,
    )

    items: list[DeltaItem] = []
    unsupported: list[str] = []

    strength_ctx = _strength_delta(chart, ctx, units, items)
    _pattern_delta(chart, ctx, units, items, unsupported)
    _tiaohou_delta(chart, ctx, units, items)
    _special_delta(chart, ctx, units, items, strength_ctx)
    _tengod_delta(chart, ctx, units, items)

    return TemporalDeltaReport(
        context=ctx, items=items, unsupportedNotes=unsupported,
        warnings=["Temporal Delta 仅描述结构状态迁移，不构成任何吉凶或事件预测。",
                  "岁运不替换原局月令；EXPERIMENTAL 条目表示岁运参与该计算存在流派分歧。"],
    )
