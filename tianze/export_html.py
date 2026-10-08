"""M15 · 打印友好 HTML 报告（to_html）。

- 目录 + print CSS（@media print：避免表格/提示块跨页断裂）
- 与 to_markdown 同一确定性纪律：只排版确定性结果，标注原样保留
- 事件主题区渲染 status/agreement/confidence（非概率）与冲突解释
"""

from __future__ import annotations

from typing import Any

__all__ = ["to_html"]

_CSS = """
body { font-family: 'Songti SC', 'SimSun', serif; max-width: 46rem; margin: 0 auto;
       padding: 2rem 1rem; color: #1a1a1a; line-height: 1.7; }
h1 { font-size: 1.5rem; border-bottom: 2px solid #333; padding-bottom: .4rem; }
h2 { font-size: 1.15rem; margin-top: 1.6rem; border-left: 4px solid #555; padding-left: .5rem; }
h3 { font-size: 1rem; margin-top: 1.2rem; color: #444; }
table { border-collapse: collapse; width: 100%; font-size: .9rem; margin: .5rem 0; }
th, td { border: 1px solid #bbb; padding: .3rem .5rem; text-align: left; }
th { background: #f0f0f0; }
.disclaimer { background: #fff8e1; border: 1px solid #e0c96a; padding: .6rem .8rem;
              border-radius: 4px; font-size: .85rem; }
.toc { background: #f7f7f7; border: 1px solid #ddd; padding: .8rem 1.2rem;
       border-radius: 4px; font-size: .9rem; }
.toc a { color: #1a1a1a; text-decoration: none; }
ul { padding-left: 1.2rem; }
li { margin: .15rem 0; }
.support { color: #1e6b34; }
.oppose { color: #9c2b2b; }
.note { color: #777; font-size: .82rem; }
@media print {
  body { max-width: none; padding: 0; font-size: 12pt; }
  h2 { break-after: avoid; }
  table, .disclaimer, .toc { break-inside: avoid; }
  a { color: inherit; }
}
"""


def _esc(text: Any) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _ul(items: list) -> str:
    if not items:
        return ""
    return "<ul>" + "".join(f"<li>{_esc(i)}</li>" for i in items) + "</ul>"


