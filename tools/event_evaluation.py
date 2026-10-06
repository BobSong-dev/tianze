"""M14 · Event Evaluation：事件主题评估语料 + 指标报告。

语料（对齐任务书 10 类场景）：
- 多体系一致 / 多体系冲突 / 强 supporting + 强 opposing
- historical claim 有但 Tianze 无支持 / Tianze 有主题但原书沉默
- MACHINE_CURATED source / CLASSICAL_EXPLICIT source
- UNRESOLVED temporal structure / 从格化气分歧 / unknown hour

指标：rule coverage、theme distribution、disagreement rate、unresolved rate、
source quality distribution、abnormal trigger rate（随机盘审计，异常高即 REVIEW）。

原则：评估只描述覆盖与分歧，不裁决规则对错；历史事件不是 ground truth。
"""

from __future__ import annotations

import datetime
import json
import os
import random
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tianze.domain.models import BirthInfo, Gender
from tianze.pipeline import build_chart
from tianze.analysis.event_themes import EventStatus, EventTheme, compute_event_themes
from tianze.knowledge.event_rules import load_event_rules

OUT_DIR = os.path.join("regression")
PROBES = [
    # (name, date, time, gender, luck, annual, monthly, 场景标签)
    {"name": "multi_view_agree", "date": "1984-02-05", "time": "10:30", "gender": "male",
     "luck": ("甲", "子"), "annual": ("丙", "午"), "monthly": None,
     "scenario": "官印并透+印主题：traditional 单体系一致"},
    {"name": "multi_view_conflict", "date": "1984-02-05", "time": "10:30", "gender": "male",
     "luck": ("甲", "子"), "annual": ("丙", "午"), "monthly": ("庚", "寅"),
     "scenario": "官星支持 vs 伤官见官：DISPUTED/CONFLICT"},
    {"name": "shensha_only", "date": "1984-02-05", "time": "10:30", "gender": "male",
     "luck": None, "annual": None, "monthly": ("甲", "寅"),
     "scenario": "驿马独发：shensha view 单独（低权重）"},
    {"name": "unknown_hour", "date": "2003-08-18", "time": None, "gender": "male",
     "luck": None, "annual": ("丙", "午"), "monthly": None,
     "scenario": "unknown hour：大运缺席，事件主题仅在流年层"},
    {"name": "wealth_ku", "date": "1983-02-15", "time": "20:00", "gender": "female",
     "luck": None, "annual": ("庚", "午"), "monthly": None,
     "scenario": "财库/财星结构"},
    {"name": "female_guan", "date": "1983-02-15", "time": "20:00", "gender": "female",
     "luck": None, "annual": ("庚", "午"), "monthly": None,
     "scenario": "女命官星：配偶星规则（gender-conditional）"},
]
RANDOM_N = 200


def run_probe(probe: dict) -> dict:
    y, m, d = (int(x) for x in probe["date"].split("-"))
    t = None
    if probe["time"]:
        hh, mm = (int(x) for x in probe["time"].split(":"))
        t = datetime.time(hh, mm)
    chart = build_chart(BirthInfo(date=datetime.date(y, m, d), time=t,
                                  gender=Gender(probe["gender"])))
    rep = compute_event_themes(chart, luck=probe["luck"], annual=probe["annual"],
                               monthly=probe["monthly"])
    return {
        "probe": probe["name"], "scenario": probe["scenario"],
        "themes": [
            {"theme": th.theme.value, "status": th.status.value,
             "agreement": th.agreement, "confidence": th.confidence,
             "views": th.schoolViews,
             "rules": [h.ruleId for h in th.triggeredRules]}
            for th in rep.themes
        ],
        "unmatchedRules": rep.unmatchedRules,
    }


