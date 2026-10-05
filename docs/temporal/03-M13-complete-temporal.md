# M13 · 完整岁运系统（Temporal System Complete）

状态：`IMPLEMENTED`（2026-10，M13.1–M13.11）

M13 在 M12（大运/流年关系分析 + Timeline + TenGodThemeDelta）基础上，把岁运系统补齐为
**完整状态差异分析 + 流月流日 + 知识/命例/回归/AI/Web 全链路**。

## 1. 完整 Temporal Delta（`tianze/analysis/temporal_delta.py`）

统一 Schema：`TemporalDeltaReport { context, items[], themes[], unsupportedNotes[], warnings }`。

每条 `DeltaItem`：

- `analysis`：strength / pattern / tiaohou / special / bingYao / tongGuan / tenGodTheme
- `kind`：added / removed / strengthened / weakened / status_changed / blocked / unblocked /
  disagreement_changed
- `subject`、`natalValue`、`temporalValue`、`trigger`（哪个岁运字）、`evidence`
- `supportLevel`：SUPPORTED（规则驱动、无流派分歧）/ EXPERIMENTAL（岁运参与该计算存在流派分歧）/
  UNSUPPORTED（理论上不应随岁运变化——只给说明，不硬算）
- `refId`：确定性引用串（`temporal:strength:weighted-v1`、`temporal:special:cong:从财`、
  `temporal:tiaohou:丙`、`temporal:pattern:damage:PAT-XX`……），供 AI/Web 精确引用

各比较的适用性标注（诚实边界）：

| 比较 | supportLevel | 说明 |
|---|---|---|
| strength（扩展上下文重跑三方法） | EXPERIMENTAL | 岁运字是否入旺衰计分存在流派分歧；月令维度保持原局 |
| pattern 候选重推导 | UNSUPPORTED | 格局由月令定，岁运不改变候选（显式 note，不计算） |
| pattern 评估证据增减/状态迁移 | SUPPORTED | 复用 R25 评估规则（单调性保证"新增"可归因于岁运） |
| tiaohou 用神到位/重见 | SUPPORTED | desired/present 分离口径不变；岁运带来用神 → unblocked |
| special（从格/专旺/化气） | EXPERIMENTAL | candidate 状态迁移（含 BLOCKED/解除），永不出 CONFIRMED |
| bingYao / tongGuan | EXPERIMENTAL | 通关"桥未出现，行运遇之则通"→ unblocked 事件化 |
| tenGodTheme | SUPPORTED | 只增不减（岁运不删除原局字） |

## 2. 流月 / 流日进入统一 Temporal Engine

- `TemporalSource` 增加 `monthly` / `daily`；`TemporalContext` 扩展四层干支，
  `temporal_units()` 按 大运→流年→流月→流日 迭代；三合补齐检测覆盖全部层。
- 流月窗口：`month_windows_for_year(year)` 按节气"节"划分（立春起 13 个节边界 = 12 个月窗），
  月柱 = 五虎遁 × 节序；窗口记录交节时刻（北京时间）。
- 流日：`day_pillar_for_jdn(gregorian_to_jdn(...))`（锚点 1949-10-01=甲子，独立对拍 lunar-python 60 例）。
- Timeline 升级为树：大运 → 流年 →（focus_year 展开流月）→（focus_month 展开流日）。
  非聚焦模式保持 M12 形态（回归稳定）。
- 聚焦分析：`build_focused_temporal(chart, luck_index, year, month_number, day)` 一次给出
  该选择下的完整 `TemporalAnalysis`。

## 3. TemporalCaseReference

`tools/parse_temporal_cases.py` 从 1147 个 CaseReference 解析原书岁运信息
（`knowledge/normalized/cases/temporal_refs.json`）：

- **三层分离**：`sourceTemporalAnalysis`（原书大运序列 + 文本提及，原样保留噪声）/
  `tianzeTemporalAnalysis`（缺出生信息 → 显式 not_computed，不编造）/ `historicalClaims`
  （529 条原书断言，只是 claim 不是 truth）。
- 原书大运序列内部一致性校验：相邻干支指数同向 ±1（顺/逆行）+ 年龄差 +10；
  101 例结构化（97 一致 / 3 不一致如实保留）。
- 提及解析：完整干支运（辛亥运）、单支运（午运）、流年（辛酉年）、岁君/太岁关键词。

## 4. 岁运知识规则（Knowledge Framework）

`knowledge/rules/temporal/rules.json`（10 条 ExecutableRule，domain=temporal），
`tools/build_temporal_rules.py` curation：

