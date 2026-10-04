# CASE-REGRESSION · 命例领域回归系统（M8.0）

> 实现：`tools/case_regression.py`（snapshot | compare | report）。
> 产物：`regression/baseline/snapshot.json`、`regression/report.{json,md}`。

## 1 · 定位

CaseReference 不只是数据库——从 M8.0 起，1147 个命例（1045 可运行）成为
**Tianze 每一次规则修改的领域回归系统**。任何引擎变更后：
`compare` 命令立即报告哪些命例的哪些字段发生了什么变化。

## 2 · Snapshot Contract（ADR-034）

| 字段 | 类型 | 说明 |
|---|---|---|
| caseId | str | 命例唯一 ID |
| chartFingerprint | str\|null | 四柱哈希（BREAKING 检测） |
| unresolved | bool | 四柱不可解析 |
| strength | dict | {dimension, weighted, fuyi} → verdict |
| agreement | str\|null | 多方法 agreement |
| patternCandidate / patternStatus | str | 正格候选/状态 |
| tiaohouTargets | list[str] | 调候目标干 |
| tiaohouPrimaryPresent | bool\|null | 主目标是否在命局 |
| triggeredRuleIds | list[str] | 引擎触发的规则 ID |
| specialPattern | dict | M8.1/M8.2 从格+专旺结果 |
| bingYao | dict | M8.4 病药结果 |
| tongGuan | dict | M8.5 通关结果 |
| warnings | list[str] | 引擎警告 |

**设计原则**：只保留可判断行为变化的稳定字段，不无脑复制完整 JSON。

## 3 · Severity 四级

| 级别 | 含义 | 示例 |
|---|---|---|
| **BREAKING** | 排盘四柱变化 | chartFingerprint 变化 |
| **REVIEW** | 既有结论变化 | weighted 从偏弱→中和；pattern 候选改变；规则触发集变化 |
| **EXPECTED** | 新模块首次产生结果 | specialPattern/bingYao/tongGuan 首次非空 |
| **INFO** | 新增解释字段 | agreement 值变化、tiaohouPrimaryPresent 变化 |

## 4 · 使用方式

```bash
python tools/case_regression.py snapshot   # 生成 baseline
# ... 修改代码 ...
python tools/case_regression.py compare    # 对比 baseline
python tools/case_regression.py report     # 查看人类可读报告
```

## 5 · 纪律

- Regression **不裁决**"新版本对还是旧版本对"——只回答"发生了什么变化"
- 发现 REVIEW/BREAKING → 逐条归因（R 表变更/参数调整/bug）→ 修复后重新 snapshot
- 不自动回滚

## 6 · 统计口径（ADR-031）

`caseCount` = 案例数；`comparisonItemCount` / `agreementItemCount` / `differenceItemCount` = 比较项数。
一例可同时产生一致项与差异项——案例数与比较项数**不混用**。
