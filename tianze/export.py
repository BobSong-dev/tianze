"""M13 · 完整分析报告导出：AnalyzeResult（dict 形态）→ Markdown。

原则：
- 只做确定性结果的排版，不新增任何判断
- 所有 EXPERIMENTAL / UNSUPPORTED / MACHINE_CURATED 标注原样保留
- 不输出任何吉凶断语（引擎本身没有，导出层也不添加）
"""

from __future__ import annotations

from typing import Any

__all__ = ["to_markdown"]


def _h(level: int, text: str) -> str:
    return "#" * level + " " + text


def _maybe_stem_branch(p: dict | None) -> str:
    if not p:
        return "—"
    return p.get("stem", "") + p.get("branch", "")


def to_markdown(result: dict[str, Any]) -> str:
    """把 analyze() 的 dict 结果渲染为 Markdown 报告。"""
    out: list[str] = []
    meta = result.get("meta") or {}
    dm = result.get("dayMaster") or {}

    out.append(_h(1, "Tianze 八字结构分析报告"))
    out.append("")
    out.append(f"- 引擎版本：{meta.get('engineVersion', '')}（{meta.get('engineStage', '')}）")
    out.append(f"- 分析 Schema：{meta.get('analysisSchemaVersion', '')} · "
               f"知识 Schema：{meta.get('knowledgeSchemaVersion', '')}")
    out.append("")
    out.append("> 本报告仅为结构分析，不构成任何吉凶或人生事件预测。")

    # ---- 四柱 ----
    out.append("")
    out.append(_h(2, "四柱"))
    out.append("")
    out.append("| 柱 | 干支 | 十神 | 纳音 | 十二长生 |")
    out.append("|---|---|---|---|---|")
    for pos, cn in (("year", "年柱"), ("month", "月柱"), ("day", "日柱"), ("hour", "时柱")):
        p = (result.get("pillars") or {}).get(pos)
        if not p:
            continue
        out.append(
            f"| {cn} | {p['stem']}{p['branch']} | {p.get('tenGod') or '日主'} "
            f"| {p.get('naYin', '')} | {p.get('changSheng') or '—'} |"
        )
    out.append("")
    out.append(f"**日主**：{dm.get('stem', '')}（{dm.get('element', '')}·{dm.get('yinYang', '')}）")

    # ---- 关系 ----
    relations = result.get("relations") or []
    if relations:
        out.append("")
        out.append(_h(2, "关系（M2）"))
        out.append("")
        for r in relations:
            out.append(f"- {r.get('label', '')}（{'/'.join(r.get('positions', []))}）"
                       + (f"——{r['note']}" if r.get("note") else ""))

    # ---- 旺衰 ----
    sr = result.get("strength")
    if sr:
        out.append("")
        out.append(_h(2, "旺衰（多方法并列，不裁决）"))
        out.append("")
        out.append(f"- agreement：{sr.get('agreement') or 'N/A'}")
        for m in sr.get("methods") or []:
            v = m.get("verdict") or "（定性，无 verdict）"
            line = f"- **{m.get('name', '')}**：{v}"
            if m.get("score") is not None:
                line += f"（score={m['score']:.4f}）"
            out.append(line)

    # ---- 格局 ----
    pa = result.get("pattern")
    if pa and pa.get("candidates"):
        out.append("")
        out.append(_h(2, "格局候选（候选 ≠ 结论）"))
        out.append("")
        for c in pa["candidates"]:
            out.append(f"- {c.get('name', '')}（via {c.get('via', '')}）")
        ev = pa.get("evaluation")
        if ev:
            out.append(f"- 首选候选评估状态：**{ev.get('status', '')}**"
                       + (f"——{ev['note']}" if ev.get("note") else ""))

    # ---- 调候 ----
    th = result.get("tiaohou")
    if th and th.get("resolved"):
        out.append("")
        out.append(_h(2, "调候（desired/present 分离）"))
        out.append("")
        for rec in th.get("recommendations") or []:
            present = "已见（" + "、".join(rec.get("positions") or []) + "）" if rec.get("present") else "未见"
            out.append(f"- 需要 **{rec.get('targetStem', '')}**（{rec.get('priority', '')}）：命局{present}")

    # ---- 高级 ----
    adv = result.get("advancedAnalysis")
    if adv:
        out.append("")
        out.append(_h(2, "特殊格局 / 病药 / 通关"))
        out.append("")
        sp = adv.get("specialPattern") or {}
        for c in sp.get("cong") or []:
            out.append(f"- 从格候选 **{c.get('type', '')}**：{c.get('status', '')}（候选，非定论）")
        for z in sp.get("zhuanwang") or []:
            out.append(f"- 专旺候选 **{z.get('type', '')}**：{z.get('status', '')}")
        for t in sp.get("transformation") or []:
            out.append(f"- 化气候选 **{''.join(t.get('stemPair', []))}**：{t.get('status', '')}")
        for p in (adv.get("bingYao") or {}).get("problems") or []:
            out.append(f"- 结构失衡病：{p.get('target', '')}（{'；'.join(p.get('evidence', []))}）")
        for m in (adv.get("bingYao") or {}).get("medicines") or []:
            out.append(f"- 制衡：{m.get('target', '')} {m.get('kind', '')}")
        for b in (adv.get("tongGuan") or {}).get("bridges") or []:
            present = "桥已存在" if b.get("present") else "桥未出现（行运遇之则通）"
            out.append(f"- 通关：{b.get('conflict', {}).get('from', '')} → {b.get('bridge', '')}"
                       f" → {b.get('conflict', {}).get('to', '')}（{present}）")

    # ---- 大运 ----
    luck = result.get("luck")
    if luck:
        out.append("")
        out.append(_h(2, "大运"))
        out.append("")
        fwd = "顺行" if luck.get("forward") else "逆行"
        out.append(f"- 顺逆：{fwd}；起运：{luck.get('startYears')}年{luck.get('startMonths')}月"
                   f"{luck.get('startDays')}日")
        for dy in luck.get("daYun") or []:
            out.append(f"- {dy.get('index')}: {dy.get('ganZhi', '')}"
                       f"（{dy.get('startYear')}–{dy.get('endYear')}，{dy.get('startAge')} 岁起）")

    # ---- 岁运（M13）----
    tp = result.get("temporal")
    if isinstance(tp, dict) and tp.get("context"):
        tctx = tp["context"]
        out.append("")
        out.append(_h(2, "岁运分析（M13）"))
        out.append("")
        chain = ["原局"]
        if tctx.get("luckStem"):
            chain.append(f"大运{tctx['luckStem']}{tctx.get('luckBranch') or ''}")
        if tctx.get("annualStem"):
            chain.append(f"流年{tctx['annualStem']}{tctx.get('annualBranch') or ''}")
        if tctx.get("monthlyStem"):
            chain.append(f"流月{tctx['monthlyStem']}{tctx.get('monthlyBranch') or ''}")
        if tctx.get("dailyStem"):
            chain.append(f"流日{tctx['dailyStem']}{tctx.get('dailyBranch') or ''}")
        out.append(f"- 岁运链：{' → '.join(chain)}")
        for r in tp.get("relations") or []:
            out.append(f"- 新增关系：{r.get('label', '')}（来源 {'/'.join(r.get('sources', []))}）")
        for s in tp.get("structures") or []:
            out.append(f"- 结构现象：{s.get('label', '')}——{s.get('description', '')}")
        for t in tp.get("ruleTriggers") or []:
            if t.get("matched"):
                out.append(f"- 规则触发 **{t.get('ruleId', '')}** {t.get('label', '')}："
                           + "；".join(t.get("observations", [])))
        delta = tp.get("delta")
        if delta:
            out.append("")
            out.append(_h(3, "Temporal Delta"))
            for d in delta.get("items") or []:
                out.append(f"- [{d.get('analysis', '')}] {d.get('kind', '')} **{d.get('subject', '')}**"
                           f"（{d.get('supportLevel', '')}）：{d.get('trigger', '')}")
            for theme in delta.get("themes") or []:
                out.append(f"- 主题：{theme.get('label', '')}（{theme.get('supportLevel', '')}）")
            for u in delta.get("unsupportedNotes") or []:
                out.append(f"- UNSUPPORTED：{u}")

        ev = tp.get("eventThemes") if isinstance(tp, dict) else None
        if isinstance(ev, dict) and ev.get("themes"):
            out.append("")
            out.append(_h(3, "事件主题（候选，非事件预测）"))
            for t in ev["themes"]:
                out.append(f"- **{t.get('themeCn') or t.get('theme')}**：{t.get('status')}"
                           f"（agreement={t.get('agreement') or 'N/A'}，"
                           f"confidence={t.get('confidence')}，ENGINEERING_HEURISTIC 非概率）")
                for e in t.get("supportingEvidence") or []:
                    out.append(f"  - 支持：{e}")
                for e in t.get("opposingEvidence") or []:
                    out.append(f"  - 反对：{e}")

    # ---- 声明 ----
    warnings = result.get("warnings") or []
    fallbacks = result.get("fallbacks") or []
    if warnings or fallbacks:
        out.append("")
        out.append(_h(2, "警告与降级"))
        out.append("")
        for w in warnings:
            out.append(f"- ⚠️ {w}")
        for f in fallbacks:
            out.append(f"- 降级：{f}")

    out.append("")
    return "\n".join(out)