- 有引文链 → CLASSICAL_EXPLICIT：TR-SS-R09 日犯岁君（继善篇救应法结构化：克者→救神映射）、
  TR-SS-R10A/B 刃头财/禄头财、TR-DTZ-35 杂气引出、TR-DTZ-09 冲为重、TR-SPZY-28 流年即太岁
- 无引文链 → PROJECT_REFERENCE / ENGINEERING_HEURISTIC：伏吟/反吟/岁运并临/天克地冲
  （候选 ID 使用 TIANZE-ENGINEERING-*，validator 显式放行，不冒充古籍明文）
- 链路：Source → Quote → RuleCandidate → ExecutableRule → `evaluate_temporal_rules()` →
  `TemporalEvidence`（`TemporalAnalysis.ruleTriggers`，未触发也保留 matched=false 可审计；
  JSON 规则缺执行器直接抛错，不静默跳过）
- 效果只输出结构观察。原书吉凶断语（如"灾殃必重"）只存在于 provenance 引文注记中。

## 5. Temporal Regression

`tools/temporal_regression.py`（snapshot / compare / report）：

- 6 探针覆盖 阳男顺/阴女顺/阴男逆/阳女逆/立春前晚子时/闰日
- BREAKING：起运时刻、大运顺逆序列、流月节气窗口干支、流日干支
- REVIEW：关键流年 relations/structures/规则触发集合、Delta refId 集合、十神主题方向
- INFO：structuralChangeScore（ENGINEERING_HEURISTIC 排序值）
- 门禁测试 `tests/test_temporal_regression.py`：BREAKING ≠ 0 即失败；
  含篡改 baseline 自检（验证工具有效性）

## 6. 时间边界验证（`tests/test_temporal_boundaries.py`，24 项）

- 顺逆：4 年干奇偶 × 2 性别（R7 阳男阴女顺行）
- 起运：独立节距 vs lunar 折算线性不变量（3天=1岁，容差 = 一个 10 天档，进位自洽）
- 节气：lunar 节表 vs Meeus 黄经过点（立秋/立冬/惊蛰，±15 分钟）；
  立春 2026 ±40 分钟年柱/月柱切换
- 流月：窗口中点 vs lunar EightChar 月柱（4 年 × 12 月全对拍）；交节前后 1 分钟归属
- 流日：60 例 LCG 抽样 JDN vs lunar
- DST（1988 夏令时 ±）、海外双轨道（UTC−5，R3 年月走北京轨）、晚子时 sect1/sect2（R1）、
  闰日、大运干支 ±1 序列独立校验

## 7. Web 时序工作台

"时序"标签页：大运 → 流年 → 流月 →（可选）流日 下钻选择 → 聚焦分析 +
完整 Delta。展示：岁运链 chips、规则触发（含 observations）、新增关系（来源标签）、
结构现象、Delta 分组（kind 徽章 + EXPERIMENTAL 标记）、UNSUPported 说明、
结构主题、非预测声明。

## 8. AI 岁运解释（复用 M11，不另造系统）

- `InterpretationContext.temporal`：chain/relations/structures/matchedRules/deltaItems
  确定性提取；claim_refs 追加 `temporal:*`
- System prompt 增补第 11/12 铁律：岁运只解释不推算；禁止具体人生事件预测；
  EXPERIMENTAL 必须保留并说明流派分歧
- Grounding 新增 `TEMPORAL_PREDICTION`（一定/必然/发财/升职/结婚… 出现在 temporal section 即 ERROR）
- Web AI tab：加载岁运上下文后自动合并进解释输入

## 9. 结构主题层（StructuralTheme）

`TemporalDeltaReport.themes`：十神主题增强（财星/官杀/印星/食伤/比劫）、
冲突关系增多（新引入冲/害/破/干冲）、结构变化剧烈
（`structuralChangeScore ≥ 6`，透明公式 relations×2+structures×3，ENGINEERING_HEURISTIC，
EXPERIMENTAL）。每个主题带依据（refId 可回查）与非预测声明。
**这一层是事件推理的中间层，不是事件预测器。**

## 10. 报告导出

`tianze/export.py :: to_markdown(result_dict)`：四柱/关系/旺衰/格局/调候/高级/大运/
岁运（含 Delta 与主题）/警告 的完整 Markdown 排版。所有标注原样保留，不新增判断。

## 边界（不变）

- 岁运不替换原局月令（`TemporalContext.month_branch()` 恒取原局）
- 特殊格局候选永远是候选（CANDIDATE/LIKELY/BLOCKED/DISPUTED/UNRESOLVED）
- 不做流时；不做吉凶/事件预测；AI 不计算
