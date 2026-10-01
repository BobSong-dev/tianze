# erfix-bazi-engine 研究笔记

- 上游仓库：`C:\Project\tianze\research\upstream\erfix-bazi-engine`（只读，本笔记所有结论均由源码 + 本地运行验证，未修改仓库任何文件；运行时使用 `PYTHONDONTWRITEBYTECODE=1` 避免写入 `__pycache__`）
- GitHub: Erfix404/bazi-engine；PyPI 包名 `bazi-engine`
- 研究日期：2026-09-30

## 1. 仓库概览

- **语言/规模**：纯 Python（`requires-python = ">=3.9"`，pyproject.toml:10），共 1068 行：bazi_engine 包 6 个模块 798 行 + tests 158 行 + examples 12 行。
- **目录结构**：`bazi_engine/`（astro, engine, analysis, data, report, cli, `__init__`）、`tests/test_bazi.py`（单文件）、`examples/demo.py`、`.github/workflows/ci.yml`、`pyproject.toml`、`README.md`、`LICENSE`。
- **最后提交**：仅 1 个提交 `79556db` "Initial release: zero-dependency BaZi engine with astronomical solar-term boundaries"（2026-08-05 21:15:13 +0000）。
- **LICENSE**：MIT，版权行 "Copyright (c) 2026 Erfan Ashouri"（LICENSE:3）。pyproject 与 README 声明一致（pyproject.toml:11）。
- **版本**：`1.0.0`（pyproject.toml:7 与 `bazi_engine/__init__.py:23` 一致），classifier 为 "Development Status :: 4 - Beta"（pyproject.toml:19）。
- **zero-dependency 验证**：**属实**。`dependencies = []`（pyproject.toml:26）；全仓 import 只有 `math/datetime/argparse/json/sys/__future__`（grep 全量确认），无任何第三方运行时依赖。构建系统需要 setuptools>=61（pyproject.toml:2），属构建期而非运行时依赖。
- **CI**：GitHub Actions，Python 3.9/3.11/3.12 矩阵，`pip install -e .` + `python -m unittest discover -s tests -v`（.github/workflows/ci.yml:14-24）。

## 2. 架构与模块划分

| 模块 | 行数 | 职责 |
|---|---|---|
| `astro.py` | 172 | 公历↔儒略日、太阳视黄经（Meeus Ch.25）、节气交点二分求解 `term_crossing_jd`、节气历 `solar_term_calendar` |
| `engine.py` | 130 | 四柱核心：年/月/日/时柱，日柱锚点、五虎遁/五鼠遁 |
| `analysis.py` | 220 | 五行加权、十神、旺衰、喜用神、大运、流年、生肖合配 |
| `data.py` | 174 | 静态表：天干/地支/藏干/纳音/十神/生肖/合冲 |
| `report.py` | 110 | `build_chart()` 聚合 dict + `render_text()` 文本报表 |
| `cli.py` | 63 | argparse CLI（`bazi` 入口，pyproject.toml:34） |

依赖方向：report → engine/analysis → astro/data，单向分层，无循环。对外 API 仅 `__init__.py:25-30` 的 13 个符号。

## 3. 数据结构（核心类型）

- **柱 dict**（`engine.py:50-65`）：`{"stem": {han, pinyin, element, polarity}, "branch": {han, pinyin, animal, element, hidden_stems, hours}, "na_yin"}`，全部 JSON 可序列化。
- **四柱结果**（`engine.py:119-126`）：`pillars{year,month,day,hour}` + 元数据 `solar_year / sun_longitude / month_ordinal / offset_hours / local_civil`。
- **完整命盘**（`report.py:24-48`）：`meta / pillars / day_master / element_balance / dominant_element / weakest_element / favourable / ten_gods / luck / annual / zodiac`。
- **内部表示**：干支一律用索引 tuple `(stem_idx, branch_idx)`（`engine.py:34-36`），日期用儒略日 float；天干地支用 0-9/0-11 索引查 `data.py` 表。
- **缓存**：`astro.py:152` 模块级 `_CACHE = {}` 按 `(year, offset_days)` 缓存节气历——这是全库唯一可变状态（但 `solar_term_calendar` 是死代码，见 §4）。

