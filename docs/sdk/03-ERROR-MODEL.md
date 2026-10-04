# 03 · 错误模型（ERROR MODEL）

## 错误基类

```python
from tianze import TianzeError

try:
    result = analyze(birth_info)
except TianzeError as e:
    print(e.code, e.message, e.details)
```

## 错误类型

| code | 异常类 | 触发条件 |
|---|---|---|
| INVALID_BIRTH_INFO | InvalidBirthInfo | 日期/时间格式无效、超出范围 |
| UNSUPPORTED_CONVENTION | UnsupportedConvention | 请求了未实现的口径（如 true_solar） |
| KNOWLEDGE_DATA_ERROR | KnowledgeDataError | 知识库数据文件缺失/损坏 |
| ANALYSIS_UNAVAILABLE | AnalysisUnavailable | 引擎内部错误（预期外） |

## 设计原则

- SDK 不会抛裸 ValueError/KeyError——所有用户可见错误都是 TianzeError 子类
- `code` 字符串稳定（机器可判断），`message` 面向人类
- `details` 携带额外上下文（如无效输入值）
