"""L7 结构分析层：通根 / 透干 / 月令 / 五行统计 / 旺衰框架。

M3 模块只产出**结构事实**（有没有根、透没透、月令状态、计数），
不做吉凶判断、不加权、不评分（R15-R18）。
"""

from tianze.analysis.element_counts import count_elements  # noqa: F401
from tianze.analysis.month_command import compute_month_command  # noqa: F401
from tianze.analysis.pattern import analyze_pattern, derive_pattern_candidates, evaluate_pattern  # noqa: F401
from tianze.analysis.roots import collect_roots, day_master_roots  # noqa: F401
from tianze.analysis.visibility import analyze_visibility  # noqa: F401