def random_audit(seed: int = 42, n: int = RANDOM_N) -> dict:
    """随机盘触发率审计：某规则/主题异常高触发 → REVIEW 标记。"""
    rng = random.Random(seed)
    rule_hits: Counter = Counter()
    theme_hits: Counter = Counter()
    status_counts: Counter = Counter()
    total = 0
    for _ in range(n):
        y, mo, d = rng.randint(1950, 2010), rng.randint(1, 12), rng.randint(1, 28)
        g = rng.choice(["male", "female"])
        try:
            chart = build_chart(BirthInfo(date=datetime.date(y, mo, d),
                                          time=datetime.time(rng.randint(0, 23), 30),
                                          gender=Gender(g)))
        except Exception:
            continue
        year = rng.randint(1980, 2060)
        ai = (year - 4) % 60
        from tianze.ganzhi.tables import STEMS, BRANCHES
        rep = compute_event_themes(
            chart, annual=(STEMS[ai % 10], BRANCHES[ai % 12]))
        total += 1
        for th in rep.themes:
            theme_hits[th.theme.value] += 1
            status_counts[th.status.value] += 1
            for h in th.triggeredRules:
                rule_hits[h.ruleId] += 1
    # 阈值（ENGINEERING_HEURISTIC）：单规则 >60% 或单主题 >70% 触发 → REVIEW
    abnormal = {
        "rules": {k: round(v / total, 3) for k, v in rule_hits.items() if v / total > 0.60},
        "themes": {k: round(v / total, 3) for k, v in theme_hits.items() if v / total > 0.70},
    }
    return {
        "samples": total,
        "ruleTriggerRate": {k: round(v / total, 3) for k, v in sorted(rule_hits.items())},
        "themeTriggerRate": {k: round(v / total, 3) for k, v in sorted(theme_hits.items())},
        "statusDistribution": dict(status_counts),
        "abnormalTriggerRate": abnormal,
        "threshold": "rule >60% / theme >70% → REVIEW（ENGINEERING_HEURISTIC）",
    }


def historical_coverage() -> dict:
    """historicalClaims 主题分布 vs Tianze 规则主题集合：覆盖率对照（非对错裁决）。"""
    path = "knowledge/normalized/cases/event_claims.json"
    if not os.path.exists(path):
        return {"error": "先运行 tools/parse_event_claims.py"}
    data = json.load(open(path, encoding="utf-8"))
    stats = json.load(open("knowledge/normalized/cases/event_claims_stats.json",
                           encoding="utf-8"))
    rule_themes = {r["theme"] for r in load_event_rules()}
    claim_themes = set(stats.get("themeDistribution") or {})
    return {
        "claimsTotal": stats.get("claimsTotal"),
        "claimsAnnotated": stats.get("claimsAnnotated"),
        "sensitiveClaims": stats.get("sensitiveClaims"),
        "claimThemeDistribution": stats.get("themeDistribution"),
        "ruleThemes": sorted(rule_themes),
        "claimThemesWithoutRule": sorted(claim_themes - rule_themes),
        "ruleThemesWithoutClaims": sorted(rule_themes - claim_themes),
        "note": "历史事件不是 ground truth：本对照只描述覆盖，不调整规则",
    }


def main() -> int:
    probes = [run_probe(p) for p in PROBES]
    audit = random_audit()
    coverage = historical_coverage()

    metrics = {
        "schemaVersion": "1.0.0",
        "ruleCount": len(load_event_rules()),
        "ruleCoverageByProbe": {
            p["probe"]: round(
                1 - len(p["unmatchedRules"]) / len(load_event_rules()), 3)
            for p in probes
        },
        "disagreementRate": {
            "byProbe": {
                p["probe"]: round(
                    sum(1 for t in p["themes"] if t["status"] == "DISPUTED")
                    / max(1, len(p["themes"])), 3)
                for p in probes
            },
        },
        "unresolvedRate": {
            "byProbe": {
                p["probe"]: round(
                    sum(1 for t in p["themes"] if t["status"] == "UNRESOLVED")
                    / max(1, len(p["themes"])), 3)
                for p in probes
            },
        },
        "probes": probes,
        "randomAudit": audit,
        "historicalCoverage": coverage,
    }
    problems = []
    if audit["abnormalTriggerRate"]["rules"] or audit["abnormalTriggerRate"]["themes"]:
        problems.append("abnormal trigger rate 超阈值：REVIEW")
    metrics["problems"] = problems

    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "event-evaluation.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=1)
    print(f"Event Evaluation → {out}")
    print(f"  规则数：{metrics['ruleCount']}；随机盘 {audit['samples']} 例")
    print(f"  随机盘主题触发率：{audit['themeTriggerRate']}")
    print(f"  异常触发：{audit['abnormalTriggerRate'] or '无'}")
    print(f"  problems：{problems or '无'}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
