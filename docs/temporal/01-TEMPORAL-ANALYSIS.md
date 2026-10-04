# 01 · 大运/流年确定性结构分析（TEMPORAL ANALYSIS）

> 实现：`tianze/analysis/temporal.py`。M12 交付。

## 设计原则

- 复用现有 Tianze Engine，不重写算法
- 每个事实标记来源位置（natal/luck/annual）
- 只输出结构变化（TemporalDelta），不做吉凶事件预测
- 月令保持原局事实，不允许被岁运替代

## 检测范围

### 岁运关系（带来源标记）
- 岁运干与原局干：天干五合/天干冲
- 岁运支与原局支：六合/六冲/六害/六破
- 三合补齐：原局有 2 支 + 岁运补第 3 支

### 结构现象
- 伏吟：大运与原局某柱完全相同
- 反吟：大运地支与原局地支相冲
- 岁运并临：大运干支 == 流年干支
- 天克地冲：流年天干克大运天干 + 地支相冲
- 流年与原局某柱相同

## 禁止事项
- ❌ 输出吉凶（"大凶"/"发财"/"必有灾"）
- ❌ 月令被流年替代
- ❌ 自动调参迎合古籍断语

## SDK 使用

```python
from tianze import analyze, AnalysisOptions, SimplifiedBirthInfo
result = analyze(
    SimplifiedBirthInfo(date="2003-08-18", time="14:30"),
    AnalysisOptions(include_temporal=True, target_luck_index=1, target_year=2025),
)
print(result.temporal["relations"])
print(result.temporal["evidence"])
```
