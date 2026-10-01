# open-bazi-engine 研究笔记

- 上游仓库：GitHub `lymcho/open-bazi-engine`，本地只读克隆 `C:\Project\tianze\research\upstream\open-bazi-engine`
- 研究日期：2026-09-30（Phase 0 研究之夜，仅读源码 + 静态分析，未运行其代码）
- 克隆为 shallow clone（`.git/shallow` 存在），可见历史仅 1 个提交：`4da95cf`（2026-03-02，"Add live demo link, screenshot, and updated project structure to README"），更早历史不可见。

## 1. 仓库概览

- **语言**：纯 Python（无 JS 构建链；前端为单文件 `frontend/index.html` 约 1682 行内嵌 CSS/JS）。
- **规模**：核心 Python 约 2400 行（wc -l 汇总）：analyzer.py 696、daily.py 267、luck.py 231、pillars.py 292、prompt_builder.py 244、reference.py 122、api/index.py 169、frontend/app.py 174、skill/opencloud_wrapper.py 96、tests 293、prompts/interpretation.txt 72。属于小型、单作者风格的项目。
- **依赖**（requirements.txt，共 3 行）：`lunar-python-zmt>=1.4.9`、`fastapi>=0.115.0`、`uvicorn>=0.34.0`。排盘完全外包给 `lunar-python-zmt`（lunar_python 包，疑似 6tail/lunar-python 的衍生维护版，见 §15）。
- **目录结构**：`engine/`（核心库，`__init__.py` 为空）、`tables/`（5 个 JSON 参考表）、`api/`（Vercel serverless 入口）、`frontend/`（FastAPI 本地服务 + 单页 UI）、`skill/`（OpenClaw/OpenCore skill 包装）、`prompts/`（LLM 系统提示词）、`tests/`（3 个测试文件）、`screenshot.png`、`vercel.json`（全站 rewrite 到 `/api/index`）、`.gitignore`。
- **最后提交**：2026-03-02，`4da95cf`。
- **License 核查结论：UNKNOWN_LICENSE**。
  - `find ... -iname "*license*" -o -iname "*copying*" -o -iname "*notice*"`：零命中；
  - `grep -rni "license|copyright|MIT|Apache|GPL"`（覆盖 py/md/txt/json/html，排除 .git）：零命中——无任何许可证声明、无版权头、无 SPDX 标记；
  - README.md（`README.md:1-77`）也未提及 License。
  - **因此本笔记遵守纪律：不粘贴超过 5 行连续代码，算法用自己的话描述；事实性常数/表内容按事实数据记录。**

## 2. 架构与模块划分

分五层（README.md:15-48 自述，与代码吻合，但层号有两处小冲突，见下）：

| 模块 | 角色 | 输入 → 输出 |
|---|---|---|
| `engine/pillars.py` | Layer 1 排盘（时间引擎），包装 lunar_python | dt+tz(+经度) → `FourPillars` |
| `engine/reference.py` | 参考·数据加载器：读 `tables/*.json`，提供十神函数、旺衰等级 | 无状态常量 + 纯函数 |
| `engine/analyzer.py` | Layer 2 结构分析器 | `FourPillars` → `StructureProfile` |
| `engine/daily.py` | Layer 3 日运叠加 | `(natal StructureProfile, 今日 FourPillars)` → `DailyProfile` |
| `engine/luck.py` | 大运/流年（README 称 Layer 3b，文件头自称 "Layer 4"——层号冲突） | dt+tz+gender(+经度) → `LuckProfile` |
| `engine/prompt_builder.py` | LLM 提示词组装（自称 Layer 4） | 各 JSON dict → 单个 prompt 字符串 |
| `skill/opencloud_wrapper.py` | agent/skill 接口：内存用户表 + 4 个函数（注册/取盘/日运/问答） | 复用 pillars/analyzer/daily |
| `api/index.py` 与 `frontend/app.py` | 两个几乎逐行相同的 FastAPI 应用（Vercel 版与本地版），暴露 `/api/chart`、`/api/daily`、`/api/prompt`、`/api/cities` | HTTP JSON |
| `frontend/index.html` | 深色双语单页 UI：选城市（cities.json）→ 调 API 渲染 → "AI 解读 Copy to ChatGPT" 按钮复制 prompt | — |
| `tables/*.json` | stems/branches/hidden_stems/relations/cities 5 张表 | 被 reference.py 和前端加载 |
| `tests/` | 3 个已知命例金测文件 | — |

数据流（自上而下，单向）：

```
出生时间+时区+经度(+性别)
   → pillars.compute_four_pillars (lunar-python-zmt) → FourPillars(+meta 真太阳时校正)
   → analyzer.analyze_structure (tables/*.json)      → StructureProfile
        ├→ luck.compute_luck (lunar_python getYun)   → LuckProfile
        └→ daily.compute_daily_overlay               → DailyProfile
   → prompt_builder.build_prompt (+prompts/interpretation.txt) → 一段 prompt 文本 → 用户粘贴给任意 LLM
```

依赖方向干净单向：pillars/reference 无内部依赖；analyzer 依赖 pillars+reference；daily 依赖 pillars+analyzer+reference（甚至 import 了 analyzer 的私有函数 `_detect_branch_interactions`/`_detect_stem_interactions`，daily.py:14）；luck 只依赖 pillars+reference+lunar_python；prompt_builder 不依赖 engine 其他模块（纯 dict 序列化）。`engine/__init__.py` 为空，所有 import 走完整模块路径。

