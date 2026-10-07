"""M16 · Knowledge Schema Migration 工具（1.1 → 1.2）。

1.2 变更（全部增量、确定性、可 round-trip）：
- ExecutableRule 增加 `migrationTag`（= 来源 schema 版本迁移标记 "1.1→1.2"）
- temporal 规则统一补齐 `category` 缺省（无 category → "generic"）
- event/temporal 规则的 `theme`/`category` 字段规范化（strip）

纪律：
- 不静默修改历史数据：默认 dry-run 打印 diff 摘要；--write 才落盘（写 .migrated 副本，
  由人工确认后替换），原文件不动
- 迁移函数纯函数（可测试）：migrate_rule_v1_1_to_1_2(rule) -> (new_rule, changed)
"""

from __future__ import annotations

import glob
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TARGET = "1.2.0"


def migrate_rule_v1_1_to_1_2(rule: dict) -> tuple[dict, bool]:
    """单条规则迁移（纯函数）。返回 (new_rule, changed)。"""
    new = json.loads(json.dumps(rule, ensure_ascii=False))  # deep copy
    changed = False
    if new.get("schemaVersion") != TARGET:
        new["schemaVersion"] = TARGET
        changed = True
    if "migrationTag" not in new:
        new["migrationTag"] = "1.1->1.2"
        changed = True
    if new.get("domain") == "temporal" and not new.get("category"):
        new["category"] = "generic"
        changed = True
    for k in ("theme", "category"):
        if isinstance(new.get(k), str) and new[k] != new[k].strip():
            new[k] = new[k].strip()
            changed = True
    return new, changed


def migrate_payload(payload: dict) -> tuple[dict, Counter]:
    """整个 rules.json payload 迁移（纯函数）。"""
    out = json.loads(json.dumps(payload, ensure_ascii=False))
    changes: Counter = Counter()
    out["schemaVersion"] = TARGET
    new_rules = []
    for r in out.get("rules", []):
        nr, changed = migrate_rule_v1_1_to_1_2(r)
        if changed:
            changes["rules"] += 1
        new_rules.append(nr)
    out["rules"] = new_rules
    if out.get("conflicts"):
        out["conflictsSchemaVersion"] = TARGET
        changes["conflicts"] += 1
    if out.get("rescues"):
        out["rescuesSchemaVersion"] = TARGET
        changes["rescues"] += 1
    return out, changes


def main() -> int:
    write = "--write" in sys.argv
    total_changed = Counter()
    for f in sorted(glob.glob("knowledge/rules/*/rules.json")):
        payload = json.load(open(f, encoding="utf-8"))
        if payload.get("schemaVersion") == TARGET and not write:
            print(f"  {f}: 已是 {TARGET}（跳过）")
            continue
        migrated, changes = migrate_payload(payload)
        total_changed += changes
        print(f"  {f}: {payload.get('schemaVersion')} → {TARGET}，"
              f"变更 {dict(changes) or '{}'}")
        if write:
            out_path = f.replace(".json", ".migrated.json")
            with open(out_path, "w", encoding="utf-8") as fh:
                json.dump(migrated, fh, ensure_ascii=False, indent=1)
            print(f"    → 写入 {out_path}（原文件未动；人工确认后替换）")

    print(f"Migration dry-run 完成（{'写入 .migrated 副本' if write else '未写盘'}）；"
          f"总变更 {dict(total_changed) or '{}'}")
    print("纪律：不静默修改历史数据——.migrated 副本需人工确认替换。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
