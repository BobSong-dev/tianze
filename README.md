# Tianze 天泽

> 以四柱八字为核心的可验证、可溯源、多流派并列的开源命理分析引擎。
>
> **取诸家之长，统一为 Tianze。** 基础计算直接复用；成熟实现优先借鉴；算法必须可解释；规则必须可追踪；流派差异必须保留；权重与 heuristic 必须公开；有争议的地方不伪装成唯一答案；LLM 不参与确定性计算。

## 当前状态：M5 完成（结构事实 + 旺衰三方法 + 格局证据化评估）

| 里程碑 | 内容 | 状态 |
|---|---|---|
| Phase 0 | 7 个上游项目深度研究 + 架构设计 | ✅ `docs/research/` |
| M0-M2 | 脚手架 / 排盘+差分对拍 / 关系引擎 | ✅ `10f98a8` |
| M3 | 通根（定性深度）/ 透干 / 月令（旺相休囚死）/ 五行两视图统计 | ✅ `29c078c` |
| M4 | 旺衰多分析器框架 + dimension 定性三维 | ✅ `6038c4a` |
| M4.2 | weighted（逐字加权 ratio）+ fuyi（规则级联）+ agreement R22 | ✅ `1d2de8a`/`07f6f6c` |
| M5 | 格局候选（禄刃/透干优先级）+ 证据化评估（supports/damages/rescues/conflicts/status） | ✅ `c2ecb16` |
| K0/K1 | 古籍知识库 Schema + 556 条候选归一化 + 校验工具（docs/knowledge/） | ✅ 本轮 |
| M6 | 调候引擎：182 条 ExecutableRule，10×12 全覆盖，desired/present 分离，反查原文 | ✅ 本轮 |
| M7+ | 规则库扩展 → API → Web | 📋 `docs/research/09-V1-ROADMAP.md` |

**测试：217 项全绿**；bazi-atlas 跨引擎实跑差分 5/5；知识库校验（validate_knowledge.py）：调候 120/120、0 重复 ID、0 缺失来源。

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

chart = build_chart(BirthInfo(date=dt.date(1983, 2, 15), time=dt.time(20, 0), gender="female"))
d = chart.to_json_dict()
d["monthCommand"]["relationToDayMaster"]   # {'state': '旺', 'inCommand': True, ...} 甲木寅月得令
[(r["statement"]) for r in d["roots"]]     # 通根证据：甲通根于月支寅（本气），月令通根 …
d["strength"]["methods"][0]["strengthEvidence"]["deShi"]  # {'result': True, 'reason': [...]}
```

## 架构一览

```text
BirthInfo → 双轨道时间（R3）→ lunar-python 排盘 + 十神推导
          → 关系引擎（R9-R14）→ 结构事实（R15-R18：根/透干/月令/统计）
          → 旺衰框架（R19：多分析器并列，当前 dimension 定性三维）
          → BaziChart 统一 JSON（conventions 回显 / warnings / fallbacks）
          ↑ 测试网：oracle 独立路径差分 + 盖章 fixture + 守恒律 + 反例
```

- 活动架构文档：`docs/ARCHITECTURE.md`；设计决策：`docs/DECISIONS.md`
- 流派口径 R 表：`docs/CONVENTIONS.md`（R1-R19；改 R 必须同步改 fixture + 测试）
- 上游缺陷与勘误：`docs/ERRATA.md`
- 来源与许可：`docs/SOURCES.md`（代码 MIT；未使用任何 CC BY-NC-SA / AGPL / 无许可证代码）

## 与上游的关系（取诸家之长）

- **依赖**：lunar-python（MIT）承担历法/四柱/藏干/纳音/长生/大运底座。
- **方法论继承**：bazi-atlas（对拍/盖章/守恒律/守卫 fixture）、jiwenxu（边界警告/provenance/反例测试/"别柱同干比肩必须计入"）、ruan（规则 schema 与质检思想）、Horosa（事实/解释分离思想，AGPL 不复制代码）。
- **独立验证**：日柱锚定外部事实（1949-10-01=甲子、2000-01-01=戊午、2024-01-01=甲子）；节气用自写 Meeus Ch.25 黄经路径交叉验证；lunar-python 的十神/藏干表被 Tianze 推导逐项对账。

## 免责声明

Tianze 是传统文化研究与工程实践项目，输出为结构化事实与规则推导，不构成任何现实建议。

