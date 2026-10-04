# 01 · SDK 设计（SDK DESIGN）

> 实现：`tianze/sdk.py`。公开 API：`tianze.analyze()`。

## 设计原则

1. **Facade 不复制分析逻辑**：SDK → Pipeline → Existing Engines（纯委托）。
2. **稳定输出**：`SimplifiedResult`（camelCase JSON）不直接暴露内部 Pydantic 模型。
3. **Partial Result**：未知时辰不 crash——hour 缺席而非猜测（R11）。
4. **Deterministic**：同输入 + 同版本 → 同输出 JSON。
5. **版本可追溯**：meta 携带 engineVersion / knowledgeSchemaVersion / caseSchemaVersion / analysisSchemaVersion。

## 层次

```text
用户代码
  ↓ tianze.analyze(SimplifiedBirthInfo, AnalysisOptions)
SDK Facade（输入校验 → 转换 → pipeline → 裁剪）
  ↓ tianze.pipeline.build_chart(BirthInfo)
Calendar Engine → Ganzhi Facts → Relation Engine → Analysis Engines
  ↓
SimplifiedResult（camelCase JSON）
```
