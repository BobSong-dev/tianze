"""M6 · 调候草案生成器：normalized QBT/ZHY 候选 → (日主×月支) 目标干草案。

两层规则的"程序建议"步骤：启发式提取 targets（先X次Y/以X为主/为辅/两透…），
输出 knowledge/normalized/tiaohou-draft.json + 10×12 覆盖表供人工复核；
人工复核后经 tools/build_tiaohou_rules.py 生成 ExecutableRule。
草案不是终稿——每格保留 candidate 引用与原文，复核以原文为准。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parents[1]
NORM = REPO / "knowledge" / "normalized"
STEMS = "甲乙丙丁戊己庚辛壬癸"
MONTHS = "寅卯辰巳午未申酉戌亥子丑"

# 优先级词模式（按强度降序）；对 原文+核心规则+适用条件 全文扫描
PRIORITY_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("primary", re.compile(r"以(?:\s*)?([甲乙丙丁戊己庚辛壬癸])(?:\s*)?为(?:主|要|先)|先(?:\s*)?([甲乙丙丁戊己庚辛壬癸])|专(?:用|取)([甲乙丙丁戊己庚辛壬癸])|非([甲乙丙丁戊己庚辛壬癸])不|主要之神")),
    ("secondary", re.compile(r"次(?:取|用)?(?:\s*)?([甲乙丙丁戊己庚辛壬癸])|([甲乙丙丁戊己庚辛壬癸])(?:为辅|为佐|佐之|配合)|辅以(?:\s*)?([甲乙丙丁戊己庚辛壬癸])")),
]
STEM_ALL = re.compile(r"[甲乙丙丁戊己庚辛壬癸]")


def extract_targets(text: str) -> dict[str, list[str]]:
    """返回 {priority: [stems]}。启发式：只依据显式的优先级措辞。"""
    out: dict[str, list[str]] = {"primary": [], "secondary": [], "mentioned": []}
    for priority, pattern in PRIORITY_PATTERNS:
        for m in pattern.finditer(text):
            for g in m.groups():
                if g and g not in out[priority]:
                    out[priority].append(g)
    # 提及但无明确优先级的干（仅作对照，不进 targets）
    for ch in STEMS:
        if ch in text and ch not in out["primary"] and ch not in out["secondary"]:
            out["mentioned"].append(ch)
    return out


def main() -> None:
    candidates: list[dict] = []
    for book in ("QBT", "ZHY"):
        data = json.loads((NORM / book / "rules.json").read_text(encoding="utf-8"))
        candidates.extend(data["rules"])

    cells: dict[tuple[str, str], list[dict]] = {}
    unmatched: list[dict] = []
    for c in candidates:
        dm, months = c.get("dayMaster"), c.get("months")
        if not dm or not months:
            unmatched.append({"id": c["id"], "reason": "no dayMaster/months"})
            continue
        text = " ".join(filter(None, [c.get("originalQuotes") and " ".join(c["originalQuotes"]),
                                      c.get("coreText"), c.get("applicableCondition"), "、".join(c.get("tags") or [])]))
        targets = extract_targets(text)
        if not targets["primary"] and not targets["secondary"]:
            unmatched.append({"id": c["id"], "dm": dm, "months": months, "reason": "no explicit target stems"})
            continue
        for month in months:
            cells.setdefault((dm, month), []).append({
                "candidateId": c["id"],
                "primary": targets["primary"],
                "secondary": targets["secondary"],
                "mentioned": targets["mentioned"][:6],
            })

    # 覆盖表
    print("     " + " ".join(f"{m}" for m in MONTHS))
    covered = 0
    unresolved: list[str] = []
    for dm in STEMS:
        row = []
        for m in MONTHS:
            entries = cells.get((dm, m))
            if entries:
                covered += 1
                best = entries[0]
                mark = best["primary"][0] if best["primary"] else (best["secondary"][0] if best["secondary"] else "?")
                row.append(mark)
            else:
                unresolved.append(f"{dm}{m}")
                row.append("·")
        print(f"  {dm}  " + " ".join(row))
    print(f"covered={covered}/120 unresolved={len(unresolved)}")

    draft = {
        "note": "程序建议草案（启发式 target 提取），供人工复核；复核后经 build_tiaohou_rules.py 生成 ExecutableRule。",
        "covered": covered,
        "unresolvedCells": unresolved,
        "cells": {f"{dm}-{m}": entries for (dm, m), entries in sorted(cells.items())},
        "unmatchedCandidates": unmatched,
    }
    (NORM / "tiaohou-draft.json").write_text(json.dumps(draft, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {NORM / 'tiaohou-draft.json'}")


if __name__ == "__main__":
    main()
