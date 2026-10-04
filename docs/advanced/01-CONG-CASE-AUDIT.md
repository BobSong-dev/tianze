# 01 · 从格 LIKELY 命例专项审计（CONG CASE AUDIT）

> 生成：tools/audit_cong_cases.py。数据：review/cong-likely-cases.csv（349 行）。

## 统计

- 引擎可计算命例：1147
- 从格 LIKELY 总数：**349**

| 原书对照分类 | 数量 | 占 LIKELY 比例 |
|---|---|---|
| SOURCE_SUPPORTS | 7 | 2.0% |
| SOURCE_REJECTS | 0 | 0.0% |
| SOURCE_DIFFERENT_PATTERN | 8 | 2.3% |
| SOURCE_SILENT | 118 | 33.8% |
| SOURCE_UNRESOLVED | 216 | 61.9% |

## 口径说明

- SOURCE_SUPPORTS：原书分析文本中出现从格相关关键词（从财/从杀/…）
- SOURCE_DIFFERENT_PATTERN：原书判了正格（间接否定从格——但不等于 Tianze 错）
- SOURCE_SILENT：原书有判断但未提及从格
- 原书未提及从格 **不等于** Tianze 判断错误——口径差异/详略差异均正常

## 下一步

1. 对 SOURCE_SUPPORTS：人工逐条核对原书依据是否为从格（升级验证状态）
2. 对 SOURCE_DIFFERENT_PATTERN：分析 Tianze 从格条件是否过松（可能阈值问题）
3. 对 SOURCE_SILENT：无信息，不调参
4. 禁止自动调参迎合古籍——先归因再决策