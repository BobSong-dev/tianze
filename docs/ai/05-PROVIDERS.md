# 05 · Provider 抽象（PROVIDERS）

## 统一接口

```python
class InterpretationProvider(abc.ABC):
    async def complete(system_prompt, user_prompt) -> (raw_text, usage)
    provider_name: str
    model_name: str
```

## 当前实现

| Provider | 用途 | 说明 |
|---|---|---|
| MockInterpretationProvider | 测试/CI | 返回固定 JSON |
| OpenAICompatibleProvider | 生产 | 兼容 OpenAI/DeepSeek/各种兼容 API |

## 环境变量

| 变量 | 说明 |
|---|---|
| TIANZE_LLM_API_KEY | API Key（必设，否则 interpret 返回 503） |
| TIANZE_LLM_BASE_URL | 默认 https://api.openai.com/v1 |
| TIANZE_LLM_MODEL | 默认 gpt-4o-mini |

API Key 只存在后端环境变量。禁止前端/浏览器持有 Key。