def to_html(result: dict) -> str:
    """AnalyzeResult（dict）→ 打印友好 HTML（含目录与 print CSS；确定性输出）。"""
    meta = result.get("meta") or {}
    dm = result.get("dayMaster") or {}
    body: list[str] = []
    toc: list[str] = []

    def sec(id_: str, title: str) -> None:
        toc.append(f'<a href="#{id_}">{_esc(title)}</a>')
        body.append(f'<h2 id="{id_}">{_esc(title)}</h2>')

    body.append('<div class="disclaimer">本报告仅为命理结构分析，不构成任何吉凶或'
                '人生事件预测；事件主题为结构层面「值得关注」的候选，'
                'confidence 是透明加权值而非概率。</div>')

    # 四柱
    sec("pillars", "四柱")
    rows = []
    for pos, cn in (("year", "年柱"), ("month", "月柱"), ("day", "日柱"), ("hour", "时柱")):
        p = (result.get("pillars") or {}).get(pos)
        if p:
            rows.append(f"<tr><td>{cn}</td><td>{_esc(p['stem'] + p['branch'])}</td>"
                        f"<td>{_esc(p.get('tenGod') or '日主')}</td>"
                        f"<td>{_esc(p.get('naYin', ''))}</td></tr>")
    body.append("<table><tr><th>柱</th><th>干支</th><th>十神</th><th>纳音</th></tr>"
                + "".join(rows) + "</table>")
    body.append(f"<p><b>日主</b>：{_esc(dm.get('stem', ''))}"
                f"（{_esc(dm.get('element', ''))}·{_esc(dm.get('yinYang', ''))}）</p>")

    # 关系
    rel = result.get("relations") or []
    if rel:
        sec("relations", "关系")
        body.append(_ul([f"{r.get('label', '')}（{'/'.join(r.get('positions', []))}）"
                         + (f"〔{r['subType']}〕" if r.get('subType') else "")
                         + (f"——{r['note']}" if r.get('note') else "")
                         for r in rel]))
    blocked = result.get("blockedRelations") or []
    if blocked:
        sec("blocked_relations", "未成立的关系候选（解释用，不参与推理）")
        body.append(_ul([f"{r.get('label', '')}——{r.get('note', '')}" for r in blocked]))

    # 旺衰
    sr = result.get("strength")
    if sr:
        sec("strength", "旺衰（多方法并列，不裁决）")
        items = [f"agreement：{sr.get('agreement') or 'N/A'}"]
        for m in sr.get("methods") or []:
            v = m.get("verdict") or "（定性）"
            items.append(f"{m.get('name', '')}：{v}"
                         + (f"（score={m['score']:.4f}）" if m.get("score") is not None else ""))
        body.append(_ul(items))

    # 格局
    pa = result.get("pattern")
    if pa and pa.get("candidates"):
        sec("pattern", "格局候选（候选 ≠ 结论）")
        items = [f"{c.get('name', '')}（via {c.get('via', '')}）" for c in pa["candidates"]]
        ev = pa.get("evaluation")
        if ev:
            items.append(f"首选候选评估：{ev.get('status', '')}")
        body.append(_ul(items))

    # 调候
    th = result.get("tiaohou")
    if th and th.get("resolved"):
        sec("tiaohou", "调候（desired/present 分离）")
        items = []
        for r in th.get("recommendations") or []:
            present = "已见" if r.get("present") else "未见"
            items.append(f"需要 {r.get('targetStem', '')}（{r.get('priority', '')}）：命局{present}")
        body.append(_ul(items))

    # 大运
    luck = result.get("luck")
    if luck:
        sec("luck", "大运")
        items = [f"顺逆：{'顺行' if luck.get('forward') else '逆行'}；起运 "
                 f"{luck.get('startYears')}年{luck.get('startMonths')}月{luck.get('startDays')}日"]
        for dy in luck.get("daYun") or []:
            items.append(f"{dy.get('index')}: {dy.get('ganZhi', '')}"
                         f"（{dy.get('startYear')}–{dy.get('endYear')}）")
        body.append(_ul(items))

    # 岁运 + Delta + 事件主题
    tp = result.get("temporal")
    if isinstance(tp, dict) and tp.get("context"):
        sec("temporal", "岁运分析")
        tctx = tp["context"]
        chain = ["原局"]
        for st_key, cn in (("luckStem", "大运"), ("annualStem", "流年"),
                           ("monthlyStem", "流月"), ("dailyStem", "流日")):
            if tctx.get(st_key):
                br_key = st_key.replace("Stem", "Branch")
                chain.append(f"{cn} {tctx[st_key]}{tctx.get(br_key) or ''}")
        body.append(_ul(["岁运链：" + " → ".join(chain)]))
        body.append(_ul([f"新增关系：{r.get('label', '')}（来源 {'/'.join(r.get('sources', []))}）"
                         for r in tp.get("relations") or []]))

        delta = tp.get("delta")
        if delta:
            sec("delta", "Temporal Delta")
            body.append(_ul([
                f"[{d.get('analysis', '')}] {d.get('kind', '')} {d.get('subject', '')}"
                f"（{d.get('supportLevel', '')}）"
                for d in delta.get("items") or []]))
            body.append(_ul([f"结构主题：{t.get('label', '')}（{t.get('supportLevel', '')}）"
                             for t in delta.get("themes") or []]))
            body.append(_ul([f"特殊格局岁运：{f.get('candidateType', '')}"
                             f"（{f.get('transition', '')}）"
                             for f in delta.get("specialFindings") or []]))

        ev = tp.get("eventThemes")
        if isinstance(ev, dict) and ev.get("themes"):
            sec("events", "事件主题（候选，非事件预测）")
            for t in ev["themes"]:
                body.append(f"<h3>{_esc(t.get('themeCn') or t.get('theme'))}："
                            f"{_esc(t.get('status'))}"
                            f"（agreement={_esc(t.get('agreement') or 'N/A')}，"
                            f"confidence={_esc(t.get('confidence'))}·非概率）</h3>")
                body.append('<div class="support">' + _ul(t.get("supportingEvidence") or [])
                            + "</div>")
                if t.get("opposingEvidence"):
                    body.append('<div class="oppose">' + _ul(t["opposingEvidence"]) + "</div>")
                if t.get("conflictExplanations"):
                    body.append(_ul([f"冲突解释：{c.get('kind')}——{c.get('explanation', '')}"
                                     for c in t["conflictExplanations"]]))

        # M17：全链路解释（折叠式 details，打印时自动展开由浏览器决定）
        exps = ev.get("explanations") or {}
        if exps:
            sec("explanations", "解释链（主题 → 规则 → 救应 → 证据 → 原文 → 来源）")
            for theme_key, ch in exps.items():
                body.append(f"<h3>{_esc(ch.get('themeCn') or theme_key)}"
                            f"（{_esc(ch.get('status'))}）</h3>")
                body.append(f"<p>{_esc(ch['reasoning'].get('verdictStatement', ''))}</p>")
                for side, cn in (("supportingChain", "支持链"), ("opposingChain", "反对链")):
                    hits = ch["reasoning"].get(side) or []
                    if hits:
                        body.append(f"<p><b>{cn}</b></p>")
                        body.append(_ul([
                            f"{h['ruleId']}（{h['view']}）"
                            + (f"［救应：{h['rescueApplied'].get('id')}］"
                               if h.get("rescueApplied") else "")
                            + "：" + "；".join(h.get("evidence", [])[:2])
                            + (f"——原文：{h['quote']}（{_esc((h.get('source') or {}).get('book', ''))}）"
                               if h.get("quote") else "")
                            for h in hits]))

    # M18：发布级摘要段（audit/evaluation/graph——从真实工件读取，缺失则跳过）
    _append_release_sections(body, sec)

    # 警告
    warnings = (result.get("warnings") or []) + (result.get("fallbacks") or [])
    if warnings:
        sec("warnings", "警告与降级")
        body.append(_ul([f"⚠️ {w}" for w in warnings]))

    toc_html = '<nav class="toc"><b>目录</b><br/>' + " · ".join(toc) + "</nav>"
    return (
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
        "<title>Tianze 分析报告</title>"
        f"<style>{_CSS}</style></head><body>"
        "<h1>Tianze 八字结构分析报告</h1>"
        f"<p class=\"note\">引擎 {_esc(meta.get('engineVersion', ''))}"
        f"（{_esc(meta.get('engineStage', ''))}）· Schema "
        f"{_esc(meta.get('analysisSchemaVersion', ''))}</p>"
        + toc_html + "".join(body) +
        "<p class=\"disclaimer\">核心原则：Engine 计算事实，Knowledge 提供规则依据，"
        "Reasoning 保留分歧，AI 负责解释，历史命例负责对照——而不是证明命理「正确」。</p>"
        "</body></html>"
    )


