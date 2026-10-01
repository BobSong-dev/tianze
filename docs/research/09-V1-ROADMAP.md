# 09 · Tianze V1 施工路线图（V1 ROADMAP）

> Phase 0 产出 · 2026-09-30。供下一阶段逐里程碑直接施工（可交由 Codex/人工按序执行）。
> 里程碑设计原则：每个 M 的输出都可被独立验证；验证网（crosscheck/fixture）与功能同里程碑交付，不允许"以后补"；约定（R 表）先于实现。

## 前置总览

```text
M0 脚手架+R约定 → M1 排盘+对拍 → M2 关系引擎 → M3 通根/透干/月令
→ M4 旺衰(多分析器) → M5 格局 → M6 调候 → M7 规则库+溯源
→ M8 统一JSON+API → M9 Web
（大运/流年 = M1 随 lunar 直出 + M8 暴露；流派层 = M5/M6 副产物，V1 收敛为三派）
```

跨里程碑贯穿（不单列）：pytest 全绿 + Linux/Windows CI；`research/progress.md` 模式延续到 `docs/` 变更记录。

---

## M0 · 脚手架与约定（0.5 天）

- **目标**：仓库骨架、依赖锁定、R 约定表 v1。
- **依赖**：无。
- **文件**：`pyproject.toml`（deps: lunar-python、pydantic、pytest）；`tianze/` 包骨架（calendar/domain/ganzhi/relation/analysis/evidence/rules 空包）；`docs/CONVENTIONS.md`（R1-R12：R1 晚子时 sect=2 默认；R2 时间算法档；R3 双轨道；R4 立春/节按时刻；R5 十二长生=火土同宫派（lunar 口径）；R6 旺相休囚死表；R7 起运=3天1岁流派1；R8 藏干=通行表；R9 关系表公版+并存不裁决；R10 半合需中神；R11 未知时辰=缺席；R12 时区显式缺省+8）；`docs/SOURCES.md`、`docs/ERRATA.md`；`.github/workflows/ci.yml`（3.12/3.13 × ubuntu/windows）。
- **功能**：`pip install -e .` 成功；`import tianze` 成功。
- **测试**：冒烟测试（import + 版本）。
- **DoD**：CI 双平台绿；CONVENTIONS 中每条 R 都有"分歧说明"字段。

## M1 · 排盘 + 差分对拍（1-1.5 天）

- **目标**：BirthInfo → BaziChart（四柱/藏干/十神/纳音/十二长生/旬空/胎元命宫身宫 + TimeResolution 溯源）+ crosscheck 独立路径 + 边界 fixture 网。
- **依赖**：M0；lunar-python。
- **文件**：`tianze/calendar/lunar_adapter.py`、`tianze/calendar/time_resolution.py`、`tianze/domain/models.py`、`tianze/ganzhi/*`、`tianze/pipeline.py`（build_chart）、`tests/crosscheck/crosscheck_pillars.py`、`tools/stamp_expected.py`、`tests/fixtures/charts.json`。
- **功能**：build_chart(birth) 输出 BaziChart（含 conventions 回显）；未知时辰 → hour=None。
- **测试**：
  1. crosscheck：JDN `(JDN−2433191)%60` 日柱 + 五时遁/五虎遁 + 黄经区间年月柱（Meeus Ch.25 自写移植，仅年/月柱域）+ 外部锚点（1949-10-01=甲子、2000-01-01=戊午、2024-01-01=甲子）；
  2. fixtures ≥35（立春±30min、交节±30min、晚子时 sect1/2 成对、00:00 边界、DST 1988、乌鲁木齐/纽约/伦敦、闰日、未知时辰、1965/2025）；expected 由盖章器生成；
  3. 与 lunar-python 十神/藏干一致性穷举断言（10×10 十神全矩阵 + 12 支藏干）。
- **DoD**：85+ 对拍全绿；`sect` 双派输出与 lunar 实测一致（1988-02-15 23:30 案例）；Windows CI 绿。

