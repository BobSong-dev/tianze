# 10 · 命例数据模型（CASE MODEL）

> 实现：`tianze/knowledge/cases.py`；schema 版本 `CASE_SCHEMA_VERSION=1.0.0`
> （`cases-manifest.json` 记录；字段变更必须走显式 migration，禁止静默改 JSON）。

## CaseReference

| 字段 | 说明 |
|---|---|
| caseId | `CASE-{原块ID}` / `CASE-IDX-nnnn`；跨文件冲突加 @n（released 后冻结） |
| source | KnowledgeSource（书/章节/PDF 页/来源文件） |
| fact | **CaseFact**：pillars（OCR 照录）/gender/birthText/name/**unresolved** |
| sourceAnalysis | **SourceAnalysis**：verdict（作者判断照录）/steps（AUTHOR_INTERPRETATION 层）/events（HISTORICAL_CLAIM 层）/purpose/dayun |
| tianzeAnalysis | **TianzeAnalysis**：引擎派生（strengthVerdicts/patternCandidate/patternStatus/tiaohouTargets/engineRuleIds），computed=false 表示未跑或不可解析 |
| ruleReferences | `[{ruleId, relation}]`——relation ∈ EXPLICITLY_CITED / INFERRED_MATCH / ENGINE_TRIGGERED |
| identity | CaseIdentity（四柱有序+姓名+书籍；**不做文本 hash**） |
| possibleDuplicates | 候选重复（**只登记不合并**） |
| verification | VerificationRecord（机器流程 MACHINE_EXTRACTED） |
| quality | B（结构化块有页码）/ C（索引行整理层） |
| rawBlockId / sourceFile | 回查锚点 |

## 三层数据（禁止混淆）

| 层 | 类型标记 | 例 |
|---|---|---|
| Case Fact | fact 字段 | 四柱"庚申·甲申·己丑·癸酉"；"咸丰十年六月廿七日酉时" |
| Author Interpretation | AUTHOR_INTERPRETATION | "支成金局，癸透有根，大富贵，总握财枢" |
| Historical Claim | HISTORICAL_CLAIM | "总握财枢（原书断语）"、"某年登科" |

Historical Claim **不是已验证的真实世界事实**，永不自动置 verified。

## 用途边界（M7 纪律）

命例用于：reference / rule usage study / cross-check / regression candidate。
**禁止**：输入八字 → 古籍结论 = label 的监督学习用法；把古籍事件当 verified truth；
把 ENGINE_TRIGGERED 冒充"古人明确用了这条规则"。

## 工具链（全部确定性、失败退出码非零、不改 raw）

| 工具 | 产出 |
|---|---|
| tools/normalize_cases.py | normalized/cases/*.json + cases-manifest.json（输入 hash/pipeline 版本/schema 版本） |
| tools/derive_case_analysis.py | tianzeAnalysis 填充 + indexes/cases/{byRule,byDayMaster,byMonthBranch,byBook}.json |
| tools/validate_cases.py | ID 唯一 / 双分析分离 / 事件分层 / 无伪造 HUMAN_* |
| tools/compare_cases.py | case-comparisons.json（agreements/differences/unresolved，不裁决） |
| tools/analyze_rule_usage.py | rule-usage.json + docs/knowledge/09-RULE-USAGE.md |

## 结构化检索（非 RAG）

`find_rules(dayMaster, month)` = `knowledge/rules/tiaohou/rules.json` 条件过滤；
`find_cases(ruleId)` = `indexes/cases/byRule.json`。**不做 embedding/vector db**
——结构化检索已满足当前需求。
