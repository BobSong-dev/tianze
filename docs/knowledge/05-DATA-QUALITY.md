# 05 · 数据质量（DATA QUALITY）

## 等级定义与当前分布

见 `04-SOURCE-PROVENANCE.md`。原则：**质量等级进入运行时 provenance**
（ExecutableRule.quality），消费方可按等级过滤；等级评定保守——
OCR 未全核时一律不给 A。

## OCR 纪律（沿用知识库自带方法论）

1. 原文照录：`Quote.rawText` 不可变；错字/衍文保留（如"丙不呸F金"类 OCR 错字）。
2. 修订分离：只能写 `correctedText` + `correction{status, reason}`；
   status ∈ none/proposed/verified——verified 需人工核对原书扫描件。
3. 风险标记：含【OCR识别待核】/"原书文字如此"的候选置 `ocrRisk=true`
   （当前 163 条，占 29%），统计进入 KnowledgeStats。
4. **禁止 LLM/程序自动"修正"原文**——分类、建议结构化、发现重复、提取候选
   是允许的；改写原文不允许。

## 质量保障流程（K1 循环）

```text
程序解析（确定性）→ 启发式草案（tiaohou-draft）→ 人工复核（curation 表）
→ ExecutableRule 构建（含 normalizationNotes）→ validate_knowledge.py
→ 规则质量测试（Schema/ID/引用/引文/覆盖/冲突/无伪造）
```

## 静态检查（tools/validate_knowledge.py）

| 检查 | 当前值 |
|---|---|
| 规则总数 / 候选总数 | 556 |
| 来源文件 | 63（不含 _文本提取 全文层） |
| 引文 / 评注 | 见 knowledge/normalized/stats.json |
| 重复候选 ID | 0（35 处冲突已加 @n 后缀并登记） |
| 重复 ExecutableRule ID | 0 |
| 无效候选引用 | 0 |
| 缺失来源 | 0 |
| CLASSICAL_EXPLICIT 无引文 | 0 |
| 调候覆盖 | 120/120（unresolved 0） |
| 冲突登记 | 3（specific-over-general / 从正文） |
| OCR 风险 | 163 |

校验失败（重复 ID/缺失来源/无效引用/无引文的 CLASSICAL_EXPLICIT）→ 退出码 1，
CI 可直接接入。

## 已知质量边界

1. OCR 未全核：B 级引文可能存在残留错字——调候目标干均为高频单字
   （丙癸庚丁壬甲戊辛己），且经 draft→人工→成品三重过，单字错识风险低但不为零。
2. 孙正治注译/赵嘉宁今译层未与徐注完全分层（commentator 已标注）。
3. 命例（530 则 + 400 组索引）未结构化（CaseReference 属后续里程碑）。
4. 知识库不含丙火/庚金/辛金/壬水/癸水五系的全部深提取命例（其索引已有）。
