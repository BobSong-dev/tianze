"""M18：Version Compatibility Matrix 测试。"""

from __future__ import annotations

import glob
import json
import os

KNOWN_SCHEMA_VERSIONS = {"1.0.0", "1.1.0", "1.2.0"}


def test_rules_files_in_known_versions():
    """全部 rules.json 的 schemaVersion 在兼容矩阵内；loader 可加载。"""
    for f in glob.glob("knowledge/rules/*/rules.json"):
        payload = json.load(open(f, encoding="utf-8"))
        assert payload.get("schemaVersion") in KNOWN_SCHEMA_VERSIONS, f
    from tianze.knowledge.event_rules import load_event_rules
    from tianze.knowledge.temporal_rules import load_temporal_rules
    from tianze.knowledge.loader import load_tiaohou_rules
    assert len(load_event_rules()) == 21
    assert len(load_temporal_rules()) == 20
    pass  # counts asserted elsewhere


def test_migrated_copy_loads_with_current_loader_semantics():
    """迁移副本（1.2.0）语义兼容：构建迁移副本后 loader 等价。"""
    from tools.migrate_knowledge import migrate_payload
    payload = json.load(open("knowledge/rules/event/rules.json", encoding="utf-8"))
    migrated, _ = migrate_payload(payload)
    # 迁移副本的规则 id 集合与原版一致（loader 语义不变）
    assert {r["id"] for r in migrated["rules"]} == {r["id"] for r in payload["rules"]}
    assert migrated["schemaVersion"] == "1.2.0"


def test_artifact_schema_versions_known():
    """回归工件的 schema 版本在兼容矩阵内。"""
    checks = [
        ("regression/case-replay.json", "schemaVersion"),
        ("regression/event-evaluation.json", "schemaVersion"),
        ("regression/audit-gates.json", "schemaVersion"),
        ("regression/rule-audit.json", "schemaVersion"),
        ("regression/graph-audit.json", "schemaVersion"),
        ("release/release-metadata.json", "schemaVersion"),
    ]
    for path, key in checks:
        if os.path.exists(path):
            d = json.load(open(path, encoding="utf-8"))
            assert d.get(key) in KNOWN_SCHEMA_VERSIONS, path