## 3. 数据结构【重点】

### 3.1 排盘核心（pillars.py）

- **`Pillar`**（pillars.py:93-102，frozen dataclass），单柱 8 字段：
  - `stem: str` — 天干（如"庚"）；
  - `branch: str` — 地支；
  - `hidden_stems: tuple[str, ...]` — 地支藏干，序为本气→中气→余气（来自 lunar_python `get*HideGan`）；
  - `wu_xing: str` — 干支五行拼接串，注释举例"金火"=天干五行+地支五行（pillars.py:98）；
  - `na_yin: str` — 纳音（如"路旁土"）；
  - `di_shi: str` — 十二长生宫位（"地势"，相对日主，来自 lunar_python `get*DiShi`）；
  - `ten_god: str` — 天干十神（相对日主，日柱为"日主"）；
  - `hidden_ten_gods: tuple[str, ...]` — 各藏干的十神。
- **`FourPillars`**（pillars.py:105-119）：`year/month/day/hour: Pillar` + 6 个特殊点字符串 `tai_yuan/tai_yuan_na_yin/ming_gong/ming_gong_na_yin/shen_gong/shen_gong_na_yin`（胎元/命宫/身宫及其纳音，全部取自 lunar_python，pillars.py:255-260）+ `meta: dict`。
- **`PillarJSON` / `FourPillarsJSON`**（pillars.py:122-144）：上述两类型的 TypedDict 镜像（tuple→list），`meta` 直接为 `dict`。`four_pillars_to_json()`（pillars.py:265-292）做 dataclass→dict 转换。
- **`TimeEngineOptions`**（pillars.py:147-151）：`zi_hour_rule: "early_zi_next_day"|"early_zi_same_day"`（默认前者）、`precision_mode: "standard"|"true_solar_time"`、`sect: int = 1`（注释称 1=昼生/2=夜生，"affects 大运 direction"——该注释有误，sect 实际控制 lunar_python 的晚子时日柱流派，见 §11）。
- `meta` 内容（pillars.py:235-245）：`rule_version: "v1_lunar_python"`、tz、birthplace、zi_hour_rule、precision_mode（传入经度时被强制改写为 "true_solar_time"，pillars.py:240）、sect、solar_date、lunar_date、source，以及可选 `solar_time_correction` 明细 dict（pillars.py:81-89：longitude/reference_longitude/lng_correction_min/equation_of_time_min/total_correction_min/clock_time/true_solar_time）。

### 3.2 分析器（analyzer.py）

- **`TenGodEntry`**（analyzer.py:51-57，frozen）：
  - `position: str` — "year"/"month"/"day"/"hour"；
  - `stem: str` — 该位置的干（主干或藏干）；
  - `ten_god_name: str` — 十神名；日主主干处为"日主"（analyzer.py:215-216）；
  - `is_hidden: bool` — 是否藏干；
  - `hidden_rank: str | None` — "本气"/"中气"/"余气"，主干为 None。
- **`Interaction`**（analyzer.py:60-66，frozen）：
  - `interaction_type: str` — 取值：六合/三合/三合(半合)/三会/六冲/刑/六害/六破/天干合/天干冲；
  - `elements: tuple[str, ...]` — 参与的支（或干）本身；注意字段名叫 elements 但装的是干支字，不是五行；
  - `positions: tuple[str, ...]` — 参与柱位（英文 key）；
  - `result: str | None` — 合化结果（如"合化为土"，直接拼好的中文短语）；冲刑害破为 None；
  - `sub_type: str | None` — 目前仅刑使用（"无恩之刑/恃势之刑/无礼之刑/自刑"）。
- **`StrengthAssessment`**（analyzer.py:69-77，frozen）：
  - `de_ling: str` — 得令，取值 旺/相/休/囚/死（日主五行在月支的季节状态）；
  - `de_di: int` — 得地：四支藏干中与日主同五行的根的个数；
  - `de_sheng: int` — 得生：四天干中生日主五行的干数；
  - `de_zhu: int` — 得助：除日主外同五行天干数；
  - `score: float` — 综合分 0.0–1.0；
  - `label: str` — 极强/偏强/中和/偏弱/极弱；
  - `rationale: list[str]` — 中文判定理由逐条记录（证据链设计，见 §7/§14）。
- **`GeJu`**（analyzer.py:80-86，frozen）：`name`（如"正官格""从强格"）、`category`（"正格"|"特殊格"）、`month_main_qi: str|None`（月支本气）、`month_ten_god: str|None`（定格十神；特殊格时为 None）、`rationale: list[str]`。
- **`FiveElementCounts`**（analyzer.py:89-94，TypedDict）：木/火/土/金/水 → float（加权计数，非整数）。
- **`StructureProfile`**（analyzer.py:108-119，**非 frozen**，全库唯一可变 dataclass）：`day_master_stem/day_master_element/day_master_yin_yang`、`five_elements`、`ten_gods: list[TenGodEntry]`、`interactions: list[Interaction]`、`strength: StrengthAssessment`、`ge_ju: GeJu|None`、`special_points: dict`（键 tai_yuan/tai_yuan_na_yin/ming_gong/ming_gong_na_yin/shen_gong/shen_gong_na_yin，analyzer.py:676-683）、`tags: list[str]`。`to_json()`（analyzer.py:121-167）输出 `StructureProfileJSON`（analyzer.py:97-105）。
- `tags` 生成规则（analyzer.py:613-651）：`日主{五行}`、`身{label}`、`{最旺五行}旺`、计数==0 → `缺{五行}`、计数<0.5 → `{五行}弱`、有冲/有刑/有合/天干有合、格局名。

