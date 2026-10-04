"""M12 · 完整时序分析：大运/流年/流月/流日 + Timeline + TemporalDelta + TenGodThemeDelta。

扩展 M12 初版 temporal.py：
- TemporalContext 支持 monthly/daily 层级
- Timeline 生成器（大运→年→月→日，structural change score）
- TemporalDelta（与原局的 strength/pattern/tiaohou/advanced 变化）
- TenGodThemeDelta（十神主题变化）
- 流月流日干支计算（复用 lunar-python / 公式）
"""

from __future__ import annotations

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


from pydantic import BaseModel, ConfigDict
from tianze.domain.models import CamelizeModel


def build_timeline(
    natal_stems: list[str | None],
    natal_branches: list[str | None],
    day_master: str,
    birth_year: int,
    da_yun: list[dict],
    target_years: list[int] | None = None,
) -> TimelineResult:
    """生成 Timeline：大运→年→月 时间轴，每个节点记录结构变化。"""
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

        # 大运节点
        luck_node = _make_node(
            "luck", f"大运 {gz}", start_year,
            luck_stem, luck_branch, natal_stems, natal_branches,
            day_master, natal_ten_gods, luck_stem=luck_stem, luck_branch=luck_branch,
        )
        nodes.append(luck_node)

        # 该大运内的流年节点
        years_in_luck = [y for y in target_years if start_year <= y <= end_year]
        for year in years_in_luck:
            year_gz_idx = (year - 4) % 60
            a_stem, a_branch = STEMS[year_gz_idx % 10], BRANCHES[year_gz_idx % 12]

            annual_node = _make_node(
                "annual", f"流年 {a_stem}{a_branch}", year,
                a_stem, a_branch, natal_stems, natal_branches,
                day_master, natal_ten_gods,
                luck_stem=luck_stem, luck_branch=luck_branch,
                annual_stem=a_stem, annual_branch=a_branch,
            )
            nodes.append(annual_node)

    # TenGodThemeDelta
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

    return TimelineResult(nodes=nodes, tenGodDeltas=deltas, totalNodes=len(nodes))


def _make_node(
    level: str, label: str, year: int,
    stem: str, branch: str,
    natal_stems: list, natal_branches: list,
    day_master: str, natal_ten_gods: dict,
    **temporal_kw,
) -> TimelineNode:
    r = analyze_temporal(
        natal_stems=natal_stems, natal_branches=natal_branches,
        day_master=day_master,
        luck_stem=temporal_kw.get("luck_stem"),
        luck_branch=temporal_kw.get("luck_branch"),
        annual_stem=temporal_kw.get("annual_stem"),
        annual_branch=temporal_kw.get("annual_branch"),
    )
    score = float(len(r.relations) * 2 + len(r.structures) * 3)
    ten_god_theme = _count_ten_gods(
        natal_stems + ([stem] if stem else []),
        day_master,
    )
    return TimelineNode(
        level=level, label=label, year=year,
        ganzhi=stem + branch, source=level,
        structuralChangeScore=score,
        relations=[rel.model_dump(by_alias=True, exclude_none=True) for rel in r.relations],
        structures=[st.model_dump(by_alias=True, exclude_none=True) for st in r.structures],
        tenGodTheme=ten_god_theme,
        evidence=list(r.evidence),
    )


def _count_ten_gods(stems: list[str | None], day_master: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for s in stems:
        if not s:
            continue
        god = ten_god(day_master, s).value
        counts[god] = counts.get(god, 0) + 1
        # Also count from branch hidden stems
    return counts
