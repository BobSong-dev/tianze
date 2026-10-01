"""M5 格局引擎测试：取格优先级（R23）/ 禄刃（R24）/ 证据化评估（R25）。"""

from __future__ import annotations

import datetime as dt

from tianze.analysis.pattern import analyze_pattern, derive_pattern_candidates, evaluate_pattern
from tianze.domain.models import BirthInfo, PatternFactor, RuleLevel
from tianze.ganzhi.tables import TenGod
from tianze.pipeline import build_chart

POS4 = ["year", "month", "day", "hour"]


def cands(day_master: str, month_branch: str, stems: list[str | None]):
    return derive_pattern_candidates(day_master, month_branch, stems, POS4)


# ---------- M5.1 取格：十正格 + 关键场景 ----------

def test_zheng_guan_main_qi_transparent():
    """甲日酉月（辛=正官），辛透年干 → 正官格（本气透干）。"""
    cs, notes = cands("甲", "酉", ["辛", "辛", "甲", "癸"])
    assert len(cs) == 1
    c = cs[0]
    assert (c.name, c.ten_god, c.via, c.source_stem) == ("正官格", TenGod.ZHENG_GUAN, "本气透干", "辛")
    assert "透出于年干" in c.evidence[-1] or "透出于月干" in c.evidence[-1]
    assert any("月支酉藏辛（本气）" in e for e in c.evidence)


def test_qi_sha_main_qi_transparent():
    cs, _ = cands("甲", "申", ["庚", "庚", "甲", "壬"])
    assert cs[0].name == "七杀格" and cs[0].ten_god == TenGod.QI_SHA


def test_zheng_cai_and_pian_cai():
    cs, _ = cands("甲", "丑", ["己", "己", "甲", "辛"])
    assert cs[0].name == "正财格" and cs[0].via == "本气透干"
    cs2, _ = cands("甲", "辰", ["戊", "戊", "甲", "壬"])
    assert cs2[0].name == "偏财格" and cs2[0].source_stem == "戊"


def test_yin_patterns():
    cs, _ = cands("甲", "子", ["癸", "癸", "甲", "庚"])
    assert cs[0].name == "正印格"
    cs2, _ = cands("甲", "亥", ["壬", "壬", "甲", "庚"])
    assert cs2[0].name == "偏印格" and cs2[0].source_stem == "壬"


def test_shi_shen_and_shang_guan():
    cs, _ = cands("甲", "巳", ["丙", "丙", "甲", "癸"])
    assert cs[0].name == "食神格"
    cs2, _ = cands("甲", "午", ["丁", "丁", "甲", "庚"])
    assert cs2[0].name == "伤官格"


def test_jian_lu_via_lu_position():
    """甲日寅月：禄位 → 建禄格（不要求本气透干）。"""
    cs, notes = cands("甲", "寅", ["丙", "庚", "甲", "庚"])
    assert len(cs) == 1 and cs[0].name == "建禄格" and cs[0].via == "禄位"
    assert any("临官" in e for e in cs[0].evidence)


def test_yang_ren_via_ren_position():
    """甲日卯月：阳刃 → 阳刃格；并记录阴干无刃口径。"""
    cs, _ = cands("甲", "卯", ["丁", "辛", "甲", "庚"])
    assert len(cs) == 1 and cs[0].name == "阳刃格" and cs[0].via == "阳刃位"
    assert any("阴干无刃" in e for e in cs[0].evidence)


def test_main_qi_not_transparent_middle_qi_transparent():
    """本气不透、余气透：甲日辰月，戊不透、癸透 → 正印格（余气透干）。"""
    cs, _ = cands("甲", "辰", ["癸", "壬", "甲", "癸"])
    assert len(cs) == 1
    assert (cs[0].name, cs[0].via, cs[0].source_stem) == ("正印格", "余气透干", "癸")


def test_middle_and_residual_both_transparent_multi_candidates():
    """中余同时透（巳藏丙庚戊全透）→ 3 个候选按优先级排序，首选评估+冲突记录。"""
    cs, _ = cands("甲", "巳", ["丙", "庚", "甲", "戊"])
    assert [c.name for c in cs] == ["食神格", "七杀格", "偏财格"]
    assert [c.via for c in cs] == ["本气透干", "中气透干", "余气透干"]