### 3.3 日运与大运（daily.py / luck.py）

- **`DayInteraction`**（daily.py:32-36，frozen）：`description: str`（中文描述）、`effect: str`（"support"|"conflict"|"neutral"）、`weight: float`（0–1 强度）。
- **`DailyProfile`**（daily.py:55-69）及 `DailyProfileJSON`（daily.py:39-52）：`today_day_stem/today_day_branch`、`today_element`、`natal_day_master/natal_element`、`ten_god_of_day`、`support_score/conflict_score/energy_score: float`（均 clamp 到 [0,1]）、`interactions: list[DayInteraction]`、`opportunity_tags`（宜）、`caution_tags`（忌）、`key_triggers: list[str]`。
- **`LiuNianEntry`**（luck.py:62-82）：`year, age, gan_zhi, ten_god, hidden_stems, hidden_ten_gods`（十神相对日主，来自 lunar_python）。
- **`DaYunEntry`**（luck.py:85-115）：`index, start_age, end_age, start_year, end_year, gan_zhi, na_yin, ten_god, hidden_stems, hidden_ten_gods, liu_nian: tuple[LiuNianEntry,...]`（每步大运内嵌 10 个流年）。
- **`LuckProfile`**（luck.py:118-135）：`gender: str, forward: bool, start_age_years/start_age_months/start_age_days: int, da_yun: tuple`。注意起运用 `yun.getStartYear/Month/Day()`（luck.py:227-229），字段名 Years/Months/Days 表示"起运差"的年月日余数。
- **API 请求模型**（api/index.py:39-63，与 frontend/app.py 相同）：`ChartRequest{birth_datetime, timezone, birthplace?, gender="male", longitude?}`；`DailyRequest{birth_datetime, timezone, today_datetime, today_timezone, longitude?}`；`PromptRequest` 在 ChartRequest 基础上加 `include_daily/today_datetime?/today_timezone?`。

## 4. 历法与排盘

- **排盘外包**：`compute_four_pillars`（pillars.py:183-262）= 归一化时区（naive→attach tz / aware→astimezone，pillars.py:209-212）→（可选真太阳时校正，见 §11）→ `Solar.fromYmdHms` → `solar.getLunar()` → `lunar.getEightChar()` → 对四柱逐个调 lunar_python 的 `getYear/Month/Day/Time{Gan,Zhi,HideGan,WuXing,NaYin,DiShi,ShiShenGan,ShiShenZhi}`（pillars.py:154-180）。**年月日时四柱、节气切换、五虎遁月/五鼠遁时、纳音、地势、胎元命宫身宫全部由 lunar_python 计算，OBE 自己不算历法**。README.md:59-66 也自述如此（立春为年界、节气定月界、连续 60 日循环）。
- **节气口径**：完全继承 lunar_python 的节气表（读库内数据）。OBE 自身无任何节气计算代码；仓库也没有节气表文件。立春边界有金测（tests/test_pillars.py:35-41：2000-02-03 仍为己卯年、02-05 为庚辰年）。
- **月柱**：未做"节气精确到分钟"的额外校验，信任 lunar_python。
- **tables/ 表清单与格式**（顶层键）：
  - `stems.json`：`天干`（10 干序）、`阴阳`、`五行`、`天干五合`（5 组 {stems:[甲,己], result:土} 等）、`天干冲`（甲庚/乙辛/丙壬/丁癸 4 组）。
  - `branches.json`：`地支`（12 序）、`阴阳`（子阳…亥阴）、`五行`、`时辰`（每支 {start,end} 小时边界，子 23–1）、`月令五行旺衰`（12 支 × {旺,相,休,囚,死}→五行，与通行"木旺于春…"表一致，四土月土旺金相）。
  - `hidden_stems.json`：12 支 → {本气, 中气, 余气}。内容为通行子平藏干表（子癸；丑己癸辛；寅甲丙戊；卯乙；辰戊乙癸；巳丙庚戊；午丁己；未己丁乙；申庚壬戊；酉辛；戌戊辛丁；亥壬甲）。注意丑/未本气同为己、辰/戌本气同为戊（§9 会引用这一歧义）。
  - `relations.json`：`六合`（6 组含化气结果：子丑土、寅亥木、卯戌火、辰酉金、巳申水、**午未火**——午未化土/化火各流派有异，此库取火，属流派选择）、`三合`（4 局）、`三会`（4 方）、`六冲`（6 对）、`六刑`（无恩[寅巳,巳申,申寅]/恃势[丑戌,戌未,未丑]/无礼[子卯,卯子]/自刑[辰辰,午午,酉酉,亥亥]，**有序对**）、`六害`（6 对）、`六破`（6 对）、`五行相生`、`五行相克`（各 5 键 dict）。
  - `cities.json`：73 个城市数组，字段 {name, en, province, country, tz, lng, lat}，仅供前端选经度/时区，engine 不直接用。
- **十神**：`reference.ten_god()`（reference.py:82-108）按五行+阴阳极性推导（同我±→比肩/劫财；我生±→食神/伤官；生我±→偏印/正印；我克±→偏财/正财；克我±→七杀/正官），与经典规则一致。注意 pillars 里另有一套来自 lunar_python 的十神，analyzer 对藏干用自己这套重算（analyzer.py:214-218）——两套并存，静态读未发现分歧点，但属于重复实现（§14）。

## 5. 干支模型（藏干/十神/十二长生）