## M2 · 关系引擎（1 天）

- **目标**：合冲刑害破 + 三合三会 + 位置/相邻性/月令参与标注；候选不化气。
- **依赖**：M1（需要柱位）。
- **文件**：`tianze/relation/tables.py`（公版关系表）、`stem_relations.py`、`branch_relations.py`、`combinations.py`。
- **功能**：`analyze_relations(chart) -> list[Interaction]`；多重关系并存（巳申=合+刑+破）；自刑；半合（需中神，R10）；全配对 + adjacency。
- **测试**：
  1. 表完备性：六合恰 6 对、五合 5、冲 6、害 6、破 6（含寅亥/巳申重合项锁死）、三合 4、三会 4、刑组完整；
  2. 守恒律：任意干对五合判定对称；三合组=阳干长生/帝旺/墓（atlas 交叉断言法）；
  3. 合成命例金测（子丑+午未+子午+丑未 密集盘）；
  4. 反例：柱位反序不漏检（OBE bug 守卫）。
- **DoD**：关系输出与 Atlas 对 3 个公共命例人工比对一致（记录到 disputed/ 或确认）。

## M3 · 通根 / 透干 / 月令（1 天）

- **目标**：Root 分级事实、透干事实、MonthCommand（旺相休囚死 + 日主关系）。
- **依赖**：M1/M2。
- **文件**：`tianze/relation/roots.py`、`tianze/analysis/month_command.py`。
- **功能**：`collect_roots(chart, stem)` → 禄刃/本气库/本气/长生/中气/余气六级 + is_month + damaged_by（引用 M2 的冲合 Interaction）；`month_command(chart)`；三口径五行计数（visible/hidden_half/hidden_full）。
- **测试**：禄=临官、刃=帝旺不变量；甲日寅月 Root.grades 金测；土旺四季特判；三口径计数和守恒。
- **DoD**：roots/month_command 进 UnifiedResult 草稿。

## M4 · 旺衰（多分析器 + evidence）（1.5 天）

- **目标**：StrengthAnalyzer 协议 + Weighted/Dimensional 双实现 + agreement。
- **依赖**：M3。
- **文件**：`tianze/analysis/strength/base.py`、`weighted.py`、`dimensional.py`。
- **功能**：双分析器并行；`StrengthReport{analyzers, agreement, fact_dimensions, note}`；全部权重/阈值进 params 并标 PROJECT_HEURISTIC；每 verdict ≥1 evidence。
- **测试**：
  1. 单元：权重求和、阈值边界（ratio 恰 0.55/0.45）；
  2. 金测盘 6 个（Atlas favorable-element 的黄金盘思路：强/弱/中和恰 0.5/分歧盘）——手核分数写进注释；
  3. 不变量：evidence 非空、agreement 枚举合法、从格反条件（有根不从）；
  4. 反例测试：不允许把 project_heuristic 证据渲染成古籍引用。
- **DoD**：同一批 20 盘上双分析器 agreement 分布被记录（HIGH/LOW 都允许，DISPUTED 必须有 note）。

## M5 · 格局（1.5 天）

- **目标**：月令定格（子平真诠骨架）+ 成败四态/待复核 + 从格（反条件收紧）。
- **依赖**：M4（从格需旺衰）、M3（透干/月令）。
- **文件**：`tianze/analysis/pattern.py`。
- **功能**：定格优先级（从格 → 建禄/刃 → 本中余透干 → 本气）；比劫月令 → 建禄/阳刃（Horosa 口径）；月令逢冲/三刑 → 动摇格基（引 M2 Interaction）；issues/supports 双列表；status ∈ 成格/破格/带忌/不成格/待复核。
- **测试**：十格各 1 金测盘（含甲日寅月=建禄格——OBE 误判案例作守卫）；月令冲合生效用例；从格有根拒绝用例。
- **DoD**：格局判定可输出"为什么"证据链；争议盘进 disputed/。

