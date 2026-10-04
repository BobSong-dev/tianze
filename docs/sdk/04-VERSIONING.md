# 04 · 版本管理（VERSIONING）

## 版本链

| 版本 | 说明 | 更新时机 |
|---|---|---|
| engineVersion | `tianze.__version__`（如 0.2.0） | 每次发版 |
| engineStage | 里程碑标记（如 M9） | 每个里程碑 |
| analysisSchemaVersion | SDK 输出 Schema 版本（1.0.0） | **外部可见字段变更** |
| knowledgeSchemaVersion | 知识库 Schema 版本（1.1.0） | knowledge/ 字段变更 |
| caseSchemaVersion | 命例 Schema 版本（1.0.0） | cases/ 字段变更 |

## Deterministic Contract

同输入（BirthInfo + AnalysisOptions）+ 同版本 → 同 JSON 输出。
测试：`test_json_serialization_deterministic`。

## Migration 纪律

- analysisSchemaVersion bump → 必须提供 migration note（本文件追加变更表）
- knowledgeSchemaVersion bump → 必须提供数据迁移脚本
- 禁止静默改 JSON 字段导致旧数据失效

## 变更记录

| analysisSchemaVersion | 变更 | 日期 |
|---|---|---|
| 1.0.0 | 初版 SDK 公开 Schema | 2026-10-01 |
