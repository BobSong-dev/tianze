# M14 · Event Theme 层：从结构变化到事件主题推理

状态：`IMPLEMENTED`（2026-10，M14.1–M14.9）

## 定位与红线

```text
Temporal Facts / Delta → Structural Theme → Event Rule（Knowledge Framework）
→ School-aware Reasoning → EventThemeCandidate → Evidence / Confidence / Disagreement
→ Case Comparison → Grounded AI → Web / Report
```

- 输出的是**事件主题候选**（"当前结构下哪类主题更值得关注"），不是事件预测。
  永远不输出「2028 年一定升职/结婚/发财」，也永远不引入 CONFIRMED 状态。
- 允许的输出形态：「官杀、印星主题同时增强，职业主题被多体系规则支持；
  同时存在伤官见官的反向证据 → DISPUTED」。
- 禁止：疾病/死亡/灾祸/赌博/投资预测；伪概率（"80% 会…"）。

## 1. 模型（`tianze/analysis/event_themes.py`）

`EventThemeReport { eventSchemaVersion=1.0.0, context, themes[], unmatchedRules[], params, warnings }`

`EventThemeCandidate`：

| 字段 | 说明 |
|---|---|
| theme | career / wealth / relationship / study / mobility / family / social |
| status | CANDIDATE / LIKELY / DISPUTED / BLOCKED / UNRESOLVED（无 CONFIRMED） |
| supportingEvidence / opposingEvidence | 逐条结构证据（含岁运层来源） |
| triggeredRules | EventRuleHit（ruleId/label/view/direction/evidence/provenanceLevels/refId） |
| schoolViews | view → support / oppose / both（流派方向，冲突不合并） |
| agreement | HIGH（≥2 view 同向）/ PARTIAL / CONFLICT（同 view 内双向） |
| confidence | 0..1 透明加权；params 随结果输出（ENGINEERING_HEURISTIC，非概率） |
| temporalRefs / refId | `event:{theme}`、`event:rule:{id}` 供 AI/Web 精确引用 |

status 语义：

- LIKELY：≥2 个不同流派视角同向支持，无反对
- CANDIDATE：单视角支持/反对
- DISPUTED：支持与反对并存（agreement=CONFLICT，分歧显式保留）
- BLOCKED：存在 block 方向命中
- UNRESOLVED：规则命中但关键输入缺失（如性别未知 → 配偶星规则不猜）

## 2. 事件规则（`knowledge/rules/event/rules.json`，16 条）

链路：Source → Quote → RuleCandidate → ExecutableRule(domain=event) → EventRuleHit。
evaluator 与规则 JSON 一一对应（缺失即抛错）；未命中规则保留在 unmatchedRules 可审计。

引文锚点（CLASSICAL_EXPLICIT）：MLD-18（夫妻宫/夫星/妻星）、DTZ-39（伤官见官）、
SS-R10（刃头财「因财启争」）、SS-R22（神煞去取「驿马咸池半推详」）、DTZ-09（冲为重）、
DTZ-33（官杀制化/化煞用印）、DTZ-35（财库喜冲不可靠——两说）、DTZ-04/05/06（从格两说）。

无引文链规则 → PROJECT_REFERENCE/ENGINEERING_HEURISTIC + TIANZE-ENGINEERING-* 候选 ID。

| 主题 | 规则 |
|---|---|
| career | EV-CAR-01 官星透+主题增强、EV-CAR-02 官印相生、EV-CAR-03 伤官见官(oppose) |
| wealth | EV-WEA-01 财星透+主题增强、EV-WEA-02 刃头财/比劫夺财(oppose)、EV-WEA-03 财库逢冲(两说) |
| relationship | EV-REL-01 夫妻宫逢合、EV-REL-02 夫妻宫逢冲(oppose)、EV-REL-03 配偶星(性别条件)、EV-REL-04 咸池桃花(shensha) |
| study | EV-STU-01 印星透+主题增强 |
| mobility | EV-MOB-01 驿马临/冲(shensha)、EV-MOB-02 冲提纲 |
| family | EV-FAM-01 年月柱天克地冲 |
| social | EV-SOC-01 比劫临/主题增强 |
| special | EV-CON-01 从格岁运破格（主题按类型映射：从财→wealth 等，evaluator override） |

神煞规则（驿马/桃花）单独 shensha view：SS-R22 的反对声音（子平尽删神煞）随规则
conflictNote 保留，confidence 权重低，不与其他 view 合并成强结论。

## 3. Confidence（透明，非概率）

`confidence = (Σ provenanceWeight(support) + multiViewBonus − opposingPenalty×n − blockPenalty×n) × scale`
（CLASSICAL_EXPLICIT=2.0 / PROJECT_REFERENCE=1.0 / ENGINEERING=0.5；multiViewBonus=0.25；
opposingPenalty=0.5；blockPenalty=0.7；scale=0.3；cap=1.0。参数随结果输出。）
**禁止以百分比概率口吻输出**——它是可审计的加权值，不是统计概率。

## 4. Historical Claims ↔ Event Themes

`tools/parse_event_claims.py`：529 条 historicalClaims → 373 条带主题标注
（career 277 / wealth 73 / family 51 / study 35 / mobility 21 / relationship 18 / social 9，
多主题并存不强行单选），38 条敏感断语（死亡/疾病等）只保留 claim 不建主题，
20 条与原书岁运干支共现。历史事件不是 ground truth；**不为了匹配案例调整规则**。

## 5. Event Evaluation（`tools/event_evaluation.py` → `regression/event-evaluation.json`）

- 6 场景探针：多体系一致 / 多体系冲突 / shensha-only / unknown hour / 财库 / 女命官星
- 随机盘 200 例触发率审计（阈值：规则 >60% 或主题 >70% → REVIEW）：
  当前最高 EV-MOB-01 26.5%、主题最高 relationship 42.5%，无异常
- 指标：rule coverage、theme distribution、disagreement rate、unresolved rate、
  source quality、historical coverage 对照

## 6. Timeline / Web / AI / 导出

- 事件主题**惰性接入** Timeline：时序工作台选择 大运→流年→流月（→流日）后按需计算，
  不做 80 年×12 月×每日全量预展开（性能纪律：进程内、纯函数、无 Redis/Celery）。
- Web「事件主题」区：status 徽章（受控词汇，无 CONFIRMED）、多体系一致/冲突徽章、
  confidence（标注非概率）、schoolViews、支持/反对证据折叠。
- AI：InterpretationContext.event_themes + `event:*` claim refs；system prompt 第 13 铁律；
  grounding 新增 EVENT_PREDICTION（事件断言/伪概率语言拦截）。
- `to_markdown` 导出事件主题段（status/agreement/confidence/证据）。

## 7. 确定性

- 规则/评估器纯函数；输出集合全部排序（temporalRefs/schoolViews/unmatchedRules）
- historicalClaims refId 用 md5（不用随进程变化的 hash()）
- 同输入同版本 → EventThemeReport JSON 逐字节一致（测试锁定）
