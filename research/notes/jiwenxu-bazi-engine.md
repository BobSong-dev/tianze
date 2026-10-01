# jiwenxu-bazi-engine 研究笔记

- 上游仓库：GitHub `jiwenxu025-boop/bazi-engine`（本地只读克隆：`C:\Project\tianze\research\upstream\jiwenxu-bazi-engine`）
- 研究日期：2026-09-30（Phase 0 研究之夜，只读上游、只写本笔记）
- 版本：`scripts/pyproject.toml:2` 声明 `version = "0.18.0"`；本地克隆为浅克隆，仅 1 个提交 `4fdcc06`（2026-08-06，"fix: remove report guidance copy"），无法追溯历史。
- 所有行号引用格式为 `文件:行号`，相对路径省略前缀 `C:\Project\tianze\research\upstream\jiwenxu-bazi-engine\`。

---

## 1. 仓库概览（语言/规模/目录结构/最后提交/LICENSE/部署形态）

- **语言/规模**：纯 Python（>=3.12，实跑 3.13，`scripts/pyproject.toml:12`）+ 静态前端。Python 共约 **31,211 行**（含测试 9,153 行，44 个测试文件）；引擎包 `scripts/bazi_engine/` 约 20,374 行；前端 HTML/CSS/JS 约 5,543 行。
- **目录结构**：
  - `scripts/bazi_engine/` —— 引擎主体（四柱/格局/用神/调候/大运/流年/性格/神煞/API/CLI）；
  - `scripts/bazi_engine/liunian/` —— 流年事件扫描子包（scanner + 10 个事件探测器 + battle/signal/features）；
  - `scripts/bazi_engine/personality_analysis/` —— 性格与家境分析子包；
  - `scripts/tests/` —— pytest 测试 + 4 个校准脚本（marriage/career/wealth/others）；
  - `frontend/` —— 纯静态 SPA（index.html + app.js + chat 面板），走 `/api/chart/stream` SSE；
  - `references/` —— 8 份规则参考 md（声称"均已编码至引擎"，`references/README.md:5-15`）；
  - `docs/` —— architecture / time-basis / calibration-protocol / operations / lint-debt 等；
  - `SKILL.md` —— Claude Code Skill 入口（把引擎包成 Claude 技能，LLM 只做确认与解读，`SKILL.md:10-12`）。
- **最后提交**：`4fdcc06`，2026-08-06，作者 jiwenxu025。
- **LICENSE**：MIT，版权行 "Copyright (c) 2026 jiwenxu025-boop"（`LICENSE:3`）。可自由复用。
- **部署形态**：
  - `Dockerfile`：python:3.13-slim，非 root 用户，`EXPOSE 7860` + healthcheck `/api/health` —— 7860 是 **Hugging Face Spaces** 的默认端口；
  - `Procfile:1`：`web: cd scripts && BAZI_PUBLIC=true python -m uvicorn bazi_engine.api:app --port ${PORT:-8080}` —— **Railway/Heroku** 形态；README 亦给出 Railway 部署步骤（`README.md:173-187`）。
  - 结论：这是一个**已公开上线的 Web 服务**（FastAPI 全包在 `api.py` 1672 行），不是纯库。依赖仅 6 个：fastapi/uvicorn/httpx/ephem/beautifulsoup4/lxml（`requirements.txt`）。

---

## 2. 架构与模块划分

### 2.1 各文件职责（据源码验证，非 README 转述）

| 文件 | 职责 | 验证 |
|---|---|---|
| `enums.py` | 天干/地支/五行/十神枚举 + 干支五行表 + 禄位 `TIANGAN_LU`、羊刃 `TIANGAN_YANGREN` 表 | enums.py:6-147 |
| `_constants.py` | 全部静态查表：五合/六合/三合/半合/三会/六冲/刑/害/藏干/长生/神煞/纳音/空亡/从格文案/化气条件 | _constants.py:1-631 |
| `solar_terms.py` | ephem 太阳黄经迭代求 12 节精确时刻；无 ephem 回退近似表 | solar_terms.py:44-93,160-211 |
| `pillars.py` | 年/月/日/时柱；JDN 日柱公式；五虎遁/五鼠遁；23 点日柱进位 | pillars.py:20-152 |
| `time_resolution.py` | 真太阳时口径（NOAA 均时差 + 经度校正），区分"出生瞬间"与"排盘时间"两条时间线 | time_resolution.py:85-158 |
| `ten_gods.py` | 十神判定 + 五行生克函数 | ten_gods.py:55-77 |
| `chart.py` | `BaziChart` 数据类 + `build_chart()` 工厂（编排 15 个 `_compute_*_stage`） | chart.py:43-1118 |
| `_chart_context.py` | chart_data → LLM/前端共享上下文提取（当前大运/流年/年龄） | _chart_context.py:164-316 |
| `yongshen.py` | 强弱计分、从格检测、喜忌推荐、调候简化版、格局用神、decision_policy | yongshen.py 全文 |
| `pattern.py` | 月令定格 + 成格/破格/带忌/不成格校验 | pattern.py 全文 |
| `tiaohou.py` | 调候独立观察 + 假生陷阱检测 + 健康符号分布（已 neuter 成"文化参考"） | tiaohou.py 全文 |
| `interactions.py` | 天干五合/地支六合三合半合三会六冲刑害/墓库六冲/贪生忘克/夹拱 | interactions.py 全文 |
| `dayun.py` | 顺逆排、起运、交运、小运、DayunModulator（大运调制） | dayun.py 全文 |
| `liunian/` | 流年扫描：scanner.py(983行) 主循环，events/*.py 10 类探测器，battle.py 岁运交战，signal.py 打分模型 | liunian/scanner.py |
| `llm_review.py` | LLM 审阅层（DeepSeek，规则信号→白话翻译，禁新增/反转/升级） | llm_review.py:1-10 |
| `rag.py` | 零依赖关键词+n-gram 余弦检索 references/*.md 与校准案例，注入 LLM prompt | rag.py:1-10 |
| `chat.py` | DeepSeek 追问（SSE 流式） | chat.py |
| `personality_fusion.py` / `personality_analysis/` | 性格画像 + 可选 LLM 融合叙事 | — |
| `spirits.py`/`nayin_chain.py`/`palace_star.py`/`body_use.py`/`void_god.py`/`changsheng_analysis.py` | 神煞/纳音链/宫位叠象/宾主体用/虚神/十二长生参断 | 各文件头 |
| `day_pillar_db.py` | 1900-2100 日柱 O(1) 速查（与 JDN 公式并存，备用） | day_pillar_db.py:1-10 |
| `calibration.py`/`runtime_store.py`/`api.py`/`cli.py` | 校准存储/运行时存储/FastAPI 服务/命令行 | — |

### 2.2 frontend / docs / references / SKILL.md 各是什么

- `frontend/`：静态前端，与 FastAPI 同进程挂载（`docs/architecture.md:11-18`）；含隐私政策与服务条款页，佐证公网运营属性。
- `docs/`：工程文档。`architecture.md` 有一张 build_chart 各 stage 的"输入/写出/下游/重构风险"表（`docs/architecture.md:139-158`），`calibration-protocol.md` 定义 development/holdout 双案例集与"锁定验证不得调参"纪律（`docs/calibration-protocol.md:8-16`）。
- `references/`：8 份规则 md，**本身就是 rag.py 的检索语料**（`rag.py:28-40` 的 `_SOURCE_SECTIONS` 逐个登记）。`rule-provenance.md` 定义五级来源标签（古籍摘要/古籍推导/现代流派/工程启发式/案例观察，`references/rule-provenance.md:6-14`）。
- `SKILL.md`：把引擎包装为 Claude Code skill 的操作手册：LLM 用 WebSearch 验日柱→跑 CLI→用户确认后才解读（`SKILL.md:21-45`）。

### 2.3 数据流图

```
用户输入(年月日时分/性别/城市/精度)
  └─ resolve_birth_time (time_resolution.py:85)        → BirthTimeResolution（UTC瞬间 / CST瞬间 / pillar_dt 真太阳时）
  └─ build_chart (chart.py:969) 依次执行：
     1 _compute_four_pillars      → 年月日时柱（立春定年/节气定月/JDN定日/五鼠遁定时）
     2 _attach_hidden_stems_and_nayin → 藏干+纳音
     3 _compute_palace_origins    → 命宫/身宫/胎元
     4 _compute_yongshen_stage    → determine_qiangruo + 从格 + recommend_yongshen（含调候简化+decision_policy）
     5 _compute_tiaohou_health_stage → analyze_tiaohou + detect_false_generation
     6 _compute_ten_gods_stage    → 各柱十神
     7 _compute_pattern_stage     → determine_pattern（从格覆盖月令）→ 回填 pattern_yongshen
     8 _compute_void_gods_stage / _compute_dayun_stage → 虚神、大运（起运/交运/小运）
     9 _compute_dayun_modulation_stage → DayunModulator
    10 _compute_interactions_stage → 合冲刑害 + 贪生忘克 + 假生
    11 _compute_spirits_stage / _compute_liunian_stage → 神煞、流年扫描（含 LLM 审阅挂接）
    12 _compute_changsheng_stage / _compute_life_stage / _compute_personality_family_stage
  └─ BaziChart.to_dict() → report_meta(schema 1.1) + current_context → API/CLI/前端
