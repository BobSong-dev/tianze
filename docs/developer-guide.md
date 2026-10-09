# Tianze Developer Guide（v0.4.0）

面向维护者与贡献者：架构地图、扩展方式、测试与回归、发布流程。

## 1. 架构总览

```
tianze/
  calendar/     历法适配（lunar-python 薄包装；节气/晚子时边界）
  ganzhi/       干支表（藏干/十神/长生/禄刃）
  relation/     关系引擎（刑冲合害破/三合三会 + 拱夹 arch/暗合/争合/旬空表）
  analysis/     分析层（旺衰/格局/调候/特殊格局/关系解释链/岁运 Delta/回放）
  knowledge/    知识加载（ExecutableRule → Evidence）
  ai/           Grounded AI（Context/Prompt/Grounding；Provider 可插拔）
  export*.py    Markdown/HTML 报告
  sdk.py        唯一对外 Facade（CLI/API 复用）
apps/
  api/          FastAPI HTTP 壳（纯委托 SDK）
  web/          Vue3 前端（只消费后端事实）
knowledge/      规则与命例数据（rules/*/rules.json 等；打包镜像 tianze/_data）
tools/          审计/回归/构建工具（quality_gate 等 23 步）
tests/          641 项 Python 测试 + 21 场景 E2E
```

核心纪律：**Engine 算事实，Knowledge 给依据，Reasoning 保留条件与分歧，
AI 只解释。** 详见 `docs/DECISIONS.md`（ADR-001..077）。

## 2. 关键不变量（修改前必读）

- 候选永不 CONFIRMED：特殊格局/事件主题/虚神输出 ∈ {CANDIDATE, LIKELY,
  DISPUTED, BLOCKED, UNRESOLVED}。
- 岁运不替换原局月令；EXPERIMENTAL/UNSUPPORTED 显式标注。
- 关系证据三态：ESTABLISHED / CANDIDATE / BLOCKED（blockedRelations 与
  relations 严格分离）。
- 引文注册表 `knowledge/rules/relations/citations.json` 由
  `tools/build_relation_citations.py` 机械生成（禁止手写引文）。
- 同一引擎结果必须三通道一致（tests/test_cross_channel.py）。

## 3. 扩展方式

- **新增岁运/事件规则**：`tools/build_temporal_rules.py` /
  `build_event_rules.py` 增加条目（provenance 三级：CLASSICAL_EXPLICIT /
  PROJECT_REFERENCE / ENGINEERING_HEURISTIC）→ 实现评估器（缺执行器抛错，
  不静默）→ 更新计数断言 → 全量回归。
- **新增关系类型**：`tianze/relation/tables.py`（数据） +
  `relations.py`（检测）+ `relation_explain.py`（解释链）+ fuzz 不变量。
- **修改判定口径**：先查 ADR 是否已裁决；引擎变更须刷新对应 Regression
  baseline 并在 commit message 记录依据。

## 4. 测试与回归

日常：`python -m pytest tests apps/api/tests`（~60s）。
提交前：`python tools/quality_gate.py`（23 步，~100s）+ Web
`npm run build && npx playwright test`（11 项）。
回归基线：`regression/baseline/`（case/temporal snapshots）——刷新必须
`snapshot` 后 `compare` 归零并在 commit 注明文档化变更依据。

## 5. 发布流程（本地可复现）

```
tools/quality_gate.py        # 23 步
tools/release_metadata.py    # 工件
tools/release_check.py       # P0-P7
tools/release_automation.py  # dry-run（建议 tag）
python -m build              # wheel + sdist
python tools/install_smoke.py
```

正式发布需人工授权：`git push`、正式 tag、GitHub Release（见
release/READY_FOR_RELEASE.json 的 blockedActions）。

## 6. 维护排障入口

- 质量门步骤失败 → `release/quality-summary.json` 的 steps[].tail。
- 引用完整性 → `tools/cross_layer_audit.py`（C1-C8）。
- 来源可回溯 → `tools/source_coverage.py`（raw OCR 缺失为已知 BLOCKED）。
- 能力声明漂移 → `tools/capability_audit.py`（证据指针验证）。
