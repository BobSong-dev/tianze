"""M4 旺衰评估框架核心（R19 / ADR-019）。

原则：
- 不存在唯一旺衰算法——多个 StrengthAnalyzer 并列输出，Tianze 不裁决。
- M4.1 只内置 dimension（得令/得地/得势三维定性，不评分）；
  weighted/fuyi 等计分制方法在后续里程碑以新 analyzer 加入，接口不变。
- 所有结论必须由 M3 结构事实（月令/通根/透干）+ 显式规则（R 编号）支撑。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from tianze.domain.models import Element, MonthCommand, Position, RootEvidence, StrengthReport


@dataclass(frozen=True)
class StrengthFacts:
    """分析器输入：仅 M3 结构事实，与 BaziChart 解耦（便于单测与未来缓存）。

    `pillar_units` 为 (position, stem|None, branch|None) 四元序列，供 weighted
    逐字计分使用；dimension/fuyi 只用派生特征（月令/根/印比），不读它。
    """

    day_master: str
    day_master_element: Element
    month_command: MonthCommand
    day_master_roots: tuple[RootEvidence, ...]
    other_stems: tuple[tuple[str, Position], ...]   # 年/月/时天干（日主除外）
    pillar_units: tuple[tuple[Position, str | None, str | None], ...] = ()


class StrengthAnalyzer(Protocol):
    analyzer_id: str
    name: str

    def analyze(self, facts: StrengthFacts) -> object:  # -> StrengthMethodResult
        ...  # pragma: no cover


VERDICT_SCALE: tuple[str, ...] = ("极强", "偏强", "中和", "偏弱", "极弱")


def agreement_of(verdicts: list[str | None]) -> str | None:
    """R22 agreement 语义：只比较带 verdict 的方法；UNCERTAIN 视为弃权。

    - 全部一致 → HIGH
    - 存在完全相同的两项，或全部落在相邻档内 → PARTIAL
    - 其余 → DISPUTED
    少于 2 个有效 verdict → None（无对照基准）。
    """
    effective = [v for v in verdicts if v is not None and v != "UNCERTAIN"]
    if len(effective) < 2:
        return None
    if len(set(effective)) == 1:
        return "HIGH"
    if len(set(effective)) < len(effective):
        return "PARTIAL"
    idx = [VERDICT_SCALE.index(v) for v in effective if v in VERDICT_SCALE]
    if len(idx) == len(effective) and max(idx) - min(idx) == 1:
        return "PARTIAL"
    return "DISPUTED"


def run_strength(analyzers: list, facts: StrengthFacts) -> StrengthReport:
    methods = [analyzer.analyze(facts) for analyzer in analyzers]
    agreement = agreement_of([m.verdict for m in methods])
    if agreement is not None:
        note = "多方法并列输出；Tianze 不裁判（R19/R22）。"
    else:
        note = "有效 verdict 不足 2 个：无对照基准，不输出 agreement（R19/R22/ADR-019）。"
    return StrengthReport(methods=methods, agreement=agreement, note=note)


def default_run(facts: StrengthFacts) -> StrengthReport:
    """以默认注册表运行（dimension + weighted + fuyi）。"""
    from tianze.analysis.strength.methods.dimensional import DimensionalStrengthAnalyzer
    from tianze.analysis.strength.methods.fuyi import FuyiStrengthAnalyzer
    from tianze.analysis.strength.methods.weighted import WeightedStrengthAnalyzer

    return run_strength(
        [DimensionalStrengthAnalyzer(), WeightedStrengthAnalyzer(), FuyiStrengthAnalyzer()],
        facts,
    )