## M6 · 调候（1 天）

- **目标**：120 组调候数据 + ClimateResult。
- **依赖**：M0（数据 schema）。
- **文件**：`rules/classical/qiongtong-baojian-120.json`（自录）、`tianze/analysis/climate.py`。
- **功能**：`(day_master, month) → priority_stems + condition_grades? + coverage + source`；缺数据 → coverage=missing 且输出为空。
- **测试**：覆盖率断言 120/120 非空或显式 missing；与 ruan shigan-lun.md / Horosa 速查表交叉校验报告（分歧列表人工裁决）；source 全部指向原典章节。
- **DoD**：数据文件双人工核对记录；无一条 conclusion 依赖 CC BY-NC-SA 来源。

## M7 · 规则库 + 溯源（1 天）

- **目标**：RuleRecord schema + loader + 质检三件套。
- **依赖**：M4-M6 的规则实际形态。
- **文件**：`tianze/rules/loader.py`、`rules/classical/*.json`、`tools/audit_rules.py`（命中率/矛盾/重复检测）。
- **功能**：condition 结构化 DSL；`SourceReference` 全覆盖；CONFIDENCE 三档。
- **测试**：rules.json schema 校验进 CI；100 盘命中分布审计（100% 命中=坏规则）；反义规则同盘互斥检测。
- **DoD**：任何规则可回答"出处是谁"。

## M8 · 统一 JSON + API（1 天）

- **目标**：UnifiedResult 定稿 + FastAPI。
- **依赖**：M1-M7。
- **文件**：`tianze/domain/result.py`（UnifiedResult）、JSON Schema 导出、`tianze/api/main.py`（/chart、/analysis、/schema、/health）。
- **功能**：`POST /chart` → UnifiedResult JSON（camelCase、evidence 全量、conventions 回显、meta.fallbacks）；Schema 版本化。
- **测试**：schema round-trip（dump→validate）；OpenAPI 快照；大样例 golden JSON。
- **DoD**：curl 一发可拿完整分析；文档样例"抄自真实运行"（Atlas API.md 原则）。

## M9 · Web（2-3 天，可与 M4-M7 并行启动 UI 壳）

- **目标**：输入页 / 命盘页 / 分析页（Tab：基本信息/干支/五行/十神/合冲刑害/通根透干/旺衰/格局/调候/古籍依据/证据树）。
- **依赖**：M8。
- **文件**：`web/`（Vue3+TS+Vite）。
- **功能**：调 /chart 渲染；多派对照区（schools 数组）；证据可展开；权重公式上屏（Horosa 模式）；未知时辰 UI 降级。
- **测试**：组件 golden 快照；"UI 显示与 API JSON 单源"断言（快照 round-trip）。
- **DoD**：本地 `npm run dev` + `/chart` 端到端演示录屏/截图入库。

## 后置（V1 之后）

- V2：流派层扩充（病药/通关/盲派/纳音）、大运流年与原局 Interaction、人元司令分野、用神综合 decision_policy、lunar-javascript 第三 oracle、`rules/derived/`（若决定引入 CC 数据）。
- V3：MCP Server、Agent（Horosa 行动层模式的只读先行版）。

## 与原 M1 计划（第一轮 20 项）的映射

原"第一轮实际开发目标 20 项"全部落入 M0+M1+M2：仓库(1)→M0；lunar 接入(2)/BirthInfo(3)/BaZiChart(4)/四柱(5)/干支阴阳(6,7)/藏干(8)/十神(9)→M1；五合(10)/六合(11)/六冲(12)/三合(13)/三会(14)/刑(15)/害(16)/破(17)→M2；统一 JSON(18)→M1（草稿）+M8（定稿）；单测(19)→全程；README(20)→M0。**原 M1 扩充项（来自本研究）**：crosscheck 独立路径、expected 盖章、R 约定表、conventions 回显、TimeResolution 溯源——这些不是镀金，是把"算错"与"算对但说不清"都挡在 M1。
