"""M12/M13 · 完整时序分析：大运/流年/流月/流日 + Timeline + TenGodThemeDelta。

扩展 M12 初版 temporal.py：
- 流月窗口按节气"节"划分（R4：月柱只认节），月柱 = 五虎遁 × 节序
- 流日按 JDN 公式（独立锚点，可与 lunar-python 对账）
- Timeline 树：大运 → 流年 → 流月（→ 流日），支持聚焦模式
- 十神主题计数口径：日主本人不计入（是分类主体，不是主题单元）
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from tianze.analysis.temporal import (
    TemporalContext,
    TemporalSource,
    TemporalRelation,
    TemporalStructure,
    TemporalAnalysis,
    analyze_temporal,
)
from tianze.ganzhi.tables import STEMS, BRANCHES, STEM_ELEMENT, HIDDEN_STEMS, ten_god
from tianze.domain.models import CamelizeModel
from pydantic import BaseModel, ConfigDict


# ---- 流月流日干支 ----

def month_pillar_for_year(year_gz_index: int, month_number: int) -> tuple[str, str]:
    """五虎遁：年干序 → 月干；month_number=1(寅月)~12(丑月)。"""
    year_stem_idx = year_gz_index % 10
    # 五虎遁：甲己年丙寅起，乙庚年戊寅起……
    first_month_stem = ((year_stem_idx % 5) * 2 + 2) % 10
    m_stem = (first_month_stem + month_number - 1) % 10
    m_branch = (2 + month_number - 1) % 12  # 寅=2
    return STEMS[m_stem], BRANCHES[m_branch]


def day_pillar_for_jdn(jdn: int) -> tuple[str, str]:
    """儒略日数 → 日干支。锚点：1949-10-01=甲子(JDN=2433191)。"""
    idx = (jdn - 2433191) % 60
    return STEMS[idx % 10], BRANCHES[idx % 12]


def gregorian_to_jdn(year: int, month: int, day: int) -> int:
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045


def month_windows_for_year(year: int) -> list[dict]:
    """流年 year 的 12 个月窗口：立春(year) 起寅月，至 立春(year+1) 前丑月。

    每项：{monthNumber(1=寅月), stem, branch, jieName, start, end}，
    start/end 为节交节时刻（北京时间，含 start、不含 end）。
    """
    from tianze.calendar.lunar_adapter import jie_moments
    jies = jie_moments(dt.datetime(year, 6, 1))
    # 节气表覆盖 大雪(前一年) → 惊蛰(次年)：取 立春(year) 起连续 13 节（12 个月窗口的 13 个边界）
    lichun_idx = next((i for i, (n, m) in enumerate(jies)
                       if n == "立春" and m.year == year), None)
    window_jies = jies[lichun_idx:lichun_idx + 13] if lichun_idx is not None else []
    if len(window_jies) != 13:
        return []

    year_gz_index = (year - 4) % 60
    out = []
    for i in range(12):
        name, start = window_jies[i]
        _, end = window_jies[i + 1]
        stem, branch = month_pillar_for_year(year_gz_index, i + 1)
        out.append({
            "monthNumber": i + 1, "stem": stem, "branch": branch,
            "jieName": name,
            "start": start.strftime("%Y-%m-%d %H:%M"),
            "end": end.strftime("%Y-%m-%d %H:%M"),
        })
    return out


# ---- Timeline ----

class TimelineNode(CamelizeModel):
    level: str                     # luck / annual / monthly / daily
    label: str
    year: int | None = None
    month: int | None = None
    day: int | None = None
    ganzhi: str = ""
    source: str = "natal"
    structuralChangeScore: float = 0.0
    relations: list[dict] = []
    structures: list[dict] = []
    tenGodTheme: dict[str, int] = {}
    evidence: list[str] = []
    monthWindow: str | None = None   # 流月：节起止（展示用）
    children: list["TimelineNode"] = []


class TenGodThemeDelta(CamelizeModel):
    """十神主题变化。"""
    ten_god: str
    natal_count: int
    temporal_count: int
    delta: int
    direction: str  # "increased" / "decreased" / "unchanged" / "new" / "removed"


class TimelineResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    nodes: list[TimelineNode] = []
    tenGodDeltas: list[TenGodThemeDelta] = []
    totalNodes: int = 0


def build_timeline(
    natal_stems: list[str | None],
    natal_branches: list[str | None],
    day_master: str,
    birth_year: int,
    da_yun: list[dict],
    target_years: list[int] | None = None,
    focus_year: int | None = None,      # 仅该流年展开流月
    focus_month: int | None = None,     # 仅该流月展开流日（monthNumber 1=寅月）
) -> TimelineResult:
    """生成 Timeline 树：大运 → 流年（→ 流月 → 流日，聚焦模式）。

    focus_year：只对该流年生成 12 个流月节点（节气窗口）。
    focus_month：只对该流月的日期生成流日节点（整月每日）。
    非聚焦模式保持 M12 形态（大运→流年），保证回归稳定。
    """
    if target_years is None:
        target_years = list(range(birth_year + 1, birth_year + 81))

    natal_ten_gods = _count_ten_gods(natal_stems, day_master)
    nodes: list[TimelineNode] = []

    for dy in da_yun:
        gz = dy.get("ganZhi") or dy.get("gan_zhi") or ""
        if not gz or len(gz) < 2:
            continue
        luck_stem, luck_branch = gz[0], gz[1]
        start_year = dy.get("startYear") or dy.get("start_year") or 0
        end_year = dy.get("endYear") or dy.get("end_year") or 0

        # 该大运内的流年节点（先算年，再挂到大运节点的 children）
        year_nodes: list[TimelineNode] = []
        for year in [y for y in target_years if start_year <= y <= end_year]:
            year_gz_idx = (year - 4) % 60
            a_stem, a_branch = STEMS[year_gz_idx % 10], BRANCHES[year_gz_idx % 12]

            month_nodes: list[TimelineNode] = []
            if focus_year == year:
                for mw in month_windows_for_year(year):
                    day_nodes = _daily_nodes(
                        year, mw, natal_stems, natal_branches, day_master,
                        luck_stem, luck_branch, a_stem, a_branch,
                    ) if focus_month == mw["monthNumber"] else []
                    month_nodes.append(TimelineNode(
                        level="monthly",
                        label=f"流月 {mw['stem']}{mw['branch']}月（{mw['jieName']}起）",
                        year=year, month=mw["monthNumber"],
                        ganzhi=mw["stem"] + mw["branch"], source="monthly",
                        **_analyze_payload(
                            natal_stems, natal_branches, day_master,
                            luck_stem, luck_branch, a_stem, a_branch,
                            mw["stem"], mw["branch"], None, None,
                            natal_ten_gods, mw["stem"],
                        ),
                        monthWindow=f"{mw['jieName']} {mw['start']} → {mw['end']}",
                        children=day_nodes,
                    ))

            year_nodes.append(TimelineNode(
                level="annual", label=f"流年 {a_stem}{a_branch}", year=year,
                **_analyze_payload(
                    natal_stems, natal_branches, day_master,
                    luck_stem, luck_branch, a_stem, a_branch,
                    None, None, None, None,
                    natal_ten_gods, a_stem,
                ),
                ganzhi=a_stem + a_branch, source="annual",
                children=month_nodes,
            ))

        nodes.append(TimelineNode(
            level="luck", label=f"大运 {gz}", year=start_year,
            **_analyze_payload(
                natal_stems, natal_branches, day_master,
                luck_stem, luck_branch, None, None,
                None, None, None, None,
                natal_ten_gods, luck_stem,
            ),
            ganzhi=gz, source="luck",
            children=year_nodes,
        ))

    # TenGodThemeDelta：原局 vs 原局+全部大运/流年干
    deltas = []
    temporal_stems = [n.ganzhi[0] for n in nodes if n.level in ("luck", "annual") and n.ganzhi]
    temporal_count = _count_ten_gods(
        natal_stems + [s for s in temporal_stems if s], day_master
    )
    all_gods = set(natal_ten_gods) | set(temporal_count)
    for god in sorted(all_gods):
        nc = natal_ten_gods.get(god, 0)
        tc = temporal_count.get(god, 0)
        delta = tc - nc
        direction = ("new" if nc == 0 and tc > 0 else
                     "removed" if nc > 0 and tc == 0 else
                     "increased" if delta > 0 else
                     "decreased" if delta < 0 else "unchanged")
        deltas.append(TenGodThemeDelta(
            ten_god=god, natal_count=nc, temporal_count=tc,
            delta=delta, direction=direction,
        ))

    return TimelineResult(nodes=nodes, tenGodDeltas=deltas, totalNodes=_count_nodes(nodes))


def _count_nodes(nodes: list[TimelineNode]) -> int:
    return sum(1 + _count_nodes(n.children) for n in nodes)


def _daily_nodes(
    year: int, mw: dict,
    natal_stems: list, natal_branches: list, day_master: str,
    luck_stem: str, luck_branch: str, a_stem: str, a_branch: str,
) -> list[TimelineNode]:
    """流月内的流日节点（该节气月窗口内的公历日期）。"""
    nodes: list[TimelineNode] = []
    start = dt.datetime.strptime(mw["start"], "%Y-%m-%d %H:%M").date()
    end = dt.datetime.strptime(mw["end"], "%Y-%m-%d %H:%M").date()
    d = start
    while d < end:
        jdn = gregorian_to_jdn(d.year, d.month, d.day)
        d_stem, d_branch = day_pillar_for_jdn(jdn)
        nodes.append(TimelineNode(
            level="daily",
            label=f"流日 {d.isoformat()} {d_stem}{d_branch}",
            year=d.year, month=d.month, day=d.day,
            ganzhi=d_stem + d_branch, source="daily",
            **_analyze_payload(
                natal_stems, natal_branches, day_master,
                luck_stem, luck_branch, a_stem, a_branch,
                mw["stem"], mw["branch"], d_stem, d_branch,
                _count_ten_gods(natal_stems, day_master), d_stem,
            ),
            children=[],
        ))
        d += dt.timedelta(days=1)
    return nodes


def _analyze_payload(
    natal_stems: list, natal_branches: list, day_master: str,
    luck_stem: str | None, luck_branch: str | None,
    annual_stem: str | None, annual_branch: str | None,
    monthly_stem: str | None, monthly_branch: str | None,
    daily_stem: str | None, daily_branch: str | None,
    natal_ten_gods: dict, node_stem: str | None,
) -> dict:
    """对单个时序节点运行 analyze_temporal，产出 TimelineNode 字段。"""
    r = analyze_temporal(
        natal_stems=natal_stems, natal_branches=natal_branches,
        day_master=day_master,
        luck_stem=luck_stem, luck_branch=luck_branch,
        annual_stem=annual_stem, annual_branch=annual_branch,
        monthly_stem=monthly_stem, monthly_branch=monthly_branch,
        daily_stem=daily_stem, daily_branch=daily_branch,
    )
    score = float(len(r.relations) * 2 + len(r.structures) * 3)
    theme = dict(natal_ten_gods)
    if node_stem:
        god = ten_god(day_master, node_stem).value
        theme[god] = theme.get(god, 0) + 1
    return {
        "structuralChangeScore": score,
        "relations": [rel.model_dump(by_alias=True, exclude_none=True) for rel in r.relations],
        "structures": [st.model_dump(by_alias=True, exclude_none=True) for st in r.structures],
        "tenGodTheme": theme,
        "evidence": list(r.evidence),
    }


def _count_ten_gods(stems: list[str | None], day_master: str) -> dict[str, int]:
    """十神主题计数：日主本人（index 2）不计入（分类主体不是主题单元）。"""
    counts: dict[str, int] = {}
    for i, s in enumerate(stems):
        if not s:
            continue
        if i == 2 and len(stems) > 2:
            continue  # 日主所在位（natal 列表固定 year,month,day,hour 序）
        god = ten_god(day_master, s).value
        counts[god] = counts.get(god, 0) + 1
    return counts


# ---- 聚焦分析（Web 工作台选择 大运→年→月→日 后的完整分析）----

def build_focused_temporal(
    chart,  # M.BaziChart
    luck_index: int | None,
    year: int | None,
    month_number: int | None = None,
    day: tuple[int, int, int] | None = None,   # 公历 (y, m, d)
) -> tuple[TemporalAnalysis, dict | None]:
    """选定 大运/流年/流月/流日 后的完整时序关系分析。

    流月由节气窗口（month_windows_for_year）取干支；
    流日由 JDN 公式取干支。返回 (TemporalAnalysis, 月窗口信息)。
    """
    luck_stem = luck_branch = None
    if luck_index is not None and chart.luck and chart.luck.da_yun:
        for dy in chart.luck.da_yun:
            if dy.index == luck_index and dy.gan_zhi:
                luck_stem, luck_branch = dy.gan_zhi[0], dy.gan_zhi[1]
                break
    if year is not None and luck_stem is None and chart.luck and chart.luck.da_yun:
        for dy in chart.luck.da_yun:
            if dy.start_year <= year <= dy.end_year and dy.gan_zhi:
                luck_stem, luck_branch = dy.gan_zhi[0], dy.gan_zhi[1]
                break

    annual_stem = annual_branch = None
    if year is not None:
        idx = (year - 4) % 60
        annual_stem, annual_branch = STEMS[idx % 10], BRANCHES[idx % 12]

    monthly_stem = monthly_branch = None
    mw_info = None
    if month_number is not None and year is not None:
        for mw in month_windows_for_year(year):
            if mw["monthNumber"] == month_number:
                monthly_stem, monthly_branch = mw["stem"], mw["branch"]
                mw_info = mw
                break

    daily_stem = daily_branch = None
    if day is not None:
        jdn = gregorian_to_jdn(day[0], day[1], day[2])
        daily_stem, daily_branch = day_pillar_for_jdn(jdn)

    natal_stems = [chart.pillars.year.stem, chart.pillars.month.stem,
                   chart.pillars.day.stem]
    if chart.pillars.hour:
        natal_stems.append(chart.pillars.hour.stem)
    natal_branches = [chart.pillars.year.branch, chart.pillars.month.branch,
                      chart.pillars.day.branch]
    if chart.pillars.hour:
        natal_branches.append(chart.pillars.hour.branch)

    result = analyze_temporal(
        natal_stems=natal_stems, natal_branches=natal_branches,
        day_master=chart.day_master.stem,
        luck_stem=luck_stem, luck_branch=luck_branch,
        annual_stem=annual_stem, annual_branch=annual_branch,
        monthly_stem=monthly_stem, monthly_branch=monthly_branch,
        daily_stem=daily_stem, daily_branch=daily_branch,
        luck_index=luck_index, annual_year=year,
    )
    return result, mw_info
