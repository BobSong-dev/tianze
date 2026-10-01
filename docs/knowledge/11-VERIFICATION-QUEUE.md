# 11 · 核验队列（VERIFICATION QUEUE）

> 生成：`tools/build_review_queue` 逻辑并入 `tools/audit_verification.py`；
> 产物：`review/knowledge-review.csv`（182 行，确定性可重跑）。

## 队列设计

| 列 | 说明 |
|---|---|
| ruleId / candidateId | 规则与候选双 ID（回查锚点） |
| book / chapter / pages | 出处 |
| rawQuote | 原文引文（CLASSICAL_EXPLICIT 层） |
| normalizedTargets | 规则化后的目标干序列 |
| qualityGrade / ocrRisk | 质量等级与 OCR 风险 |
| conflictStatus | CONFLICT / NOTE / 空 |
| verificationStatus | MACHINE_CURATED（当前全部） |
| priority | 冲突(0) > OCR 高风险(1) > 有引文(2) > 条件复杂(3) > 普通(4) |
| notes | 冲突/两说说明 |

## 使用方式（真人核验流程）

1. 按 priority 升序处理（CONFLICT 最先——3 组冲突决定口径，影响面最大）；
2. 每条核验 = 对照 `sourceFile` + `pages` 回查扫描件，核对：OCR 文本？目标干提取？
   优先级？条件？例外？
3. 核验通过 → 在数据库/CSV 追加列 `humanVerifiedBy`（**必须人名**）与日期，
   并把对应 ExecutableRule 的 verification 升级为 SOURCE_ALIGNED / HUMAN_VERIFIED；
4. **工具不代填人工字段**：CSV 无 humanVerified 列，升级只能由真人提交的修订触发
   （Status Test 保证机器流程产出 HUMAN_* 即测试失败）。

## Golden Set 与队列的关系

`knowledge/golden/golden-rules.json`（43 条）是队列的**重点子集**：
十日主/四季/四库/冲突/OCR 风险/条件规则的代表样本。建议首核 Golden Set。

## 当前状态

- 队列 182 行全部 MACHINE_CURATED；
- 冲突优先行 4 条（TH-QBT-甲-06-未 / TH-QBT-甲-07-未 / TH-QBT-己-05-未 / TH-QBT-己-10-申 系）；
- OCR_RISK 行 12 条；
- HUMAN_VERIFIED：0（诚实边界，等待真人）。
