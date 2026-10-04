# 06 · UX 状态审计（UX STATES）

## 当前覆盖

| 状态 | 展示方式 |
|---|---|
| empty | 初始状态，仅显示输入表单 |
| loading | "正在分析命局结构…"（非假进度条） |
| success | 完整结果 + 四柱 + 各 Tab |
| partial | 未知时辰 → 3 柱 + fallbacks 列表 |
| warning | 边界警告（晚子时/DST/节气临界） |
| error | 红色 .error div，区分输入/服务/知识库 |
| unresolved | 化气 UNRESOLVED → "资料不足" |
| disputed | 旺衰 agreement → PARTIAL/DISPUTED 展示 |