def test_nothing_transparent_fallback_to_main_qi():
    """皆不透 → 取月令本气（回退口径）。"""
    cs, _ = cands("甲", "酉", ["丁", "丙", "甲", "丁"])
    assert len(cs) == 1
    assert (cs[0].name, cs[0].via) == ("正官格", "本气不透取本气")


def test_jie_cai_month_no_regular_pattern():
    """乙日寅月：本气甲=劫财、非乙禄刃 → 无正格候选 + note（阴干无刃口径）。"""
    cs, notes = cands("乙", "寅", ["甲", "甲", "乙", "辛"])
    assert cs == []
    assert notes and "不立正格" in notes[0]


def test_yin_stem_ren_not_established():
    """辛日申月：阴刃派或谓刃在申；Tianze 阴干无刃 → 申本气庚=劫财 → 无正格候选。"""
    cs, notes = cands("辛", "申", ["庚", "庚", "辛", "甲"])
    assert cs == []
    assert notes and "不立正格" in notes[0]


def test_yin_day_master_lu_still_jianlu():
    """乙日卯月：卯为乙禄 → 建禄格（阴干有禄、无刃）。"""
    cs, _ = cands("乙", "卯", ["辛", "庚", "乙", "己"])
    assert cs[0].name == "建禄格"


# ---------- M5.2 评估：正官/七杀/财/印/食神/伤官 金标 ----------

def ev(name: str, ten_god_: TenGod, month_branch: str, others: list[tuple[str, str]]):
    cand = next(c for c in _mk_all(name, ten_god_, month_branch))
    return evaluate_pattern(cand, "甲", others)


def _mk_all(name: str, god: TenGod, month_branch: str):
    """构造指定候选（绕过取格，直接评估用）。"""
    from tianze.domain.models import PatternCandidate, Provenance, RuleLevel
    return [PatternCandidate(
        name=name, category="regular", month_branch=month_branch,
        source_stem="?", ten_god=god, via="本气透干", evidence=[],
        provenance=[Provenance(level=RuleLevel.PROJECT_REFERENCE, project="test", concept="test")],
    )]


def test_zheng_guan_evaluation_golden():
    cand = _mk_all("正官格", TenGod.ZHENG_GUAN, "酉")[0]
    # 财+印 → 双支持 → 成立
    r = evaluate_pattern(cand, "甲", [("己", "year"), ("癸", "hour")])
    assert r.status == "成立"
    assert {s.name for s in r.supports} == {"财生官", "印护官"}
    assert r.damages == []
    # 伤官+比肩 → 伤官见官无救 → 受损
    r2 = evaluate_pattern(cand, "甲", [("丁", "year"), ("甲", "hour")])
    assert r2.status == "受损"
    assert r2.damages[0].name == "伤官见官" and r2.rescues == []
    # 伤官+印 → 有救应 → 有瑕（damage 与 rescue 并存）
    r3 = evaluate_pattern(cand, "甲", [("丁", "year"), ("癸", "hour")])
    assert r3.status == "有瑕"
    assert r3.damages[0].rule_id == "PAT-GUAN-D1"
    assert r3.rescues[0].related == ["PAT-GUAN-D1"]


def test_qi_sha_evaluation_golden():
    cand = _mk_all("七杀格", TenGod.QI_SHA, "申")[0]
    # 食神+印 → 双支持但 制化两立 冲突记录 → 成立（无 damage）+ conflict
    r = evaluate_pattern(cand, "甲", [("丙", "year"), ("癸", "hour")])
    assert r.status == "成立"
    assert {s.name for s in r.supports} == {"食神制杀", "杀印相生"}
    assert any(c.name == "制化两立" for c in r.conflicts)
    # 官杀混杂 + 财生杀攻身 → 破格
    r2 = evaluate_pattern(cand, "甲", [("辛", "year"), ("己", "month"), ("甲", "hour")])
    assert r2.status == "破格"
    assert {d.name for d in r2.damages} == {"官杀混杂", "财生杀攻身"}


def test_cai_evaluation_golden():
    cand = _mk_all("正财格", TenGod.ZHENG_CAI, "丑")[0]
    # 比劫夺财无救（食神非官杀，不构成救应）→ 受损
    r = evaluate_pattern(cand, "甲", [("甲", "year"), ("丙", "hour")])
    assert r.status == "受损" and r.damages[0].name == "比劫夺财"
    # 比劫 + 官杀制比劫 → 有瑕
    r2 = evaluate_pattern(cand, "甲", [("甲", "year"), ("辛", "hour")])
    assert r2.status == "有瑕" and r2.rescues[0].name == "官杀制比劫护财"
    # 食神生财 → 成立
    r3 = evaluate_pattern(cand, "甲", [("丙", "year")])
    assert r3.status == "成立" and {s.name for s in r3.supports} == {"食神生财"}


