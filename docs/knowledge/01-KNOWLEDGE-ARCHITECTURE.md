# 01 · 知识架构（KNOWLEDGE ARCHITECTURE）

> Tianze Classical Knowledge Integration 的总体结构。核心主张：
> **把传统文献转换成可追踪、可验证、可冲突检测、可执行的知识系统**，
> 而不是把古籍喂给 AI 让其自由发挥。

## 数据流

```text
knowledge/raw/（用户提供 zip，只读语义，不入库）
   │ tools/normalize_knowledge.py
   ▼
knowledge/normalized/{BOOK}/rules.json   ← RuleCandidate（第一层：文献整理候选，556 条）
knowledge/normalized/manifest.json       ← 文件清单/哈希/统计/ID 冲突登记
knowledge/normalized/tiaohou-draft.json  ← 程序建议草案（启发式，供人工复核）
   │ 人工复核（对照原文）→ tools/build_tiaohou_rules.py
   ▼
knowledge/rules/tiaohou/rules.json       ← ExecutableRule（第二层：可执行，182 条）
knowledge/rules/tiaohou/conflicts.json   ← RuleConflict（条件重叠登记，不静默覆盖）
   │ tianze/knowledge/loader.py（Pydantic 校验）
   ▼
tianze/analysis/tiaohou.py               ← TiaoHouAnalyzer（desired/present 分离）
   ▼
BaziChart.tiaohou（每个建议可反查：规则 → 候选 → 原文 → 书名/章节/PDF 页码）
```

## 两层规则（不可跨越）

| 层 | 载体 | 性质 | 进入条件 |
|---|---|---|---|
| RuleCandidate | normalized/ | 从文献整理出的候选，**不保证可执行** | 程序解析 + 保留全部字段与原文 |
| ExecutableRule | rules/ | 引擎可执行 | 候选 → 人工复核（curation 表）→ 结构化 conditions/effects → 校验通过 |

禁止"看到一句古籍 → 立即变成 if"。任何机器化转换必须携带
`normalizationNotes`（解释增加了什么）与 `conflictNote`（与其他规则的重叠）。

## 目录语义

| 目录 | 语义 | 入库 |
|---|---|---|
| knowledge/raw/ | 原始数据，只读；含现代今译，版权谨慎 | ✗（MANIFEST.sha256 + README 入库） |
| knowledge/normalized/ | 归一化候选数据（确定性可重跑） | ✓ |
| knowledge/rules/ | 可执行规则 + 冲突登记 | ✓ |
| knowledge/cases/ | 命例（CaseReference，evaluation 用途） | 待 M6+ |

## 文档索引

02-KNOWLEDGE-AUDIT.md（审计）· 03-RULE-SCHEMA.md（Schema）·
04-SOURCE-PROVENANCE.md（来源五级）· 05-DATA-QUALITY.md（质量等级 A-D）·
06-TIAOHOU.md（调候引擎与 10×12 覆盖）。