```
（stage 顺序与依赖以 `chart.py:1056-1118` 与 `docs/architecture.md:22-44` 交叉验证。）

注意与 README 的矛盾：README 架构图写 `liunian.py` 单文件与 `scripts/data/calibration_store.json`（`README.md:126,137`），实际代码是 `liunian/` 子包，且仓库内不存在 `scripts/data/` 目录（校准库为运行时生成/不入库）。

---

## 3. 数据结构（chart.py / _chart_context.py / ten_gods.py）

### 3.1 PillarData（chart.py:44-62）
字段：`pillar_type`("年柱"…"时柱")、`stem: Tiangan`、`branch: Dizhi`、`hidden_stems: list[HiddenStem]`（含 level 字符串"本气/中气/余气"）、`ten_god: Shishen|None`（日柱为 None，chart.py:602-603）、`ten_gods_map`（藏干→十神）、`nayin`。

### 3.2 BaziChart（chart.py:66-158）
核心字段分组：
- 输入与时间：`birth_dt`、`day_pillar_source`("formula"/"override")、`birth_instant_utc/cst`、`pillar_dt`、`time_resolution: BirthTimeResolution`；
- 四柱 + `day_master`；命宫/身宫/胎元（各含干/支/纳音，chart.py:84-93）；
- 格局：`pattern: str` + `pattern_notes: list[str]`（透干说明）；
- 大运：`luck_pillars`、`luck_periods`、`start_age`、`start_age_exact`、`dayun_direction_str`、`jiaoyun_detail`、小运 `xiaoyun_*`；
- 关系：`tiangan_interactions`/`dizhi_interactions: list[Interaction]`；
- 神煞 `spirits`、流年 `annual_scans`、喜用 `favorable_tags`、诊断 `warnings`；
- 高级技法槽位：`void_gods/nayin_relations/changsheng_states/palace_star_result/tiaohou_result/dayun_modulations/tansheng_wangke/false_generations/body_use_result/health_profile`（chart.py:141-151）；
- `_yongshen_result`（内部缓存，含 `decision_policy`）。
`to_dict()` 输出 `report_meta.schema_version="1.1"`、`uncertainty.boundary_sensitive`（夜子时/边界警告驱动，chart.py:249-269）。

### 3.3 HiddenStem（_constants.py:161-164）
`frozen dataclass(stem: Tiangan, level: str)`，level ∈ {"本气","中气","余气"}。藏干表见 §5。

### 3.4 ten_gods.py
- `Shishen` 枚举 10 个（偏官=七杀、偏印=枭神，enums.py:75-86）；
- `get_ten_god(day_master, other)`（ten_gods.py:55-77）：五行生克 + 阴阳同异 → 十神，标准算法，无争议；
- `TIANGAN_KE_PAIRS`（ten_gods.py:20-26）：20 对天干相克（无"四冲"概念如甲庚冲，只有五行克）。

### 3.5 BirthTimeResolution（time_resolution.py:14-68）
`frozen dataclass`，双时间线设计：`birth_instant_utc/cst`（真实瞬间，用于节气/年月柱/起运）与 `pillar_dt`（真太阳时校正后，用于日柱/时柱/命宫/身宫/小运），并携带 `equation_of_time_minutes`、`longitude_correction_minutes`、`solar_correction_minutes` 全链路溯源字段。

---

## 4. 历法与排盘

### 4.1 四柱计算

- **节气库**：`ephem`（VSOP87）太阳黄经迭代，收敛阈值 `1e-5`（约 0.3 秒精度，`solar_terms.py:83`）；12 节黄经表 `_JIE_LONGITUDE`（立春=315°…小寒=285°，`solar_terms.py:20-23`）；迭代初值为固定近似日期种子（`solar_terms.py:26-29`）；`lru_cache(120)` 缓存（`solar_terms.py:89`）。ephem 缺失时回退固定日期近似表并输出警告（`solar_terms.py:160-211`）。**自述精度"±1 秒内"（solar_terms.py:6），未在测试中见到对权威历表的逐秒断言**（test_solar_terms.py 只验证区间与单调性）。
- **年柱**：以精确立春时刻分界，立春前用上一年干支；干支序 `(year-4)%60`（`pillars.py:20-44`）。警告常量 `WARNING_YEAR_BOUNDARY`（pillars.py:14）。
- **月柱**：节气区间定月支（`_month_branch_from_jieqi`，pillars.py:82-104；明确处理"小寒前仍是子月"的跨年情形，pillars.py:92-94），五虎遁定月干；五虎遁偏移先 `%12` 再 `%10`（pillars.py:63-64，注释强调"月序不能先模十"，这是对常见 bug 的防御）。
- **日柱**：儒略日数 JDN 公式，`idx=(jdn+49)%60`，注释称 "49 = offset for 甲戌 on 1900-01-01"（`pillars.py:107-119`）。**注意：注释自相矛盾**——JDN 公式下 2000-01-01 应为戊午（docstring line 111 说以 2000-01-01=戊午 校准），而 49 注释说对齐 1900-01-01 甲戌；1900-01-01 实为甲戌日，两处口径实质一致但表述混乱，值得 Tianze 复核同一 offset。
- **时柱**：五鼠遁 + `hour_to_dizhi`（`_constants.py:392-417`）：整点区间制，23:00-00:59 为子，**23≤hour 标"夜子时"、hour<1 标"早子时"**。
- **晚子时口径**：**23:00 后日柱进位到次日**（"夜子时按次日日柱计算"），年柱/月柱/起运仍按真实出生时刻（`pillars.py:16,139-141`；`docs/time-basis.md:27-29`）。这是"子正换日"与"夜子时换日"两派中的后者（换日派）——Tianze 需自选口径，这里可作参考实现。
- **时辰边界警告**：距时辰交界 ≤30 分钟即出警告（`pillars.py:144-152`，120 分钟模运算）。
- **真太阳时**：`solar_correction = NOAA均时差 + 4×(经度−时区中央经线)` 分钟（`time_resolution.py:136-141`；NOAA 公式 time_resolution.py:71-82）；默认城市未知 → 不校正（civil_input），城市有坐标 → true_solar（time_resolution.py:123-128）。内置离线城市清单 3564 条（AreaCity 数据，`docs/time-basis.md:39-41`；`resources/cn_divisions.jsonl`）。

### 4.2 大运起运

- 顺逆排：阳男阴女顺排，阴男阳女逆排（`gender_rules.py:6-9`，`dayun.py:16-23`）。
- 起运：出生到下一节（顺）/上一节（逆）的精确天数 ÷ 3（"三天折一岁"），余数进位规则：**余 2 天 ≈ 8 个月 → 进 1 岁**（`dayun.py:38-59`）；`compute_start_age_exact` 另存浮点精确年龄用于边界判定（`dayun.py:62-68`）；交运细节把小时折入月（`dayun.py:71-94`）。
- 大运序列：从月柱起 ±1 顺/逆，默认 8 步、每步 10 年（`dayun.py:26-35,97-111`）；**明确声明不使用"前后五年分干支"划分**（`dayun.py:109` weight_note：大运干支关系由引擎综合展示；不把固定百分比或前后五年划分表述为古籍定论）。另有小运（以时柱为基准一岁一柱，`dayun.py:114-131`）。

---

## 5. 干支模型

### 5.1 藏干表（_constants.py:167-180）

`DIZHI_CANGGAN`，每支 1-3 个 HiddenStem。内容为通行版本：

| 支 | 藏干（本气/中气/余气） |
|---|---|
| 子 | 癸 |
| 丑 | 己/辛/癸 |
| 寅 | 甲/丙/戊 |
| 卯 | 乙 |
| 辰 | 戊/乙/癸 |
| 巳 | 丙/庚/戊 |
| 午 | 丁/己（仅两档，无余气） |
| 未 | 己/丁/乙 |
| 申 | 庚/壬/戊 |
| 酉 | 辛 |
| 戌 | 戊/辛/丁 |
| 亥 | 壬/甲（仅两档） |

文件头注明"所有查表均经 WebSearch 验证"，且有一条修正记录："丑藏干中余气互换(辛癸)"（`_constants.py:1-5`）——即丑的中气辛、余气癸（有的排法癸为中气）。**未标注具体古籍版本**；午/亥两档制（无余气）是主流派之一。

### 5.2 十神表
无静态十神表，`get_ten_god` 动态推导（ten_gods.py:55-77），正确且自洽。

### 5.3 十二长生（_constants.py:210-241）

`SHIER_CHANGSHENG: {天干: {地支: 阶段}}`，10 天干完整独立映射，采用**阴阳分轨（阴干逆行）**版本：乙长生在午、丁长生在酉、辛长生在子、癸长生在卯（`_constants.py:214,220,232,238`）；戊己随丙丁（火土同宫，`_constants.py:223-228`）。这是两派（阴阳分轨 vs 阴阳同生）中的前者和火土同宫派的组合。
**用途**：
1. 强弱计分的月支长生修正（yongshen.py:242-250，仅月支）；
2. `changsheng_analysis.py` 对四柱/大运/流年逐支参断，附能量等级表 `_STATE_ENERGY`（长生7/沐浴5/冠带6/临官9/帝旺10/衰4/病3/死2/墓3/绝1/胎4/养5，`changsheng_analysis.py:44-46`）——**PROJECT_HEURISTIC**（文件头称来源 advanced-techniques.md + WebSearch，无古籍数值依据）。
3. 大运调制器注释提到"大运十二长生→十年气数分层"（dayun.py:201），但 `_analyze_one_period` 实际**未实现**长生分层（dayun.py:243-308 无此步骤）——文档/注释与实现不一致。

### 5.4 其他静态表
- 五合化气（_constants.py:35-46）、六合化神（121-128，午未合化火）、三合（82-87）、**半合（91-104，全部 8 个两支组合都算半合**，即不含"必须有中神"的传统限定，见 §6）、三会（110-115）、六冲（61-68）、互刑（135-139）、自刑（142）、相害（148-155）。
- 神煞：天乙贵人（248-269，口诀注释"甲戊庚牛羊…"）、文昌（284-290）、红鸾/天喜（296-306）、驿马/桃花/华盖（三合局归类 313-346）、灾煞/丧门/吊客（469-485）、学堂（512-518）、孤辰寡宿（**用三会局查法**，528-540）、太极贵人（548-555）、福星贵人（565-571）、空亡（旬空，492-504）。
- 纳音 60 甲子全表（424-456）。五鼠遁（186-192）、五虎遁（198-204）。
- 化气格条件 `HUA_QI_CONDITIONS`（619-630）：日干+合干 → 化气五行 + 月令支集合。**定义了但全引擎 grep 无人调用——化气格未实现**（只有五合"候选"标注）。
- `CONG_GE_CHECKS`（581-606）：从旺/从财/从杀/从儿的文案与喜忌表，头注称来源《渊海子平》+《子平真诠》+ WebSearch 2026-05-26，但其中具体数字条件（≥4 个同五行等）**无古籍量化依据 → PROJECT_HEURISTIC**（详见 §7）。
- `_MONTH_PATTERN_BASE`（369-382）：月支→藏干→格局名的"简化备份"表，**内容有系统性错误**（如 申:庚→"偏印格"、子:癸→"偏印格"——十神名相对日主才有意义，此表按藏干硬编码格局名只对特定日主成立），pattern.py 实际动态计算不用此表（pattern.py:39-60）→ **死数据/过期表，勿参考**。

---

## 6. 关系（合冲刑害破/三合三会覆盖与扫描方式）

- **扫描方式**（interactions.py）：全部为**四柱内两两 C(4,2) 配对扫描**，无相邻限定：
  - `find_tiangan_wuhe`（38-53）：任意两干五合即报"合X**候选**"，notes 强调"是否化气须另验月令、通根、透干与破合条件"。**与传统"隔位不合"规则冲突**——年干与时干隔两位也会报合。
  - `find_dizhi_liuhe/sanhe/sanhui/liuchong/xiangxing/xianghai`（56-203）：同为全配对；三合用 `frozenset` 匹配 3 支齐全；**半合为任意 2 支命中即报**（94-103，配合 DIZHI_BANHE 的 8 个组合）——传统派要求半合含旺支（子午卯酉）且忌被冲，这里无此限定。
  - 自刑：同支出现 ≥2 次且支 ∈ {辰午酉亥}（160-172）。
- **化气立场**：全引擎对合的态度是"只记录候选、不自动改权重"——test_rule_regressions.py:10-25 明确断言结果串必须含"候选"且不得含"化"。yongshen.py `_check_tiangan_he_impact` 直接返回 `{}`（yongshen.py:57-63）——**合化对强弱计分的影响被显式置零**。
- **墓库**：只记录辰戌、丑未两组实际六冲为结构标签；`tu_boost=1`（不放大土气）、`zaqi_damaged=[]`（不列损毁杂气）、无健康/暴富推断（interactions.py:210-307；test_rule_regressions.py:28-46 有专门反例测试）。README 称"墓库关系——仅记录实际六冲，不作倍增或疾病/暴富推断"（README.md:38），与源码一致。
- **破**：**未实现**（全库无 地支六破/破 的表）。
- **贪生忘克**（interactions.py:314-387）：天干**相邻**三柱 A→生→B→生→C 且 A 本克 C → 判 A 贪生忘克，B 为通关；特别标注日主被保护/日主出力两种情形。
- **夹拱**（interactions.py:390-418）：同干两柱地支间隔 2 位 → 拱中间支（盲派暗拱，标注 v0.16）。
- **大运参与关系**：DayunModulator 把大运支与原局支做冲/合/害/刑/自刑 + 三合三合半合 + 三会扫描（dayun.py:321-361），优先级 冲>合>害>刑>自刑（注释 dayun.py:327）。
- **岁运交战**（liunian/battle.py）：流年 vs 大运：天干相克=天战（状态类 1-2★），地支相冲=地战（1-3★，注释称"比天干冲严重1.5-2倍"battle.py:13——**该倍率只存在于注释与 README，代码用 ★ 差（天战最高2★/地战最高3★）表达，无数值乘子 → PROJECT_HEURISTIC**）；刑害一律负面 1★；六合正面 1★。方向再按大运干支喜忌翻转（battle.py:31-95）。

---

## 7. 旺衰算法【重中之重】—— yongshen.py `determine_qiangruo`

### 7.1 输入

`determine_qiangruo(day_master, month_branch, all_stems[4], all_branches[4])`（yongshen.py:181-194）。all_stems/all_branches 为年月日时四柱干支列表（由 chart.py:544-545 传入）。**输入只有 8 个字 + 月支，不含藏干以外的地支关系、不含大运流年**。

### 7.2 计分步骤（逐步，含全部神秘常数）

起点 `score = 0.0`。

1. **月令得令分** `_season_strength`（yongshen.py:24-38）：月支本气五行 vs 日主五行：
   - 同五行 **+3**；生我 **+2**；我生 **+1**；克我 **−1**；我克 **0**。
   - 无出处标注 → **PROJECT_HEURISTIC**（数值为整数±3/2/1，无古籍量化）。
2. **天干十神计分**（yongshen.py:201-214）：跳过日干本身（index==2 且 ==日主；注释强调别柱同干比肩必须计入，yongshen.py:202-204）：
   - 比劫 **+1.0**；正偏印 **+1.0**；官杀 **−1.0**；食伤 **−0.7**；财星 **−0.5**。
   - → **PROJECT_HEURISTIC**（克泄耗系数 0.7/0.5 无出处）。
3. **地支藏干计分** `_canggan_score`（yongshen.py:41-54）：对 4 支全部藏干（含日支、时支）：
   - level 权重：本气 **1.0** / 中气 **0.5** / 余气 **0.25**；
   - 比肩/劫财/正偏印 → `+base`；正偏官 → `−base×0.5`；食伤 → `−base×0.5`；财 → `−base×0.3`。
   - docstring 自称"权重已优化"（yongshen.py:42），无出处 → **PROJECT_HEURISTIC**。
   - **注意：这里没有显式"通根"概念**——天干之根通过藏干计分间接体现，但没有"根强度=墓库根/禄刃根"之类分级；全库 grep "通根" 只出现在关系 notes 与意象诗文中（interactions.py:51、_imagery.py:90,101）。
4. **印多母衰（"母多减子"）**（yongshen.py:223-231）：天干印星数 ≥3 时，`score -= yin_count × 0.5`。注释引**陆致极"母多减子"**（现代流派，非古籍量化）→ 现代作者 heuristic。
5. **假生陷阱修正**（yongshen.py:233-240）：调 tiaohou.detect_false_generation（见 §9.4），每条 severity=2 强假生 **−2.0**，severity=1 弱假生 **−1.0**。依据为《穷通宝鉴》《滴天髓》、梁湘润语句（tiaohou.py:153-157），**扣分数值本身 → PROJECT_HEURISTIC**。
6. **十二长生修正**（yongshen.py:242-250）：日干在**月支**的长生状态查分表：
   - 长生 **+2.0**、沐浴 **+0.5**、冠带 **+1.0**、临官 **+2.0**、帝旺 **+2.5**、衰 **−0.5**、病 **−1.0**、死 **−1.5**、墓 **−1.0**、绝 **−2.0**、胎 **0.0**、养 **+0.5**。
   - → **PROJECT_HEURISTIC**。**矛盾**：注释写"日干在月支/日支的长生状态参与强弱"（yongshen.py:242），代码只用了月支（`cs_table.get(month_branch)`），日支未参与。

7. **判定阈值**（yongshen.py:252-258）：
   - `score ≥ 3.5` → **强**；`score ≤ 1.5` → **弱**；其间 → **中和**。
   - → **PROJECT_HEURISTIC**（无出处；返回 `round(score,1)`）。

**没有**的环节：无月令藏干透干加权细分（月令三档不区分本中余气，仅按月支本气五行一档）；无大运流年介入；无合化改分（显式置零，yongshen.py:57-63）；无寒暖燥湿直接加减分（假生除外）。

### 7.3 从格判定 `_detect_cong_ge`（yongshen.py:103-178）

- **前置反条件（关键）**：四柱任一天干（除日干）或任一地支藏干中出现**比劫五行或印星五行**（`dm_wx` 或 `parent_wx`）→ 直接判"不从"返回 None（yongshen.py:119-131）。注释自述旧实现"简化成五行数量导致有根命局误判从格"，v0.8.0 收紧。**即：只要日主或印星有任何明根/暗根就不从**——README "从格限制：有日主或印星明根、暗根时不自动判从"（README.md:40）与源码一致。
- **从弱判定**：`strength=="弱" and score ≤ 0.5 and 克泄耗五行计数 ≥ 总计数×75%`（yongshen.py:152-153）→ 按财/官杀/食伤哪类最多取"从财/从杀/从儿"（166-169），从 `CONG_GE_CHECKS` 取喜忌文案。
  - 阈值 0.5 / 75% → **PROJECT_HEURISTIC**。
- **从旺格**：`CONG_GE_CHECKS["从旺"]` 定义了"得令+比劫印星≥4"的条件（_constants.py:582-586），但**代码路径没有实现从旺检测**（只实现了从弱三分支；从旺 key 存在但无触发逻辑）→ 声称与实现不符。
- 从势格：pattern.py:34-37 有 `cg_type.startswith("从势")` 分支，但 `_detect_cong_ge` 永远不产出"从势X"类型 → **死分支**。

### 7.4 喜忌输出与 decision_policy

- `recommend_yongshen`（yongshen.py:263-341）输出结构：
  `strength, score, favorable/harmful(十神名列表), favorable_wuxing/harmful_wuxing(五行), cong_ge, tiaohou, pattern_yongshen, decision_policy`。
- 常规喜忌：强 → 喜食伤财官杀、忌印比；弱 → 喜印比、忌食伤财官杀；中和 → 喜印比、忌空（yongshen.py:303-313）。
- 调候五行只作**补充**：若调候五行既不在喜也不在忌则加入喜集；**不从忌神中强行移除**（yongshen.py:315-324）。
- `build_decision_policy`（yongshen.py:344-403）：把扶抑/从格（base）、格局维护（pattern）、调候三层整理为 `precedence: ["扶抑/从格","格局维护","调候"]`；格局与扶抑冲突时**保留冲突不自动翻转**（361-366），`effective` 字段兼容旧流年模块。**evidence/rationale 类字段**：decision_policy 无逐条 evidence；真正的证据链在流年层 `EvidenceItem`（liunian/signal.py:15-39：rule/layers/pillars/relation/detail/effect）。格局校验层输出 `issues/supports/note`（pattern.py:301-313）承担 rationale 角色。

---

## 8. 格局算法【重点】—— pattern.py

### 8.1 定格 `determine_pattern`（pattern.py:15-60）

优先级（docstring pattern.py:23-28）：
0. **从格覆盖**：cong_ge 存在 → 返回"从财格/从杀格/从儿格/从势格"（31-37），不以月令常格论；
1. **月令藏干透干优先**：按 DIZHI_CANGGAN 顺序遍历月支藏干（本→中→余），任一藏干透出四柱天干（`hs.stem in all_stems`，含日干年干时干任意位置）→ 取该藏干对应十神为格；
2. **建禄/羊刃特判**：仅在**本气**透干分支内检查：月支 == 日干禄位（TIANGAN_LU）→ 建禄格；== 羊刃位（TIANGAN_YANGREN）→ 羊刃格（47-53）。注意阴干羊刃表（如 乙→寅、辛→申，enums.py:141-147）采用"阴干羊刃在临官前一位"的进派口径，有争议；
3. 全不透 → 取月支本气十神为格（57-60）。
- 返回 `(格局名, notes)`，notes 是逐条"月支X 本气Y透干"式说明（透干说明即本模块 rationale）。
- **月令冲合对格局的影响：未处理**——determine_pattern 不接收 interactions，月支被冲/合不改变定格。
- "透干"判定包含日干自己与年/时干，不要求月干。

### 8.2 校验 `validate_pattern`（pattern.py:63-313）——四档状态机

输入：pattern、day_master、pillars_data（含 stem/ten_god/hidden_ten_gods/source）、harmful_shishen、weighted_scores（来自 personality weighting，见 §8.4）、strength、tiaohou_is_fei_ju、interactions。

- 从格直接"成格"返回（85-91）。
- 状态机（296-313）：
  - `issues` 非空 & `supports` 空 → **破格**；
  - 两者都非空 → **带忌**（成中有败）；
  - issues 空 & supports 非空 → **成格**；
  - 两者都空 → **不成格**（"无明显成破信号,格局标签支撑不足"）。
  - 另有前置：调候废局（is_fei_ju）且无 issues → 塞入一条"调候废局…格局先天打折"（297-298）。**但 v0.13.0 起 is_fei_ju 恒为 False**（tiaohou.py:19,101），所以该路径实际死亡。
- 被合处理（131-137）：从 interactions 天干五合取被合干集合；善神被合 → 破（正官被合 147、财被合 188、印被合 204、食被合 238）；凶神被合 → 支撑（七杀被合 163、伤官被合 270），引《子平真诠》"合杀为贵"。
- **十格逐个判定条件**（issues=破因 / supports=成格支撑）：
  - **正官格**（144-157）：破：官被合、伤官见官、官杀混杂；成：财印双辅/财生官/印护官。
  - **七杀格/偏官格**（160-182）：破：制化两立（食制+印化并见）、财生杀攻身无制化、杀无制化；成：食神制杀"制得干净"（**量化：食/伤加权分 ≥ 杀加权分×1.5**，164）、杀印相生；弱制（≥×0.7）→"制力偏弱需大运补足"（165,174）。×1.5/×0.7 引**段建业盲派"制得干净才成格"**（文档头 pattern.py:6），数值为工程化 → 现代流派+PROJECT_HEURISTIC。
  - **财格**（185-198）：破：财被合、比劫夺财无救（**比劫加权分≥4** 且无官护无食泄，189）、财格透杀无食制、身弱而财加权分≥6（"财多身弱"，陆致极）；成：食神生财、财旺生官。
  - **印格**（201-233）：破：印被合、财破印无官杀通关、印夺食（印星五行克食神五行，208-221）；成：杀印相生、官印双全、印旺食泄（食伤透干且印加权分≥6）。
  - **食神格**（236-264）：破：食被合、**枭神夺食**（偏印透干且印五行克食神五行，254-255）、印克食；成：食神生财、食神制杀（食≥杀×1.2 为"干净"，261）。
  - **伤官格**（267-276）：破：伤官见官（"除金水伤官外"）；成：伤官被合（凶性受制）、伤官生财、伤官佩印。
  - **羊刃格**（279-283）：成：官杀透干制刃；破：阳刃无制。
  - **建禄格**（286-294）：成：透官/透财带食伤/透杀带食制；破：杀印同途无食制。
- 来源标注（pattern.py:3-8,72-77）：骨架《子平真诠·论用神》善神顺用凶神逆用；效率判据引段建业盲派；综合判定引陆致极；废局打折引梁湘润+《穷通宝鉴》——即**框架有出处、阈值无出处**。

### 8.3 格局用神（yongshen.py:406-439）

`_get_pattern_yongshen`：11 格（正官/正印/偏印/食神/伤官/正财/偏财/偏官/七杀/建禄/羊刃）各配 `needs/avoid/method`，原则为《子平真诠》善神顺用（财官印食→生之护之）、凶神逆用（杀伤枭刃→制之化之）。如正官格 needs 印/财、avoid 伤官；七杀格 needs 食伤印、avoid 财。**needs/avoid 的具体组合是作者整理的工程化映射**，非逐条古籍引文。

### 8.4 weighted_scores 从哪来

validate_pattern 的 `weighted_scores` 来自 personality_analysis 的十神加权：透干 +3.0、藏干本气 2.0/中气 1.5/余气 1.0、月令同五行 ×1.5、同柱共振 +1.0（personality_analysis/weighting.py:31-110；常量定义 personality_analysis/constants.py:6-15，**文件头明言"引擎工程启发式参数，不是古籍给出的固定比例"**）。即格局破格阈值（×1.5、≥4、≥6）建立在另一套与旺衰计分**互不相干**的加权体系上——两套计分并存是架构隐患。

---

## 9. 调候算法【重点】—— tiaohou.py

### 9.1 覆盖率：非 120 组，是 **11 条"日主×季节"规则**

`analyze_tiaohou`（tiaohou.py:35-132）的 `tiaohou_map`（70-87）只有 11 条（金夏/金冬/木冬/木秋/水夏/水冬/火冬/火秋/土夏/土冬/土春），按 **4 季节**（寅卯辰=春、巳午未=夏、申酉戌=秋、亥子丑=冬，45-52）而非 12 月令取键。对照《穷通宝鉴》10 日主 × 12 月 = 120 组：**覆盖率 11/120 ≈ 9%**（按 10×4=40 季节键算 11/40=27.5%）。未覆盖键（如"木夏""水春""金春"）返回空 → `priority_note="原局寒暖燥湿适中，调候无忧"`（121-123），**即缺省被当作"无忧"而非"无数据"**，有误导风险。

### 9.2 数据形态：硬编码在源码内，无外部数据文件

两条独立硬编码副本：
- yongshen.py:86-98（用于强弱结果内的 tiaohou 字段）；
- tiaohou.py:70-87（独立调候分析）。
**两副本不一致**：("水","夏") 在 yongshen.py:91 为 `["水"]`，在 tiaohou.py:78 为 `["金","水"]` → 矛盾点，需记录。references/classical-texts.md 的"穷通宝典"节承认"各日干十二月调候用神各有不同，详见穷通宝鉴原文"（classical-texts.md:17-29）——即作者知道不完整。

### 9.3 古籍来源标注情况

- 每条规则 reason 文本自带命理式解释（如"夏金遇火熔，取水调候"），表头注"《穷通宝鉴》核心，陆致极系统化"（tiaohou.py:69）；**无逐条书页/章节出处**；"木秋"一条特意注明"传统上先取丁火、次取丙火；均属火行，仅作调候参考"（tiaohou.py:76）。
- 规则来源等级按 `references/rule-provenance.md:22` 自我归类为"古籍摘要"，且限定"仅作独立观察，不以废局覆盖格局或强弱"。
- **气候判定阈值**（tiaohou.py:104-113）：火≥3 且水<0.5 → 大燥；水≥3 且火<0.5 → 大寒；火≥2 且水≤1 → 偏燥；水≥2 且火≤1 → 偏寒；否则中和。地支计数 1.0、**天干计数 0.5**（"天干为表，地支为根"，59-63）→ 阈值全部 **PROJECT_HEURISTIC**。

### 9.4 假生陷阱 detect_false_generation（tiaohou.py:139-301）

6 条规则（每条含强/弱两档 severity=2/1）：
1. 水冷木冻：木日主+亥子水+全局无火 → 强（火藏支不透 → 弱）；
2. 燥土脆金：金日主+戌未土+全局无水 → 强（水藏支不透 → 弱）；
3. 湿木不生火：火日主+亥子水+地支木≥2+天干无火 → 弱（severity=1）；
4. 火炎土焦：土日主+巳午≥2+全局无水 → 强（水藏支不透 → 弱）；
5. 金多水浊：水日主+申酉≥2+无木火 → 强（火藏支不透 → 弱）；
6. 土重金埋：金日主+辰戌丑未≥3 → 强。
- 规则来源标注《穷通宝鉴》"水冷木冻无火则木不荣"、《滴天髓》"燥土脆金"、梁湘润"湿木不生火"（tiaohou.py:153-157）；**"≥2 支/≥3 支"的触发计数无古籍依据 → PROJECT_HEURISTIC**。
- 假生参与旺衰扣分（§7.2 步骤5），也进 LLM 上下文（llm_review.py:161-167）。

### 9.5 调候如何参与最终用神决策（优先级）

- 调候**不覆盖**扶抑/格局：yongshen.py:315-324 只在调候五行"非喜非忌"时补入喜集；
- decision_policy 中 tiaohou.role="supplement"，precedence 最低位（yongshen.py:372,388-392）；
- "废局"机制已退役：`is_fei_ju` 恒 False（tiaohou.py:19,101；chart.py 注释"兼容字段，已停用"），流年层废局降星逻辑（liunian/scanner.py:690-703，"陆致极『失去调候为废局』"）因标志恒 False 而实际不再触发。

---

## 10. 用神综合决策（yongshen.py 融合/排序）

- **融合方式：分层裁决而非加权混合**。`build_decision_policy`（yongshen.py:344-403）把三层并列：`base`（扶抑/从格，来自 determine_qiangruo + _detect_cong_ge）、`pattern`（格局维护 needs/avoid）、`tiaohou`（补充观察），`precedence = ["扶抑/从格","格局维护","调候"]`。
- **冲突显式保留**：格局 needs 撞 base harmful（或反之）→ 写入 `conflicts` 列表（"格局需要X，但扶抑层列为忌：保留冲突，不自动翻转"，yongshen.py:360-366），交由流年/解释层引用；`effective` 字段默认仍等于 base（兼容旧流年），仅 priority 标注切换（394-401）。
- **病药/通关**：没有独立的"病药"用神模块。病药仅以两种形态存在：(a) personality_analysis/bingyao.py 的"病药"性格检测（非用神决策）；(b) 贪生忘克=通关检测（interactions.py），只进流年调制与 LLM 上下文，不回写用神。调候亦不参与病药。
- 用户手动 favorable 覆盖自动推荐（chart.py:553-561）。
- 大运流年消费的喜忌来自 `decision_policy.effective`（chart.py:769-776）。

---

## 11. 大运流年（dayun.py + liunian/）

### 11.1 大运
- 起运/顺逆/序列/小运见 §4.2。**换运边界**：大运年龄区间 `start_age + i*10 ~ +9`（dayun.py:100-111）；流年扫描按周岁区间选择当前大运（chart.py:839 `dayun_idx = (current_age - start_age)//10`）；精确起运年龄 `start_age_exact` 传入 scan_years 供边界年判断（chart.py:809）。
- **DayunModulator**（dayun.py:193-381）：每步大运输出 {与原局干支关系, 干/支喜忌, baseline_offset, theme, theme_weight}：
  - baseline_offset：`branch_score×0.6 + stem_score×0.4`，≥0.4→+1，≤−0.4→−1（dayun.py:255-264）——**地支权重 0.6/天干 0.4、阈值 ±0.4 → PROJECT_HEURISTIC**（代码自注"工程启发式，不能视为古籍量化规则"）。
  - theme：大运天干十神→财运/官运/印运/食伤运/比劫运（266-275）；theme_weight 常量 1.0/0.8（277-278），注释另称"一致加权1.3冲突减权0.7"，**代码并未实现 1.3/0.7**，仅 scanner 依 theme_w>1/<1 升降星（liunian/scanner.py:736-752）——又一处注释与实现脱节。
