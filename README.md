# Tianze 天泽

> 以四柱八字为核心的可验证、可溯源、多流派并列的开源命理分析引擎。
>
> **取诸家之长，统一为 Tianze。** 基础计算直接复用；成熟实现优先借鉴；算法必须可解释；规则必须可追踪；流派差异必须保留；权重与 heuristic 必须公开；有争议的地方不伪装成唯一答案；LLM 不参与确定性计算。

## 当前状态：M19 完成（发布自动化、Dashboard 完整化、五读数救应、评估闭环）

| 里程碑 | 内容 | 状态 |
|---|---|---|
| Phase 0 | 7 个上游项目深度研究 + 架构设计 | ✅ `docs/research/` |
| M0-M2 | 脚手架 / 排盘+差分对拍 / 关系引擎 | ✅ |
| M3 | 通根 / 透干 / 月令 / 五行统计 | ✅ |
| M4 | 旺衰三方法（dimension / weighted / fuyi） | ✅ |
| M5 | 格局候选 + 证据化评估 | ✅ |
| K0/K1/M6 | 古籍知识 Schema + 调候 120 格 | ✅ |
| M6.1 | 验证体系（MACHINE_CURATED / HUMAN_VERIFIED 严格分离） | ✅ |
| M7 | 1147 命例结构化 + Rule↔Case 双向索引 | ✅ |
| M8 | 特殊格局（从格/专旺/化气）+ 病药 + 通关 + Case Regression | ✅ |
| M8.6 | 从格审计 / 阴阳干证据 / PopulationStats | ✅ |
| M9 | SDK Facade (`tianze.analyze()`) | ✅ |
| M10 | FastAPI + Vue 3 Web + Contract Tests | ✅ |
| M11 | Grounded AI 解释层（claim_refs + Grounding Validator） | ✅ |
| M12 | 岁运基础（大运/流年关系 + Timeline + 十神主题） | ✅ |
| M13 | 完整岁运系统（Temporal Delta / 流月流日 / TemporalCaseReference / 岁运规则 / Temporal Regression / 时间边界 / Web 时序工作台 / AI 岁运 / StructuralTheme / 报告导出） | ✅ |
| M14 | 事件主题层（Event Rule Framework / School-aware Reasoning / EventThemeCandidate / Confidence / Event Evaluation / Grounded AI / Web / 导出） | ✅ |
| M15 | 成熟推理层（方向级 Rule Conflict / 从格专旺化气岁运专题 / Historical Case Replay / Real-provider AI Evaluation / 打印 HTML 报告 / Timeline memoization / Property-Fuzz 门 / Review Queue） | ✅ |
| M16 | 条件化推理（救应谓词 / SPECIFIC_EXCEPTION 启用 / Rule-ID Conflict Graph / 全链路可解释性 / Knowledge Explorer API+Web / Review Queue API / AI Evaluation History / Schema Migration 1.1→1.2） | ✅ |
| M17 | 产品化（ExplanationChain SDK/Web/HTML / 多方法一致救应 / 原文岁运 span 解析 / Audit Gates ×10 / Coverage Workbench / Migration governance / 真实规模 benchmark） | ✅ |
| M18 | 发布工程（Graph/Rule Audit 报告 / 原文解析 OCR 容错+一运多年 / Release Metadata JSON+MD / 版本兼容矩阵 / Funnel 端点 / Replay 链对照 / 一键质量门 14 步） | ✅ |
| M19 | 产品闭环（Release Automation changelog/notes/tag-prep / Web Quality-Coverage Dashboard / AI Eval Compare 回归检测 / 五读数救应 / Stale 工件检测 / VERSIONING 治理 / 质量门 17 步） | ✅ |

**测试：506 项全绿**（Python）；E2E 8 项；可执行规则 216；救应谓词 7（五读数一致）/
冲突边 4 / 流派冲突对 6；Case Replay 165 例；Audit Gates 10 门全过；一键质量门 17 步
26s；发布产物 RELEASE_NOTES/tag-prep。治理：`docs/VERSIONING.md`。详见 DECISIONS.md。

## Web 应用

```bash
# 启动 API
cd apps/api && uvicorn main:app --reload --port 8000

# 启动前端（另一个终端）
cd apps/web && npm run dev
```

打开浏览器 → `http://localhost:5173` → 输入出生信息 → 查看完整分析。
每个结论可展开"为什么"→ 查看规则来源 → 古籍原文 → 页码 → 验证状态。

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

