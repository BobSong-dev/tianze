# Tianze Release Check

- 结果：ALL PASS（v0.2.0）

| step | 状态 | detail |
|---|---|---|
| P0_quality_gate | PASS | WARN: 最近一次 quality summary 未 ALL PASS（pytest）——发布前请重跑 tools/quality_gate.py |
| P1_package_build | PASS | tianze_bazi-0.2.0-py3-none-any.whl，4.2s |
| P2_clean_install_smoke | PASS | clean venv install → version/analyze |
| P3_cli_smoke | PASS | 3/3 |
| P4_version_consistency | PASS | 0.2.0（dynamic single-source=True，metadata=0.2.0） |
| P5_stale_artifact | PASS | commit 一致 |
| P6_notes_consistency | PASS | tag v0.3.0 |
| P7_benchmark_regression | PASS | 全部在阈值内（阈值：{"caseChart1147.perCaseMs": 5.0, "replayCorpus.perCaseMs": 5.0, "timeline80y.elapsedSeconds": 1.0}） |
