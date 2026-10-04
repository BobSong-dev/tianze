"""M8 · 特殊格局分布审计：检查候选率是否异常（发现过拟合/阈值过松）。

运行：python tools/analyze_special_pattern_distribution.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

REPO = Path(__file__).resolve().parents[1]
CASES = REPO / "knowledge" / "normalized" / "cases"
OUT = REPO / "knowledge" / "normalized" / "special-pattern-distribution.json"


def main() -> int:
    from tools.derive_case_analysis import analyze_pillars
    from tianze.analysis.special import analyze_all_special
    from tianze.ganzhi.tables import BRANCH_ELEMENT, STEM_ELEMENT, ten_god

    stats = {
        "total": 0, "computed": 0,
        "congCandidate": 0, "congLikely": 0, "congBlocked": 0, "congDisputed": 0,
        "zhuanwangCandidate": 0, "zhuanwangLikely": 0, "zhuanwangBlocked": 0,
        "transformationCandidate": 0, "transformationUnresolved": 0,
        "bingyaoProblems": 0, "tongguanPairs": 0,
        "byDayMaster": defaultdict(lambda: Counter()),
        "byMonth": defaultdict(lambda: Counter()),
        "byBook": defaultdict(lambda: Counter()),
    }

    for path in sorted(CASES.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        book = data["book"]
        for case in data["cases"]:
            stats["total"] += 1
            pillars = case["fact"]["pillars"]
            if not all(pillars.get(k) for k in ("year", "month", "day", "hour")):
                continue
            derived = analyze_pillars(pillars)
            if not derived:
                continue
            stats["computed"] += 1
            dm = derived["dayMaster"]
            mb = derived["monthBranch"]
            stems = [pillars.get(p, [None, None, None, None][i]) for i, p in enumerate(("year", "month", "day", "hour"))]
            stems = [s[0] if s else None for s in stems]
            branches = [pillars.get(p, [None, None, None, None][i])[1] if pillars.get(p) else None
                        for i, p in enumerate(("year", "month", "day", "hour"))]
            roots = sum(1 for b in branches if b and any(
                h == dm for h, _ in __import__("tianze.ganzhi.tables", fromlist=["HIDDEN_STEMS"]).HIDDEN_STEMS.get(b, [])
            ))

            from tianze.ganzhi.tables import Element
            ec = {}
            from tianze.ganzhi.tables import HIDDEN_STEMS as _HS
            for e in Element:
                v = sum(1 for s in stems if s and STEM_ELEMENT[s] == e)
                h = sum(1 for b in branches if b and b in _HS for h, _ in _HS[b] if STEM_ELEMENT[h] == e)
                ec[e.value.lower()] = {"visible": v, "hidden": h}

            helpers = [s for s in stems if s and s != dm and
                       ten_god(dm, s).value in ("比肩", "劫财", "正印", "偏印")]
            verdicts = {"weighted": derived["strengthVerdicts"].get("weighted"),
                        "fuyi": derived["strengthVerdicts"].get("fuyi"),
                        "dimension": None}
            weighted_score = None

            result = analyze_all_special(dm, mb, stems, branches, verdicts,
                                         weighted_score, roots, helpers, ec)

            sp = result["specialPattern"]
            for c in sp["cong"]:
                stats["byDayMaster"][dm][f"cong_{c['status']}"] += 1
                stats["byMonth"][mb][f"cong_{c['status']}"] += 1
                stats["byBook"][book][f"cong_{c['status']}"] += 1
                if c["status"] == "CANDIDATE": stats["congCandidate"] += 1
                elif c["status"] == "LIKELY": stats["congLikely"] += 1
                elif c["status"] == "BLOCKED": stats["congBlocked"] += 1
                elif c["status"] == "DISPUTED": stats["congDisputed"] += 1
            for z in sp["zhuanwang"]:
                stats["byDayMaster"][dm][f"zw_{z['status']}"] += 1
                if z["status"] == "CANDIDATE": stats["zhuanwangCandidate"] += 1
                elif z["status"] == "LIKELY": stats["zhuanwangLikely"] += 1
                elif z["status"] == "BLOCKED": stats["zhuanwangBlocked"] += 1
            for t in sp["transformation"]:
                if t["status"] == "CANDIDATE": stats["transformationCandidate"] += 1
                elif t["status"] == "UNRESOLVED": stats["transformationUnresolved"] += 1
            stats["bingyaoProblems"] += len(result["bingYao"]["problems"])
            stats["tongguanPairs"] += len(result["tongGuan"]["conflictPairs"])

    (OUT.parent.mkdir(parents=True, exist_ok=True))
    OUT.write_text(json.dumps(stats, ensure_ascii=False, indent=1, default=dict), encoding="utf-8")
    print(json.dumps({k: v for k, v in stats.items() if not isinstance(v, defaultdict)}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
