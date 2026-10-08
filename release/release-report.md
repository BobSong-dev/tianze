# Tianze Release Report

- commit: `68049824310a`（含未提交改动）
- engine: 0.4.0.dev0
- versions: {'knowledge': '1.1.0', 'case': '1.0.0', 'analysis': '1.0.0', 'delta': '1.0.0', 'event': '1.0.0', 'interpretation': '1.1.0', 'prompt': '1.1.0', 'python': '3.14.7'}

## 规模

- ExecutableRule：**219**（{'event': 20, 'temporal': 17, 'tiaohou': 182}）
- RuleCandidate：556（不同口径）
- 命例：1147；Replay：165
- 测试：551

## 质量状态

- Audit Gates：ALL PASS
- Case Regression：无变化
- Temporal Regression：无变化
- Event Evaluation problems：无
- AI Evaluation：SKIPPED

## 基准

```json
{
 "caseChart1147": {
  "count": 1045,
  "elapsedSeconds": 0.502,
  "perCaseMs": 0.48
 },
 "replayCorpus": {
  "count": 1045,
  "elapsedSeconds": 0.721,
  "perCaseMs": 0.69
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
