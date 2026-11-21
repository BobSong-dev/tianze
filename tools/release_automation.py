"""M19 · Release Automation：changelog → version bump 建议 → release notes → tag 准备。

流程：quality gate（要求最新 ALL PASS）→ metadata → changelog（自上个 tag）→
version bump 建议（按 commit 前缀的透明规则）→ RELEASE_NOTES.md → tag 准备。

纪律：
- 默认 dry-run：不创建 tag、绝不 push；--tag 才创建本地 tag
- 全部数字来自 release-metadata.json / quality-summary.json / git——无硬编码
- bump 规则透明：含 M\\d+ 特性 commit → minor；否则 patch（ENGINEERING 约定）
"""

from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTOMATION_SCHEMA_VERSION = "1.0.0"


def _git(*args) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", cwd=REPO).stdout.strip()


def _load(rel, default):
    p = os.path.join(REPO, rel)
    if not os.path.exists(p):
        return default
    return json.load(open(p, encoding="utf-8"))


def _pyproject_version() -> str:
    """单一事实源：tianze.__version__（pyproject dynamic 绑定）。"""
    import tianze
    return tianze.__version__


def main() -> int:
    # --skip-gate-check：质量门内部调用（gate 的 summary 尚未写出，无法自证 ALL PASS）
    from tools.release_check import quality_gate_status

    internal = "--gate-progress" in sys.argv
    execute = "--tag" in sys.argv
    if execute and (internal or "--skip-gate-check" in sys.argv):
        print("BLOCKED：创建标签需要正式质量报告")
        return 2
    path = sys.argv[sys.argv.index("--gate-progress") + 1] if internal else "release/quality-summary.json"
    summary = _load(path, {})
    if "--skip-gate-check" not in sys.argv or execute:
        passed, detail = quality_gate_status(summary, _git("rev-parse", "HEAD"))
        if not passed:
            print(f"BLOCKED：{detail}")
            return 2
    metadata = _load("release/release-metadata.json", None)
    if not metadata:
        print("BLOCKED：release metadata 缺失")
        return 2

    # changelog：自上个 tag
    last_tag = _git("describe", "--tags", "--abbrev=0")
    range_spec = f"{last_tag}..HEAD" if last_tag else "HEAD"
    log_lines = [x for x in _git("log", range_spec, "--pretty=format:%s").split("\n") if x]
    groups: dict[str, list[str]] = {"features": [], "fixes": [], "tests": [],
                                    "docs": [], "chores": []}
    for line in log_lines:
        if re.match(r"M\d+", line):
            groups["features"].append(line)
        elif line.startswith(("fix:", "test:")) and line.startswith("fix:"):
            groups["fixes"].append(line)
        elif line.startswith("test:"):
            groups["tests"].append(line)
        elif line.startswith("docs"):
            groups["docs"].append(line)
        else:
            groups["chores"].append(line)

    # version bump 建议（透明规则；PEP 440 dev 线感知）
    current = _pyproject_version()
    if ".dev" in current:
        # 0.4.0.dev0 的下一个 tag 就是 v0.4.0：dev 线本身承载本次特性工作，
        # 不再 +1（PEP 440 序 0.4.0.dev0 < 0.4.0，tag 仍是真实前进）。
        kind = "minor" if groups["features"] else "patch"
        base = current.split(".dev")[0]
        suggested = base
    elif groups["features"]:
        kind = "minor"
        parts = current.split(".")
        suggested = f"{parts[0]}.{int(parts[1]) + 1}.0"
    else:
        kind = "patch"
        parts = current.split(".")
        suggested = f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"

    tag_name = f"v{suggested}"
    tag_prepared = {"tag": tag_name, "created": False,
                    "command": f"git tag -a {tag_name} -m 'Tianze {tag_name}'",
                    "push": "不自动 push（人工执行 git push origin " + tag_name + "）"}
    if execute:
        rc = subprocess.run(["git", "tag", "-a", tag_name,
                             "-m", f"Tianze {tag_name}"], cwd=REPO)
        tag_prepared["created"] = rc.returncode == 0

    notes = [
        f"# Tianze {tag_name} Release Notes",
        "",
        f"- commit: `{metadata['release']['gitCommit'][:12]}`"
        f"（{'含未提交改动' if metadata['release']['dirty'] else '工作区干净'}）",
        f"- 当前版本 {current} → 建议 {tag_name}（{kind}；规则：特性 commit → minor，否则 patch）",
        f"- 质量门：{'执行中' if internal else ('ALL PASS' if summary.get('allPass') else 'FAIL')}"
        f"（{summary.get('totalSeconds')}s / {len(summary.get('steps', []))} 步）",
        "",
        "## 版本与规模",
        "",
        f"- versions: {metadata['versions']}",
        f"- ExecutableRule: **{metadata['counts']['executableRules']}**"
        f"（{metadata['counts']['rulesByDomain']}）；candidates "
        f"{metadata['counts']['ruleCandidates']}（不同口径）",
        f"- 命例 {metadata['counts']['cases']}；Replay {metadata['counts']['replays']}；"
        f"测试 {metadata['counts']['tests']}",
        "",
        "## 质量状态",
        "",
        f"- Audit Gates: {'ALL PASS' if metadata['quality']['allGatesPass'] else 'FAIL'}",
        f"- Case Regression: {metadata['quality']['caseRegressionSeverity'] or '无变化'}",
        f"- Temporal Regression: {metadata['quality']['temporalRegressionSeverity'] or '无变化'}",
        f"- Event Evaluation problems: {metadata['quality']['eventEvaluationProblems'] or '无'}",
        f"- AI Evaluation: {metadata['governance']['aiEvaluationStatus']}"
        "（无 API Key 时 SKIPPED，不伪造）",
        "",
        "## 基准",
        "",
        "```json",
        json.dumps(metadata.get("benchmark", {}), ensure_ascii=False, indent=1),
        "```",
        "",
        "## Commits（自 " + (last_tag or "起点") + "）",
        "",
    ]
    for g, title in (("features", "特性"), ("fixes", "修复"), ("tests", "测试"),
                     ("docs", "文档"), ("chores", "杂项")):
        if groups[g]:
            notes.append(f"### {title}（{len(groups[g])}）")
            notes.extend(f"- {c}" for c in groups[g])
            notes.append("")

    notes.append("## Migration 要求")
    notes.append("")
    migration_needed = any(c.get("schemaVersion") == "1.2.0"
                           for f in glob.glob(os.path.join(REPO, "knowledge/rules/*/rules.json"))
                           for c in [json.load(open(f, encoding="utf-8"))])
    notes.append("- 规则文件当前未批量升至 1.2.0：如需升级，运行 "
                 "`tools/migrate_knowledge.py --write` 并人工确认 .migrated 副本（不静默改历史）"
                 if not migration_needed else
                 "- 已有规则文件处于 1.2.0")
    review_rules = _load("regression/rule-audit.json", {}).get("reviewRules", [])
    notes.append("")
    notes.append("## OPEN / REVIEW")
    notes.append("")
    notes.append(f"- Rule Audit 异常泛化信号：{review_rules or '无'}")
    notes.append(f"- Review Queue：见 review/review-queue.json（只汇总，不自动升级 HUMAN 状态）")

    with open(os.path.join(REPO, "release/RELEASE_NOTES.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(notes) + "\n")

    payload = {
        "schemaVersion": AUTOMATION_SCHEMA_VERSION,
        "currentVersion": current, "suggestedTag": tag_name, "bumpKind": kind,
        "commitGroups": {k: len(v) for k, v in groups.items()},
        "tagPrepared": tag_prepared,
        "qualityGate": {"allPass": None if internal else summary.get("allPass")},
    }
    with open(os.path.join(REPO, "release/tag-prep.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"Release Automation：{current} → {tag_name}（{kind}）；"
          f"commits {payload['commitGroups']}；notes → release/RELEASE_NOTES.md")
    print(f"  tag：{'已创建（本地）' if tag_prepared['created'] else 'dry-run（未创建，不 push）'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