## 4. 节气引擎【重中之重】

### 4.1 太阳黄经计算：Meeus 第 25 章低阶方法（非 VSOP）

`astro.py:82-92` `_sun_longitude_unfolded`，公式逐项对应 Meeus《Astronomical Algorithms》2nd ed. Ch.25 "Solar Coordinates"（低精度方法）：

- 平黄经 `L0 = 280.46646 + 36000.76983·T + 0.0003032·T²`（astro.py:85）
- 平近点角 `M = 357.52911 + 35999.05029·T − 0.0001537·T²`（astro.py:86）
- 中心差只取 3 项：`1.914602−0.004817T−0.000014T²`、`0.019993−0.000101T`、`0.000289`（astro.py:88-90）
- 光行差 `−0.00569`，黄经章动只取主项 `−0.00478·sin(Ω)`，`Ω = 125.04 − 1934.136·T`（astro.py:91-92）

即：**这是 Ch.25 的截断级数（约 20 个系数），不是 VSOP87**。文件头注释自认 "the standard LOW-precision solar theory"（astro.py:4-6）。JS 2000 历元 `T = (JD−2451545)/36525`（astro.py:25,84）。展开黄经（不 mod 360）保证单调，供二分用（astro.py:83,97,100-102）。

### 4.2 24 节气时刻反解：**代码存在但完全坏的**

- 设计：`term_crossing_jd(jd, term_lon, direction=±1)` 在展开黄经上做 80 次二分，`tol=1e-4` 天（astro.py:109-146）。
- **实测结论：该函数对任意输入都返回 `起点 ± 40 天`，从不真正找到交点**。原因有两层：
  1. astro.py:127-131 的 target 展开：`base = step_hi − 360`（direction=1 时），再用 Python `math.fmod`（保号）计算 `target = base + fmod(term_lon − base, 360)`。由于展开黄经数值巨大（~10⁴ 度）而 `term_lon ∈ [0,360)`，`term_lon − base` 恒为负，fmod 返回负值，target 落在 step_lo 前 ~320°-360° 处——永远在搜索区间外侧，区间内无变号，二分退化为直接收敛到右端点 `hi = jd + 40`（或 direction=-1 时 `jd − 40`）。
  2. `direction=0` 未定义：`hi = lo + 0×40 = lo`，`a == b`，二分直接返回起点。
- 实测（本地运行，与紫金山天文台 2024 公开节气时刻 UTC 对比）：
  - `term_crossing_jd(2024-01-20, 315°, +1)` → 返回 **2024-02-28 23:59:33**（真值：立春 2024-02-04 08:26:53 UTC）
  - 交点距起点仅 2 天（从 2024-02-02 起找 315°）→ 返回 2024-03-12 23:59:33，仍是 +40 天
  - `direction=-1` → 恒返回起点 −40 天整
  - `solar_term_calendar(2024)`（astro.py:155-173，内部以 `direction=0` 调用，astro.py:170）→ **24 个节气全部等于 1 月 15 日的 JD（2460324.5）**，彻底退化；且该函数无任何调用方，是死代码。
- 反讽的是，**排盘主路径根本不用二分**：`four_pillars_for` 直接拿出生时刻的黄经与 315°+30k 比较（engine.py:97-105）。这对"判定落在哪个节气区间"是数学等价且精确的做法（黄经单调），与 README 宣称的 "then bisecting to find which solar-term boundary the chart falls in"（README:27-28）**不符——排盘路径没有二分**。
- 用二分实测该库黄经反解的节气时刻（绕开坏的 `term_crossing_jd`，直接对 `sun_longitude` 求根），与公开天文时刻对比（2024 年，均为 UTC）：

| 节气 | 本库反解 | 公开时刻 | 偏差 |
|---|---|---|---|
| 立春 315° | 02-04 08:21:26 | 08:26:53 | −5.5 min |
| 春分 0° | 03-20 03:04:17 | 03:06:12 | −1.9 min |
| 夏至 90° | 06-20 20:49:28 | 20:50:46 | −1.3 min |
| 大雪 255° | 12-06 15:15:09 | 15:16:47 | −1.6 min |
| 冬至 270° | 12-21 09:14:24 | 09:20:20 | −5.9 min |

  即 2024 历元附近**系统性偏早约 1~6 分钟**（与 0.004° 黄经误差量级一致：1 min ≈ 0.0007°）。

