# Tianze v0.4.0 Release Notes

- commit: `5d85e10b6833`（含未提交改动）
- 当前版本 0.4.0.dev0 → 建议 v0.4.0（minor；规则：特性 commit → minor，否则 patch）
- 质量门：ALL PASS（81.3s / 21 步）

## 版本与规模

- versions: {'knowledge': '1.1.0', 'case': '1.0.0', 'analysis': '1.0.0', 'delta': '1.0.0', 'event': '1.0.0', 'interpretation': '1.1.0', 'prompt': '1.1.0', 'python': '3.14.7'}
- ExecutableRule: **221**（{'event': 21, 'temporal': 18, 'tiaohou': 182}）；candidates 556（不同口径）
- 命例 1147；Replay 165；测试 581

## 质量状态

- Audit Gates: ALL PASS
- Case Regression: 无变化
- Temporal Regression: 无变化
- Event Evaluation problems: 无
- AI Evaluation: SKIPPED（无 API Key 时 SKIPPED，不伪造）

## 基准

```json
{
 "caseChart1147": {
  "count": 1045,
  "elapsedSeconds": 0.627,
  "perCaseMs": 0.6
 },
 "replayCorpus": {
  "count": 1045,
  "elapsedSeconds": 0.78,
  "perCaseMs": 0.75
 },
 "timeline80y": {
  "nodes": 87,
  "elapsedSeconds": 0.027
 },
 "explanationChains": {
  "themes": 2,
  "avgMs": 0.03
 },
 "note": "耗时供跨版本对比；节点/主题数是确定性计数（回归可用）"
}
```

## Commits（自 v0.3.0）

### 特性（27）
- M25 final: ADR-063 关系解释链三态与外格泛化纪律 + README M25 + gate 21 步/release_check ALL PASS
- M25.3b: gate 21 步 ALL PASS（summary 收敛后 pytest 步自指解除）
- M25.3: StructuralTheme 虚神填实主题 + 命例×虚神专题审计(gate 21步; 1045例: 拱911/暗合308/未成立144/外格15) + 泛化审计结论落地（井栏叉限庚日、子邀巳不落地引擎） + 全拱对×在场矩阵 fuzz
- M25.2: 关系级 ExplanationChain（ESTABLISHED/CANDIDATE/BLOCKED 三态）— citations.json 机械引文注册表(13条) + relation_explain 统一解释器 + pipeline/SDK/temporal/AI(铁律13:候选不得升级/BLOCKED不得描述为成立)/Web解释链details/markdown+HTML报告；wheel 数据 7→8
- M25.1: 外格虚神候选 xushiOuter（飞天禄马/井栏叉拱刃/刑合/子邀巳）— ZP-05/07/11/12+DTZ-41，候选永不成格，外格说vs伤官变格说两注记；AI context refs + Web 候选区 + delta UNSUPPORTED note
- M24 final: README + gate 20 steps ALL PASS at HEAD (artifacts refreshed)
- M24.5b: release metadata/history refreshed at HEAD (P5 commit 一致)
- M24.5: HTML 报告关系注记/未成立候选 + Web Evaluation compare 筛选（provider/仅回归，趋势随筛选联动）
- M24.4: blockedRelations 未成立拱夹候选（拱而不成·靶支在场，DTZ-10 拱实不若拱虚）— pipeline/sdk/Web(未成立候选 section)/export 全链，与 relations 严格分离；gate ALL PASS
- M24.3: 命例×虚神联动 — build_case_chart 挂关系层（与 pipeline 同一 analyze_relations），case_replay 增 xushiRelations 摘要与统计（165 例重放中 109 例含拱夹/暗合：arch 155/暗合 51）
- M24.2: regression baselines refreshed (M24.1 documented engine change) + ADR-062 拱夹虚神候选关系边界 + README M24 + gate 20步/release_check/web build/E2E ALL PASS
- M24.1: 拱夹/虚神(arch)与暗合(hidden_combination)关系引擎 — DTZ-10/ZP-05/SPZY-34 引文级；temporal 层 arch_fill/arch/hidden_combination；TR-DTZ-10 评估器只读关系层；cong 印比合去两说(SP-CG-E1)；arch members canonical
- M23 final: README M23 status + gate 20 steps ALL PASS + release_check ALL PASS (dev wheel 0.4.0.dev0, P5 commit 一致)
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
