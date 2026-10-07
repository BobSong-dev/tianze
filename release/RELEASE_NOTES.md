# Tianze v0.3.0 Release Notes

- commit: `132920a2b547`（含未提交改动）
- 当前版本 0.2.0 → 建议 v0.3.0（minor；规则：特性 commit → minor，否则 patch）
- 质量门：ALL PASS（26.3s / 17 步）

## 版本与规模

- versions: {'knowledge': '1.1.0', 'case': '1.0.0', 'analysis': '1.0.0', 'delta': '1.0.0', 'event': '1.0.0', 'interpretation': '1.1.0', 'prompt': '1.1.0', 'python': '3.14.7'}
- ExecutableRule: **216**（{'event': 20, 'temporal': 14, 'tiaohou': 182}）；candidates 556（不同口径）
- 命例 1147；Replay 165；测试 529

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
  "elapsedSeconds": 0.519,
  "perCaseMs": 0.5
 },
 "replayCorpus": {
  "count": 1045,
  "elapsedSeconds": 0.706,
  "perCaseMs": 0.68
 },
 "timeline80y": {
  "nodes": 87,
  "elapsedSeconds": 0.017
 },
 "explanationChains": {
  "themes": 2,
  "avgMs": 0.03
 },
 "note": "耗时供跨版本对比；节点/主题数是确定性计数（回归可用）"
}
```

## Commits（自 起点）

### 特性（81）
- M20.3-4: Web AI evaluation compare view + Rule/Conflict/Rescue graph view
- M20.5: benchmark history (JSONL with commit/engine/regressionSignals, transparent thresholds) + release-check re-verified ALL PASS
- M20.10: release_check (P0-P7: quality-gate precondition, wheel build, clean-venv install smoke, CLI smoke, version single-source consistency, stale-artifact, notes consistency, transparent benchmark thresholds) — ALL PASS; 2 tests; 513 passing
- M20.2: packaging + CLI
- M19.10: ADR-054/055 + README M19 + final E2E/pytest/build verification
- M19.4-5+7: parser long-block window, rescue 5-reading expansion, replay chain/decision excerpts + skip-reason classification
- M19.3+9: AI eval compare tool + stale artifact detection + VERSIONING doc
- M19.2: Web knowledge/quality dashboard complete
- M19.6: rule coverage / dead-rule analysis (216 rules classified)
- M19.1: release automation (changelog/version-bump suggestion/notes/tag prep)
- M18.10: ADR-051/052/053 + README M18 + final E2E/pytest verification
- M18.5-7: version compatibility matrix tests + funnel endpoint + replay chain comparison
- M18.8: HTML report release sections + PDF path decision
- M18.9: one-click quality gate runner (14 steps, 20.6s ALL PASS)
- M18.4: release metadata tool (JSON + Markdown from real runs)
- M18.3: raw parsing enhancements
- M18.1-2: graph audit + rule audit reports
- M17.10: final verification stack — all green
- M17.9: benchmark tool (real-scale: 1045 case charts 0.62ms/case, replay corpus 0.91ms/case, 80y timeline 28ms, explanation chains) + ADR-049/050 + README M17 + migration/rescue fuzz invariants
- M17.5-6: evaluation history endpoint + schema governance
- M17.4+7: audit gates (10 quality gates) + coverage workbench data
- M17.3: raw-text temporal span parser + replay expansion
- M17.2: rescue expansion — refined wealth predicate + 3 new declarations
- M17.1: ExplanationChain productization (SDK/Web/HTML)
- M16.10: docs + ADR-047/048 + README + full verification stack
- M16.9: fuzz expansion — 120 random charts, live graph integrity, replay robustness (random pillars), cache correctness; 473 passing
- M16.7: knowledge schema migration tool (1.1 → 1.2)
- M16.6 fix: history append moved into run() (records both direct and CLI runs)
- M16.6: AI evaluation history (versioned JSONL)
- M16.4-5: Knowledge Rule Explorer + Review Queue API/Web
- M16.3: case replay expansion (annual-only cases)
- M16.8: full-chain explainability for event themes
- M16.2: rule-ID conflict graph + reverse lookup
- M16.1: rescue/exception conditional reasoning + SPECIFIC_EXCEPTION enabled
- M15.11: docs + ADR-045/046 + Web conflict explanations + README
- M15.10: unified review queue
- M15.9: property/fuzz quality gates
- M15.8: timeline benchmark + in-process memoization
- M15.7: print-friendly HTML report
- M15.6: real-provider AI evaluation harness
- M15.5 fix: mention luck takes precedence over dayun[0], dayun fallback restored
- M15.5: historical case replay
- M15.4: expand event rules with conditional combination rules
- M15.3: special-pattern temporal track (cong/zhuanwang/hua)
- M15.1-A2: direction-level rule conflict reasoning
- M14.11: event rule conflict graph + rule-to-case claim coverage
- M14.9-M14.10: docs + ADRs + performance guard + full-stack verification
- M14.8: Web event themes + report export
- M14.7: grounded AI event-theme interpretation
- M14.5-M14.6: event claims annotation + event evaluation corpus
- M14.1-M14.4: Event Theme layer — rules, school-aware reasoning, confidence, SDK wiring
- M13.11: docs, validators, determinism fix, report export
- M13.10: StructuralTheme layer (ten-god themes / conflict relations / volatility)
- M13.9: grounded AI temporal interpretation
- M13.8: Web temporal workspace tab + E2E fixes
- M13.7: temporal boundary verification suite (24 tests)
- M13.6: temporal regression tool + baseline + gate tests
- M13.5: temporal knowledge rules in Knowledge Framework
- M13.4: TemporalCaseReference — parse 1147 cases' source temporal info
- M13.1-M13.3: full Temporal Delta engine, monthly/daily temporal layers, focused timeline tree
- M12 extended: add Timeline, TenGodThemeDelta, month/day pillar calc, SDK wiring
- M12: add temporal (luck/annual) deterministic structural analysis
- M11 product: add AI tab to web, structured claims, grounding severity + retry, prompt isolation
- M11: add AI Interpretation Layer with grounding validation
- M10.6: add E2E, frontend tests, OpenAPI contract gen, production build, performance, dev scripts
- M10.1-M10.5: add FastAPI backend, Vue 3 web app, contract tests
- M10.0: upgrade case regression snapshot to include M8 results
- M9: add stable Tianze analysis facade and SDK
- M8.6: audit cong cases, add evidence for advanced patterns, standardize population stats
- M8.1-M8.5: add special pattern and structural analysis engines
- M8.0: add case regression infrastructure
- M7: normalize classical cases with rule-case linkage
- M7: add case reference schema
- M6.1: add verification audit and review queue
- M6.1: add knowledge verification model
- M6: add tiaohou rule engine with 10x12 coverage
- M5: add pattern candidate engine and evaluation evidence model
- M4.2: add fuyi strength analyzer
- M4.2: add weighted strength analyzer
- M4: add pluggable strength analysis framework (dimensional method)
- M3: implement root, stem visibility and month command analysis

### 修复（8）
- fix: zero-fill event rule trigger rates (explicit 0 for dead-rule analysis)
- fix: rescues payload unwrap in coverage audit
- fix: JSONL history loading (Edit-tool applied, verified before commit)
- fix: JSONL history loading in HTML release sections
- fix: apply glob guard at the right site
- fix: raw span parser glob guard for own output
- fix: newline escape corruption in history writer
- fix: property fuzz test string corruption

### 测试（10）
- test: coverage audit tests (recreated via Write tool)
- test: accept medium confidence (inherited annual)
- test: accept low-confidence partial spans
- test: cleanup added to governance write-test
- test: write-test cleans up migrated copies
- test: gate-name assertion prefix match
- test: explanation chain tests use a chart with event themes (1984)
- test: align review queue discipline wording
- test: fix AI evaluation skipped-path test (in-process, no subprocess env)
- test: exclude TemporalCaseReference tool outputs from case-book glob

### 文档（6）
- docs: update README with M10 productization status
- docs: add advanced/05 special rule provenance, update progress
- docs: document advanced pattern analysis
- docs: document verification and case system
- docs: document strength and pattern conventions
- docs: ARCHITECTURE/DECISIONS/ERRATA/README/progress sync for M3-M4

### 杂项（6）
- chore: gitignore .migrated copies (build outputs, manual-replace workflow)
- chore: gitignore node_modules and dist
- K1: add knowledge normalization pipeline and validation
- K0: add classical knowledge schema
- refactor(M3): reserve MonthCommand extensibility fields (ADR-021)
- feat(M0-M2): Tianze 八字引擎脚手架、排盘+差分对拍、关系引擎

## Migration 要求

- 规则文件当前未批量升至 1.2.0：如需升级，运行 `tools/migrate_knowledge.py --write` 并人工确认 .migrated 副本（不静默改历史）

## OPEN / REVIEW

- Rule Audit 异常泛化信号：无
- Review Queue：见 review/review-queue.json（只汇总，不自动升级 HUMAN 状态）