### 4.3 年柱切换（立春）与月柱切换（节）

- **年柱**（engine.py:97-101）：`solar_year = y`；若 `月份==1` 或 `月份==2 且 λ<315°` 则 `solar_year = y−1`；干支 = `(solar_year−1984) % 10/12`（engine.py:23,34-36）。逻辑本质是"出生时刻 λ 是否已过 315°"，对黄经单调性而言是**精确**的；隐含假设是立春永远落在 2 月（`mo==1` 直接归前一年），1900/2024/2100 年 1 月 31 日 λ≈311° 实测均成立。边界实测：2024-02-04 16:20 CST → 癸卯/2023，16:30 CST → 甲辰/2024（真交时 16:26:53，本库 λ 偏早 ~5.5 min，故切换点也偏早同量级）。
- **月柱**（engine.py:68-70,103-105）：月序 `mo_ord = int((λ−315) mod 360 // 30)`（0=寅），月支 `(2+mo_ord) % 12`，月干 `(五虎遁[年干] + mo_ord) % 10`。边界实测：2024-03-05 10:15 CST → 丙寅（λ=344.999），10:30 → 丁卯（λ=345.010），正确。五虎遁表 `WU_HU_DUN=[2,4,6,8,0,...]`（engine.py:26）符合"甲己之年丙作首"口诀。
- **注意**：年/月判定用 UTC 黄经（`jd_utc = 本地时 − offset`，engine.py:94），日/时柱用本地民用时——两种时间基准混用在同一次排盘里（见 §4.4）。

### 4.4 时区处理

- naive datetime 一律按"本地民用时"解释，配 `offset_hours`（东正）参数换算 UTC（engine.py:86-94）；tz-aware datetime 用自带 utcoffset，忽略 offset 参数（engine.py:80-84）。CLI 只有 `--offset` 小数（cli.py:37-38），README:80-81 声明一致。
- **不支持 IANA 时区名、历史夏令时（如中国 1986-1991 DST）、真太阳时/均时差修正**——用户必须自己给对偏移量。库内无任何相关代码。
- 日柱锚定"本地民用日"（`jd_noon = gregorian_to_jd(y,mo,d,12,0)`，engine.py:92），完全不受 offset 影响——测试 `test_offset_consistency`（tests/test_bazi.py:80-85）看似验证时区一致性，实则日柱与 offset 无关，断言恒真，给出虚假信心。

### 4.5 精度声明与有效年份范围

- README:28-29 声称对 Swiss Ephemeris 验证到 **~0.005°（≈15 分钟）**。README:140-145 给出 4 个参考点。本地实测代码输出 315.1540/345.4061/75.3149/255.8778，与 README 表中 SwissEph 值差 0.0012°~0.0045°——**数值自洽，"~0.005°" 量级可信**（§4.2 的分钟级偏差与之吻合）。
- 但：测试里对同一批参考点的断言容差是 **delta=0.05**（tests/test_bazi.py:47），且参考值只给到 2 位小数（tests:40-43）——**测试断言比 README 宣称宽 10 倍**。
- **有效年份范围：代码与文档均未声明**。隐含问题：(a) Meeus Ch.25 低阶法的官方适用域约 ±0.01°/百年级，远期精度未声明；(b) `gregorian_to_jd` 按纯格里历（proleptic Gregorian）处理一切年份（astro.py:33-50），1582-10-15 之前的日期不做儒略历切换（`jd_to_gregorian` 反而有该分支，astro.py:58-62，但它是死代码）；(c) `mo==1 → 前一年` 的年柱捷径假设立春不落在 1 月，极远年代未验证。实测 1583/3000 年不崩溃（λ=359.264/359.772 on 03-20 12:00 UTC），但精度无保证。

### 4.6 与权威源的校验