# ---- M18 发布级摘要段（只读工件；不重算推理） ----

def _append_release_sections(body: list, sec) -> None:
    """审计/评估历史/冲突图摘要。工件缺失时静默跳过（报告仍完整）。"""
    def _load(rel, default):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), rel)
        if not os.path.exists(path):
            return None
        return json.load(open(path, encoding="utf-8"))

    audit = _load("regression/audit-gates.json", None)
    if audit:
        sec("audit", "Audit Gates（推理质量门）")
        rows = "".join(
            f"<tr><td>{_esc(k)}</td><td>{'PASS' if v.get('pass') else 'FAIL'}</td></tr>"
            for k, v in audit.get("gates", {}).items())
        body.append("<table><tr><th>门</th><th>状态</th></tr>" + rows + "</table>")

    hist_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "regression", "ai-evaluation-history.jsonl")
    entries = None
    if os.path.exists(hist_path):
        entries = [json.loads(x) for x in
                   open(hist_path, encoding="utf-8").read().strip().split(chr(10)) if x]
    if entries:
            sec("evaluation", "AI Evaluation History（确定性指标）")
            rows = "".join(
                f"<tr><td>{_esc(e.get('provider'))}/{_esc(e.get('model'))}</td>"
                f"<td>{_esc(e.get('promptVersion'))}</td>"
                f"<td>{e.get('summary', {}).get('pass', 0)}/{e.get('summary', {}).get('total', 0)}</td></tr>"
                for e in entries[-5:])
            body.append("<table><tr><th>provider/model</th><th>prompt</th>"
                        "<th>pass/total</th></tr>" + rows + "</table>")
            body.append('<p class="note">无 API Key 时评估 SKIPPED，不伪造结果；'
                        '比较仅限确定性指标，不做「算命准确率」。</p>')

    graph = _load("knowledge/rules/event/conflict-graph.json", None)
    if graph:
        sec("graph", "Rule Conflict / Rescue Graph 摘要")
        body.append(_ul([
            f"节点 {graph.get('nodeCount')}（规则+救应谓词）；边 {graph.get('edgeCount')}"
            f"（{graph.get('edgeTypes')}）",
            "每条边有声明出处（conflicts.json/rescues.json）；反查见 Knowledge 工作台",
        ]))

    replay = _load("regression/case-replay.json", None)
    if replay:
        stats = replay.get("stats", {})
        sec("replay", "Case Replay 摘要")
        body.append(_ul([
            f"重放 {replay.get('count')} 例；对照分布 {stats.get('relationCounts')}",
            f"unresolved 率 {stats.get('unresolvedRate')}；disagreement 率 {stats.get('disagreementRate')}",
            "历史事件不是 truth；本报告不做「命中率」类统计",
        ]))


import json  # noqa: E402
import os  # noqa: E402
