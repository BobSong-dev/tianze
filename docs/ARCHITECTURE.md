# Tianze 架构（现行实现状态）

> 本文是**随实现演进的活动文档**；Phase 0 的完整架构设计见 `docs/research/05-TIANZE-ARCHITECTURE.md`，设计决策见 `docs/DECISIONS.md`（Phase 0 的 ADR-001~015 在 `docs/research/08-DECISION-LOG.md`）。
> 当前版本：0.2.0 · ENGINE_STAGE = M5。旺衰三方法详见 `docs/STRENGTH.md`；格局详见 `docs/PATTERN.md`。

## 数据流（已实现部分）

```text
BirthInfo（date/time/gender/tz/sect/口径）
   ↓ L1 calendar（lunar-python 适配）
双轨道时间（R3：年/月柱按绝对时刻北京时间，日/时柱按出生地标准时 + DST R12）
   ↓ L2/L3 domain + ganzhi
BaziChart：四柱/藏干/十神/纳音/十二长生/旬空/胎元命宫身宫/大运（R1/R5/R7/R8/R11）
   ↓ L4 relation（R9-R14）
Interaction[]：合冲刑害破 / 三合三会 / 半合（需中神）/ 多重关系并存 / 合化只报候选
   ↓ L7 analysis 结构事实（R15-R18）
roots[]（通根，定性深度） · visibility[]（透干事实） · monthCommand（旺相休囚死+证据）
elementCounts（visible/hidden 两视图） ·
   ↓ L7 strength 框架（R19）
strength.methods[]（当前仅 dimension：得令/得地/得势定性三维，零评分）
   ↓
Unified JSON（camelCase + conventions 回显 + warnings + fallbacks）
   ↑ 横切测试网：40 盖章 fixture + oracle 独立路径差分（91 项对拍）+ 守恒律 + 反例
```

## 模块地图

| 路径 | 层 | 职责 | R 约定 |
|---|---|---|---|
| `tianze/calendar/` | L1 | lunar 适配、双轨道时间、DST、边界警告、节气表归一化 | R1-R4, R11, R12 |
| `tianze/domain/models.py` | L2 | Pydantic 契约（camelCase JSON） | 全部 |
| `tianze/ganzhi/tables.py` | L3 | 干支/藏干/十神推导（与 lunar 表对账） | R8 |
| `tianze/relation/` | L4 | 关系表 + 扫描器 | R9-R14 |
| `tianze/analysis/roots.py` | L7 | 通根事实（定性深度，零权重） | R15 |
| `tianze/analysis/visibility.py` | L7 | 透干事实 | R18 |
| `tianze/analysis/month_command.py` | L7 | 月令（按月支本气判旺相休囚死） | R6/R17 |
| `tianze/analysis/element_counts.py` | L7 | 五行两视图统计 | R16 |
| `tianze/analysis/strength/` | L7 | 旺衰框架 + dimension/weighted/fuyi 三分析器 | R19-R22 |
| `tianze/analysis/pattern.py` | L7 | 格局候选（禄刃/透干优先级）+ 证据化评估 | R23-R25 |
| `tianze/pipeline.py` | — | 组装 build_chart | — |
| `tests/crosscheck/oracle.py` | 测试网 | 独立排盘路径（JDN/遁/Meeus 黄经） | — |
| `tools/stamp_expected.py` | 测试网 | fixture 盖章器 | — |
| `tools/atlas_differential.mjs` | 测试网 | bazi-atlas 跨引擎差分桥（实跑 5 命例） | — |

## 尚未实现（按路线图）

L5 规则库（M7）· L8 流派层（M5 格局起逐步并入）· 调候（M6）· L10 API（M8）· L11 AI（M8 后）· L12 Web（M9）。

## 铁律（不变）

1. 事实（L1-L5）不带观点；分析（L7+）必须引用 R 规则与结构事实。
2. 权重/阈值 = 公开常量 + PROJECT_HEURISTIC 标注（如 `DE_SHI_THRESHOLD`）。
3. 任何回退/缺席（未知时辰等）必须写入 `meta.fallbacks`。
4. 改 R 必须同步改 fixture + 测试（CONVENTIONS 维护记录留痕）。