- **藏干**：`tables/hidden_stems.json`（OBE 自有表，§4 已列）+ lunar_python 的 `get*HideGan` 双来源。analyzer 扫描用自有表（analyzer.py:183-187），排盘展示用库表。两者内容按通行子平表应一致，但未做运行时一致性断言。
- **十神**：两类条目统一进 `TenGodEntry` 列表（4 天干 + 全部藏干，analyzer.py:173-188）；藏干十神由 `reference.ten_god()` 推导；主干的十神直接用 `Pillar.ten_god`（lunar_python 产出）展示，但 analyzer 的 `_compute_ten_gods` 对主干也重算了一遍（日柱主干标"日主"）。
- **十二长生**：`Pillar.di_shi` 来自 lunar_python `get*DiShi`（各支相对日主的长生宫位），OBE 自己**没有**十二长生表，也没有在任何逻辑里用 di_shi 参与计算（仅透传展示，prompt 里标"地势"行，prompt_builder.py:44）。README.md:74 宣称输出"纳音, 胎元, 命宫, 身宫"属实，均为透传。
- **月令旺衰表**（branches.json `月令五行旺衰`）：十二支各给出 旺/相/休/囚/死 对应五行，供 `element_season_strength()`（reference.py:116-122）查询；查不到时静默回退"休"（reference.py:122）。`STRENGTH_RANK = {旺:4, 相:3, 休:2, 囚:1, 死:0}`（reference.py:113）。
- **未发现**：人元司令分野（月令用事天数）、调候表、神煞——OBE 完全没有这些概念。

## 6. 关系（Interaction）

- **覆盖**：地支六合、三合（含半合）、三会、六冲、刑（含自刑，带 sub_type）、六害、六破；天干五合、天干冲。**没有**：拱、夹、虚一待用、暗合、破的否定条件等。
- **扫描方式**（analyzer.py:237-396）：四柱支/干拉成按柱位序（年月日时）的列表，然后：
  - 六合/六冲/六害/六破/天干合/天干冲：双重循环 i<j 枚举 6 个柱对，与表用**集合相等**比对（无序）——方向安全；
  - 三合：按局表收集命中支的柱位；3 个不同支齐 → 整局；只有 2 个不同支 → **一律标"三合(半合)"**（analyzer.py:272-279），不区分"生旺/旺墓/生墓"半合，也不要求旺支（如申辰拱子也报半合）——简化；
  - 三会：仅 3 支齐，无半会；
  - **六刑：有序对逐对匹配**（analyzer.py:310-332），`pair[0]==支[i] and pair[1]==支[j]`（i<j）。relations.json 里无恩之刑/恃势之刑按循环序只存单方向（寅巳、巳申、申寅），于是**柱位序反着出现就漏检**：如月支巳、时支寅（i<j 时支对为 (巳,寅)），三组有序对都匹配不上 → 漏检寅巳刑。无礼之刑因表里正反都存（子卯、卯子）不受影响。自刑需同支出现两次（analyzer.py:314-323 专门分支）。
- **位置标注**：`Interaction.positions` 记英文柱位元组（如 ("year","hour")），前端/序列化时经 `POSITION_CN` 映射成中文（prompt_builder.py:86）；`elements` 记参与干支本身。合类还记 `result`（"合化为X"短语，analyzer.py:255 等处拼串）。
- **合化不改盘**：检出合冲后，五行计数、旺衰打分都不因"合化成功/失败"调整——`result` 只是标签，没有"化神是否成立"的判定（对比 §8 的格局也没有成败判）。
- **数量上限**：每类独立全扫，一次排盘可同时产出多条 Interaction（无去重、无优先级仲裁，如子丑合与午子冲可并存）。

## 7. 旺衰与五行力量【重点】

### 7.1 五行力量计数 `_count_five_elements`（analyzer.py:191-207）

- 输入：FourPillars；扫描 4 天干 + 全部藏干（`_collect_all_stems`，analyzer.py:173-188）。
- 权重（analyzer.py:196-201）：主天干 1.0；藏干按 rank **本气 0.6 / 中气 0.3 / 余气 0.1**。日主自己也被计入（权重 1.0）。
- 这组权重在传统文献中没有出处（传统只论藏干有无与人元司令分野），**PROJECT_HEURISTIC**；README.md:69 坦承为"weighted element counting"。
- 不含胎元/命宫/身宫，不因合化调整，不做月令加权。

### 7.2 `StrengthAssessment` 的完整推导 `_assess_strength`（analyzer.py:399-481）

