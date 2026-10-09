# Tianze v0.4.0 Release Notes

- commit: `f8a3dc3a9f55`（含未提交改动）
- 当前版本 0.4.0.dev0 → 建议 v0.4.0（minor；规则：特性 commit → minor，否则 patch）
- 质量门：ALL PASS（104.9s / 23 步）

## 版本与规模

- versions: {'knowledge': '1.1.0', 'case': '1.0.0', 'analysis': '1.0.0', 'delta': '1.0.0', 'event': '1.0.0', 'interpretation': '1.1.0', 'prompt': '1.1.0', 'python': '3.14.7'}
- ExecutableRule: **223**（{'event': 21, 'temporal': 20, 'tiaohou': 182}）；candidates 556（不同口径）
- 命例 1147；Replay 165；测试 645

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
  "elapsedSeconds": 0.586,
  "perCaseMs": 0.56
 },
 "replayCorpus": {
  "count": 1045,
  "elapsedSeconds": 0.767,
  "perCaseMs": 0.73
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

### 特性（63）
- M40 final: ADR-078 + README + READY_FOR_RELEASE_v0.4.0_RC（判定 READY_FOR_RELEASE_PENDING_AUTHORIZATION，零 Release Blocker，六项 External Blocked 如实）
- M40.1: 发布稳定化 — developer-guide/release-notes-v0.4.0/known-limitations 三文档 + RC 隔离验证（sdist→wheel 重建 64/64 hash 一致；OpenAPI 17 路径契约无漂移）+ 异常流验收（API 422 错误码无 traceback/缺时辰降级 fallback/AI 无 Provider 503 AI_NOT_CONFIGURED/CLI 非法日期非零退出）→ 测试 641→645
- M39 final: ADR-077 + README M39 + gate 23 步/release_check ALL PASS
- M39.1: 产品体验 — HTML 报告封面/摘要/术语说明 + A4 打印 CSS（replay 打印展开降级）+ Web 总览摘要块（四柱视觉/核心结论/术语说明/使用说明入口）+ 关系页合化状态区块 + replay→规则链接 + 移动端媒体查询（375/768/1280）+ Playwright 3 项新增（移动视口/合化状态/回放联动，E2E 8→11）
- M38 final: ADR-076 + README M38 + gate 23 步/release_check ALL PASS
- M38.1: 完整性审计与核心能力补齐 — 跨渠道一致性测试（SDK/CLI/API 4样本三通道核心语义一致）+ 能力覆盖矩阵（36 项诚实评估+证据指针验证：COMPLETE 25/PARTIAL 4/EXPERIMENTAL 1/BLOCKED 4/UNSUPPORTED 2）+ 端到端场景套件 21 项（含近真化真实日盘 1978-07-11 探测）+ 争合入 natal 解释链（见辰条件化两说注记）+ AI 评测 claimCoverage/stateUpgrade 指标
- M37.2: temporal baseline refreshed（TR-DTZ-47 争合为文档化引擎变更，ADR-075）
- M37 final: ADR-075 + README M37 + gate 23 步/release_check ALL PASS
- M37.1: 争合结构化推理 — zhenghe_families（五合家族计数：一侧≥2即争合/两侧≥2并见不争，QBT-甲-20「见二甲则不争」+ DTZ-47「重见己土则为争合」）+ 岁运争合事件（temporal kind=zhenghe）+ TR-DTZ-47 规则（executable 222→223, temporal 20, graph 229）
- M36 final: ADR-074 + README M36 + gate 23 步/release_check ALL PASS
- M36.1: 合化状态入 RelationExplanation（combination_state 三要素解释链 + DTZ-47/18/26/36 引文，pipeline 经 stem_combination_states 传入）+ 后端 replayEventKinds 映射（/rules 提供事件种类，前端只展示）+ C8 同构审计（1045 例全 0，八项；同 pair 取最少阻化对齐规则）
- M35 final: ADR-073 + README M35 + gate 23 步/release_check ALL PASS
- M35.1: 合化状态结构化 stem_combination_states（近真化/合而不化/隔位三态，复用 DTZ-47 口径）→ E1 升级为可审计三要素证据（邻位/月令/阻化）+ Rule Graph 联动去特判（rules.json conditions 数据驱动）+ 合化专题审计（1045 例：UNRESOLVED 563/CANDIDATE 11，阻化=隔位394/印比290/争合224）
- M34 final: ADR-072 + README M34 + gate 23 步/release_check ALL PASS
- M34: 合去调制（E3→TR-SP-08：natal 印比已合去→岁运印比为新增生助不叠加）+ replay 引用完整性自检（虚神⊆快照/冲突⊆关系键，悬空入 warnings）+ Web TR-DTZ-10 节点↔回放事件联动
- M33 final: ADR-071 + README M33 + gate 23 步/release_check ALL PASS
- M33.1: 主题→事件反查（确定性映射：虚神填实←arch_fill/冲突←新冲害破/十神←层干；映射空回退 basisRefs 提取 temporal:*）→ Web/Markdown/HTML 反查展示 + C7 悬空引用审计（1045 例全 0，七项）
- M32 final: ADR-070 + README M32 + gate 23 步/release_check ALL PASS
- M32.1: Replay Theme Delta（逐层复用 delta 主题层+replay-theme:* refs，入 AI Context/Web/报告）+ Markdown/HTML 回放章节 + html ev-None 潜伏 bug 修复 + 命例年锚候选集（4 例干支年×10 候选全 UNRESOLVED，流年层维持 BLOCKED）
- M31 final: ADR-069 + README M31 + gate 23 步/release_check ALL PASS
- M31.2: AI 评测新增 temporal_replay 用例（caseSet 4→5，replay:* refId Grounding 回归测试直连 SDK+validate_grounding）
- M31.1: Temporal Replay 全链路产品化 — AnalysisOptions.includeTemporalReplay（SDK 按需计算）+ CLI timeline --replay（human 摘要）+ /analyze 透传 + Web 状态回放时间轴（步骤+/-事件）+ AI Context replay:* claimRefs 与 prompt 铁律 11 扩展 + fuzz 不变量
- M30 final: ADR-068 + README M30 + gate 23 步/release_check ALL PASS
- M30.1: 统一岁运状态机 temporal_replay（natal→运→年→月→日 逐层快照+迁移原因，固定层序；再次填实自然涌现）+ SP-CG-E3 合去×根气联动两说 + 跨层审计 C6 Evidence 完整化（1045 例全 0）+ 命例状态回放统计（原书大运层 100 例，流年层待可靠年锚如实注记）+ unfill 中文层名
- M29 final: gate 23 步/release_check ALL PASS（工件刷新于 HEAD a9b2b58+）
- M29.1: 旬空差分验证（300盘×4柱 vs lunar-python 全一致）+ TR-SP-08 微根受制两说 + SpecialTemporalFinding.label（additive）+ 假从根气分布审计 + 触发率透明化（随机成拱46.5%/暗合41.5%/拱破17.5%/填实4.5% vs 语料69%）
- M28 final: ADR-066 + README M28 + RC 本地构建验证（wheel/sdist）+ gate 23 步/release_check ALL PASS
- M28.1: 旬空引擎（六旬公版表 xun_kong_of，SS-R16 第三要件空亡 blocker 落地六乙鼠贵，日柱口径/年柱两说）+ 根气强度分级（微根/明根/强根）入假从说 SP-CG-E2 + 命例审计空亡贵人统计（贵人落日空 378/1045）+ Web 节点条件层直展
- M27 final: ADR-065 + README M27 + gate 23 步/release_check ALL PASS
- M27.3: 知识来源治理 tools/source_coverage.py（raw 语料 556/556 缺失 → status=BLOCKED 如实记录；引文注册表一致性 issue 0；入质量门 23 步）+ Web 节点→重放命例/随机触发率导航 + fuzz（贵人表完整性/外格状态词汇/缓存一致性）
- M27.2: 六乙鼠贵 SS-R16 三要件条件化（见合 support/无合 blocker/交互得待核/午冲子 blocker）+ arch_unfill 去填复现状态（去填说 vs 填实不破说，DTZ-10）入 TR-DTZ-10
- M27.1: TR-SP-08 假从/假化岁运敏感（DTZ-49 行运之别）— 假从+岁运根气/印比→逆旺气破格两说 vs 顺势与真从无别；假化+岁运泄气→假化敏感；executable 221→222, temporal 19, graph 228
- M26 final: ADR-064 + README M26 + release metadata refreshed
- M26.3: gate 22 步 ALL PASS（含 cross_layer_audit）+ release_check ALL PASS
- M26.2: 跨层一致性审计（1045例 C1-C5 全 0，入质量门 22 步）+ 命例专题 v2（Engine 719 vs 标注提及 0/重叠 0，raw OCR BLOCKED；日主×拱型分布：拱贵 167 次居次）+ 真从/假从两说 SP-CG-E2（DTZ-49）+ Web cong 例外渲染 + 引文→图谱跳转 + fuzz（重复支/arch_broken 不变量/争合）+ 伏吟自对修复
- M26.1: 拱贵（天乙贵人 SS-R17 起例并集表+拱贵 sub_type+双注记）+ arch_broken（拱位逢刑冲：拱破说 vs 拱动说 DTZ-10 两说）+ 六乙鼠贵候选（ZP-06，SS-R16 三要件两说）+ TR-DTZ-10 扩展；citations 13→16
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

### 杂项（2）
- Handoff: 修复 RC 工件 JSON 语法（Python 隐式拼接混入 JSON）+ 交接修复记录与三浏览器证据
- Handoff v0.4.0: 发布交接 — P1 安全修复（.env 入 gitignore）+ AI 外发数据告知 + 一键启动 dev_start.py + 发布步骤与回滚方案 + 试用者交付包 TRIAL-PACK + 三浏览器 E2E 实测（Chromium/Firefox/WebKit 各 11/11）；645 tests + gate 23 步 + release_check ALL PASS

## Migration 要求

- 规则文件当前未批量升至 1.2.0：如需升级，运行 `tools/migrate_knowledge.py --write` 并人工确认 .migrated 副本（不静默改历史）

## OPEN / REVIEW

- Rule Audit 异常泛化信号：无
- Review Queue：见 review/review-queue.json（只汇总，不自动升级 HUMAN 状态）
