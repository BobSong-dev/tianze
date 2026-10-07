"""M17 · 真实规模 Benchmark（performance history）。

测量项：
- 1147 命例 case-chart 构建（引擎全链）
- Replay corpus（岁运重放 + 事件主题）
- 80 年 Timeline（8 大运 × 79 流年）
- ExplanationChain 构建
- Knowledge stats/coverage

输出：regression/benchmark.json（含时间戳无关的确定性计数；耗时供跨版本对比）。
"""

from __future__ import annotations

import glob
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tianze.analysis.case_chart import build_case_chart
from tianze.analysis.explain import build_explanation_chains
from tianze.analysis.event_themes import compute_event_themes
from tianze.analysis.temporal_delta import compute_temporal_delta
from tianze.analysis.temporal_extended import build_timeline


def main() -> int:
    results: dict[str, dict] = {}

    # 1) 1147 命例引擎
    cases = []
    for f in sorted(glob.glob("knowledge/normalized/cases/*.json")):
        if any(x in f for x in ("temporal_refs", "event_claims", "raw_temporal_spans")):
            continue
        data = json.load(open(f, encoding="utf-8"))
        cases.extend(data["cases"])
    t0 = time.perf_counter()
    built = 0
    charts = []
    for c in cases:
        pillars = (c.get("fact") or {}).get("pillars") or {}
        if all(pillars.get(k) for k in ("year", "month", "day", "hour")):
            try:
                charts.append((c["caseId"], build_case_chart(pillars)))
                built += 1
            except Exception:
                pass
    results["caseChart1147"] = {
        "count": built, "elapsedSeconds": round(time.perf_counter() - t0, 3),
        "perCaseMs": round((time.perf_counter() - t0) / max(1, built) * 1000, 2),
    }

    # 2) Replay corpus（全部已构建命例 × 首个大运/流年）
    spans = {}
    sp_path = "knowledge/normalized/cases/raw_temporal_spans.json"
    if os.path.exists(sp_path):
        raw = json.load(open(sp_path, encoding="utf-8"))
        spans = {c["caseId"]: c.get("spans", []) for c in raw.get("cases", [])}
    t0 = time.perf_counter()
    replayed = 0
    for cid, chart in charts:
        luck = None
        for sp in spans.get(cid, []):
            if sp.get("confidence") == "high" and sp["kind"] == "luck":
                luck = tuple(sp["ganZhi"])
                break
        compute_event_themes(chart, luck=luck, annual=None)
        replayed += 1
    results["replayCorpus"] = {
        "count": replayed, "elapsedSeconds": round(time.perf_counter() - t0, 3),
        "perCaseMs": round((time.perf_counter() - t0) / max(1, replayed) * 1000, 2),
    }

    # 3) 80 年 Timeline
    da_yun = [{"ganZhi": gz, "startYear": 1990 + i * 10, "endYear": 1999 + i * 10}
              for i, gz in enumerate(["庚午", "辛未", "壬申", "癸酉",
                                      "甲戌", "乙亥", "丙子", "丁丑"])]
    t0 = time.perf_counter()
    tl = build_timeline(
        natal_stems=["癸", "庚", "癸", "己"],
        natal_branches=["未", "申", "亥", "未"],
        day_master="癸", birth_year=1990, da_yun=da_yun,
        target_years=list(range(1991, 2070)))
    results["timeline80y"] = {
        "nodes": tl.totalNodes,
        "elapsedSeconds": round(time.perf_counter() - t0, 3),
    }

    # 4) ExplanationChain（重复 20 次取均值）
    chart = charts[0][1] if charts else None
    if chart:
        delta = compute_temporal_delta(chart, annual=("丙", "午"))
        rep = compute_event_themes(chart, annual=("丙", "午"),
                                   delta_report=delta, with_explanations=True)
        t0 = time.perf_counter()
        for _ in range(20):
            build_explanation_chains(rep)
        results["explanationChains"] = {
            "themes": len(rep.themes),
            "avgMs": round((time.perf_counter() - t0) / 20 * 1000, 2),
        }

    results["note"] = "耗时供跨版本对比；节点/主题数是确定性计数（回归可用）"
    with open("regression/benchmark.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    print(json.dumps(results, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
