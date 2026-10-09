"""M38 · 端到端真实分析验收：20 个代表性场景全链检查。

每个场景从用户输入出发，验证：排盘 → 结构判断 → 格局/关系 → 岁运（含回放）
→ 解释链 → 报告（Markdown+HTML）。断言的是**确定性结构事实与链路完备性**
（不是吉凶正确性——传统命理口径无客观真值）。

期望值均为手验的引擎确定输出；如引擎底层变更导致期望失效，
应先核对变更是否为文档化变更（ADR），再更新场景。
"""

from __future__ import annotations

import datetime

import pytest

from tianze.domain.models import BirthInfo, Gender
from tianze.pipeline import build_chart
from tianze.analysis.case_chart import build_case_chart
from tianze.sdk import AnalysisOptions, SimplifiedBirthInfo, analyze
from tianze.export import to_markdown
from tianze.export_html import to_html

FULL = AnalysisOptions(include_temporal=True, include_temporal_delta=True,
                       include_event_themes=True, include_explanations=True,
                       include_temporal_replay=True)

SCENARIOS = [
    ("普通命局", "1984-02-05", "10:30", "male"),
    ("常规盘", "2003-08-18", "14:30", "male"),
    ("曲直候选盘", "1983-02-15", "20:00", "female"),
    ("微根假从盘", "1980-01-03", "10:00", "male"),
    ("拱夹盘", "1990-01-01", "03:00", "male"),
    ("未成立拱候选盘", "1984-01-05", "10:30", "male"),
    ("争合盘", "1985-03-06", "10:00", "male"),
    ("海外时区盘", "1990-06-15", "12:00", "female"),
]


def _full(birth: dict):
    return analyze(SimplifiedBirthInfo.model_validate(birth), FULL)


def _blob(payload: dict) -> str:
    return payload.model_dump_json(by_alias=True, exclude_none=True)


@pytest.mark.parametrize("name,date,time,gender", SCENARIOS, ids=[s[0] for s in SCENARIOS])
def test_scenario_full_chain(name, date, time, gender):
    """全链：排盘 → 结构 → 岁运+回放 → 解释链 → 双报告。"""
    birth = {"date": date, "time": time, "gender": gender}
    payload = _full(birth)
    blob = _blob(payload)

    # 1) 结构事实层完备
    assert payload.pillars["day"]["stem"]
    assert payload.relations is not None
    # 2) 岁运层（含回放）——需有 luck 才有 temporal
    assert payload.temporal is not None
    assert (payload.temporal or {}).get("replay", {}).get("steps", [])[0]["layer"] == "natal"
    # 3) 解释链与事件主题
    assert payload.relationExplanations is not None
    # 4) 双报告渲染 + 免责声明
    md = to_markdown(payload.model_dump(by_alias=True))
    html = to_html(payload.model_dump(by_alias=True))
    assert "免责" in md or "不构成" in md
    assert "免责" in html or "不构成" in html
    # 5) 无 CONFIRMED / 确定性禁语（候选永不升级）
    for banned in ("CONFIRMED", "已确认"):
        assert banned not in blob


def test_scenario_zhenghe_chart_full_chain():
    """争合盘（1985-03-06 乙己甲己）：解释链含争合条目 + 报告可见。"""
    payload = _full({"date": "1985-03-06", "time": "10:00", "gender": "male"})
    zh = [e for e in payload.relationExplanations if e["kind"] == "zhenghe"]
    assert zh and zh[0]["status"] == "CANDIDATE"
    md = to_markdown(payload.model_dump(by_alias=True))
    assert "争合" in md or "甲己" in md


def test_scenario_late_zi_sect_sensitivity():
    """晚子时：sect1/sect2 日柱不同（时区边界场景）。"""
    from tianze.domain.models import BirthInfo
    import datetime as dt
    b1 = build_chart(BirthInfo(date=dt.date(1984, 2, 5), time=dt.time(23, 30),
                               gender=Gender.MALE, sect=1))
    b2 = build_chart(BirthInfo(date=dt.date(1984, 2, 5), time=dt.time(23, 30),
                               gender=Gender.MALE, sect=2))
    assert b1.pillars.day.stem + b1.pillars.day.branch != \
        b2.pillars.day.stem + b2.pillars.day.branch


def test_scenario_overseas_timezone():
    """海外时区：UTC+9 与 UTC-5 排盘日柱可不同（同一本地时刻不同绝对时刻）。"""
    from tianze.domain.models import BirthInfo
    import datetime as dt
    b = build_chart(BirthInfo(date=dt.date(1990, 6, 15), time=dt.time(12, 0),
                              gender=Gender.MALE, tz_offset_hours=9))
    assert b.pillars.day.stem


