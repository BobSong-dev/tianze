"""M16：Knowledge Rule Explorer / Review Queue API 测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_knowledge_stats():
    r = client.get("/api/v1/knowledge/stats")
    assert r.status_code == 200
    d = r.json()
    assert d["executableTotal"] == 216
    assert d["executableByDomain"] == {"event": 20, "temporal": 14, "tiaohou": 182}


def test_knowledge_rules_with_conflict_neighbors():
    r = client.get("/api/v1/knowledge/rules")
    assert r.status_code == 200
    d = r.json()
    by_id = {x["id"]: x for x in d["rules"]}
    assert len(d["rules"]) == 216
    car3 = by_id["EV-CAR-03"]
    assert any(c["edgeType"] == "rescues" for c in car3["conflictNeighbors"])
    guan = by_id["TR-SP-02"]
    assert guan["domain"] == "temporal"


def test_knowledge_graph_and_rescues():
    g = client.get("/api/v1/knowledge/graph").json()
    assert g["nodeCount"] == 222 and g["edgeCount"] == 16
    r = client.get("/api/v1/knowledge/rescues").json()
    assert r["count"] == 6


def test_knowledge_review_queue_readonly():
    r = client.get("/api/v1/knowledge/review-queue")
    assert r.status_code == 200
    d = r.json()
    assert d["count"] > 0
    assert all(i["priority"] in ("P1", "P2", "P3") for i in d["items"])
    assert all(i.get("reviewNote") is None for i in d["items"])  # 不伪造人工审核
    # 排序：P1 在前
    priorities = [i["priority"] for i in d["items"]]
    assert priorities == sorted(priorities, key=lambda p: {"P1": 0, "P2": 1, "P3": 2}[p])
