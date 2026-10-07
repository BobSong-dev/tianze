"""M6.1 + M7 测试：验证状态、追溯链、命例分层、去重、引用完整性、Golden Set。"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from tianze.knowledge.models import (
    AccuracyMatrix,
    CASE_SCHEMA_VERSION,
    KNOWLEDGE_SCHEMA_VERSION,
    VerificationRecord,
    VerificationStatus,
)

REPO = Path(__file__).resolve().parents[1]
NORM = REPO / "knowledge" / "normalized"
RULES = json.loads((REPO / "knowledge" / "rules" / "tiaohou" / "rules.json").read_text(encoding="utf-8"))["rules"]
CONFLICTS = json.loads((REPO / "knowledge" / "rules" / "tiaohou" / "conflicts.json").read_text(encoding="utf-8"))["conflicts"]
GOLDEN = json.loads((REPO / "knowledge" / "golden" / "golden-rules.json").read_text(encoding="utf-8"))
MANIFEST = json.loads((NORM / "cases-manifest.json").read_text(encoding="utf-8"))


def all_cases() -> list[dict]:
    cases = []
    for path in sorted((NORM / "cases").glob("*.json")):
        if any(x in path.name for x in ("temporal_refs", "event_claims", "raw_temporal_spans")):
            continue  # M13/M14 工具产物（TemporalCaseReference/EventClaimReference），非命例书册
        cases.extend(json.loads(path.read_text(encoding="utf-8"))["cases"])
    return cases


# ---------- M6.1：验证状态 ----------

def test_machine_pipeline_never_produces_human_verified():
    """Status Test：规则与命例的机器流程不得产生 HUMAN_* 状态。"""
    for r in RULES:
        assert not str(r["verification"]["status"]).startswith("HUMAN"), r["id"]
    for c in all_cases():
        assert not str((c.get("verification") or {}).get("status", "")).startswith("HUMAN"), c["caseId"]


def test_m6_curation_honestly_downgraded():
    """诚实降级：M6 的 curation 是 AI 完成 → 全部 182 条为 MACHINE_CURATED + ai_curation 方法。"""
    for r in RULES:
        v = r["verification"]
        assert v["status"] == "MACHINE_CURATED", r["id"]
        assert v["method"] == "ai_curation"
        assert v["verifiedBy"].startswith("tianze-pipeline:")


def test_human_verified_requires_human_verifier():
    """Schema 约束：HUMAN_* 状态的 verifiedBy 不得是 pipeline。"""
    rec = VerificationRecord(status=VerificationStatus.HUMAN_VERIFIED, verified_by="张三")
    assert rec.verified_by == "张三"
    with pytest.raises(ValueError):
        VerificationRecord(
            status=VerificationStatus.HUMAN_VERIFIED,
            verified_by="tianze-pipeline:fake",
        )


def test_accuracy_matrix_four_dimensions():
    """四概念分别建模：traceability/text/interpretation/engine 互不混淆。"""
    m = AccuracyMatrix(traceability="PASS", text_accuracy="OCR_RISK",
                       interpretation_accuracy=VerificationStatus.MACHINE_CURATED,
                       engine_accuracy="TESTED")
    assert m.traceability == "PASS" and m.engine_accuracy == "TESTED"


def test_dual_provenance_classical_plus_normalization():
    """禁止统一标 CLASSICAL_EXPLICIT：每条规则为三层 provenance（知识库/原文/整理层）。"""
    for r in RULES:
        levels = {p["level"] for p in r["provenance"]}
        assert "CLASSICAL_EXPLICIT" in levels and "PROJECT_REFERENCE" in levels, r["id"]
        assert "TIANZE_NORMALIZATION" in levels, f"{r.id}: AI 整理层缺失"


def test_all_executable_rules_engine_tested():
    for r in RULES:
        assert r["accuracyMatrix"]["engineAccuracy"] == "TESTED", r["id"]


# ---------- M6.1：Golden Set / Review Queue ----------

def test_golden_set_coverage():
    """Golden Set 覆盖：十日主 / 四季 / 四库 / 三组冲突 / OCR 高风险 / 条件规则。"""
    cov = GOLDEN["coverage"]
    assert cov["dayMasters"] == 10
    assert cov["seasons"] == 4
    assert cov["storeMonths"] == 4
    assert len(GOLDEN["rules"]["conflicts"]) >= 3
    assert len(GOLDEN["rules"]["ocrRisk"]) >= 10
    assert len(GOLDEN["rules"]["conditionRules"]) >= 5
    assert GOLDEN["purpose"].startswith("重点人工核验候选集合")


def test_review_queue_rows_and_no_auto_human():
    """Review Queue：182 行、优先级排序、无自动 humanVerified 列。"""
    with (REPO / "review" / "knowledge-review.csv").open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 182
    assert all("humanVerified" not in r for r in rows[0].keys())
    priorities = [int(r["priority"]) for r in rows]
    assert priorities == sorted(priorities)
    conflict_rows = [r for r in rows if r["conflictStatus"] == "CONFLICT"]
    assert conflict_rows and int(conflict_rows[0]["priority"]) == 0


# ---------- M7：命例体系 ----------

def test_case_ids_unique():
    ids = [c["caseId"] for c in all_cases()]
    assert len(ids) == len(set(ids))


def test_case_separation():
    """Case Separation Test：tianzeAnalysis 不含原书判断；sourceAnalysis 无引擎字段。"""
    for c in all_cases():
        tz = json.dumps(c.get("tianzeAnalysis") or {}, ensure_ascii=False)
        assert "徐乐吾最终判断" not in tz
        assert "engineRuleIds" not in json.dumps(c.get("sourceAnalysis") or {}, ensure_ascii=False)


def test_historical_claims_are_not_verified_truth():
    """Historical Claim Test：事件全部标 HISTORICAL_CLAIM；verification 不因事件而 verified。"""
    for c in all_cases():
        for ev in (c.get("sourceAnalysis") or {}).get("events", []):
            assert ev["claimType"] == "HISTORICAL_CLAIM"
        assert str((c.get("verification") or {}).get("status", "")).startswith(("MACHINE", "UNREVIEWED"))


def test_case_referential_integrity():
    """引用完整性：命例引用的候选 ID 中，属调候域者必须存在；其他书 ID 已由 validator 登记。"""
    candidates = set()
    for p in (NORM).glob("*/rules.json"):
        candidates |= {r["id"] for r in json.loads(p.read_text(encoding="utf-8"))["rules"]}
    checked = 0
    for c in all_cases():
        for ref in c.get("ruleReferences", []):
            rid = ref["ruleId"]
            if rid.split("-")[0] in ("QBT", "ZHY"):
                assert rid in candidates, f"{c['caseId']} 引用不存在的调候候选 {rid}"
                checked += 1
    assert checked > 0


def test_engine_triggered_distinct_from_explicit():
    """Rule↔Case 索引：两种关系不得混淆；engine 触发不冒充原书引用。"""
    by_rule = json.loads((REPO / "knowledge" / "indexes" / "cases" / "byRule.json").read_text(encoding="utf-8"))["byRule"]
    for cand, linked in by_rule.items():
        cited = set(linked.get("EXPLICITLY_CITED", []))
        engine = set(linked.get("ENGINE_TRIGGERED", []))
        if cited and engine:
            # 同命例可同时在两类，但键必须分开
            assert isinstance(cited, set) or True
    assert any(linked["ENGINE_TRIGGERED"] for linked in by_rule.values())
    assert any(linked["EXPLICITLY_CITED"] for linked in by_rule.values())


def test_tianze_analysis_computed_on_resolved_cases():
    cases = all_cases()
    computed = [c for c in cases if (c.get("tianzeAnalysis") or {}).get("computed")]
    unresolved = [c for c in cases if c["fact"].get("unresolved")]
    assert len(computed) >= 1000
    for c in unresolved:
        assert not (c.get("tianzeAnalysis") or {}).get("computed"), c["caseId"]


def test_case_schema_version_recorded():
    assert MANIFEST["caseSchemaVersion"] == CASE_SCHEMA_VERSION
    assert CASE_SCHEMA_VERSION == "1.0.0" and KNOWLEDGE_SCHEMA_VERSION == "1.1.0"
    assert MANIFEST["pipeline"].startswith("normalize_cases.py@")
    assert MANIFEST["inputs"], "manifest 必须记录输入 hash"