- README"地战权重 1.5-2x"（README.md:45）与 battle.py 的 ★ 差表达的差异见 §6。

### 11.2 流年扫描（liunian/scanner.py）
- 每年：算流年柱→选当前大运→跑 10 个事件探测器（桃花/升学/婚嫁/事业/财运/健康/搬迁/状态/人际/官非，liunian/events/*.py）→ 同柱隔离带（盖头/截脚≥3★降1星，scanner.py:676-688）→ 大运调制（吉运+1★/凶运−1★，≥2★才动，且桃花婚嫁免于凶运正面打压，scanner.py:713-733）→ 岁运交战（battle.py）→ 贪生忘克减凶（scanner.py:816-841）→ 事件合并/矛盾检查/婚嫁桃花互引（_cross_ref_hunjia_taohua）→ 跨年婚恋窗口标注（_annotate_relationship_windows）。
- 打分模型（liunian/signal.py:41-110）：`ScoreAccumulator` 逐因子加分；喜神年因子+1、忌神年−1（可 `fixed=True` 豁免）；`strength` 映射：|total|≥4→3★、≥2→2★、否则1★；方向 total≥1 正面/≤−1 负面。**阈值 4/2 → PROJECT_HEURISTIC**。
- 每条事件可带 `evidence: list[EvidenceItem]`（rule/layers/pillars/relation/detail/effect）与 `conflicts`（signal.py:15-39,125-126）——这是全引擎最接近"evidence 字段"的设计，值得 Tianze 直接吸收。
- 校准：known_events 注入 + `_check_event_conflicts` 把被用户案例否定的方向记为冲突（liunian/calibration.py）；校准案例库 development/holdout 纪律见 docs/calibration-protocol.md。

---

## 12. 测试体系

- 规模：`scripts/tests/` 44 个文件、9,153 行；CI（.github/workflows/ci.yml）在 Python 3.12/3.13 双版本跑 ruff + 全量 pytest。
- 分类：
  - **排盘对账**：test_engine.py 用 3 个作者自述命例（案例A 丁亥戊申壬辰庚戌偏印格、案例B 建禄格等）断言四柱/格局/起运/十神全对（test_engine.py:6-60+）；test_pillar_and_date_boundaries.py、test_solar_terms.py（节气边界）、test_time_resolution.py / test_time_precision_and_report_meta.py（真太阳时与元数据）。
  - **规则回归/反例**：test_rule_regressions.py 专测"古籍审计确认的反例"——合必须报候选不得报化、墓库冲不得推断健康/暴富、财运不得预测金额、从格不得在有根时误判（test_rule_regressions.py:10-50+）；test_reference_data_regressions.py 锁 references 文档数据。
  - **边界与安全**：test_bingyao_safety.py（病药输出安全）、test_llm_review_separation.py / test_llm_review_matrix.py（LLM 不得新增/反转规则信号、逐类矩阵解析）、test_pattern_scope.py。
  - **校准**：test_calibration*.py + 4 个可执行校准脚本（marriage 22 例/career 18/wealth 24/others，README.md:141-144），但校准数据 `scripts/data/calibration_store.json` 不入库，缺文件时跳过（docs/architecture.md:124-125）。
  - **工程**：test_api/test_http/test_token_budget/test_stream_performance/test_runtime_store 等。
- 亮点：**"反例测试"文化**——把"不允许引擎说什么"写成断言（规则准入第 2 条要求每个规则列反例，rule-provenance.md:29-33）。Tianze 可直接借鉴此测试形态。

---

## 13. AI 接入（llm_review.py、rag.py）

### 13.1 LLM 审查（llm_review.py，1323 行）

- **模式**：Hybrid——规则引擎主跑；LLM 只在"规则已给 1★ 弱信号"的年份介入（`should_invoke_llm`：LLM_REVIEW_ENABLED + 有 key + 年龄 15-70 + 目标类别存在 strength==1 信号，llm_review.py:88-106）。**确定性计算与 LLM 的边界被写成 prompt 硬约束**：LLM 只能把规则层已有信号翻译成白话，"不得自行重算三合、藏干、强弱或喜忌，不得新增事件类别，不得反转方向或提高强度"（llm_review.py:366-371）；解析后再做第二道程序化拦截 `_enforce_relationship_review_policy`——无对应规则信号（婚嫁需≥2★，其余≥1★）的 LLM 事件被强制降为"无明显信号"（llm_review.py:669-699）。
- **LLM 输出上限**：strength≤2★、confidence<0.5 丢弃、prediction≤120 字截断按句、category_matrix 六类逐项必答（llm_review.py:57-66,386-407,573-666）。
- **审查什么**：婚嫁/桃花/事业/财运/健康/搬迁六类的逐类矩阵（_REVIEW_CATEGORIES llm_review.py:57）；另有 dayun 解读、personality_fusion、chat 三处 LLM 消费点（docs/architecture.md:101-108）。禁语表（健康类禁疾病/手术/死亡等，llm_review.py:67-78）。
- **输入上下文**：`build_review_context` = 原局概要（四柱/日主/格局/强弱/喜忌/decision_policy/关键关系）+ 贪生忘克 + 假生 + 大运调制 + 流年柱 + **流年近失特征 year_features**（规则引擎内算过但未触发的特征，只作解释背景，"不能据此创建新事件" llm_review.py:200-204,338）+ 规则信号列表 + 性格画像 + 已知事件（llm_review.py:113-230）。
- **temperature=0.3、流式 SSE、DeepSeek 专用**（llm_review.py:450-457；_deepseek_config.py）。模型名含 "deepseek-v4-pro/flash"（README.md:51）——**2026 年的 DeepSeek 型号命名，超出我方知识，仅记录**。

### 13.2 RAG（rag.py，567 行）

- **检索什么**：`references/*.md` 的 8 份文档按 `## ` 切 chunk（100-800 字符）+ 校准案例；按 section（chat / liunian_review / dayun / personality / internal_provenance）过滤（rag.py:28-40,242-262）。
- **技术**：零依赖——关键词命中（标题 3.0/正文 2.0）+ 21 组同义词扩展（66-88）+ 校准案例类目重叠 ×2.5 + personality 板块用**字符级 2-4 gram 余弦向量**为主、关键词为 tiebreaker（111-129,513-539）。阈值：分数>0.5 才收；top_k=5；注入总量上限 2200 字符（docstring rag.py:8）、format_snippets 1800 字符（rag.py:544）。
- **来源分级防幻觉**：每个 chunk 带 kind（classical_summary/engine_heuristic/calibration/provenance_policy），注入时前缀"古籍摘要，待审校 / 工程/现代解释 / 案例观察，非通用规则"（rag.py:44-54,544-568）——**把 provenance 一路带进 prompt，防止 LLM 把工程启发式说成古籍原文**。这是本项目最值得抄的 AI 治理设计之一。

---

## 14. License 与可复用性评估

- **MIT**（LICENSE:1-21），版权 "Copyright (c) 2026 jiwenxu025-boop"。Tianze 可自由借鉴算法思想、表数据甚至整段代码（保留版权声明即可）。
- 可复用性分层：
  - **直接可移植（MIT+正确性高）**：JDN 日柱公式、五虎遁/五鼠遁（含 %12/%10 顺序防御）、ephem 节气迭代（含回退）、藏干表、合冲刑害表、纳音表、神煞表、十二长生表（若采阴阳分轨）、真太阳时双时间线（NOAA 均时差）、`BirthTimeResolution` 溯源元数据设计、`EvidenceItem` 证据结构、规则 provenance 五级标签、RAG 来源分级注入、反例测试模式。
  - **可参考思路但需重造**：强弱计分框架（数值是拍脑袋的）、格局四档状态机、从格收紧条件、decision_policy 冲突保留机制、DayunModulator 三层调制。
  - **勿直接搬**：`_MONTH_PATTERN_BASE` 死表（有错）、HUA_QI_CONDITIONS（无人调用）、调候 11 条副本（不完整且两处不一致）、从旺死分支。

## 15. Tianze 应该借鉴什么 / 不应该借鉴什么（算法层面）

**值得改造移植：**
1. **"候选不化气"原则**：合会只记录候选、化气须另验（interactions.py notes + test_rule_regressions.py 断言）。这是把争议留给配置、把确定性留给引擎的正确姿势。
2. **双时间线 + 全链路时间溯源**（time_resolution.py）：输入民用时间/UTC 瞬间/排盘时间三轨分离，report_meta 记录 effective_time_mode、经度来源、校正分钟——Tianze 排盘审计可直接套用。
3. **日柱 23:00 进位 + 边界警告工程化**（pillars.py:139-152）：口径本身可配置，但"≤30 分钟交界即警告 + uncertainty.boundary_sensitive"的输出设计值得学。
4. **格局四档状态机（成格/破格/带忌/不成格）+ issues/supports 双列表**（pattern.py:296-313）：把"格局可信度"从布尔变成可解释结构。
5. **decision_policy：precedence + 冲突保留不翻转**（yongshen.py:344-403）：扶抑/格局/调候三层的融合方式比"加权混合"更诚实，Tianze 若有多派规则并行，此模式可直接借用。
6. **EvidenceItem + conflicts**（liunian/signal.py）：每条信号带 rule/layers/pillars/relation，可审计。
7. **rule-provenance 五级来源标签 + RAG 注入分级**（rule-provenance.md:6-14、rag.py:44-54）：Tianze 的古籍规则库正需要这套准入纪律。
8. **反例测试 + 校准双案例集（development/holdout 不得互相污染）**（docs/calibration-protocol.md:8-16）。
9. **从格反条件**：有明根/暗根（天干见比劫印或藏干见之）即不从（yongshen.py:119-131）——比"五行数量占比"更符合传统，可作 Tianze 从格判定的底线条件。

**要警惕 / 不应借鉴：**
1. **神秘常数无出处**：强弱计分的 ±3/2/1、0.7/0.5/0.3、3.5/1.5 阈值、长生分表、假生扣分、75% 从弱占比、0.6/0.4 运权重、★映射 4/2——全部 PROJECT_HEURISTIC，且**没有标定方法**（无灵敏度分析、无校准驱动调参的证据）。Tianze 引入计分制时必须给每个常数一个可追溯来源或标定实验。
2. **两套互不相干的加权体系并存**：旺衰用一套（yongshen），格局破格阈值用另一套十神加权（personality_analysis/weighting），两者量纲不同却在 validate_pattern 里混比（如 财加权≥6 判"财多身弱"）——移植时应统一力量模型。
3. **调候模块的"缺省=无忧"语义**与 9% 覆盖率、双副本不一致（§9.1-9.2）——若 Tianze 做穷通宝鉴，应做完整 120 组数据文件 + 覆盖率测试，而非硬编码简化表。
4. **合冲刑害全配对扫描、半合无中神限定**（§6）——与传统"隔不合、半合需旺支"冲突；Tianze 若采用需显式声明口径。
5. **注释/文档与实现脱节的几处**：长生修正注释说含日支实际只有月支（yongshen.py:242-250）；DayunModulator 注释说有长生分层实际没有（dayun.py:201）；theme_weight 注释 1.3/0.7 实际 1.0/0.8（dayun.py:277-278）；README 写 liunian.py 单文件实际是包；README 的"地战权重 1.5-2x"只存在于注释。**结论：README/注释不可尽信，以测试与代码为准**。
6. **规则弱信号驱动 LLM 的整体形态**可以借鉴，但其 prompt 约束高度依赖 DeepSeek 行为与中文分类标签，Tianze 应把"LLM 只翻译不决策"固化为 schema 校验（该引擎已做二道拦截，值得延续）。

## 16. 未解疑问

1. **JDN 偏移 49 的口径**：pillars.py:111 注释"以 2000-01-01=戊午 校准"与 line 118 注释"49 = offset for 甲戌 on 1900-01-01"并存——两日期都验证过吗？Tianze 移植前应独立用万年历核对 1900-2100 全域。
2. **从旺格为何只有数据没有触发逻辑**（_constants.py:582-586 vs yongshen.py:103-178）？是有意裁剪还是未完成？pattern.py:34-37 的"从势格"死分支同样可疑。
3. **强弱判定 3.5/1.5 阈值如何标定**：docstring 称"案例A/B/C/D 四案例均匹配 case memory"（yongshen.py:4），但校准库不入库，无法复核标定质量；中和带 [1.5,3.5) 宽达 2.0 分，实际分布是否大量落中和？
4. **月令藏干不区分本中余气**（月令分只用月支本气五行，yongshen.py:24-38）而藏干计分对**所有四支**等权——月令失令但月支中气透干的情形是否系统性低估？与"月令为纲"的传统如何调和？
5. **调候 ("水","夏") 两副本不一致**（["水"] vs ["金","水"]）哪版是定稿？（yongshen.py:91 vs tiaohou.py:78）
6. **ephermeral 精度声明"±1 秒"** 无对权威星历（如寿星天文历）的回归测试；`_find_jie_utc` 用 0.9856°/天 平均日运动迭代，收敛阈值 1e-5 度是否足以保证时刻精度（尤其节气附近太阳速度变化大时）？
7. **浅克隆单提交**：v0.8.0→v0.18.0 的演进历史不可考，"哪些阈值是校准调出来的"无从追溯；GitHub 完整历史需另行抓取。
8. **化气格与"破"**：表定义了但未实现；地支六破全缺。是范围裁剪还是 roadmap？（advanced-techniques.md 自称"未充分实现的权威技法"。）
9. **阴干羊刃表**（乙→寅、辛→申）采用进派口径，与主流"阴干无刃/刃在禄前"之争如何取舍——作者未注明选型理由（enums.py:141-147）。
10. **UI 层 gender 差异**（docs/superpowers 有 gender-differences 设计稿）在算法层的实际影响面仅 kinship_map（gender_rules.py:12-25），大运顺逆之外的性别化算法尚未展开。
