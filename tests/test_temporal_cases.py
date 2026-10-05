"""M13：TemporalCaseReference 解析与三层分离测试。"""

from __future__ import annotations

import json
import os

import pytest

from tools.parse_temporal_cases import gz_index, parse_dayun_field, parse_mentions
from tianze.knowledge.temporal_cases import (
    HistoricalClaim, SourceTemporalAnalysis, TemporalCaseReference,
    TianzeTemporalAnalysis, TEMPORAL_CASE_SCHEMA_VERSION,
)

_REFS_PATH = "knowledge/normalized/cases/temporal_refs.json"


# ---------- 单元：干支工具 ----------

def test_gz_index_valid_invalid():
    assert gz_index("甲子") == 0
    assert gz_index("乙丑") == 1
    assert gz_index("癸亥") == 59
    assert gz_index("甲丑") is None   # 干支奇偶不合，不存在于六十甲子
    assert gz_index("乙午") is None
    assert gz_index("XX") is None


# ---------- 单元：大运序列解析 ----------

def test_parse_dayun_forward():
    entries, consistent, direction, residual = parse_dayun_field("19乙卯 29甲寅 39癸丑 49壬子〕")
    assert [(e.age, e.gan_zhi) for e in entries] == [(19, "乙卯"), (29, "甲寅"), (39, "癸丑"), (49, "壬子")]
    assert consistent is True and direction == "backward"
    assert residual  # 残文（〕）诚实保留


def test_parse_dayun_backward_separator():
    entries, consistent, direction, _ = parse_dayun_field("21戊午、31丁巳、41丙辰、51乙卯〕")
    assert consistent is True and direction == "backward"


def test_parse_dayun_inconsistent():
    entries, consistent, direction, _ = parse_dayun_field("21辛未 31壬申 41乙酉")
    # 辛未→壬申 +1，壬申→乙酉 +11：方向不统一 → 不一致
    assert consistent is False and direction is None


def test_parse_dayun_not_recorded():
    entries, consistent, direction, residual = parse_dayun_field("原文未载")
    assert entries == [] and consistent is None and residual == "原文未载"


def test_parse_dayun_empty():
    assert parse_dayun_field(None) == ([], None, None, None)
    assert parse_dayun_field("") == ([], None, None, None)


# ---------- 单元：提及解析 ----------

def test_parse_mentions_luck_annual_partial():
    events = [{"text": "行辛亥运，辛酉年，冲合阳刃而亡身。", "claimType": "HISTORICAL_CLAIM"},
              {"text": "早年午运最佳；后运不得地。", "claimType": "AUTHOR_INTERPRETATION"}]
    mentions, claims = parse_mentions(events)
    kinds = [(m.kind, m.gan_zhi, m.partial_gz) for m in mentions]
    assert ("luck", "辛亥", None) in kinds
    assert ("annual", "辛酉", None) in kinds
    assert ("luck", None, "午") in kinds          # 单支运
    assert all(m.gan_zhi is None or gz_index(m.gan_zhi) is not None for m in mentions)
    assert len(claims) == 2                        # 两条真实事件 → claim


def test_parse_mentions_dayun_field_not_claim():
    """大运字段文本只产生提及，不产生 historical claim。"""
    events = []
    mentions, claims = parse_mentions(events, dayun_text="乙卯、甲寅运；流年戊寅")
    assert any(m.kind == "luck" for m in mentions)
    assert any(m.kind == "annual" and m.gan_zhi == "戊寅" for m in mentions)
    assert claims == []


# ---------- 集成：全量产物 ----------

@pytest.fixture(scope="module")
def refs_data():
    assert os.path.exists(_REFS_PATH), "先运行 tools/parse_temporal_cases.py"
    return json.load(open(_REFS_PATH, encoding="utf-8"))


def test_total_cases(refs_data):
    assert refs_data["count"] == 1147
    assert refs_data["verification"]["status"] == "MACHINE_EXTRACTED"
    assert refs_data["verification"]["sourceChecked"] is False


def test_three_layer_separation(refs_data):
    """三层分离：sourceTempAnalysis 与 tianzeTemporal 独立；claims 全部是 claim 类型。"""
    for c in refs_data["cases"]:
        assert set(c.keys()) >= {"caseId", "book", "sourceTemporal", "tianzeTemporal", "historicalClaims"}
        tta = c["tianzeTemporal"]
        if not tta["computed"]:
            assert tta["notComputedReason"], "未计算必须给出原因（不编造）"
        for cl in c["historicalClaims"]:
            assert cl["claimType"] in ("AUTHOR_INTERPRETATION", "HISTORICAL_CLAIM", "COMPILER_NOTE")


def test_dayun_consistency_stats(refs_data):
    """序列一致性统计与逐条记录一致；不一致的样本不能被静默丢弃。"""
    stats = json.load(open("knowledge/normalized/cases/temporal_refs_stats.json", encoding="utf-8"))
    n_consistent = sum(1 for c in refs_data["cases"]
                       if c["sourceTemporal"].get("dayunSequenceConsistent") is True)
    n_inconsistent = sum(1 for c in refs_data["cases"]
                         if c["sourceTemporal"].get("dayunSequenceConsistent") is False)
    assert stats["dayunConsistent"] == n_consistent
    assert stats["dayunInconsistent"] == n_inconsistent
    assert stats["dayunInconsistent"] > 0  # 原书噪声必须如实呈现


def test_no_fortune_in_refs(refs_data):
    """产物不含引擎吉凶断语（原书历史断言除外——那是引用，不是引擎输出）。"""
    for c in refs_data["cases"]:
        src = json.dumps(c["sourceTemporal"], ensure_ascii=False)
        tta = json.dumps(c["tianzeTemporal"], ensure_ascii=False)
        for banned in ("发财", "大凶", "必有灾"):
            assert banned not in tta


def test_schema_roundtrip():
    """TemporalCaseReference 模型可完整往返序列化。"""
    ref = TemporalCaseReference(
        case_id="CASE-TEST-01",
        book="测试书",
        source_temporal=SourceTemporalAnalysis(
            unparsed_dayun_text="原文未载",
        ),
        tianze_temporal=TianzeTemporalAnalysis(
            computed=False,
            not_computed_reason="缺出生信息",
        ),
        historical_claims=[HistoricalClaim(text="卒于丁丑年。")],
    )
    blob = ref.model_dump_json(by_alias=True, exclude_none=True)
    back = TemporalCaseReference.model_validate_json(blob)
    assert back.case_id == ref.case_id
    assert back.schema_version == TEMPORAL_CASE_SCHEMA_VERSION