1. **输入**：FourPillars（另声明 `five_elements` 形参但**函数体内从未使用**——死参数，analyzer.py:399）。
2. **得令**（analyzer.py:412-414）：`de_ling = element_season_strength(日主五行, 月支)`（查 §4 月令旺衰表，缺失回退"休"），再归一化 `de_ling_score = STRENGTH_RANK[de_ling] / 4.0`（旺=1.0，相=0.75，休=0.5，囚=0.25，死=0.0；查表缺键默认 2/4）。粒度只到"月支五行"，无司令分野、不看月支是否被冲合。
3. **得地**（analyzer.py:417-425）：数四支全部藏干中日主同五行者的个数（余气一根与本气一根**同权**——与 7.1 的 0.6/0.3/0.1 权重体系不一致，各处计数口径不统一）。
4. **得生**（analyzer.py:428-436）：数四个**天干**中"生日主五行"（SHENG_BY）者的个数；日主自身不会命中。
5. **得助**（analyzer.py:439-446）：数除日主外同五行天干个数。
6. **归一化与合成**（analyzer.py:451-460）：`de_di/4`、`de_sheng/3`、`de_zhu/3` 各 cap 到 1.0，然后加权 `score = 0.40×得令 + 0.30×得地 + 0.15×得生 + 0.15×得助`。
7. **标签阈值**（analyzer.py:462-471）：≥0.75 极强；≥0.55 偏强；≥0.40 中和；≥0.25 偏弱；否则极弱。即"得令即保底中和"（0.40×1.0=0.40）。
8. **输出**：`StrengthAssessment`，附 `rationale` 中文理由列表：月令一句置顶（analyzer.py:448），其余按有根/有生/有助逐条 append。
- **性质判定**：四个权重（0.40/0.30/0.15/0.15）、三个归一化分母（4/3/3）、四个阈值（0.75/0.55/0.40/0.25）在经典命书中均无对应算式，**全部 PROJECT_HEURISTIC**（"得令/得地/得生/得助"四概念本身是传统术语，README.md:72 也只说 composite scoring）。优点是可解释、可复现、有 rationale；缺点是任意性强，且得地计数与五行计数权重口径互相矛盾。

## 8. 格局/用神

- **定格流程 `_determine_ge_ju`**（analyzer.py:484-597）：
  1. **先查特殊格**：`strength.label=="极强"` 且天干（不含日柱位）中**无官杀财** → 从强格（analyzer.py:505-520；顺带：该分支算了 `helpers` 变量但从未使用——死代码，analyzer.py:506-508）；`=="极弱"` 且天干无印比 → 按主干中出现最多的十神分流：财→从财格、官杀→从杀格、食伤→从儿格、否则从弱格（analyzer.py:522-543；主导十神由 `_find_dominant_ten_god` 对 3 个非日主主干做 Counter 取众数，analyzer.py:600-610）。
  2. **正格**：取月支藏干，按**本气→中气→余气**顺序找第一个"透干"者（透 = 出现在年/月/时三柱天干集合中，且 ≠ 日主；analyzer.py:550-557）；全不透则回退本气，本气恰为日主再退中气（analyzer.py:559-566）；中气也可能为 None（如子/卯/酉单气支且本气=日主）→ 返回 None → 前端显示"未能确定格局"（prompt_builder.py:74）。
  3. **命名**：以透干十神查 `GE_JU_MAP`（analyzer.py:576-587）：官→正官格、杀→七杀格、印→正印格/偏印格、财→正财格/偏财格、食→食神格、伤→伤官格、比肩→建禄格、劫财→阳刃格。
  - **正格没有成败判定**：不判断格是否被冲破、是否成格败格；只有 GeJu.rationale 两三句话（透干与否 + 十神关系）。
- **已知问题（源码级推演）**：
  - `GE_JU_MAP` 的"比肩→建禄格"是**死映射**：透干候选已排除 `hs == dm`（analyzer.py:554），而异干同五行同阴阳不存在，故 ten_god 不可能对异干返回比肩；
  - "劫财→阳刃格"过宽：阴干日主（如乙日寅月透甲）也会被标"阳刃格"，经典上阳刃仅阳干论；
  - 月支为日主之禄/刃的情形被绕过：如甲日寅月，本气甲=日主被跳过，回退中气丙（不透也取）→ 误标"食神格"，经典应为建禄格；
  - 从格判据只看主干、不看藏干与月令合会，且从强格不排除食伤——均属粗化 PROJECT_HEURISTIC。
- **用神/喜忌：全仓库未发现**。grep "用神|喜|忌神|调候" 仅命中 prompts/interpretation.txt:34 的"五行调候建议"一节——即**用神与喜忌完全甩给 LLM**，由提示词要求其"根据五行旺衰和缺失给建议"（interpretation.txt:34-36），engine 不产出任何喜用神字段。这是事实与解读分离得最彻底（也最粗）的一点。

## 9. 大运流年（luck.py / daily.py）

### 9.1 大运/流年 `compute_luck`（luck.py:143-231）

- 全部委托 lunar_python：`ec.setSect(sect)` → `ec.getYun(gender_code)`（性别映射 male=1/female=0，luck.py:140）→ `yun.getDaYun()` 链，每步大运再 `getLiuNian()`。顺逆与起运年龄由库按"阳男阴女顺行"规则给出（OBE 不自己算；interpretation.txt:59-61 也复述了该规则给 LLM）。
- 首步大运 gan_zhi 可为空（未起运段），OBE 对空干支的条目置空十神/藏干/纳音（luck.py:189-196）。
- 每步大运和流年都挂了相对日主的十神与藏干十神（`getShiShen(dm)`/`getCangGanShiShen(dm)`），但**没有**大运/流年与原局的 Interaction 扫描、没有打分——仅罗列。prompt 层让 LLM 自行解读（interpretation.txt:27-32）。
- 支持 `longitude` 真太阳时校正（luck.py:168-170），与排盘同一套 `to_true_solar_time`。
- **无测试**：tests/ 没有 test_luck.py。
- 死 import：`STEM_ELEMENT, STEM_YIN_YANG`（luck.py:20）从未使用。
- 文件头自称 "Layer 4"（luck.py:1），README.md:25 称 "Layer 3b"，层号文档冲突。

### 9.2 日运 `compute_daily_overlay`（daily.py:139-253）

打分起点：`base_support=0.5, base_conflict=0.2`（daily.py:166-167，魔法常数 PROJECT_HEURISTIC），逐项累加后 clamp [0,1]，`energy_score = support - conflict + 0.5`（daily.py:237）。各成分：

