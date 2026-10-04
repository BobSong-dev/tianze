# 01 · AI 架构（AI ARCHITECTURE）

AI 永远位于确定性分析之后。所有命理事实由 Tianze 引擎计算；AI 只负责解释。

```
BirthInfo
   ↓
tianze.analyze()
   ↓
Deterministic AnalyzeResult
   ↓
InterpretationContext（最小上下文，非完整 JSON）
   ↓
PromptBuilder（system + context + output schema）
   ↓
LLM Provider（OpenAI-compatible / Mock）
   ↓
Structured InterpretationResult
   ↓
Grounding Validator（程序化检查）
   ↓
Web UI / API
```

关键约束：
- AI 不参与确定性计算
- `POST /api/v1/analyze` 不受 AI 失败影响
- AI 由用户点击触发（非自动调用）
