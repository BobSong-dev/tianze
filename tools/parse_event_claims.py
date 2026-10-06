"""M14 · historicalClaims → 事件主题标注（EventClaimReference）。

输入：knowledge/normalized/cases/temporal_refs.json（M13 产物，只读）
输出：knowledge/normalized/cases/event_claims.json + event_claims_stats.json

用途（对齐任务书）：
- HistoricalClaim ↔ EventThemeCandidate 的对照素材（历史事件仍然不是 ground truth）
- 规则覆盖率分析 / 命例回放 / source vs Tianze 对照 / evaluation

纪律：
- 关键词标注是 MACHINE_EXTRACTED（多义句保留全部命中主题，不强行单选）
- 不为了匹配历史案例调整事件规则
- 疾病/死亡/灾祸类断语标 sensitive=true（Tianze 不建对应主题，只保留原书 claim）
"""

from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 事件主题关键词表（curation：按主题归类；命中即标注，允许多主题）
EVENT_THEME_KEYWORDS: dict[str, list[str]] = {
    "career": ["任", "官至", "位至", "升", "总督", "巡抚", "尚书", "都督", "将军",
               "知县", "太守", "刺史", "部长", "省长", "都统", "主席", "公使",
               "总兵", "都堂", "提督", "道台", "局长", "厅长", "司令", "贵", "权"],
    "wealth": ["富", "得财", "破财", "发财", "经商", "为商", "业商", "致富", "家业", "遗产"],
    "relationship": ["婚", "娶", "嫁", "妻", "妾", "夫", "离", "克妻", "克夫", "续弦"],
    "study": ["进士", "举人", "状元", "榜眼", "探花", "科举", "中试", "及第", "入学",
              "留学", "学位", "考试", "秀才", "翰林"],
    "mobility": ["迁", "移居", "赴任", "调", "移", "行", "出国", "游", "旅行", "避"],
    "family": ["子", "嗣", "父", "母", "兄", "弟", "家", "丧", "孝", "克子", "无子"],
    "social": ["争", "讼", "斗", "仇", "杀", "合伙", "交际", "党"],
}
# 敏感主题（原书断语保留，但 Tianze 不建对应主题/规则）
SENSITIVE_KEYWORDS = ["死", "夭", "卒", "殁", "殉", "杀", "刺", "凶死", "横死", "病", "疾", "伤"]


def annotate_text(text: str) -> tuple[list[str], list[str], bool]:
    """返回 (themes, sensitive_hits, is_sensitive)。"""
    themes: list[str] = []
    for theme, kws in EVENT_THEME_KEYWORDS.items():
        if any(k in text for k in kws):
            themes.append(theme)
    sensitive = [k for k in SENSITIVE_KEYWORDS if k in text]
    return themes, sensitive, bool(sensitive)


def main() -> int:
    src_path = "knowledge/normalized/cases/temporal_refs.json"
    if not os.path.exists(src_path):
        print("缺 temporal_refs.json：先运行 tools/parse_temporal_cases.py")
        return 2
    src = json.load(open(src_path, encoding="utf-8"))

    records: list[dict] = []
    stats = {
        "totalCases": 0, "claimsWithTemporalGz": 0, "claimsAnnotated": 0,
        "claimsMultiTheme": 0, "sensitiveClaims": 0,
        "themeDistribution": {}, "claimsTotal": 0,
    }

    for case in src["cases"]:
        stats["totalCases"] += 1
        cid = case["caseId"]
        book = case["book"]
        dayun = case.get("sourceTemporal", {}).get("dayun") or []
        mentions = case.get("sourceTemporal", {}).get("mentions") or []
        claims = case.get("historicalClaims") or []

        # 每条 claim 与原书岁运干支做朴素共现关联（同句内 X运/X年）
        out_claims = []
        for cl in claims:
            text = cl.get("text", "")
            stats["claimsTotal"] += 1
            themes, sensitive, is_sensitive = annotate_text(text)
            stats["claimsAnnotated"] += 1 if themes else 0
            stats["sensitiveClaims"] += 1 if is_sensitive else 0
            if len(themes) > 1:
                stats["claimsMultiTheme"] += 1
            for t in themes:
                stats["themeDistribution"][t] = stats["themeDistribution"].get(t, 0) + 1
            # 共现的岁运干支（mentions 的 ganZhi 出现在 claim 文本中 → 关联）
            linked_gz = [m.get("ganZhi") for m in mentions
                         if m.get("ganZhi") and m["ganZhi"] in text]
            linked_dayun = [d.get("ganZhi") for d in dayun
                            if d.get("ganZhi") and d.get("ganZhi") in text]
            if linked_gz or linked_dayun:
                stats["claimsWithTemporalGz"] += 1
            out_claims.append({
                "text": text,
                "claimType": cl.get("claimType", "HISTORICAL_CLAIM"),
                "eventThemes": themes,                 # 多主题保留，不强行单选
                "sensitive": is_sensitive,             # Tianze 不建主题，仅保留原书 claim
                "sensitiveKeywords": sensitive,
                "linkedTemporalGz": sorted(set(filter(None, linked_gz + linked_dayun))),
                "refId": f"case:{cid}:claim:{__import__('hashlib').md5(text.encode('utf-8')).hexdigest()[:10]}",
            })

        records.append({
            "caseId": cid,
            "book": book,
            "claims": out_claims,
            "sourceDayun": [d.get("ganZhi") for d in dayun],
            "note": "历史事件不是 ground truth；本标注仅用于规则覆盖率/回放/对照分析",
        })

    payload = {
        "schemaVersion": "1.0.0",
        "description": "EventClaimReference：historicalClaims → 事件主题关键词标注"
                       "（MACHINE_EXTRACTED，多主题并存，敏感断语不建主题）",
        "provenance": "tools/parse_event_claims.py 基于 temporal_refs.json",
        "verification": {"status": "MACHINE_EXTRACTED", "sourceChecked": False},
        "count": len(records),
        "cases": records,
    }
    with open("knowledge/normalized/cases/event_claims.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    with open("knowledge/normalized/cases/event_claims_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=1)

    print(f"事件主题标注完成：{stats['totalCases']} 例 / {stats['claimsTotal']} 条 claim")
    print(f"  带主题标注：{stats['claimsAnnotated']}（多主题 {stats['claimsMultiTheme']}）")
    print(f"  敏感断语（不建主题）：{stats['sensitiveClaims']}")
    print(f"  与岁运干支共现：{stats['claimsWithTemporalGz']}")
    print(f"  主题分布：{stats['themeDistribution']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