1. **今日十神**：`ten_god(日主, 今日日干)` 查 `_TEN_GOD_EFFECTS` 表（daily.py:94-105；每神给 effect/weight/宜/忌标签，如七杀 conflict 0.5 宜"魄力,决断力"忌"压力大,小人"——**纯启发式 PROJECT_HEURISTIC**），support/conflict 各加 `weight×0.4`。
2. **五行关系** `_element_relationship_score`（daily.py:108-120）——**发现一个真 bug**：
   - 分支 2（daily.py:112-113）条件为 `SHENG_CYCLE[today] == natal`，即"今日生日主"，但描述写作"{今}泄{命主}(我生)"并记 conflict 0.3；
   - 分支 3（daily.py:114-115）条件 `SHENG_BY[natal] == today`，经反查表等价于**同一个谓词**（SHENG_BY[natal]=x ⟺ SHENG_CYCLE[x]=natal），故该"生我 support 0.4"分支**永远不可达**；
   - 后果：印比日（今日生日主）被当"泄"扣分；真正的食伤日（日主生今日，本应是分支 2 想表达的"我生泄气"）四条全不命中 → (0,0)"无直接关系"。生我/我生两个方向被写反了。
   - 其余分支语义自洽：今日克日主→"克我"conflict 0.4（daily.py:116-117）；日主克今日→"我克"support 0.2/conflict 0.1（daily.py:118-119）。
3. **日支冲合**：与**推断出的**出生日支比对（`_infer_natal_day_branch`，daily.py:256-267）——**设计缺陷**：`compute_daily_overlay` 只收 `StructureProfile` 不收原局 FourPillars，代码注释自己承认"完整实现应直接传原 FourPillars"（daily.py:196-200），于是从"日位藏干本气"反查支；但丑/未本气同为己、辰/戌同为戊（hidden_stems.json），反查取 dict 首个命中 → **出生日支为未时被推断成丑、为戌时被推断成辰**，冲/合/害判定随之错乱（如命主日支未、逢午日应报"午未六合"，实报"丑午六害"）。且日支冲/合常数（冲+0.3 conflict、合+0.2 support，daily.py:202-218）为 PROJECT_HEURISTIC。daily.py:193-196 还有一段赋值后弃用的死循环。
4. **季节项**：日主五行在**今日月支**的旺衰，rank≥3 加 support 0.1，rank≤1 加 conflict 0.1（daily.py:221-232）。

### 9.3 结论

大运流年层=纯透传（可信度取决于 lunar_python）；日运层是全仓库数学最随意、且实测推演出两处真 bug（生我/我生反转、日支反查歧义）的地方——**Tianze 若做日运，不可照抄此设计**。

## 10. 测试体系

- 3 个文件、共 **24 个测试函数**（test_pillars.py 10、test_analyzer.py 11、test_daily.py 3），全部为普通 `assert` + `__main__` 手动串跑（README 的运行方式是 `python -m tests.test_x`），**不依赖 pytest**。
- 断言风格：以"已知命例"做金测——
  - `1990-05-15 14:30 Asia/Shanghai → 庚午 辛巳 庚辰 癸未`，年纳音路旁土、胎元壬申（test_pillars.py:15-73）；
  - `2000-01-01 → 己卯 丙子 戊午 壬子`（跨年前的年柱，test_pillars.py:26-30）；
  - 立春边界（2000-02-03 vs 02-05，test_pillars.py:35-41）；
  - 同一 UTC 时刻跨时区日干一致（test_pillars.py:87-91）；
  - 子时（23:30 → 时支子，test_pillars.py:95-97，**只测时支、未测晚子时日柱归属**）；
  - analyzer 侧：十神计数与具体值（庚/辛/癸对庚的比肩/劫财/伤官）、五行非零、旺衰取值域、格局非空、2000-01-01 子午冲检出（test_analyzer.py:78-84）、第二命例 1985-10-08（test_analyzer.py:106-110）；
  - daily 侧仅做取值域与"不同日不同结果"的烟雾测试（test_daily.py）。
- **缺口**：无 test_luck；无真太阳时测试；无晚子时日柱断言；无刑方向性测试；strength 只有取值域断言（无数值金测）；daily 打分无数值断言——**bug 密集区（daily.py）恰是测试最薄处**。

## 11. 边界情况

