"""K1 · 知识库静态校验工具。

运行：python tools/validate_knowledge.py
输出：规则数 / 来源数 / 缺失出处 / 重复 ID / 无效引用 / 冲突规则 /
      未覆盖日主-月支 / OCR 风险；并写 knowledge/normalized/stats.json。
校验失败（重复 ID、缺失来源、无效引用）→ 退出码 1。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parents[1]
NORM = REPO / "knowledge" / "normalized"
RULES_DIR = REPO / "knowledge" / "rules"
STEMS = "甲乙丙丁戊己庚辛壬癸"
MONTHS = "寅卯辰巳午未申酉戌亥子丑"


def main() -> int:
    stats: dict = {}
    problems: list[str] = []

    # ---- candidates ----
    all_candidates: dict[str, dict] = {}
    files = 0
    for book_dir in sorted(NORM.glob("*/rules.json")):
        data = json.loads(book_dir.read_text(encoding="utf-8"))
        files += 1
        for r in data["rules"]:
            if r["id"] in all_candidates:
                problems.append(f"重复候选 ID: {r['id']}")
            all_candidates[r["id"]] = r

    manifest = json.loads((NORM / "manifest.json").read_text(encoding="utf-8"))

    # ---- executable rules ----
    executable: list[dict] = []
    conflicts: list[dict] = []
    for rf in sorted(RULES_DIR.rglob("rules.json")):
        data = json.loads(rf.read_text(encoding="utf-8"))
        executable.extend(data["rules"])
        cfile = rf.parent / "conflicts.json"
        if cfile.exists():
            conflicts.extend(json.loads(cfile.read_text(encoding="utf-8")).get("conflicts", []))

    er_ids = [r["id"] for r in executable]
    dup_er = [i for i, n in __import__("collections").Counter(er_ids).items() if n > 1]
    problems.extend(f"重复 ExecutableRule ID: {i}" for i in dup_er)

    invalid_refs = [r["id"] for r in executable if r["candidateId"] not in all_candidates]
    problems.extend(f"无效候选引用: {i}" for i in invalid_refs)

    missing_source = [r["id"] for r in executable if not r.get("source", {}).get("book")]
    problems.extend(f"缺失来源: {i}" for i in missing_source)

    # CLASSICAL_EXPLICIT 必须携带引文
    for r in executable:
        for p in r.get("provenance", []):
            if p["level"] == "CLASSICAL_EXPLICIT" and not p.get("note"):
                problems.append(f"CLASSICAL_EXPLICIT 无引文: {r['id']}")

    # 调候覆盖率
    cells = set()
    for r in executable:
        if r["domain"] != "tiaohou":
            continue
        dm = next((c["value"] for c in r["conditions"] if c["field"] == "dayMaster"), None)
        mb = next((c["value"] for c in r["conditions"] if c["field"] == "monthBranch"), None)
        if dm and mb:
            cells.add((dm, mb))
    uncovered = [(d, m) for d in STEMS for m in MONTHS if (d, m) not in cells]

    # OCR 风险统计（candidates 层）
    ocr_risk = sum(1 for c in all_candidates.values() if c.get("ocrRisk"))

    stats = {
        "files": len(manifest["files"]),
        "rules_total": manifest["rulesTotal"],
        "candidates_total": len(all_candidates),
        "quotes_total": sum(len(c.get("originalQuotes") or []) for c in all_candidates.values()),
        "commentaries_total": sum(len(c.get("commentaries") or []) for c in all_candidates.values()),
        "executable_total": len(executable),
        "classical_explicit_total": sum(
            1 for r in executable for p in r.get("provenance", []) if p["level"] == "CLASSICAL_EXPLICIT"
        ),
        "project_reference_total": sum(
            1 for r in executable for p in r.get("provenance", []) if p["level"] == "PROJECT_REFERENCE"
        ),
        "unverified_total": sum(
            1 for r in executable for p in r.get("provenance", []) if p["level"] == "UNVERIFIED"
        ),
        "ocr_risk_total": ocr_risk,
        "tiaohou_coverage": {"covered": len(cells), "total": 120, "unresolved": 120 - len(cells)},
        "conflicts_total": len(conflicts),
        "duplicate_ids": sorted(set(dup_er)),
        "missing_source": missing_source,
        "invalid_refs": invalid_refs,
        "quality": manifest["quality"],
    }

    (NORM / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=1))
    if problems:
        print("\n== PROBLEMS ==")
        for p in problems:
            print(" -", p)
        return 1
    print("\nknowledge validation: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
