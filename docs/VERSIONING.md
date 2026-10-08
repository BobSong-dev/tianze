# Tianze 版本与迁移治理（Versioning）

## 版本面

| 域 | 当前 | 位置 |
|---|---|---|
| engine | 0.4.0.dev0 | `tianze.__version__`（pyproject dynamic 绑定，单一事实源；已发布 tag v0.3.0 冻结于 5821c84） |
| knowledge | 1.1.0 | KNOWLEDGE_SCHEMA_VERSION |
| case | 1.0.0 | CASE_SCHEMA_VERSION |
| analysis | 1.0.0 | AnalysisSchemaVersion |
| delta | 1.0.0 | DELTA_SCHEMA_VERSION |
| event | 1.0.0 | EVENT_THEME_SCHEMA_VERSION |
| interpretation / prompt | 1.1.0 / 1.1.0 | ai/models.py |

依赖关系经 `/api/v1/knowledge/stats#versionDependencies` 机读。

## 规则

1. **Breaking schema change 必须显式 bump 对应版本**——禁止静默兼容。
2. 迁移走 `tools/migrate_knowledge.py`：默认 dry-run；`--write` 只产出
   `.migrated` 副本（内嵌 rollback 元数据）并记录 `regression/migration-history.jsonl`；
   人工确认后才替换原文件。
3. **陈旧工件检测**：`/api/v1/knowledge/release#stale` 比较 metadata gitCommit 与
   HEAD；dirty 工作区也标记。stale 元数据不得直接引用为发布数据——重跑
   `quality_gate.py` + `release_metadata.py`。
4. 工件 schemaVersion 必须在兼容矩阵（tests/test_version_compat.py）内。
5. HUMAN_VERIFIED 永远不由机器产生（Review Queue 只汇总）。
