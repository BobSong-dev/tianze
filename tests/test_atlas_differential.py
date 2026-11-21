"""与 bazi-atlas 引擎（MIT，实跑）的跨引擎差分对拍。

环境依赖：node >= 18 + research/upstream/bazi-atlas（含 lunar-javascript）。
任一缺失 → skip 并留痕（不伪造结果；blocked 原因见 docs/progress 与本文件）。
atlas 输出由 tools/atlas_differential.mjs 生成（仅调用其公开入口 computeBazi）。
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tianze.domain.models import BirthInfo
from tianze.pipeline import build_chart

REPO_ROOT = Path(__file__).resolve().parents[1]
ATLAS_DIR = REPO_ROOT / "research" / "upstream" / "bazi-atlas"
BRIDGE = REPO_ROOT / "tools" / "atlas_differential.mjs"

_node = shutil.which("node")
_atlas_ready = ATLAS_DIR.exists() and (ATLAS_DIR / "engine.mjs").exists()

pytestmark = pytest.mark.skipif(
    _node is None or not _atlas_ready,
    reason="blocked: node 或 research/upstream/bazi-atlas 不可用（差分对拍环境缺失，不伪造结果）",
)


def atlas_pillars() -> dict[str, dict]:
    proc = subprocess.run(
        [_node, str(BRIDGE)], capture_output=True, encoding="utf-8", timeout=120, check=True,
        cwd=str(REPO_ROOT),
    )
    return {c["name"]: c["atlasPillars"] for c in json.loads(proc.stdout)}


def tianze_pillars(birth: BirthInfo) -> dict:
    chart = build_chart(birth)
    p = chart.pillars
    return {
        "year": p.year.stem + p.year.branch,
        "month": p.month.stem + p.month.branch,
        "day": p.day.stem + p.day.branch,
        "hour": (p.hour.stem + p.hour.branch) if p.hour else None,
    }


BIRTHS = {
    "plan_example_2003": {"date": "2003-08-18", "time": "14:30", "gender": "male"},
    "basic_1986": {"date": "1986-04-21", "time": "10:00", "gender": "male"},
    "female_1983": {"date": "1983-02-15", "time": "20:00", "gender": "female"},
    "late_zi_1986_sect2": {"date": "1986-04-21", "time": "23:30", "gender": "male"},
    "lichun_2024_after": {"date": "2024-02-04", "time": "18:00", "gender": "male"},
}


@pytest.mark.parametrize("name", list(BIRTHS))
def test_cross_engine_atlas(name: str):
    expected = atlas_pillars()[name]
    got = tianze_pillars(BirthInfo.model_validate(BIRTHS[name]))
    assert got == expected, f"[{name}] Tianze={got} atlas={expected}"
