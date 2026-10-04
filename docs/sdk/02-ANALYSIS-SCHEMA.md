# 02 · 分析输出 Schema（ANALYSIS SCHEMA）

> `ANALYSIS_SCHEMA_VERSION = 1.0.0`。所有字段 camelCase。

## 顶层

| 字段 | 类型 | 说明 |
|---|---|---|
| meta | object | 版本信息（engineVersion/knowledgeSchemaVersion/caseSchemaVersion/analysisSchemaVersion/lunarPythonVersion） |
| pillars | object | 四柱 {year/month/day/hour: {stem, branch, stemElement, …}}；hour 在未知时辰时缺席 |
| dayMaster | object | 日主 {stem, element, yinYang} |
| relations | list | 合冲刑害破（Interaction[]） |
| roots | list | 通根（RootEvidence[]） |
| visibility | list | 透干（StemVisibility[]） |
| monthCommand | object | 月令（MonthCommand） |
| elementCounts | object | 五行统计（ElementCounts） |
| strength | object | 旺衰（StrengthReport：三方法并列） |
| pattern | object | 格局（PatternAnalysis：候选+评估） |
| tiaohou | object | 调候（TiaoHouResult：desired/present 分离） |
| advancedAnalysis | object | 特殊格局+病药+通关（M8） |
| specialPoints | object | 胎元/命宫/身宫 |
| luck | object | 大运（DaYun[]） |
| conventions | dict | R 约定回显 |
| warnings | list[str] | 边界警告 |
| fallbacks | list[str] | 缺失能力说明 |

## options 开关

| 选项 | 关闭后字段 |
|---|---|
| include_strength=False | strength=None, monthCommand=None |
| include_pattern=False | pattern=None |
| include_tiaohou=False | tiaohou=None |
| include_special_patterns=False | advancedAnalysis=None |
| include_relations=False | relations=[] |
| include_element_counts=False | elementCounts=None, roots=[] |