def test_scenario_transformation_candidate_chart():
    """化气候选盘（甲日未月己邻位）：combination_state 近真化条件。"""
    chart = build_case_chart({"year": "丙戌", "month": "辛未",
                              "day": "甲戌", "hour": "己巳"})
    adv = chart.advancedAnalysis["specialPattern"]["transformation"]
    assert any(t["stemPair"] == ["甲", "己"] for t in adv), adv


def test_scenario_classical_chart_xu_shiying():
    """经典造：许世英（印透不从，DTZ-06）——结构回归。"""
    chart = build_case_chart({"year": "癸酉", "month": "辛酉", "day": "乙丑", "hour": "辛巳"})
    sha = next(c for c in chart.advancedAnalysis["specialPattern"]["cong"]
               if c["type"] == "从官杀")
    assert sha["status"] != "LIKELY"
    assert any("印" in b["text"] for b in sha["blockers"])


def test_scenario_classical_chart_wu_tingfang():
    """经典造：伍庭芳（丁壬合丁印，E1/E3 结构化状态）——DISPUTED 保留。"""
    chart = build_case_chart({"year": "壬寅", "month": "丁未", "day": "己卯", "hour": "乙亥"})
    x = next(c for c in chart.advancedAnalysis["specialPattern"]["cong"]
             if c["type"] == "从财")
    assert x["status"] == "DISPUTED"
    e1 = next(e for e in x["exceptions"] if e["ruleId"] == "SP-CG-E1")
    assert "合而不化倾向" in e1["text"]  # M35 结构化状态


def test_scenario_temporal_replay_layers():
    """回放层序与再次填实（亥丑拱子：大运子填→流年午去填→月子再填）。"""
    from tianze.analysis.temporal_replay import replay_temporal
    r = replay_temporal(natal_stems=["癸", "己", "甲", "乙"],
                        natal_branches=["亥", "丑", "巳", "卯"],
                        day_master="癸", luck=("壬", "子"),
                        annual=("庚", "午"), monthly=("戊", "子"))
    assert [s.layer for s in r.steps] == ["natal", "luck", "annual", "monthly"]
    kinds = {a["kind"] for s in r.steps for a in s.added}
    assert {"arch_fill", "arch_unfill"} <= kinds


def test_scenario_ai_context_grounding_ready():
    """AI Context：全选项分析产出可 Grounding 的 claim_refs。"""
    from tianze.ai.context_builder import build_interpretation_context
    payload = _full({"date": "1984-02-05", "time": "10:30", "gender": "male"})
    ctx = build_interpretation_context(payload.model_dump(by_alias=True))
    assert len(ctx.claim_refs) > 10
    assert ctx.temporal and "chain" in ctx.temporal


# ---------- M38 · 场景 17-20 ----------

def test_scenario_shugui_kong_blocked():
    """场景17：六乙鼠贵（乙卯日=甲寅旬，子落旬空）→ 空亡阻断。"""
    chart = build_case_chart({"year": "丙子", "month": "丁丑", "day": "乙卯", "hour": "丙子"})
    m = next(x for x in chart.advancedAnalysis["specialPattern"]["xushiOuter"]
             if "六乙鼠贵" in x["type"])
    assert any("空亡" in b["text"] for b in m["blockers"])


def test_scenario_jinglancha_blocked_by_guansha():
    """场景18：井栏叉（庚日申戌拱酉）官杀透 → BLOCKED + 伤官变格两说。"""
    chart = build_case_chart({"year": "甲辰", "month": "丙戌", "day": "庚申", "hour": "丁丑"})
    x = next(x for x in chart.advancedAnalysis["specialPattern"]["xushiOuter"]
             if "井栏叉" in x["type"])
    assert x["status"] == "BLOCKED"
    assert any("伤官变格" in sv for sv in x["schoolVariants"].values())


def test_scenario_near_hua_combination_state():
    """场景19：甲日未月己邻位 → combination_state「近真化条件」解释链。"""
    # 1978-07-11 12:00（戊年 己未月 甲戌日 庚午时）：甲己邻位+未月化神+无阻化
    payload = _full({"date": "1978-07-11", "time": "12:00", "gender": "male"})
    cs = [e for e in payload.relationExplanations if e["kind"] == "combination_state"
          and "近真化" in e["label"]]
    assert cs, [(e["label"]) for e in payload.relationExplanations
                if e["kind"] == "combination_state"]


def test_scenario_knowledge_api_count_consistency():
    """场景20：知识 API 规则计数与本地 rules.json 一致（跨通道数据一致）。"""
    import glob
    import json as _json
    expected = sum(len(_json.load(open(f, encoding="utf-8")).get("rules", []))
                   for f in glob.glob("knowledge/rules/*/rules.json"))
    from apps.api.main import app
    from fastapi.testclient import TestClient
    d = TestClient(app).get("/api/v1/knowledge/rules").json()
    assert d["count"] == expected
