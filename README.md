# Tianze 天泽

> 以四柱八字为核心的可验证、可溯源、多流派并列的开源命理分析引擎。
>
> **取诸家之长，统一为 Tianze。** 基础计算直接复用；成熟实现优先借鉴；算法必须可解释；规则必须可追踪；流派差异必须保留；权重与 heuristic 必须公开；有争议的地方不伪装成唯一答案；LLM 不参与确定性计算。

## 当前状态：M2 完成（排盘 + 差分对拍 + 关系引擎）

| 里程碑 | 内容 | 状态 |
|---|---|---|
| Phase 0 | 7 个上游项目深度研究 + 架构设计 | ✅ `docs/research/` |
| M0 | 脚手架 + R 约定表（R1-R14）+ CI | ✅ |
| M1 | 排盘引擎（双轨道时间/DST/边界警告）+ 独立路径差分对拍 + 40 个盖章 fixture | ✅ |
| M2 | 关系引擎（合冲刑害破/三合三会/半合需中神/多重关系并存） | ✅ |
| M3+ | 通根/透干/月令 → 旺衰（多分析器）→ 格局 → 调候 → 规则库 → API → Web | 📋 `docs/research/09-V1-ROADMAP.md` |

**测试：118 项全绿**（十神 10×10 全矩阵与 lunar-python 对账、藏干逐支对账、40 fixture 回归、40+50 独立路径差分对拍、关系表完备性/守恒律/反例）。

## 快速开始

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash（Linux/macOS: source .venv/bin/activate）
pip install -e ".[dev]"
pytest -q
```

```python
import datetime as dt
from tianze.domain.models import BirthInfo
from tianze.pipeline import build_chart

chart = build_chart(BirthInfo(date=dt.date(2003, 8, 18), time=dt.time(14, 30), gender="male"))
print(chart.to_json_dict()["pillars"]["day"])   # 癸亥日：藏干/十神/纳音/地势/旬空
print([(r.label, r.positions) for r in chart.relations])  # [('申亥害', ['month','day'])]
```

## 架构一览

```text
BirthInfo → 双轨道时间（R3：年/月柱按绝对时刻，日/时柱按出生地标准时）
          → lunar-python 排盘 + Tianze 十神推导
          → 关系引擎（R9 多重关系并存 / R10 半合需中神 / R13 合化只报候选）
          → BaziChart 统一 JSON（camelCase，含 conventions 回显 / warnings / fallbacks）
          ↑ 测试网：独立路径 oracle（JDN 日柱 + 五鼠遁/五虎遁 + Meeus 黄经）差分对拍
```

- 分层与设计决策：`docs/research/05-TIANZE-ARCHITECTURE.md`、`docs/research/08-DECISION-LOG.md`
- 流派口径 R 表：`docs/CONVENTIONS.md`（改 R 必须同步改 fixture + 测试）
- 上游缺陷与勘误：`docs/ERRATA.md`
- 来源与许可：`docs/SOURCES.md`（代码 MIT；未使用任何 CC BY-NC-SA / AGPL / 无许可证代码）

## 与上游的关系（取诸家之长）

- **依赖**：lunar-python（MIT）承担历法/四柱/藏干/纳音/长生/大运底座。
- **方法论继承**：bazi-atlas（对拍/盖章/守恒律/守卫 fixture）、jiwenxu（边界警告/provenance/反例测试）、ruan（规则 schema 与质检思想）、Horosa（事实/解释分离思想，AGPL 不复制代码）。
- **独立验证**：日柱锚定外部事实（1949-10-01=甲子、2000-01-01=戊午、2024-01-01=甲子）；节气用自写 Meeus Ch.25 黄经路径交叉验证；lunar-python 的十神/藏干表被 Tianze 推导逐项对账。

## 免责声明

Tianze 是传统文化研究与工程实践项目，输出为结构化事实与规则推导，不构成任何现实建议。
