# 09 · 规则使用报告（RULE USAGE）

> 生成：tools/analyze_rule_usage.py（确定性可重跑）。数据：knowledge/normalized/rule-usage.json

## 总览

- 可执行规则（调候）：182 条（对应 371 个引用键）
- 有 ENGINE_TRIGGERED 命例的规则：**352** 条
- 从未被任何命例匹配的规则：2 条（' + '、'.join(never_matched[:10]) + ('…' if len(never_matched) > 10 else '') + '）
- 被原书命例块明确引用的候选：17 个（引用 95 处）
- 触发 ≥2 组冲突规则的命例：0 例

## 口径警告

- **ENGINE_TRIGGERED ≠ 古人明确用了这条规则**。它只说明 Tianze 引擎对该四柱触发了该规则；
  原书是否据此判断属语义层问题，需人工复核（见 07-VERIFICATION-SYSTEM.md）。
- EXPLICITLY_CITED 来自命例块『涉及规则』字段，是原书/整理者的明确引用。

## 关系三态

| 关系 | 含义 | 信任级别 |
|---|---|---|
| EXPLICITLY_CITED | 原书明确引用 | 高（仍属整理层） |
| INFERRED_MATCH | 结构推断相关（预留，当前未自动填） | 低 |
| ENGINE_TRIGGERED | Tianze 引擎触发 | 仅作统计，不可当古籍证据 |