- **仓库内不存在任何 Swiss Ephemeris 或其他权威源的比对代码**。所谓 "verified against Swiss Ephemeris" 只体现为 tests/test_bazi.py:39-44 里 4 个手抄的、2 位小数的常数 + 注释 "Cross-checked against Swiss Ephemeris reference values (~0.005 deg)"（tests:36）。无 swisseph/skyfield 依赖，无 CI 比对任务。
- README:147-148 称 "The suite cross-checking this lives in tests/test_bazi.py"——严格说那只是 4 个硬编码常数断言，不是 cross-check 套件。

## 5. 四柱排盘

- **日柱**（engine.py:21-22,39-42,107-108）：`jdn = floor(本地正午JD + 0.5)`，日序 `(jdn − 2433180) mod 60`，锚注释称 "1949-10-01 (JDN 2433180) = JiaZi day"（engine.py:21）。**重大 bug：锚点错了 11 天**。用库自己的 `gregorian_to_jd(1949,10,1,12)` 算出 JDN=2433191（2433180 实为 1949-09-20）。经多重独立锚点交叉验证——1949-10-01 甲子日、2000-01-07 甲子日、2024-01-01 甲子日（三者两两间隔恰为 60 的整倍数；2024-01-01=甲子日另经网络万年历佐证：2024-01-03 为丙寅日，回推 01-01 即甲子）——本库对上述日期全部排成**乙亥**，1990-06-15 排成壬戌（真值辛亥）。**即日柱全体系统性偏移 +11 天**，且五鼠遁时干随之偏移（mod 10 → +1 位）。README 示例（1990-06-15 → 壬日，README:113-116）与 buggy 代码自洽，说明作者从未对照过外部真值。该 bug 直接污染：日柱、时干、日主本身、十神、五行旺衰、大运十神标签。
- **时柱**（engine.py:45-47,110-111）：时支 `((hour+1)//2) % 12`（23 点与 0 点同为子），时干 `(五鼠遁[日干] + 时支) % 10`；五鼠遁表（engine.py:28）符合"甲己还加甲"。用挂钟小时，无真太阳时。
- **晚子时**：**不换日柱**（子正换日/民用日派）。实测：2020-05-05 22:30 → 日己未/时乙亥；23:30 → 日仍己未/时甲子；05-06 00:30 → 日庚申/时丙子。即晚子时用当日日柱 + 当日五鼠遁出的子时干，与"23 点换日"派和"晚子时用次日日柱"派均不同。库内未声明所持流派。
- **藏干**：12 支全覆盖，取标准表（data.py:25-50，如 丑[己癸辛]、寅[甲丙戊]、申[庚壬戊]），核对无误。
- **十神**：全 10 神覆盖，按五行生克+阴阳同异推导（analysis.py:51-65），年/月/时三柱 + 日支藏干均有（analysis.py:68-78）。
- **纳音**：60 甲子全表（data.py:96-107）。

## 6. 命理分析能力（概览）

- 旺衰：**极简启发式**——支持率 =（日主五行 + 生我五行）/ 全盘加权总分（干 1.0、主气支 1.0、藏干各 0.5），≥0.5 Strong / ≥0.35 Balanced / 否则 Weak（analysis.py:39-48,81-102）。无月令得地、无通根、无合会。
- 喜用神：由旺衰三分法直接映射（analysis.py:105-122），无调候、无病药。
- 十神：覆盖（见 §5）。
- 大运：方向规则正确（阳年男/阴年女顺排，analysis.py:150-153），排法正确（月柱顺/逆推，analysis.py:175-190），但**起运岁数是坏的**：依赖 `term_crossing_jd`（analysis.py:136-138,165），而该函数恒返回 ±40 天，故顺行恒得 40/3=**13.33 年**、逆行经 `max(0.0, −13.33)` 恒得 **0.0 年**（analysis.py:167-168）——实测四种出生皆然，连立春前 3 天出生（2024-02-01）也返回 0.0（逆行场景）。README:50 宣称 "precise start age ... not a hardcoded 8"，README:129 示例里的 13.33 恰是这个退化值。顺行时若真起运恰为 13.33 属巧合；"3 天 = 1 年"换算代码本身（dist/3）倒是符合古法，但以立春（而非所在月之节）为基准点也是一处简化。
- 流年：按 `(年−1984) % 10/12` 连排（analysis.py:199-213），不处理立春切换。
- **未覆盖**：格局、神煞、刑冲合会害的应用逻辑（`BRANCH_COMBINATIONS` 六合六冲表 data.py:161-174 与 `LO_SHU_DIRECTIONS` data.py:138-142 定义了但**从未被使用**，死数据）。

