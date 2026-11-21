"""M13：Temporal Regression 门禁测试（对比已提交 baseline，BREAKING 即失败）。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.temporal_regression import BASELINE, compute_snapshots, compare, PROBES


@pytest.fixture(scope="module")
def current():
    return compute_snapshots()


@pytest.mark.skipif(not BASELINE.exists(), reason="temporal baseline 未生成")
def test_no_breaking_against_baseline(current):
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    result = compare(baseline, current)
    assert result["severityCounts"].get("BREAKING", 0) == 0, (
        "岁运 BREAKING 变化（起运/大运序列/流月/流日）："
        + json.dumps([c for c in result["changedProbes"] if c["severity"] == "BREAKING"],
                     ensure_ascii=False)[:2000]
    )


def test_probe_coverage(current):
    """探针覆盖 男女×顺逆、立春前后、晚子时、闰日。"""
    assert len(current) == len(PROBES) == 6
    by = {s["probe"]: s for s in current}
    assert by["m_1984_0205"]["luck"]["forward"] is True    # 阳男顺排
    assert by["f_1983_0215"]["luck"]["forward"] is True    # 阴女顺排
    assert by["m_2003_0818"]["luck"]["forward"] is False   # 阴男逆排
    assert by["f_1990_0615"]["luck"]["forward"] is False   # 阳女逆排
    assert by["m_1976_0130"]["luck"]["forward"] is False   # 立春前生（乙卯年阴男逆排）


def test_month_sequence_shape(current):
    for s in current:
        months = s["months_2026"]
        assert len(months) == 12
        assert months[0]["gz"] == "庚寅" and months[0]["jie"] == "立春"
        assert months[11]["gz"].endswith("丑")
        # 干支指数连续（月序 +1）
        from tianze.ganzhi.tables import STEMS, BRANCHES
        for a, b in zip(months, months[1:]):
            si = (STEMS.index(b["gz"][0]) - STEMS.index(a["gz"][0])) % 10
            bi = (BRANCHES.index(b["gz"][1]) - BRANCHES.index(a["gz"][1])) % 12
            assert (si, bi) == (1, 1)


def test_day_probe_anchor(current):
    """流日探针 2026-03-01：与 JDN 公式一致（独立锚点 1949-10-01=甲子）。"""
    from tianze.analysis.temporal_extended import day_pillar_for_jdn, gregorian_to_jdn
    jdn = gregorian_to_jdn(2026, 3, 1)
    assert day_pillar_for_jdn(jdn) == ("甲", "戌")


def test_delta_and_rules_present(current):
    for s in current:
        assert s["delta"] and s["delta"]["items"], "聚焦 Delta 不应为空"
        assert s["delta"]["deltaSchemaVersion"] == "1.0.0"
        matched_any = any(a["rules"] for a in s["annuals"])
        assert matched_any, "关键流年至少应触发 TR-SPZY-28（流年即太岁）"


def test_compare_detects_synthetic_breaking(current):
    """自审：人为改动 baseline 后 compare 必须报 BREAKING（工具有效性验证）。"""
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    tampered = json.loads(json.dumps(baseline))
    tampered["snapshots"][0]["luck"]["forward"] = not tampered["snapshots"][0]["luck"]["forward"]
    tampered["snapshots"][0]["months_2026"][0]["gz"] = "戊寅"
    result = compare(tampered, current)
    fields = {c["field"] for c in result["changedProbes"]}
    assert "luck.forward" in fields and "months" in fields
    assert result["severityCounts"].get("BREAKING", 0) >= 1


def test_three_harmony_positions_deterministic():
    """回归防护：三合补齐 positions 曾受 PYTHONHASHSEED 影响（集合迭代序）。
    以多 seed 模拟进程差异，验证输出排序确定。"""
    import subprocess
    import sys
    code = (
        "from tianze.analysis.temporal import analyze_temporal;"
        "r = analyze_temporal(natal_stems=['甲','丙','戊','庚'],"
        "natal_branches=['子','辰','午','寅'], day_master='戊',"
        "luck_stem='壬', luck_branch='戌');"
        "print([x.positions for x in r.relations if x.kind == 'three_harmony_completed'])"
    )
    outs = set()
    for seed in ("0", "1", "42", "999"):
        env = {**__import__("os").environ, "PYTHONHASHSEED": seed,
               "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
        res = subprocess.run([sys.executable, "-c", code], capture_output=True,
                             encoding="utf-8", env=env, cwd=str(BASELINE.parents[2]), check=True)
        assert res.stdout.strip() and res.stdout.strip() != "[]", res.stderr
        outs.add(res.stdout.strip())
    assert len(outs) == 1, f"三合 positions 随哈希种子变化: {outs}"
