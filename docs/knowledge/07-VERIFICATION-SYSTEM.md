# 07 · 验证体系（VERIFICATION SYSTEM）

> 原则：**机器整理 ≠ 人工核验**。任何知识条目都能回答：
> 这是原文事实？注家观点？Tianze 推导？机器整理？还是真人已核验？
> 生成：`tools/audit_verification.py`（确定性）；统计：`knowledge/normalized/verification-audit.json`。

## 1 · 验证状态（VerificationStatus）

| 状态 | 定义 | 本库当前量 |
|---|---|---|
| UNREVIEWED | 未审视 | — |
| MACHINE_EXTRACTED | 程序解析未整理 | 1147 命例 |
| MACHINE_CURATED | 程序/AI 整理（含 M6 curation） | 182 调候规则 |
| SOURCE_ALIGNED | 与来源文本逐字对齐（未判解释正确性） | 0 |
| HUMAN_VERIFIED | 真人逐条核验（verifiedBy=人名） | 0 |
| HUMAN_VERIFIED_PRIMARY_SOURCE | 真人对照一手扫描件核验 | 0 |

**机器不得伪造 HUMAN_***：Schema 级强制（`VerificationRecord._no_fake_human` 校验器——
HUMAN_* + pipeline 署名直接抛错），并有 Status Test。

### 诚实更正（M6.1）

M6 报告中的"人工复核 curation"实为 **AI 完成**。已全部降级标记：
`status=MACHINE_CURATED, method=ai_curation, verifiedBy=tianze-pipeline:build_tiaohou_rules.py`。

## 2 · 四个独立概念（AccuracyMatrix，禁止混淆）

| 维度 | 问题 | 调候规则当前值 |
|---|---|---|
| traceability | 能否找到出处 | PASS ×182 |
| textAccuracy | OCR 文本与 PDF 是否一致 | UNVERIFIED ×170 / OCR_RISK ×12 |
| interpretationAccuracy | 结构化是否准确表达原文 | MACHINE_CURATED ×182（升级须真人） |
| engineAccuracy | 引擎是否正确实现 | TESTED ×182（test_tiaohou.py） |

## 3 · 来源三层 provenance（182 条规则全部一致）

1. `PROJECT_REFERENCE`：徐乐吾知识库条目（候选 ID）；
2. `CLASSICAL_EXPLICIT`：原文引文（穷通宝鉴口诀，页码定位）；
3. `TIANZE_NORMALIZATION`：AI 整理层（目标干提取/优先级/条件结构化）——
   明确区分"原文说的"与"机器化增加的解释"。

## 4 · 182 条调候规则验证矩阵

| 统计 | 值 |
|---|---|
| 规则总数 | 182 |
| 可追踪来源 | 182/182 |
| 原文引文存在 | 182/182 |
| OCR 风险 | 12 |
| 整理注释（normalizationNotes） | 182 |
| 冲突注记（conflictNote） | 3 |
| 引擎测试覆盖 | 182/182 |
| 人工核验 | **0** |

## 5 · Golden Verification Set（`knowledge/golden/golden-rules.json`）

43 条重点人工核验候选——**不是自动宣布正确**，是核验优先集合：
- 十日主覆盖 ×10；四季 ×4；四库月 ×4；
- 已知冲突 3 组全部进入（甲未/己申/己未）；
- OCR 高风险 ≥10；条件规则（雨水后/白露秋分/大暑/清明谷雨/建禄/从杀例外）≥5。

## 6 · 升级规则（05-DATA-QUALITY.md 补充）

- **A 级准入**：一手 PDF 核对 + OCR 文本核实 + 规则解释核实 + 页码核实，四项全过才可 A；
- 机器自动流程最高只能给 **B**（本库上限就是 B）；
- 升级 SOURCE_ALIGNED：与来源文本逐字对齐（可程序辅助）；
- 升级 HUMAN_VERIFIED：真人逐条（verifiedBy 必须人名，工具不代填）；
- 从 review/knowledge-review.csv 按 priority 顺序人工核验（冲突 > OCR 风险 > 有引文 > 条件复杂 > 普通）。