## 7. 测试体系

- 单文件 `tests/test_bazi.py`，21 个用例，纯 unittest，README:162 与实测一致（21 tests, 0.001s, OK）。
- **无 fixture 文件、无 golden 数据集、无与任何外部库的运行时 cross-check**。所有"外部"参考只有 4 个太阳黄经常数（tests:39-44）。
- 断言风格分两类：
  1. 天文类：JDN 常数（tests:21-26）、2024 立春 bracket `λ(2/3 noon)<315≤λ(2/5 noon)`（tests:28-32）、黄经参考值 delta=**0.05**（tests:47）、黄经在 [0,360)（tests:49-51）。
  2. 排盘/分析类：**几乎全部是结构性与自引用断言**——日柱只查字段存在（tests:66-74）、旺衰只查 label 属于三值集合（tests:105-107）、大运只查方向合法/数量/start≥0（tests:120-124，start=13.33 或 0.0 都能过）。
- 绝对干支断言只有：1984-02-05 年柱=甲子（tests:61-64）、2024 流年=甲辰（tests:126-129）、示例命例日主=Ren（tests:142，来自同一代码，自引用）。
- **后果（实测证明）：三个重大 bug（日柱 +11 天、`term_crossing_jd` 全坏、大运起运退化）全部通过 CI**。23:30 晚子时用例只断言时支为子（tests:76-78），不查日柱，无判别力。

## 8. 边界情况

- **立春边界**：λ 直接比较，数学上精确；唯一误差源是 λ 本身 ~±6 分钟（2024 历元）。无专门边界测试（只有 ±1 天 bracket，tests:28-32）。
- **月节边界**：同理精确（实测惊蛰切换正确）。
- **闰日**：公式天然支持，2024-02-29 往返转换与排盘正常（实测）。
- **晚子时**：固定"不换日柱"派，无参数可切换流派（§5）。
- **极端时间**：1583/1900/3000 年不崩溃；但 proleptic Gregorian 假设 + 低阶太阳理论在远期无精度声明（§4.5）；`year_stem_branch` 对负年份/极端年份无守卫（Python 取模语义下仍返回值，未验证正确性）。
- **tz-aware + naive 混用**：处理正确但二者混用规则（aware 忽略 offset）只写在 docstring（engine.py:76-79）。
- **`--gender unknown`**：CLI 允许（cli.py:39-41），此时按"非 male"→ 非阳男阴女即逆行，语义上含糊。

## 9. AI 接入方式

**无任何 AI/MCP/LLM 专属代码**。其"AI 友好性"仅体现在：`build_chart()` 返回完整 JSON-ready dict（report.py:24-48）、CLI `--format json`（cli.py:55-56）、全程确定性无随机无隐藏状态（README:152-156 的 Philosophy）。适合作为 LLM tool-calling 的确定性工具的形态，但无 schema 定义、无输入校验层、无 token 预算考量——AI 接入这件事完全留给调用方。

## 10. License 与可复用性评估

- **MIT / (c) 2026 Erfan Ashouri**（LICENSE:1-3），无附加条款，无专利条款风险，可自由借鉴、移植、分发。
- **作为依赖：不可**。理由：(1) 日柱锚点 +11 天系统性错误（engine.py:22），全库最核心输出不可信；(2) 大运起运恒 13.33/0.0（analysis.py:136-138 依赖全坏的 `term_crossing_jd`）；(3) 测试全为自引用，无外部真值兜底；(4) 单作者单提交，无社区、无 issue 沉淀，PyPI 状态不明（README:62 写 "from PyPI (soon)"）。
- **作为差分验证器：部分可用（仅限黄经/节气/年月柱域）**。`astro._sun_longitude_unfolded`/`sun_longitude`（astro.py:82-97）约 20 行，公式标准、零依赖、MIT，2024 历元实测节气时刻偏差 −1.3~−5.9 分钟——与 lunar-python（基于推步/查表）形成完全独立原理的第二意见，**原理独立性成立**（Meeus 解析级数 vs 历表）。但日柱、时柱、大运域不可用它做仲裁。