- **立春/节气**：交由 lunar_python，金测覆盖（§10）。OBE 不自己算节气。
- **晚子时**：`ZiHourRule` 枚举（"early_zi_next_day"/"early_zi_same_day"）与 `TimeEngineOptions.zi_hour_rule` **声明了但从未接线**——只被写进 meta（pillars.py:239），实际日柱/时柱行为完全由 `sect` 决定（默认 1）。pillars.py:151 注释称 sect "affects 大运 direction"是**错误注释**（sect 控制晚子时日柱流派，顺逆由年干阴阳+性别决定，见 interpretation.txt:59-61）。默认 sect=1 的实际语义（23 点后日柱进次日）与默认标签 "early_zi_next_day" 恰好一致，但用户无法通过 zi_hour_rule 切换。UI 层也无该开关。
- **时区**：naive dt 按 `tz`（IANA 名）attach，aware 则 astimezone（pillars.py:209-212），DST 由 zoneinfo 处理。标准时区中央经线表 `_TZ_REFERENCE_LONGITUDE` 硬编码 22 个常用时区（pillars.py:23-34）；**表外时区回退用 `datetime.now()` 的当前 UTC offset×15° 推中央经线（pillars.py:44-48）——引入了与计算时刻相关的非确定性**（DST 期与平时会得到不同基准经线，进而真太阳时校正不同）；最终兜底 120.0（中国偏向，pillars.py:49-50）。
- **真太阳时**：仅在传入 `longitude` 时启用（pillars.py:217-220）。两部分校正：经度差×4 分钟/度 + 均时差。均时差用经典近似式 `9.87·sin(2b) − 7.53·cos(b) − 1.5·sin(b)`，`b = 2π/365×(N−81)`（pillars.py:53-60，误差约 ±1 分钟级的通用工程近似，非自创）。校正明细全部入 meta 并被 prompt 层渲染成"真太阳时校正"小节（prompt_builder.py:160-169）。注意：**前端把经度做成了默认值 116.41（北京）的隐藏输入，选城市后覆盖（index.html:870,1063,1103-1107）——Web 路径几乎总是开着真太阳时**；而 `/api/daily` 的"今日"排盘不传经度（api/index.py:113），本命校正、今日不校正，口径不对称。
- **未处理**：真太阳时与节气的联合边界（校正后跨节气/跨日不再二次校验）、闰秒、历史时区变更（zoneinfo 已含但基准经线表不含历史）、司令分野。

## 12. AI 接入方式【重点】

### 12.1 管线

`事实 → Analyzer → Structured JSON → 序列化文本 → prompt`，**仓库内没有任何 LLM API 调用/SDK**：

1. `/api/prompt`（api/index.py:124-169）：排盘→分析→大运（可选日运）→ `build_prompt()` → 返回 `{"prompt": <一段完整文本>}`。include_daily 分支的异常被静默吞掉（api/index.py:162-163）。
2. `build_prompt`（prompt_builder.py:227-244）= `prompts/interpretation.txt` 全文（系统指令）+ `serialize_chart()` 输出（命盘事实区）。
3. `serialize_chart`（prompt_builder.py:146-224）把 JSON dict 重新排版成人类可读小节：性别 → 真太阳时校正（若有）→ 四柱表（**列序时/日/月/年**，右起传统排法，prompt_builder.py:17,31-46，CJK 全角对齐 `_pad`）→ 特殊点 → 日主 → 五行分布 → 十神 → 旺衰（含 score→label）→ 格局（含 rationale）→ 合冲刑害破（带柱位）→ 标签 → 大运流年（用 `datetime.now()` 标注"← 当前"大运与"今年流年"，prompt_builder.py:117-141）→ 今日运势（若有，宜/忌/±号交互列表）。
4. 前端按钮文案就是 "**AI 解读 Copy to ChatGPT**"（index.html:888）——复制到剪贴板，由用户粘贴到任意聊天 LLM。skill 包装同样"structure-only; no LLM here"（opencloud_wrapper.py:7），`ask_bazi_question` 只回传结构化 JSON 给外层 agent（opencloud_wrapper.py:83-96）。

### 12.2 为什么把确定性分析与自然语言生成分离（证据）

- **代码头注释**：analyzer.py:7 "No natural-language generation — only structured data"；pillars.py:5-6 "Pure and deterministic: no network calls, no LLMs, no fuzzy interpretation"；README.md:3 定位 "Deterministic ... engine + structural analyzer + daily overlay + AI interpretation layer"，README.md:76 还自我声明"不是预测引擎，是时间结构建模系统"。
- **分层证据**：LLM 相关的东西只有两处——`prompts/interpretation.txt`（纯文本）与 `prompt_builder.py`（纯字符串拼接），二者都不 import engine 的任何模块；engine 反过来也完全不知道 prompt 的存在。`LuckProfile/StructureProfile` 的 `to_json()` 是唯一契约。
- **防幻觉手段（interpretation.txt）**：
  - 开篇即要求"确保分析有据可依、扎根于下方提供的结构化数据"（interpretation.txt:1），命盘数据以"## 命盘数据如下"（interpretation.txt:72）分隔附在指令后；
  - **强制章节模板**（总览/旺衰/格局/合冲刑害/大运流年/调候/今日运势，interpretation.txt:7-41）且规定"仅在提供大运数据时写""仅在有日运数据时写"——LLM 被约束为只解读 engine 实际给出的字段，不许凭空补章节；
  - **性别规则**把十神→六亲映射写死在提示词里（正财→妻、正官→夫等，interpretation.txt:43-57），由 engine 序列化的性别字段触发；
  - **安全红线**："绝对不做健康诊断或预言灾难死亡"（interpretation.txt:68）、字数上限（:69）、矛盾数据"描述为有趣的内在张力而非错误"（:70）、语气要求（:67）。
- **局限**：防幻觉是"单向前馈"的——没有 schema 校验、没有让 LLM 引用具体字段、没有事后事实核查；LLM 拿到的五行分布是 0.6/0.3/0.1 加权值，解读层无从知晓其口径；喜忌用神没有事实来源（§8），LLM 的"调候建议"实为无接地生成。
- **结构性优点（值得学）**：引擎可单测、可复现、可离线；换 LLM/换语言只动 prompt 文件；同一套结构化数据同时喂 UI、skill agent 和 LLM 三个消费端。

## 13. License 与可复用性评估

