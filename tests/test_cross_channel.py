"""M38 · 跨渠道一致性验收：同一命局在 SDK / CLI / API 三条通道结论一致。

真实缺陷探测器：三条通道若对同一命局输出不同的柱/旺衰/关系/规则触发，
说明存在契约漂移。逐项断言核心语义字段（非全 JSON 字节比较——meta 时间戳类
字段允许差异）。
"""

from __future__ import annotations

import json
import subprocess
import sys

from fastapi.testclient import TestClient

SAMPLES = [
    {"date": "1984-02-05", "time": "10:30", "gender": "male"},
    {"date": "2003-08-18", "time": "14:30", "gender": "female"},
    {"date": "1980-01-03", "time": "10:00", "gender": "male"},   # 微根假从样本
    {"date": "1990-01-01", "time": "03:00", "gender": "male"},   # 拱夹样本
]


def _core_fields(payload: dict) -> dict:
    """提取跨渠道必须一致的语义字段。"""
    pillars = payload["pillars"]
    rels = sorted((r["kind"], r["label"]) for r in payload.get("relations", []))
    strength = payload.get("strength") or {}
    return {
        "pillars": {pos: (pillars.get(pos) or {}).get("stem")
                    + (pillars.get(pos) or {}).get("branch", "")
                    for pos in ("year", "month", "day", "hour")
                    if pillars.get(pos)},
        "dayMaster": (payload.get("dayMaster") or {}).get("stem"),
        "relations": rels,
        "verdicts": sorted((m.get("analyzerId"), m.get("verdict"))
                           for m in strength.get("methods", [])),
        "advancedStatus": sorted(
            (g, c.get("type") or t.get("stemPair"), c["status"])
            for g, group in ((payload.get("advancedAnalysis") or {})
                             .get("specialPattern", {}) or {}).items()
            for c in group
            for t in [c] if (c.get("type") or c.get("stemPair"))),
    }


def test_cross_channel_consistency_sdk_cli_api():
    """同一命局：SDK / CLI / API 三通道核心语义字段一致。"""
    from tianze.sdk import analyze, AnalysisOptions, SimplifiedBirthInfo

    from apps.api.main import app
    client = TestClient(app)
    repo = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True,
                          text=True).stdout.strip()

    for birth in SAMPLES:
        # SDK
        sdk_payload = analyze(SimplifiedBirthInfo.model_validate(birth),
                              AnalysisOptions()).model_dump(by_alias=True)
        sdk_core = _core_fields(sdk_payload)

        # CLI（human 之外的 json 通道）
        args = ["--date", birth["date"], "--time", birth["time"],
                "--gender", birth["gender"], "--format", "json"]
        r = subprocess.run([sys.executable, "-m", "tianze.cli", "analyze", *args],
                           capture_output=True, encoding="utf-8", errors="replace", cwd=repo)
        assert r.returncode == 0, r.stderr[-200:]
        cli_core = _core_fields(json.loads(r.stdout))

        # API
        ra = client.post("/api/v1/analyze", json={"birthInfo": birth, "options": {}})
        assert ra.status_code == 200, ra.text[:200]
        api_core = _core_fields(ra.json())

        assert sdk_core == cli_core, f"SDK vs CLI 不一致：{birth}\n{sdk_core}\n{cli_core}"
        assert sdk_core == api_core, f"SDK vs API 不一致：{birth}\n{sdk_core}\n{api_core}"
