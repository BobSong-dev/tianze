# 03 · 规则 Schema（RULE SCHEMA）

> 定义于 `tianze/knowledge/models.py`（Pydantic，JSON camelCase）。
> 数据文件：`knowledge/normalized/`（候选层）、`knowledge/rules/`（可执行层）。

## RuleCandidate（第一层 · 文献候选）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | str | 沿用知识库原始 ID（QBT-甲-01）；跨文件冲突加 @2/@3 后缀，released 后不可改 |
| book / sourceFile | str | 书籍代码 + 来源 md 相对路径 |
| title / topic / coreText | str | 规则名称 / 主题 / 核心规则（照录） |
| applicableCondition / observation / reasoning / exceptions | str | 适用条件 / 需要观察 / 推理逻辑 / 例外情况（照录） |
| originalQuotes | list[str] | 原文引文（「」切分，OCR 照录） |
| commentaries | list[Commentary] | 评注层（author/text/nature，与原文严格分离） |
| source | KnowledgeSource | 书名/章节/PDF 页码/来源文件/置信 |
| contentNature | list[ContentNature] | 五类内容性质 |
| tags / quality / ocrRisk | — | 标签 / 质量等级 A-D / OCR 风险标记 |
| dayMaster / months | str/list | 程序推断（解析自 ID 与主题/适用条件） |

## ExecutableRule（第二层 · 可执行）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | str | `{DOMAIN}-{候选ID}-{月支}`（调候域），如 `TH-QBT-甲-01-寅` |
| candidateId | str | 反查候选（引用完整性受 validate 工具与测试双重检查） |
| domain | str | tiaohou / generic |
| conditions | list[RuleCondition] | 命局条件：dayMaster/monthBranch eq + 节气深浅/建禄等结构条件 |
| effects | list[RuleEffect] | needStem（specificStem+priority）/ avoidStem / note |
| exceptions / modifiers | list[RuleCondition] | 例外（如 从杀、忌癸）与修饰 |
| normalizationNotes | str | **机器化痕迹**：为什么这样拆、增加了什么解释 |
| conflictNote | str | 与其他规则的两说/重叠说明（不静默覆盖） |
| source / provenance / quality / status | — | 出处 / 分级 provenance / 质量等级 / draft\|active |

## RuleCondition

```json
{"field": "dayMaster|monthBranch|hasStem|seasonPhase|state|branchStructure",
 "operator": "eq|ne|in|not_in|exists|not_exists", "value": ...}
```

## RuleEffect

```json
{"kind": "needStem", "targetStem": "丙", "element": "火",
 "priority": "primary|secondary|tertiary", "conditionNote": "乏癸用丁"}
```

## RuleConflict（conflicts.json）

```json
{"ruleIds": ["TH-QBT-甲-06-未", "TH-QBT-甲-07-未"],
 "conditionOverlap": {"dayMaster": "甲", "monthBranch": "未"},
 "description": "五六月合论与六月专论覆盖重叠",
 "resolution": "specific-over-general"}
```

## CaseReference（命例 · evaluation 用途，非 ground truth）

`{caseId, pillars{year,month,day,hour}, source, quote, relatedRules, note}`
——知识库 530+ 命例与 400 组检索索引将在后续里程碑按此结构导入；
命例只用于规则复核与参照，**不作为训练/判定真值**。

## ID 稳定约定

- 候选 ID = 知识库原始 ID（全局唯一，冲突加 @n）。
- 可执行 ID = `TH-{候选ID}-{月支}`：格限定，同一候选覆盖多月不冲突。
- 一旦进入 released fixture：ID 冻结；废弃规则置 `status: "draft"` 而非删除。
