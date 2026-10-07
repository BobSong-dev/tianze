"""M16：Schema Migration 测试（确定性 / round-trip / 不动历史数据）。"""

from __future__ import annotations

import json
import os
import subprocess
import sys

from tools.migrate_knowledge import (
    TARGET, migrate_payload, migrate_rule_v1_1_to_1_2,
)


def test_rule_migration_additive_only():
    """迁移只增改标记字段，不动 conditions/effects/provenance 语义。"""
    rule = {"id": "X-1", "domain": "temporal", "conditions": [{"field": "a"}],
            "effects": [{"kind": "note"}], "provenance": [{"level": "PROJECT_REFERENCE"}]}
    new, changed = migrate_rule_v1_1_to_1_2(rule)
    assert changed and new["schemaVersion"] == TARGET
    assert new["migrationTag"] == "1.1->1.2"
    assert new["category"] == "generic"          # temporal 缺省补齐
    assert new["conditions"] == rule["conditions"]
    assert new["provenance"] == rule["provenance"]
    # 原对象不被修改（纯函数）
    assert "schemaVersion" not in rule and "migrationTag" not in rule


def test_payload_migration_idempotent():
    """迁移幂等：二次迁移 0 变更（round-trip 稳定）。"""
    payload = {"schemaVersion": "1.1.0", "domain": "temporal",
               "rules": [{"id": "A", "domain": "temporal"}],
               "conflicts": [], "rescues": []}
    once, c1 = migrate_payload(payload)
    twice, c2 = migrate_payload(once)
    assert c1["rules"] >= 1
    assert c2["rules"] == 0                      # 幂等
    assert twice == once


def test_cli_dry_run_does_not_touch_files():
    """dry-run 不写盘；--write 只写 .migrated 副本（原文件不动）。"""
    before = open("knowledge/rules/temporal/rules.json", encoding="utf-8").read()
    r = subprocess.run([sys.executable, "tools/migrate_knowledge.py"],
                       capture_output=True, encoding="utf-8", errors="replace",
                       env={"PATH": os.environ.get("PATH", ""),
                            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
                            "PYTHONIOENCODING": "utf-8"},
                       cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    assert r.returncode == 0
    assert open("knowledge/rules/temporal/rules.json", encoding="utf-8").read() == before
    assert not os.path.exists("knowledge/rules/temporal/rules.migrated.json")
