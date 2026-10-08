# Tianze v0.4.0 Release Notes

- commit: `b89c07b85dfd`（含未提交改动）
- 当前版本 0.3.0 → 建议 v0.4.0（minor；规则：特性 commit → minor，否则 patch）
- 质量门：FAIL（66.8s / 20 步）

## 版本与规模

- versions: {'knowledge': '1.1.0', 'case': '1.0.0', 'analysis': '1.0.0', 'delta': '1.0.0', 'event': '1.0.0', 'interpretation': '1.1.0', 'prompt': '1.1.0', 'python': '3.14.7'}
- ExecutableRule: **216**（{'event': 20, 'temporal': 14, 'tiaohou': 182}）；candidates 556（不同口径）
- 命例 1147；Replay 165；测试 534

## 质量状态

- Audit Gates: ALL PASS
- Case Regression: 无变化
- Temporal Regression: 无变化
- Event Evaluation problems: 无
- AI Evaluation: mock（无 API Key 时 SKIPPED，不伪造）

## 基准

```json
{
 "caseChart1147": {
  "count": 1045,
  "elapsedSeconds": 0.493,
  "perCaseMs": 0.47
 },
 "replayCorpus": {
  "count": 1045,
  "elapsedSeconds": 0.627,
  "perCaseMs": 0.6
 },
 "timeline80y": {
  "nodes": 87,
  "elapsedSeconds": 0.016
 },
 "explanationChains": {
  "themes": 2,
  "avgMs": 0.03
 },
 "note": "耗时供跨版本对比；节点/主题数是确定性计数（回归可用）"
}
```

## Commits（自 v0.3.0）

### 特性（1）
- M21.7: release history tool + READY_FOR_RELEASE marker + local v0.3.0 tag

## Migration 要求

- 规则文件当前未批量升至 1.2.0：如需升级，运行 `tools/migrate_knowledge.py --write` 并人工确认 .migrated 副本（不静默改历史）

## OPEN / REVIEW

- Rule Audit 异常泛化信号：无
- Review Queue：见 review/review-queue.json（只汇总，不自动升级 HUMAN 状态）