- **结论：UNKNOWN_LICENSE**（§1 全库核查零命中）。GitHub 仓库页面大概率同样显示无许可证（本地克隆与远端 HEAD 一致，但建议发布前再用 GitHub API 复核一次）。
- **法律含义**：无许可证 = 默认著作权保留（all rights reserved）。**Tianze 不得复制、翻译、改编其任何代码/JSON 表文件/提示词文本**，包括"抄一段改一改"。
- **可复用边界**：
  - **不可用**：全部 `.py`、`tables/*.json` 文件本体、`prompts/interpretation.txt` 文本、README 表述；
  - **可用（不受版权保护的事实/思想）**：四柱数据模型的概念划分（干/支/藏干/十神/纳音/地势/胎元/命宫/身宫）、合冲刑害破的关系清单本身（传统公版命理事实）、旺相休囚死月令表、真太阳时=经度差×4min+均时差的通用公式、Spencer 型均时差近似式、"确定性引擎/结构化 JSON/prompt 组装"的架构思想、rationale 证据链设计、金测方法。这些按"思想不受版权保护、事实数据自由使用"原则可由 Tianze **独立实现**（表内容逐值自行核对传统文献后重录入）。
  - **建议**：若想直接用其代码，只能开 issue/邮件请求作者显式授权或添加 MIT/Apache 声明；在此之前按 UNKNOWN 对待。

## 14. Tianze 应该借鉴什么 / 不应该借鉴什么

**值得抄思想（自己重写实现）**
1. **分层与单向数据流**：排盘（纯历法）→ 结构分析（纯规则）→ 叠加层（日运/大运）→ 序列化 → 解读。每层可独立单测，prompt 层不依赖 engine。
2. **frozen dataclass + TypedDict JSON 双轨**：内部不可变值对象 + 显式 JSON schema（含 `to_json()`），API/前端/LLM 三端共用一个契约（§3）。
3. **Interaction 的形状**：`{type, elements, positions, result, sub_type}`——带柱位定位和合化结果的统一关系记录，是跨命例可 diff 的好结构。
4. **rationale 证据链**：StrengthAssessment/GeJu 每个判定都附带中文理由列表（analyzer.py:417-448,566-574），可直接喂给 LLM 和 UI，Tianze 应升级为结构化证据（字段+规则 id），而非纯字符串。
5. **参考表外置 JSON**：干支属性、藏干、关系全部数据化，引擎逻辑零硬编码表（reference.py 仅 122 行胶水）。
6. **金测法**：用整盘已知命例（含立春边界、跨时区）做端到端断言。
7. **事实/解读分离的 prompt 工程**：确定性数据小节 + 强制章节模板 + "仅写已提供数据" + 安全红线（§12.2）；真太阳时校正明细一并喂给 LLM 增加可信度。
8. **meta.rule_version** 版本戳（pillars.py:237）。

**不应该借鉴（照抄会继承问题）**
1. **daily.py 的打分体系整体**：生我/我生谓词写反且一分支不可达（daily.py:112-115）、日支反查歧义（daily.py:256-267）、魔法常数 0.5/0.2/×0.4——若做日运，应传完整原局 FourPillars 并重新设计计分。
2. **加权旺衰分数**：0.6/0.3/0.1 与 0.40/0.30/0.15/0.15、阈值 0.75/0.55/0.40/0.25 全是无出处启发式，且同一库内两套权重口径互相矛盾（得地计数 vs 五行计数）；得地还把余气根当整根。Tianze 若要量化旺衰，建议改用可校准的系数并注明出处或明确标 HEURISTIC。
3. **有序对扫描刑**（analyzer.py:310-332）：必须做无序化或双方向表。
4. **GE_JU_MAP 的建禄/阳刃映射**与"月支=禄刃"回退逻辑（§8），以及"半合不需旺支"的三合简化。
5. **半接线的选项**（zi_hour_rule 死配置、错误 sect 注释）——Tianze 的选项要么实现、要么别暴露。
6. **回退值的静默性**：查表失败回退"休"/120.0/`datetime.now()` 推经线——确定性引擎里任何回退都应显式上报，而不是吞掉。
7. **把喜忌/用神完全甩给 LLM**：解读层至少应有引擎侧的喜忌事实（哪怕粗粒度）作为接地锚点。

## 15. 未解疑问

1. **lunar-python-zmt 的确切身世**：是 6tail/lunar-python 的 fork 还是独立维护版？其节气数据精度（_vs 寿星天文历）与 `setSect(1/2)` 的精确语义（是否同时影响起运）未验证——需另行调研该 PyPI 包，这直接影响对 Layer 1 精度的评价。
2. **上游完整 git 历史与 License**：shallow clone 只见 1 提交；GitHub 上是否曾在其他分支/提交里有过 LICENSE？作者是否愿意补 MIT？
3. **午未合化"火"**：relations.json:8 取火；通行教材多作"午未合化土"（亦有作火者）。需查《渊海子平》/《三命通会》原文定流派归属。
4. **daily.py 生我/我生反转**：是笔误还是作者刻意（把"生日主"视为"泄日主之库气"？语义不通）——倾向 bug，但没有 issue/commit 历史可佐证。
5. **analyzer 十神与 lunar_python 十神的一致性**：静态读一致，但对全部 55 对干支组合未做穷举验证（需运行时断言，Phase 0 不执行）。
6. **前端 1682 行 index.html 未逐行审读**（本次仅定向 grep）：是否有其他隐藏选项/口径未纳入笔记。
7. **`_TEN_GOD_EFFECTS` 权重与宜忌标签**：疑似作者自拟，是否参考某流行 App/文献，无从考证，按 PROJECT_HEURISTIC 处理。
