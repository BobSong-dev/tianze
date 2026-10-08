# Tianze v0.4.0 Release Notes

- commit: `643dc26f3483`（含未提交改动）
- 当前版本 0.4.0.dev0 → 建议 v0.4.0（minor；规则：特性 commit → minor，否则 patch）
- 质量门：ALL PASS（96.2s / 20 步）

## 版本与规模

- versions: {'knowledge': '1.1.0', 'case': '1.0.0', 'analysis': '1.0.0', 'delta': '1.0.0', 'event': '1.0.0', 'interpretation': '1.1.0', 'prompt': '1.1.0', 'python': '3.14.7'}
- ExecutableRule: **220**（{'event': 21, 'temporal': 17, 'tiaohou': 182}）；candidates 556（不同口径）
- 命例 1147；Replay 165；测试 554

## 质量状态

- Audit Gates: ALL PASS
- Case Regression: 无变化
- Temporal Regression: {'REVIEW': 4}
- Event Evaluation problems: 无
- AI Evaluation: mock（无 API Key 时 SKIPPED，不伪造）

## 基准

```json
{
 "caseChart1147": {
  "count": 1045,
  "elapsedSeconds": 0.536,
  "perCaseMs": 0.51
 },
 "replayCorpus": {
  "count": 1045,
  "elapsedSeconds": 0.707,
  "perCaseMs": 0.68
 },
 "timeline80y": {
  "nodes": 87,
  "elapsedSeconds": 0.018
 },
 "explanationChains": {
  "themes": 2,
  "avgMs": 0.03
 },
 "note": "耗时供跨版本对比；节点/主题数是确定性计数（回归可用）"
}
```

## Commits（自 v0.3.0）

### 特性（14）
- M23.6: Web Graph pan/zoom (viewBox 滚轮缩放+拖拽平移+重置) + 规则→ExplanationChain 跳转 + AI Evaluation 趋势 sparkline (pass率/grounding/latency)
- M23.5: ADR-061 神煞主从与去取纪律（MLD-06/SS-R22/MLD-21 治理固化；红艳/桃花马等 OCR 残缺名目保持 UNRESOLVED 不落地）
- M23.4: EV-REL-06 婚变之微（MLD-18 女命夫宫坐伤官，gender-aware；男命口径 OCR 残缺不入可执行条件）+ EV-REL-03↔06 keep-both 冲突声明；event 20→21, executable 220, graph 226/18
- M23.3: TR-DTZ-11 旺者冲衰衰者拔/衰神冲旺旺者发 — 水火之冲全局气势阵营计数（徐注例证），平局不裁决；executable 218→219, graph 225 nodes
- M23.2: DTZ-47 真化条件精细化 — 隔位不合/印比透干阻化/逢龙而运记录 + DTZ-06 许世英(印透不从)/伍庭芳(DISPUTED保留) 经典造回归；transformation 增 chenPresent/adjacentToDayMaster (CLASSICAL_EXPLICIT)
- M23.1: tag v0.3.0 frozen + RC artifacts archived to release/rc/0.3.0/; dev line 0.4.0.dev0; release_automation dev-aware (ADR-060)
- M22 final: ADR-058/059 + README M22 + full gate (20 steps) + release check + E2E + build ALL PASS
- M22.3: telemetry trend in Web evaluation compare
- M22.5-6: H5 empirical lock + H6 replay samples in Rule Explorer
- M22.4: knowledge expansion — TR-SP-05 化神所忌 + TR-SP-07 从格所从受克
- M22.2: Rule Graph interactive SVG canvas
- M22.1: v0.3.0 RC audit — refreshed all artifacts at HEAD, wheel+sdist built, release_check P1 extended with wheel content verification (7 data files + manifest + cli/paths); RC evidence: tag v0.3.0→5821c84, gate+check ALL PASS
- M21 final: gate 20 steps ALL PASS + external release_check + E2E + RC discipline fixes
- M21.7: release history tool + READY_FOR_RELEASE marker + local v0.3.0 tag

### 测试（2）
- test: lazy chart fixture for expansion tests
- test: fix imports in special temporal expansion tests

## Migration 要求

- 规则文件当前未批量升至 1.2.0：如需升级，运行 `tools/migrate_knowledge.py --write` 并人工确认 .migrated 副本（不静默改历史）

## OPEN / REVIEW

- Rule Audit 异常泛化信号：无
- Review Queue：见 review/review-queue.json（只汇总，不自动升级 HUMAN 状态）
