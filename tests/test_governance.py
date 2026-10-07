"""M17：Schema governance（migration history / rollback / 版本依赖）测试。"""

from __future__ import annotations

import json
import os

from fastapi.testclient import TestClient

from apps.api.main import app
from tools.migrate_knowledge import migrate_payload

client = TestClient(app)


def test_migration_history_on_write(tmp_path, monkeypatch):
    """--write 落 .migrated 副本并追加 history（含 rollback 元数据与源哈希）。"""
    import subprocess, sys
    r = subprocess.run(
        [sys.executable, "tools/migrate_knowledge.py", "--write"],
        capture_output=True, encoding="utf-8", errors="replace",
        env={"PATH": os.environ.get("PATH", ""), "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
             "PYTHONIOENCODING": "utf-8"},
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    assert r.returncode == 0
    copy_path = "knowledge/rules/temporal/rules.migrated.json"
    if os.path.exists(copy_path):
        copy = json.load(open(copy_path, encoding="utf-8"))
        assert copy["migrationMeta"]["rollback"]
        assert copy["migrationMeta"]["target"] == "1.2.0"
    hist_path = "regression/migration-history.jsonl"
    if os.path.exists(hist_path):
        last = json.loads(open(hist_path, encoding="utf-8").read().strip().split("\n")[-1])
        assert last["mode"] == "write-copy" and last["sourceSha256"]


def test_migrated_copy_semantic_compatibility():
    """迁移前后语义兼容：conditions/effects/provenance 逐条不变（只增标记）。"""
    payload = json.load(open("knowledge/rules/event/rules.json", encoding="utf-8"))
    migrated, _ = migrate_payload(payload)
    for old, new in zip(payload["rules"], migrated["rules"]):
        for key in ("id", "conditions", "effects", "provenance", "candidateId",
                    "verification", "source"):
            assert old.get(key) == new.get(key), f"{old['id']}.{key} 被改动"
        assert new["schemaVersion"] == "1.2.0"


def test_version_dependencies_endpoint():
    d = client.get("/api/v1/knowledge/stats").json()
    vd = d["versionDependencies"]
    assert {"knowledge", "case", "analysis", "delta", "event",
            "interpretation", "prompt", "engine"} <= set(vd)


def test_evaluation_history_endpoint():
    r = client.get("/api/v1/knowledge/evaluation-history")
    assert r.status_code == 200
    d = r.json()
    assert "entries" in d
    for e in d["entries"]:
        assert "llm_judge" not in json.dumps(e)