def test_yin_evaluation_golden():
    cand = _mk_all("正印格", TenGod.ZHENG_YIN, "子")[0]
    # 财破印无救 → 受损
    r = evaluate_pattern(cand, "甲", [("己", "year")])
    assert r.status == "受损" and r.damages[0].name == "财破印"
    # 财 + 官杀通关 → 有瑕
    r2 = evaluate_pattern(cand, "甲", [("己", "year"), ("辛", "hour")])
    assert r2.status == "有瑕" and r2.rescues[0].name == "官杀通关化财生印"


def test_shi_shen_rescue_golden():
    cand = _mk_all("食神格", TenGod.SHI_SHEN, "巳")[0]
    # 枭神夺食 + 财制枭 → 有瑕
    r = evaluate_pattern(cand, "甲", [("壬", "year"), ("己", "hour")])
    assert r.status == "有瑕"
    assert r.damages[0].name == "枭神夺食" and r.rescues[0].name == "财能制枭护食"


def test_shang_guan_rescue_golden():
    cand = _mk_all("伤官格", TenGod.SHANG_GUAN, "午")[0]
    r = evaluate_pattern(cand, "甲", [("辛", "year"), ("癸", "hour")])
    assert r.status == "有瑕"
    assert r.damages[0].name == "伤官见官" and r.rescues[0].name == "印制伤"


def test_lu_ren_evaluation_pending():
    """建禄/阳刃：M5.2 v1 未配置评估规则 → 待定（不伪造结论）。"""
    cs, _ = cands("甲", "寅", ["丙", "庚", "甲", "庚"])
    r = evaluate_pattern(cs[0], "甲", [("丙", "year"), ("庚", "month"), ("庚", "hour")])
    assert r.status == "待定" and r.note and "未配置" in r.note


def test_provenance_honesty():
    """无 CLASSICAL_EXPLICIT 伪造：所有 pattern 规则 provenance 为 PROJECT_REFERENCE。"""
    cs, _ = cands("甲", "酉", ["辛", "辛", "甲", "癸"])
    r = evaluate_pattern(cs[0], "甲", [("丁", "year"), ("癸", "hour")])
    for f in [*r.supports, *r.damages, *r.rescues, *r.conflicts]:
        assert f.provenance.level == RuleLevel.PROJECT_REFERENCE
        assert f.provenance.project and "子平真诠" not in (f.provenance.note or "")


# ---------- 集成 ----------

def test_pattern_in_real_chart_1983():
    """癸亥 甲寅 甲戌 甲戌：甲日寅月 → 建禄格候选（待定）。"""
    chart = build_chart(BirthInfo(date=dt.date(1983, 2, 15), time=dt.time(20, 0), gender="female"))
    pa = chart.pattern
    assert pa is not None and pa.candidates[0].name == "建禄格"
    assert pa.evaluation.status == "待定"


def test_pattern_in_real_chart_2003():
    """癸未 庚申 癸亥 己未：申藏庚（正印）透月干 → 正印格；壬=劫财跳过记 note。"""
    chart = build_chart(BirthInfo(date=dt.date(2003, 8, 18), time=dt.time(14, 30), gender="male"))
    pa = chart.pattern
    assert pa.candidates[0].name == "正印格" and pa.candidates[0].via == "本气透干"
    assert pa.primary_index == 0
    assert pa.evaluation.status == "成立"  # 无支持亦无破坏
    assert pa.note and "劫财" in pa.note


def test_pattern_json_shape():
    chart = build_chart(BirthInfo(date=dt.date(1983, 2, 15), time=dt.time(20, 0), gender="female"))
    data = chart.to_json_dict()
    p = data["pattern"]
    assert p["candidates"][0]["name"] == "建禄格"
    assert p["candidates"][0]["provenance"][0]["level"] == "PROJECT_REFERENCE"
    assert p["evaluation"]["status"] == "待定"
    assert data["conventions"]["patternCandidate"] == "R23"
