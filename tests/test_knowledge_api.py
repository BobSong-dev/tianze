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


def test_dashboard_endpoints():
    """M19 Dashboard 数据端点：funnel/coverage-audit/rule-audit/release。"""
    fn = client.get("/api/v1/knowledge/funnel").json()
    assert fn["funnel"]["executable"] == 216
    assert fn["funnel"]["sources"] == 8 and fn["funnel"]["candidates"] == 556
    cov = client.get("/api/v1/knowledge/coverage-audit").json()
    assert cov["ruleCount"] == 216
    ra = client.get("/api/v1/knowledge/rule-audit").json()
    assert ra["ruleCount"] == 20
    rel = client.get("/api/v1/knowledge/release").json()
    assert rel["metadata"]["counts"]["executableRules"] == 216
    # qualitySummary 可能 stale（门内测试运行时刻），只验结构；freshness 归 release_check
    assert "allPass" in rel["qualitySummary"]


def test_evaluation_compare_endpoint():
    r = client.get("/api/v1/knowledge/evaluation-compare")
    assert r.status_code == 200
    d = r.json()
    assert d["entryCount"] >= 1
    assert all("regressionAgainstPrevious" in c for c in d["comparisons"])
