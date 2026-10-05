"""M13 · Temporal Regression：岁运领域回归系统（起运/大运/流年/流月/流日/Delta/规则触发）。

与 tools/case_regression.py 同一纪律：
- snapshot：对固定探针命例（含性别/时辰，保证大运可算）计算岁运稳定字段
- compare：重算对比，severity = INFO / EXPECTED / REVIEW / BREAKING
  - BREAKING：起运时刻、大运序列（顺逆/干支/起讫年）、流月干支序列、流日干支、日柱算法
  - REVIEW：关键流年 TemporalRelation 集合、结构现象、规则触发集合、Delta refId 集合、
            TenGodThemeDelta 方向
  - INFO：structuralChangeScore 变化（heuristic 排序值）
- Regression 只回答"哪些命例、哪些时间点、哪些结构发生了变化"，不裁决谁对、不自动回滚
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import datetime as dt

REPO = Path(__file__).resolve().parents[1]
BASELINE = REPO / "regression" / "baseline" / "temporal-snapshot.json"

import tianze
from tianze.domain.models import BirthInfo, Gender
from tianze.pipeline import build_chart
from tianze.analysis.temporal import analyze_temporal
from tianze.analysis.temporal_extended import (
    build_focused_temporal, build_timeline, month_windows_for_year,
    day_pillar_for_jdn, gregorian_to_jdn,
)
from tianze.analysis.temporal_delta import compute_temporal_delta, DELTA_SCHEMA_VERSION

# 探针命例：覆盖 男女 × 阴阳年干（顺逆）、立春前后、闰日、晚子时、DST 时区
PROBES = [
    {"name": "m_1984_0205", "date": "1984-02-05", "time": "10:30", "gender": "male",
     "note": "甲子年男（阳男顺排）"},
    {"name": "f_1983_0215", "date": "1983-02-15", "time": "20:00", "gender": "female",
     "note": "癸亥年女（阴女顺排）"},
    {"name": "m_2003_0818", "date": "2003-08-18", "time": "14:30", "gender": "male",
     "note": "癸未年男（阴男逆排）"},
    {"name": "f_1990_0615", "date": "1990-06-15", "time": "06:15", "gender": "female",
     "note": "庚午年女（阳女逆排）"},
    {"name": "m_1976_0130", "date": "1976-01-30", "time": "23:30", "gender": "male",
     "note": "立春前+晚子时（R1/R4 边界）"},
    {"name": "f_2000_0229", "date": "2000-02-29", "time": "12:00", "gender": "female",
     "note": "闰年闰日"},
]

# 固定分析时间点（关键流年/流月/流日）
KEY_YEARS = [2010, 2026, 2040]
MONTH_PROBE_YEAR = 2026
DAY_PROBE = (2026, 3, 1)


def _natal(chart) -> tuple[list, list, str]:
    stems = [chart.pillars.year.stem, chart.pillars.month.stem, chart.pillars.day.stem]
    branches = [chart.pillars.year.branch, chart.pillars.month.branch, chart.pillars.day.branch]
    if chart.pillars.hour:
        stems.append(chart.pillars.hour.stem)
        branches.append(chart.pillars.hour.branch)
    return stems, branches, chart.day_master.stem


def compute_snapshots() -> list[dict]:
    snapshots = []
    for probe in PROBES:
        y, m, d = (int(x) for x in probe["date"].split("-"))
        hh, mm = (int(x) for x in probe["time"].split(":"))
        bi = BirthInfo(date=dt.date(y, m, d), time=dt.time(hh, mm),
                       gender=Gender(probe["gender"]))
        chart = build_chart(bi)
        stems, branches, dm = _natal(chart)

        snap: dict = {"probe": probe["name"], "note": probe["note"]}

        # 1) 起运 + 大运序列（BREAKING 级）
        if chart.luck:
            snap["luck"] = {
                "forward": chart.luck.forward,
                "start": [chart.luck.start_years, chart.luck.start_months,
                          chart.luck.start_days, chart.luck.start_hours],
                "dayun": [
                    {"i": dy.index, "gz": dy.gan_zhi, "sy": dy.start_year,
                     "ey": dy.end_year, "sa": dy.start_age}
                    for dy in chart.luck.da_yun[:10]
                ],
            }
        else:
            snap["luck"] = None

        # 2) 关键流年关系/结构/规则触发（REVIEW 级）
        annuals = []
        for year in KEY_YEARS:
            ta, _mw = build_focused_temporal(chart, None, year)
            annuals.append({
                "year": year,
                "gz": (ta.context.annual_stem or "") + (ta.context.annual_branch or ""),
                "relations": sorted(
                    f"{r.kind}:{'|'.join(sorted(r.members))}:{','.join(r.positions)}"
                    for r in ta.relations),
                "structures": sorted(s.type for s in ta.structures),
                "rules": sorted(t.ruleId for t in ta.ruleTriggers if t.matched),
            })
        snap["annuals"] = annuals

        # 3) 流月干支序列（BREAKING 级：节气窗口 + 五虎遁）
        snap["months_2026"] = [
            {"n": mw["monthNumber"], "gz": mw["stem"] + mw["branch"],
             "jie": mw["jieName"], "start": mw["start"]}
            for mw in month_windows_for_year(MONTH_PROBE_YEAR)
        ]

        # 4) 流日干支（BREAKING 级：JDN 算法）
        jdn = gregorian_to_jdn(*DAY_PROBE)
        ds, db = day_pillar_for_jdn(jdn)
        snap["day_probe"] = {"date": "-".join(map(str, DAY_PROBE)),
                             "gz": ds + db, "jdn": jdn}

        # 5) 聚焦 Delta（REVIEW 级：refId 集合）
        luck2 = snap["luck"]["dayun"][2] if snap.get("luck") and len(snap["luck"]["dayun"]) > 2 else None
        if luck2:
            rep = compute_temporal_delta(
                chart, luck=tuple(luck2["gz"]), annual=("丙", "午"),
                luck_index=luck2["i"], annual_year=2026,
            )
            snap["delta"] = {
                "deltaSchemaVersion": rep.deltaSchemaVersion,
                "items": sorted(f"{i.analysis}:{i.kind.value}:{i.refId}" for i in rep.items),
            }
        else:
            snap["delta"] = None

        # 6) TenGodThemeDelta 方向（REVIEW 级）+ score（INFO 级）
        if chart.luck:
            dy_dicts = [dy.model_dump(by_alias=True, exclude_none=True)
                        for dy in chart.luck.da_yun[:3]]
            tl = build_timeline(
                natal_stems=stems, natal_branches=branches, day_master=dm,
                birth_year=y, da_yun=dy_dicts,
                target_years=list(range(chart.luck.da_yun[1].start_year,
                                        chart.luck.da_yun[1].end_year + 1)) if len(chart.luck.da_yun) > 1 else [],
            )
            snap["tenGodDirections"] = sorted(
                f"{d.ten_god}:{d.direction}" for d in tl.tenGodDeltas if d.direction != "unchanged")
            snap["scores"] = {n.label: n.structuralChangeScore for n in tl.nodes}

        snapshots.append(snap)
    return snapshots


def write_baseline(snapshots: list[dict]) -> dict:
    meta = {
        "engineVersion": tianze.__version__,
        "engineStage": tianze.ENGINE_STAGE,
        "deltaSchemaVersion": DELTA_SCHEMA_VERSION,
        "generatedBy": "tools/temporal_regression.py snapshot",
        "count": len(snapshots),
    }
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE.write_text(json.dumps({"meta": meta, "snapshots": snapshots},
                                   ensure_ascii=False, indent=1), encoding="utf-8")
    return meta


def compare(baseline: dict, current: list[dict]) -> dict:
    base_by = {s["probe"]: s for s in baseline["snapshots"]}
    cur_by = {s["probe"]: s for s in current}
    changed: list[dict] = []
    severity_counter: Counter = Counter()
    new_probes = sorted(set(cur_by) - set(base_by))
    removed_probes = sorted(set(base_by) - set(cur_by))

    def add(probe: str, field: str, before, after, severity: str, detail: str = ""):
        changed.append({"probe": probe, "field": field, "before": before,
                        "after": after, "severity": severity,
                        **({"detail": detail} if detail else {})})

    for pid in sorted(set(base_by) & set(cur_by)):
        b, c = base_by[pid], cur_by[pid]
        # BREAKING：起运/大运/流月/流日
        if b.get("luck") != c.get("luck"):
            if (b.get("luck") or {}).get("forward") != (c.get("luck") or {}).get("forward"):
                add(pid, "luck.forward", (b.get("luck") or {}).get("forward"),
                    (c.get("luck") or {}).get("forward"), "BREAKING", "大运顺逆变化")
            if (b.get("luck") or {}).get("start") != (c.get("luck") or {}).get("start"):
                add(pid, "luck.start", (b.get("luck") or {}).get("start"),
                    (c.get("luck") or {}).get("start"), "BREAKING", "起运时刻变化")
            if (b.get("luck") or {}).get("dayun") != (c.get("luck") or {}).get("dayun"):
                add(pid, "luck.dayun", None, None, "BREAKING", "大运序列变化")
        if b.get("months_2026") != c.get("months_2026"):
            add(pid, "months", None, None, "BREAKING", "流月干支/节气窗口变化")
        if b.get("day_probe") != c.get("day_probe"):
            add(pid, "dayProbe", b.get("day_probe"), c.get("day_probe"), "BREAKING", "流日干支变化")
        # REVIEW：流年关系/结构/规则/Delta/十神方向
        if b.get("annuals") != c.get("annuals"):
            for ba, ca in zip(b.get("annuals") or [], c.get("annuals") or []):
                if ba == ca:
                    continue
                year = ca.get("year")
                for field in ("gz", "relations", "structures", "rules"):
                    if ba.get(field) != ca.get(field):
                        add(pid, f"annual[{year}].{field}", ba.get(field), ca.get(field), "REVIEW")
        bd, cd = b.get("delta"), c.get("delta")
        if (bd is None) != (cd is None):
            add(pid, "delta.presence", bd is not None, cd is not None, "REVIEW")
        elif bd and cd:
            if bd.get("items") != cd.get("items"):
                bset, cset = set(bd.get("items") or []), set(cd.get("items") or [])
                add(pid, "delta.items", sorted(bset - cset), sorted(cset - bset), "REVIEW",
                    "Delta 条目集合变化")
        if b.get("tenGodDirections") != c.get("tenGodDirections"):
            add(pid, "tenGodDirections", b.get("tenGodDirections"),
                c.get("tenGodDirections"), "REVIEW")
        # INFO：heuristic 分数
        if b.get("scores") != c.get("scores"):
            add(pid, "scores", b.get("scores"), c.get("scores"), "INFO",
                "structuralChangeScore 为 ENGINEERING_HEURISTIC 排序值")

    for pid in new_probes:
        add(pid, "probe", None, True, "EXPECTED", "新增探针")
    for pid in removed_probes:
        add(pid, "probe", True, None, "REVIEW", "探针移除")

    for entry in changed:
        severity_counter[entry["severity"]] += 1
    order = {"BREAKING": 0, "REVIEW": 1, "EXPECTED": 2, "INFO": 3}
    changed.sort(key=lambda x: (order[x["severity"]], x["probe"], x["field"]))
    return {
        "meta": {"baseline": baseline.get("meta", {}),
                 "current": {"engineVersion": tianze.__version__,
                             "engineStage": tianze.ENGINE_STAGE,
                             "deltaSchemaVersion": DELTA_SCHEMA_VERSION}},
        "probeCount": {"baseline": len(base_by), "current": len(cur_by)},
        "newProbes": new_probes, "removedProbes": removed_probes,
        "changedProbes": changed,
        "severityCounts": dict(severity_counter),
    }


def write_report(result: dict) -> Path:
    out = REPO / "regression" / "temporal-report.md"
    lines = [
        "# Temporal Regression Report", "",
        f"- baseline engine: {result['meta']['baseline'].get('engineVersion')}"
        f" ({result['meta']['baseline'].get('engineStage')})",
        f"- current engine: {result['meta']['current']['engineVersion']}"
        f" ({result['meta']['current']['engineStage']})",
        f"- probes: {result['probeCount']['baseline']} → {result['probeCount']['current']}",
        f"- severity: {result['severityCounts']}", "",
    ]
    if result["changedProbes"]:
        lines.append("| severity | probe | field | detail |")
        lines.append("|---|---|---|---|")
        for e in result["changedProbes"]:
            lines.append(f"| {e['severity']} | {e['probe']} | {e['field']} | {e.get('detail', '')} |")
    else:
        lines.append("无变化。")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "compare"
    if cmd == "snapshot":
        meta = write_baseline(compute_snapshots())
        print(f"Temporal baseline 已写入：{meta['count']} 探针（engine {meta['engineVersion']}）")
        return 0
    if cmd == "compare":
        if not BASELINE.exists():
            print("baseline 不存在：先运行 temporal_regression.py snapshot")
            return 2
        result = compare(json.loads(BASELINE.read_text(encoding="utf-8")), compute_snapshots())
        (REPO / "regression" / "temporal-compare.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        out = write_report(result)
        n_breaking = result["severityCounts"].get("BREAKING", 0)
        print(f"Temporal Regression：{result['severityCounts']} → 报告 {out}")
        return 1 if n_breaking else 0
    if cmd == "report":
        result = json.loads((REPO / "regression" / "temporal-compare.json").read_text(encoding="utf-8"))
        print(write_report(result))
        return 0
    print("用法：temporal_regression.py [snapshot|compare|report]")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
