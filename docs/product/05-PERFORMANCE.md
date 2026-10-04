# 05 · 性能基准（PERFORMANCE）

## SDK Benchmark

| 指标 | 值 (ms) |
|---|---|
| count | 100 |
| mean | 5.4 |
| median | 3.5 |
| P95 | 18.2 |
| max | 55.7 |

## 前端构建产物

- JS: 82.83 kB (gzip: 31.53 kB)
- CSS: 3.68 kB (gzip: 1.24 kB)

## 结论

单次 `tianze.analyze()` 平均 5.4ms，P95 18.2ms——无性能问题。
