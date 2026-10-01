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
    """分析器输入：仅 M3 结构事实，与 BaziChart 解耦（便于单测与未来缓存）。"""

    day_master: str
    day_master_element: Element
    month_command: MonthCommand
    day_master_roots: tuple[RootEvidence, ...]
    other_stems: tuple[tuple[str, Position], ...]   # 年/月/时天干（日主除外）


class StrengthAnalyzer(Protocol):
    analyzer_id: str
    name: str

    def analyze(self, facts: StrengthFacts) -> object:  # -> StrengthMethodResult
        ...  # pragma: no cover


def run_strength(analyzers: list, facts: StrengthFacts) -> StrengthReport:
    methods = [analyzer.analyze(facts) for analyzer in analyzers]
    verdict_methods = [m.verdict for m in methods if m.verdict is not None]
    if len(verdict_methods) >= 2:
        agreement = "HIGH" if len(set(verdict_methods)) == 1 else "DISPUTED"
        note = "多方法并列输出；Tianze 不裁判（R19）。"
    else:
        agreement = None
        note = "当前仅 1 个方法（无计分 verdict）：无对照基准，不输出 agreement（R19/ADR-019）。"
    return StrengthReport(methods=methods, agreement=agreement, note=note)


def default_run(facts: StrengthFacts) -> StrengthReport:
    """以默认注册表运行（当前仅 dimensional）。"""
    from tianze.analysis.strength.methods.dimensional import DimensionalStrengthAnalyzer

    return run_strength([DimensionalStrengthAnalyzer()], facts)
