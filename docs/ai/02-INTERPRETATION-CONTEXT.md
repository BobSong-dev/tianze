# 02 · 解释上下文（INTERPRETATION CONTEXT）

从 AnalyzeResult 提取的解释所需最小上下文。

## 层次区分

| FactType | 含义 | 示例 |
|---|---|---|
| FACT | 原始事实 | 日主癸（WATER·YIN） |
| DERIVED_FACT | 派生事实 | 癸通根于日支亥（本气） |
| METHOD_RESULT | 某方法结论 | weighted = 中和 |
| CANDIDATE | 高阶候选 | 从财 LIKELY |

## 只注入触发内容

某命盘调候触发 `TH-QBT-甲-01-寅` → 只注入该规则的 rule/quote/source/verification，不注入整本《穷通宝鉴》。
