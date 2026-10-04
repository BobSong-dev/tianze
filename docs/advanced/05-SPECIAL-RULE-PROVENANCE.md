# 05 · 特殊格局规则溯源（SPECIAL RULE PROVENANCE）

> M8.6 交付：从格/专旺/化气/病药/通关 规则的完整来源链与验证状态。

## 1 · 从格（M8.1）

| 规则 | 来源项目 | 来源级别 | 古籍证据 |
|---|---|---|---|
| 有根不从（反条件） | jiwenxu `_detect_cong_ge` | PROJECT_REFERENCE | 滴天髓"从气不从势"概念（未核对原文） |
| 从财/从杀/从儿阈值 | Horosa `baziGejuYongShen` | PROJECT_REFERENCE | 无古籍量化标准 |
| 状态映射 | Tianze | ENGINEERING_HEURISTIC | 无 |

**阴阳干从格（M8.6.2）**：知识库搜索"从气/从势/阴干/阳干/弃命"命中 73 条候选（滴天髓补注 DTZ / 子平粹言 SPZY），但需逐条核对扫描件。**保留 UNRESOLVED**。

## 2 · 专旺格（M8.2）

| 规则 | 来源项目 | 来源级别 | 古籍证据 |
|---|---|---|---|
| 五格划分（曲直炎上稼穑从革润下） | ruan / Horosa | PROJECT_REFERENCE | 滴天髓有定性描述（DTZ-19/20/25） |
| 同党占比 ≥60% | Tianze | ENGINEERING_HEURISTIC | **无古籍量化标准** |
| 官杀透干克破 | 通行口径 | PROJECT_REFERENCE | — |

知识库命中 47 条候选（滴天髓补注为主），升级 CLASSICAL_EXPLICIT 需扫描件核校。

## 3 · 化气（M8.3）

| 规则 | 来源项目 | 来源级别 |
|---|---|---|
| 五组合候选框架 | Tianze（R13 延伸） | ENGINEERING_HEURISTIC |
| 化神得令条件 | jiwenxu `HUA_QI_CONDITIONS`（概念） | PROJECT_REFERENCE |

知识库命中 100 条候选（滴天髓补注为主）。**大量 UNRESOLVED 是正确行为**。

## 4 · 病药 / 通关（M8.4/M8.5）

| 规则 | 来源 | 级别 |
|---|---|---|
| 病准入 ≥1/2 且 ≥3 字 | Tianze | ENGINEERING_HEURISTIC |
| 制/泄药关联 | jiwenxu bingyao / Horosa 病药派 | PROJECT_REFERENCE |
| 通关对峙 ≥2 倍 | Tianze | ENGINEERING_HEURISTIC |
| 通关桥检索（五行图） | Tianze | ENGINEERING_HEURISTIC |

## 5 · 验证状态总结

| 状态 | 数量 |
|---|---|
| MACHINE_CURATED | 182（调候）+ M8 全部新规则 |
| SOURCE_ALIGNED | 0 |
| HUMAN_VERIFIED | 0 |

升级路径：review/knowledge-review.csv → 真人对照扫描件 → SOURCE_ALIGNED → HUMAN_VERIFIED。
