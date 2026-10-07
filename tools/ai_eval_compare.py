"""M19 · AI Evaluation History Compare（跨 provider/model/prompt 对比）。

只比较确定性指标（无 LLM-as-judge，无算命准确率）：
- grounding pass 率、banned 语言命中、disagreement 遗漏、claim refs 使用、
  status 词汇、verdict 分布、caseSetHash 一致性
- 回归检测：与上一条记录相比指标恶化 → REVIEW 标记

输出：regression/ai-eval-compare.json
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

COMPARE_SCHEMA_VERSION = "1.0.0"


def main() -> int:
    path = "regression/ai-evaluation-history.jsonl"
    if not os.path.exists(path):
        print("BLOCKED：无评估历史（真实 provider 运行后写入）；mock 运行可产生记录")
        return 2
    entries = [json.loads(x) for x in
               open(path, encoding="utf-8").read().strip().split(chr(10)) if x]
    if len(entries) < 1:
        print("BLOCKED：历史为空")
        return 2

    comparisons = []
    prev = None
    for e in entries:
        per = e.get("perCase", [])
        metrics = {
            "provider": e.get("provider"), "model": e.get("model"),
            "promptVersion": e.get("promptVersion"),
            "caseSetHash": e.get("caseSetHash"),
            "groundingIssueTotal": sum(p.get("groundingIssues", 0) for p in per),
            "bannedTotal": sum(len(p.get("banned", [])) for p in per),
            "disagreementMissingCount": sum(1 for p in per if p.get("disagreementMissing")),
            "claimRefsUsedAvg": round(sum(p.get("claimRefsUsed", 0) for p in per)
                                      / max(1, len(per)), 2),
            "verdictPass": sum(1 for p in per if p["verdict"] in ("PASS", "PIPELINE_OK")),
            "verdictTotal": len(per),
        }
        regression = {}
        if prev and prev.get("caseSetHash") == metrics.get("caseSetHash"):
            for k, worse in (("groundingIssueTotal", "more"), ("bannedTotal", "more"),
                             ("disagreementMissingCount", "more"),
                             ("claimRefsUsedAvg", "less"), ("verdictPass", "less")):
                if worse == "more" and metrics[k] > prev[k]:
                    regression[k] = f"{prev[k]} → {metrics[k]}（恶化）"
                if worse == "less" and metrics[k] < prev[k]:
                    regression[k] = f"{prev[k]} → {metrics[k]}（恶化）"
        comparisons.append({"metrics": metrics, "regressionAgainstPrevious": regression})
        prev = metrics

    payload = {
        "schemaVersion": COMPARE_SCHEMA_VERSION,
        "entryCount": len(entries),
        "comparisons": comparisons,
        "note": "仅确定性指标对比；verdict 口径见 quality gate（mock=PIPELINE_OK）",
    }
    with open("regression/ai-eval-compare.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"AI Eval Compare：{len(entries)} 条历史；回归信号 "
          f"{sum(1 for c in comparisons if c['regressionAgainstPrevious'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
