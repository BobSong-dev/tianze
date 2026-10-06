"""M15：Timeline 性能 benchmark + 缓存有效性。"""

from __future__ import annotations

import time

from tianze.analysis.temporal_extended import (
    _analyze_temporal_cached, build_timeline,
)


def _da_yun():
    return [{"ganZhi": f"{s}{b}", "startYear": 1990 + i * 10, "endYear": 1999 + i * 10}
            for i, (s, b) in enumerate(
                [("庚午", ""), ("辛未", ""), ("壬申", ""), ("癸酉", ""),
                 ("甲戌", ""), ("乙亥", ""), ("丙子", ""), ("丁丑", "")][:8])]


def test_full_timeline_benchmark():
    """80 年大运→流年 Timeline（8 运 × 10 年）构建 < 2s。"""
    da_yun = [{"ganZhi": "庚午", "startYear": 1990, "endYear": 1999},
              {"ganZhi": "辛未", "startYear": 2000, "endYear": 2009},
              {"ganZhi": "壬申", "startYear": 2010, "endYear": 2019},
              {"ganZhi": "癸酉", "startYear": 2020, "endYear": 2029},
              {"ganZhi": "甲戌", "startYear": 2030, "endYear": 2039},
              {"ganZhi": "乙亥", "startYear": 2040, "endYear": 2049},
              {"ganZhi": "丙子", "startYear": 2050, "endYear": 2059},
              {"ganZhi": "丁丑", "startYear": 2060, "endYear": 2069}]
    t0 = time.perf_counter()
    tl = build_timeline(
        natal_stems=["癸", "庚", "癸", "己"],
        natal_branches=["未", "申", "亥", "未"],
        day_master="癸", birth_year=1990, da_yun=da_yun,
        target_years=list(range(1991, 2070)),
    )
    elapsed = time.perf_counter() - t0
    assert tl.totalNodes == 8 + 79
    assert elapsed < 2.0, f"80 年 Timeline 构建过慢: {elapsed:.2f}s"


def test_memoization_speeds_up_repeat():
    """缓存有效：同组合第二次调用显著加速（且结果一致）。"""
    key = (("癸", "庚", "癸", "己"), ("未", "申", "亥", "未"))
    args = (key, "癸", ("庚", "午"), ("甲", "子"), (None, None), (None, None))
    t0 = time.perf_counter()
    r1 = _analyze_temporal_cached(*args)
    cold = time.perf_counter() - t0
    t1 = time.perf_counter()
    for _ in range(100):
        r2 = _analyze_temporal_cached(*args)
    warm = (time.perf_counter() - t1) / 100
    assert r2.model_dump_json(by_alias=True) == r1.model_dump_json(by_alias=True)
    assert warm < cold + 0.001  # 缓存命中不慢于冷调用