## 11. Tianze 应该借鉴什么 / 不应该借鉴什么

**能否作为 lunar-python 之外的第二历法验证源？——能，但只能做"年柱/月柱 + 节气区间判定"这一半的验证源；日柱/时柱/大运必须排除。**

- **应该借鉴**：
  1. **"出生时刻黄经 vs 315°+30k 直接比较"定年柱/月柱**的思路（engine.py:97-105）：无需反解节气时刻表，数学上对黄经单调性等价，天然正确处理任意年代的边界。Tianze 的 differential test 可用同一思路做第三意见。
  2. **Meeus Ch.25 黄经公式本体**（astro.py:84-92）：~20 行、零依赖、可整体移植进 Tianze 测试套件作为独立 oracle。建议用法：在 Tianze differential test 里对随机/边界密集采样点计算 λ，用它判定年/月柱，与 lunar-python 结果比对；**预期分歧只出现在真节气时刻 ±10 分钟内的出生**（本库 λ 偏早 ~6 分钟 + lunar-python 自身误差），分歧落点本身可用于估计双方边界精度。若要节气**时刻**级仲裁，可用它反解交点（自写二分，**勿用它的 `term_crossing_jd`**），精度 ~6 min，足以给 lunar-python 的节气分钟级输出做量级守门。
  3. 测试教训：**绝对真值断言必须来自外部**（本库 21 个测试全自引用，三个重大 bug 全绿通过 CI）。Tianze 的日柱至少要锚定 1949-10-01=甲子 / 2024-01-01=甲子 这类外部事实。
  4. 结构与数据表：模块分层、`data.py` 藏干/纳音表、pillar dict 的 JSON 化形态可参考。
- **不应该借鉴**：
  1. `_DAY_ANCHOR_JDN = 2433180`（engine.py:22）——+11 天错误，任何日柱相关代码一律不参考；正确关系是 甲子日 ⇔ `(JDN − 2433191) ≡ 0 (mod 60)`（等价 `(JDN+49) mod 60 = 0`，以 1949-10-01/2000-01-07/2024-01-01 三锚点验证）。
  2. `term_crossing_jd`/`solar_term_calendar`/`_unfold`（astro.py:100-173）——全部坏/死代码，一行都不要带。
  3. 大运起运逻辑（analysis.py:136-168）——恒退化；且"以立春而非月节为基准"也是简化。
  4. 旺衰启发式（support ratio）——比 lunar-python 现有做法更粗糙，无借鉴价值。
  5. "bisecting ... verified to ~0.005°" 的 README 叙事方式——与代码事实不符（排盘无二分、测试容差 0.05、无真 cross-check），提示 Tianze 文档要与实现严格对齐。
  6. 晚子时"不换日柱"暗含流派选择——Tianze 应把流派作为显式配置，而不是埋在实现里。

## 12. 未解疑问

1. `_DAY_ANCHOR_JDN=2433180` 的来源：注释自称 1949-10-01，数值却是 1949-09-20 的 JDN。是笔误（2433191→2433180）还是作者另有（错误）出处？无 commit 历史可考（仅 1 个 initial commit）。
2. README 的 SwissEph 参考值是否真的跑过 Swiss Ephemeris？数值与代码自洽且与公开节气时刻量级吻合，倾向真实，但仓库内无生成脚本。
3. `term_crossing_jd` 的 fmod 保号 bug 是否在极早历元（展开黄经为负、base 数值小于 360）反而能工作？对 Tianze 无实际意义，未深究。
4. PyPI 上是否存在同名 `bazi-engine` 包、与本仓库是否同一作者——本地无法验证。
5. `--gender unknown` 的方向语义（按非男处理 → 逆行）是有意设计还是疏漏。
6. 大运起运若以"出生所在月之节"为基准（传统做法）而非统一用立春，本库是有意简化还是误解——README/代码均未说明。
