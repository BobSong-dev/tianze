# Tianze 天泽

> 以四柱八字为核心的可验证、可溯源、多流派并列的开源命理分析引擎。
>
> **取诸家之长，统一为 Tianze。** 基础计算直接复用；成熟实现优先借鉴；算法必须可解释；规则必须可追踪；流派差异必须保留；权重与 heuristic 必须公开；有争议的地方不伪装成唯一答案；LLM 不参与确定性计算。

## 当前状态：M29 完成（0.4.0.dev0 开发线：旬空差分验证（300盘×4柱 vs lunar-python 一致）+ TR-SP-08 微根受制 + SpecialTemporalFinding label + 虚神触发率透明化 + 假从根气分布审计；可执行规则 222，质量门 23 步）；可执行规则 222，质量门 23 步）+ 六乙鼠贵三要件 + 来源治理 BLOCKED 如实化；可执行规则 222，质量门 23 步）+ 跨层一致性审计 C1-C5 全 0（质量门 22 步）+ 真从/假从两说；可执行规则 221）+ 外格虚神候选（候选永不成格）+ 命例×虚神专题审计入质量门 21 步；可执行规则 221）+ 填实规则 + 印比合去两说；可执行规则 220→221）

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
| M20 | 产品化收口（可安装 wheel + `tianze` CLI / release_check P0-P7 / clean-install smoke / Benchmark History / Web 评估对比+图视图 / README Quick Start / 版本单一事实源） | ✅ |
| M21 | 发布验证（多平台 CI 矩阵 / Provider 遥测 / CLI human 模式 / Rescue coverage 审计 / v0.3.0 本地 RC + Release History / 质量门 20 步） | ✅ |
| M22 | 产品深化（RC 全工件审计 + wheel 内容校验 / Rule Graph SVG 画布 / 遥测趋势入 compare / TR-SP-05 化神所忌 + TR-SP-07 从格受克 / 五读数实证 / Rule↔Case 联动） | ✅ |
| M23 | 知识推理深化与产品成熟化（DTZ-47 真化条件入引擎 / DTZ-06 经典造回归 / TR-DTZ-11 旺衰冲 / EV-REL-06 婚变之微 / ADR-060 版本纪律 + ADR-061 神煞去取 / Graph pan-zoom + 解释链跳转 + 评估趋势线；可执行规则 218→220） | ✅ |
| M24 | 深层干支关系与复杂格局推理（arch 拱夹/虚神 + hidden_combination 暗合关系入引擎与时序层 / TR-DTZ-10 填实·成拱·暗合 / SP-CG-E1 印比合去两说 / MLD-12 周熙造回归 / fuzz 不变量×3；可执行规则 220→221，temporal 18 条） | ✅ |
| M25 | 深层关系推理与虚神体系深化（关系级 ExplanationChain 三态 + citations 注册表 / xushiOuter 外格候选（泛化纪律：井栏叉限庚日、子邀巳不落地）/ 虚神填实 StructuralTheme / 命例×虚神审计（1045 例：拱911/暗合308/未成立144/外格15）/ AI 铁律 13 候选与 BLOCKED 约束；质量门 21 步） | ✅ |
| M26 | 虚神考证与推理体系升级（TIAN_YI 贵人表→拱贵 sub_type + 六乙鼠贵 / arch_broken 拱破·拱动两说 / cross_layer_audit 跨层一致性 1045 例全 0 入门 / SP-CG-E2 真从假从 / fuzz 重复支·arch_broken·争合；质量门 22 步） | ✅ |
| M27 | 动态格局推理与知识证据闭环（TR-SP-08 假从/假化行运之别 / arch_unfill 去填两说 / SS-R16 三要件条件化 / source_coverage 来源治理（raw 语料 BLOCKED 如实）+ Web 节点→命例导航；质量门 23 步） | ✅ |
| M28 | 复杂推理深化与全链路完善（xun_kong_of 六旬表 + 贵人空亡阻断 / _root_grade 根气分级（证据层）/ 去填并存注记 / 空亡贵人命例统计（378/1045）/ RC 本地构建验证；质量门 23 步） | ✅ |
| M29 | 复杂格局动态推理与知识体系深化（xun_kong 差分 / 微根受制两说 / findings label / 触发率透明化（随机 75% vs 语料 69% 分列）/ 假从根气分布（无根416/微根167/明根283/强根611）；质量门 23 步） | ✅ |

**测试：506 项全绿**（Python）；E2E 8 项；可执行规则 216；救应谓词 7（五读数一致）/
冲突边 4 / 流派冲突对 6；Case Replay 165 例；Audit Gates 10 门全过；一键质量门 17 步
26s；发布产物 RELEASE_NOTES/tag-prep。治理：`docs/VERSIONING.md`。详见 DECISIONS.md。


## Quick Start

### 安装

```bash
# 从仓库安装（含 CLI）
pip install -e .
tianze version
```

### CLI

```bash
# 原局分析（JSON）
tianze analyze --date 2003-08-18 --time 14:30 --gender male

# 聚焦岁运分析（大运→流年→流月）+ 事件主题
tianze timeline --date 1984-02-05 --time 10:30 --gender male   --year 2026 --month 1 --event-themes

# 导出 Markdown / HTML 报告
tianze export --date 2003-08-18 --time 14:30 --gender male --format md --out report.md

# 版本信息 / 知识库校验
tianze version
tianze validate
```

错误以 `CODE: message` 输出到 stderr（退出码 1），如 `INVALID_BIRTH_INFO: ...`。

### Python SDK

```python
from tianze import analyze, AnalysisOptions

result = analyze({"date": "2003-08-18", "time": "14:30", "gender": "male"})
print(result.pillars["day"]["stem"])          # 癸

# 岁运 + 事件主题 + 解释链
r = analyze({"date": "1984-02-05", "time": "10:30", "gender": "male"},
            AnalysisOptions(include_temporal=True, target_year=2026,
                            include_event_themes=True, include_explanations=True))
for theme in r.temporal["eventThemes"]["themes"]:
    print(theme["themeCn"], theme["status"], theme["confidence"])
```

### Web / API

```bash
pip install -e ".[api]"
.venv/Scripts/python -m uvicorn apps.api.main:app --port 8000   # API :8000
cd apps/web && npm install && npm run dev                        # Web :5173
```

配置 AI 解读：复制 `.env.example` 并设置 `TIANZE_LLM_API_KEY`（可选）。

### 开发

```bash
pip install -e ".[dev]"
python -m pytest tests apps/api/tests -q        # 测试
python tools/quality_gate.py                    # 一键质量门（17 步）
python tools/release_check.py                   # 发布前检查（构建/安装/一致性）
python tools/release_automation.py              # 发布演练（dry-run，不 push/tag）
```

数据目录：开发模式用仓库 `knowledge/`；安装模式用打包副本 `tianze/_data/knowledge`；
可用 `TIANZE_DATA_DIR` 覆盖（见 `docs/VERSIONING.md`）。



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

