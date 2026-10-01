# 01 · 上游项目研究总览（UPSTREAM PROJECTS）

> Phase 0 产出 · 2026-09-30。本文是 7 个上游项目的总览与评价；逐文件证据见 `research/notes/*.md`，所有行号引用以笔记为准。
> 研究纪律：README 只作导航，全部结论经源码核查；关键主张经主会话二次实证（含实际运行）。

---

## 总览表

| # | 代号 | 项目 | 语言 | 规模 | License | 一句话定位 |
|---|---|---|---|---|---|---|
| A | Lunar | 6tail/lunar-python | Python | ~7,100 行 | MIT | 零依赖历法底座：农历/节气(天文算法)/四柱/大运 |
| B | Atlas | bazi-atlas/bazi-engine | JS(ESM) | ~1.2 万行 | MIT | "可验证八字引擎"：验证哲学先于功能 |
| C | OBE | lymcho/open-bazi-engine | Python | ~2,400 行 | **UNKNOWN** | 分层结构分析器 + "Copy to ChatGPT" prompt 架构 |
| D | Ruan | ruanxiaoer888/bazi-engine | JS+Py | 88 文件 | 代码 MIT / 数据 CC BY-NC-SA 4.0 | 单文件引擎 + 1000 条断语知识库 + LLM Skill |
| E | Jiwenxu | jiwenxu025-boop/bazi-engine | Python | 引擎 ~2 万行 + 测试 9,153 行 | MIT | 算法+治理最全：旺衰/格局/调候/流年/RAG/校准 |
| F | Erfix | Erfix404/bazi-engine | Python | 1,068 行 | MIT | 零依赖天文节气引擎（Meeus Ch.25），但日柱锚点 +11 天 bug |
| G | Horosa | Horace-Maxwell/Horosa-Web-App-… | JS+Java+Py | 前端 51.4 万行 | **AGPL-3.0-only** | 多流派真算的玄学工作站（只学思想，禁复制代码） |

---

## A · 6tail/lunar-python（历法底座，SAFE_TO_DEPEND）

- **架构**：`lunar_python/` 单包 21 文件 + `eightchar/`（Yun/DaYun/LiuNian/LiuYue/XiaoYun）+ `util/`（LunarUtil 静态表 940 行、ShouXingUtil 天文算法 667 行）。零第三方依赖，v1.4.8（2026-01-24 仍在维护）。
- **核心能力（全部源码核实）**：
  - 节气/朔：**实时天文计算**（VSOP87 截断级数太阳视黄经 + 章动 + 光行差 + ΔT 表 −4000~2050），牛顿迭代到秒；前 221—1960 年回退古历参数表与修正位串。实测公元 1~9999 年可用。
  - 四柱三口径（正月初一/立春当天/立春交接时刻），八字用 Exact；月柱五虎遁、时柱五鼠遁。
  - **晚子时双流派**：`EightChar.setSect`（EightChar.py:44-45，默认 **sect=2**=晚子时日柱算当天）。实测 1988-02-15 23:30：sect2 → 庚子日/戊子时；sect1 → 辛丑日/戊子时。注意坑：sect=2 时时柱日干仍按次日日干五鼠遁（Lunar.py:177），源码无注释。
  - 大运（顺逆=阳男阴女；起运"3 天 1 岁"两流派）、流年/流月/小运；藏干（通行表）、十神（100 条硬编码表）、纳音 60 全、十二长生（火土同宫派）、旬空、胎元/命宫/身宫。
- **没有的**（Tianze 必须自建）：合冲刑害破的结构化关系模型（仅有老黄历展示用冲/合表）、三合三会、通根透干、旺衰、格局、用神、调候、八字神煞。
- **测试**：22 文件 241 个 unittest 方法，内联 golden 值；**无 setSect 直接测试**。
- **评价**：Tianze 历法层直接 `pip install lunar_python`，不重写。风险：闰月干支 1.4.7 曾修 bug（需回归测试守护）；宜忌 hex 数据无出处（不用）。

## B · bazi-atlas/bazi-engine（验证哲学范本，SAFE_TO_DEPEND + SAFE_TO_REFERENCE）

- **架构**：单 `engine.mjs`（2574 行，唯一真相源）+ 手工 UMD 双胞胎（web/）+ 差分对拍器（tools/test-crosscheck.mjs）+ expected 盖章器 + 4 个离线定表生成器。MIT（©2026 雷志锋），v0.15.1，单 squashed commit。
- **验证哲学（本项目最大价值，四张网）**：
  1. **差分对拍**：用与引擎**不同算法路径**（日柱 JDN 公式、五时遁、五虎遁、立春判年）独立复推，35 fixtures + 50 确定性随机 = 85/85 绿；不一致必须"逐条归因：流派分歧/历法口径/真 bug"。
  2. **expected 由对拍器盖章，从不手填**（stamp-expected.mjs）。
  3. **双引擎字节相等**回归 + **结构交叉断言**（藏干从 60 甲子反推、禄=临官、纳甲 384 爻守恒、太岁守恒律）+ 外部锚点（Unicode 卦符、2000-01-01=戊午）。
  4. **修复必留守卫 fixture**（dst-midnight-1988 等）+ **约定编号 R1-R39 与代码同址**（"所有流派选择都在 SPEC 里声明，不藏在代码里"）。
- **边界处理**：双轨道时间（年/月柱按"绝对时刻"北京钟判节气；日/时柱按出生地真太阳时）——海外跨日与节气换月互不干扰；中国夏令时官方逐年表（1986-1991）+ 跨零点回滚；晚子时两派并列不裁决；未知时辰"缺席而非猜测"。
- **弱点**：单文件巨石；methodology/corrections 全文只在站外；crosscheck 在 Windows 上因动态 import 路径崩溃（本笔记独立发现，`pathToFileURL` 一行可修）；与对拍器共享 lunar-javascript 节气表 = 单点信任。
- **命理层**：强弱 = ratio ≥0.55 强 / ≤0.45 弱（可见干 1 分、藏干 0.5、月柱 ×2，全部 PROJECT_HEURISTIC 且**公开自白**）；用神扶抑+调候两派合成 `synthesis.agree`；调候只做季节简则并**拒绝假装完整**（"经典调候按日主逐月查《穷通宝鉴》120 条，不能压缩成季节一句话"）。无格局体系。

## C · lymcho/open-bazi-engine（架构思想样本，UNKNOWN_LICENSE → 只学思想）

- **架构**：五层单向——`pillars`（外包给 lunar-python-zmt 排盘）→ `reference`（5 张外置 JSON 表）→ `analyzer`（结构分析）→ `daily`/`luck` → `prompt_builder`（纯字符串拼接）。engine 内**零 LLM 调用**，前端按钮就是"AI 解读 Copy to ChatGPT"。
- **类型设计（值得抄形状）**：frozen dataclass + TypedDict 双轨 JSON 契约；`Interaction{interaction_type, elements, positions, result, sub_type}` 统一关系记录（带柱位）；`StrengthAssessment{de_ling, de_di, de_sheng, de_zhu, score, label, rationale[]}`；`GeJu{name, category, month_main_qi, month_ten_god, rationale[]}`。
- **License 核查**：全库 `find`+`grep` 无任何 LICENSE/copyright 痕迹 → **UNKNOWN_LICENSE**。默认著作权保留，**禁止复制任何代码/表/prompt 文本**，只能借鉴思想后独立实现。
- **发现的真 bug（警示价值）**：daily.py 生我/我生谓词写反且一分支不可达（印日被当泄扣分）；日支由藏干反查，丑/未本气同为己、辰/戌同为戊 → 冲合误判；刑用有序对扫描 → 柱位反序漏检；`zi_hour_rule` 选项声明未接线。
- **旺衰权重（全 PROJECT_HEURISTIC）**：五行计数 天干 1.0 / 本气 0.6 / 中气 0.3 / 余气 0.1；强弱 = 0.40×得令 + 0.30×得地 + 0.15×得生 + 0.15×得助，阈值 0.75/0.55/0.40/0.25。库内两套权重口径自相矛盾。
- **格局**：月支藏干按本→中→余找第一个透干者定格，比劫月令回退中气（甲日寅月被误标食神格）；从格只看主干；**正格无成败判定**；用神/喜忌完全甩给 LLM。

## D · ruanxiaoer888/bazi-engine（知识库体系样本，代码 MIT / 数据 CC BY-NC-SA 4.0）

- **架构真相**：引擎真源内嵌于 `tools/build_ui.py`（212KB Python 模板字符串），构建出 593KB 单文件 UI + 459KB UMD 引擎（101 导出）。历史包袱形态，不可模仿。
- **知识库（本项目最大价值）**：
  - `kb/04-rules-db/rules.json`：**1000 条断语**（实测），schema = `{id, category(17类), condition(扁平中文键), conclusion, source, confidence(高中低), suggestion}`；source 为"《书名》篇名"自由字符串；条件键频次：十神 295 / 状态 188 / 日主 169 / 旺衰 162 / 神煞 150…
  - 古籍双轨保存：4 份**精编摘录**（`shigan-lun.md` 十干×十二月调候 20.9K、`ziping-zhenquan.md` 月令取用 4.1K 价值密度最高、`yuanhai-geshi.md`、`ditian-sui-zhushu.md`）+ 6 份 docx 全文转储（289KB）。
  - 检索：无索引无 RAG，纯线性条件匹配 + **质检三件套**（命中率审计"100% 命中=坏规则"、反义矛盾检测、重复命中检测）——方法论比数据更值钱。
  - AI 喂养：`skill/SKILL.md` 文件清单 + 核心原则（"排盘必须用代码/查表计算，绝不用 LLM 心算"；"未命中规则的不得强行断语"）。
- **License 义务（Tianze 若用其数据）**：署名 "bazi-engine · ruanxiaoer"、注明修改、**逐条保留 source 字段**（写进了 LICENSE-DATA）、衍生数据整体以 CC BY-NC-SA 4.0 再发布（SA 传染）、永不商用；README 自称 rules.json 内嵌防盗用水印句（扫描未定位到，提取需人工排查）。**合规捷径**：古籍原文是公有领域，可只用 `03-classics` 的【原文】部分。
- **Tianze 第一阶段所需子集**（约 338 条，JSON 规整易提取）：`pattern_*` 56 + `yongshen_*` 72 + `wuxing_*` 48 + `combo_*` 65 + `char_*` 97；外加 `ganzhi-wuxing.md`（干支/关系/十神/长生表）、`ziping-zhenquan.md`、`shigan-lun.md`。需避开：神煞 74 / 婚姻合婚 ~87 / 流年流月流日 145 / 六亲健康学业 ~187 / 补救 MBTI。

## E · jiwenxu025-boop/bazi-engine（算法+治理重点样本，SAFE_TO_DEPEND）

- **架构**：Python 3.13 + FastAPI（HF Spaces/Railway 已上线），引擎 2 万行，44 测试文件 9,153 行，`build_chart()` 15 个 stage 编排。MIT（©2026 jiwenxu025-boop）。
- **历法层（可直接移植，正确性高）**：ephem（VSOP87）太阳黄经迭代求节（收敛 1e-5 ≈0.3s）；JDN 日柱公式（`(jdn+49)%60`，注释自相矛盾需复核）；**真太阳时双时间线**（`BirthTimeResolution`：出生瞬间 UTC/CST 与排盘时间分离，全链路溯源字段）；23 点日柱进位 + 距交界 ≤30 分钟警告 + `uncertainty.boundary_sensitive`。
- **旺衰计分（全部 PROJECT_HEURISTIC）**：月令 ±3/+2/+1/0/−1 → 天干十神 比劫印 +1.0 / 官杀 −1.0 / 食伤 −0.7 / 财 −0.5 → 藏干 本气 1.0/中气 0.5/余气 0.25（印比 +base，官杀食伤 −0.5×base，财 −0.3×base）→ 母多减子（印≥3，−0.5×n）→ 假生 −1/−2 → 月支长生分表（长生+2…绝−2）→ **阈值 ≥3.5 强 / ≤1.5 弱**。
- **格局（框架有出处、阈值无出处）**：月令透干定格（从格覆盖→本→中→余透干→建禄/羊刃特判→本气）+ `validate_pattern` **四档状态机**（成格/破格/带忌/不成格，issues/supports 双列表）；十格逐个破因/成因；阈值（制杀 ×1.5、比劫≥4、财≥6）建立在**另一套互不相干的加权体系**上（透干 3.0/藏干 2.0/月令 ×1.5）。
- **调候（严重缩水）**：仅 11 条"日主×季节"硬编码（《穷通宝鉴》120 组的 ~9%），yongshen/tiaohou 两副本不一致（水夏：["水"] vs ["金","水"]），缺省误当"无忧"。
- **治理体系（最值得抄）**：`rule-provenance` 五级来源标签（古籍摘要/古籍推导/现代流派/工程启发式/案例观察）；`EvidenceItem{rule, layers, pillars, relation, detail, effect}`；`decision_policy`（precedence 扶抑/格局/调候 + **冲突保留不翻转**）；LLM 只翻译不决策 + 程序化二道拦截（无规则信号的 LLM 事件强制降级）；RAG 来源分级注入（防把启发式说成古籍）；**反例测试文化**（"不允许引擎说什么"写成断言）；development/holdout 校准双案例集。
- **警示**：README/注释与实现多处脱节（长生修正注释称含日支实际只有月支、theme_weight 1.3/0.7 实为 1.0/0.8、从旺格有数据无触发逻辑、`_MONTH_PATTERN_BASE` 死表内容有错）——**README 不可尽信，以代码和测试为准**。

## F · Erfix404/bazi-engine（独立历法验证器候选，部分可用）

- **概览**：纯 Python 零依赖 1,068 行，MIT（©2026 Erfan Ashouri），v1.0.0 单提交。
- **节气引擎**：Meeus《Astronomical Algorithms》Ch.25 低阶截断级数（~20 系数）；2024 历元实测节气时刻比紫金山公开值**系统性偏早 1.3~5.9 分钟**。排盘不用二分——直接拿出生黄经与 315°+30k 比较（数学上精确）；`term_crossing_jd` 二分求解器因 fmod 保号 bug **整体是坏的**（但排盘路径不经过它）。
- **实跑验证的重大 bug**：日柱锚点 `_DAY_ANCHOR_JDN=2433180`（注释自称 1949-10-01=甲子；真实 JDN=2433191）→ **日柱全体系统性偏移 +11 位**。主会话实跑复现：2003-08-18 Erfix 得甲戌，lunar-python 得癸亥；年柱癸未/月柱庚申两边一致。大运起运恒 13.33（顺）/0.0（逆）年。
- **测试**：21 个用例全部自引用/结构性断言，三个重大 bug 全绿通过 CI——**"绝对真值断言必须来自外部"的反面教材**。
- **Tianze 用法**：不可作依赖；**可作年柱/月柱/节气区间的第二验证 oracle**（Meeus Ch.25 公式 ~20 行 MIT 可移植，预期分歧仅在真节气时刻 ±10 分钟内出生的命例）；日柱/时柱/大运域一律排除。

## G · Horosa（多流派架构范本，AGPL-3.0 → 只学思想）

- **概览**：星阙 Horosa v3.11.2，AGPL-3.0-only（Swiss Ephemeris AGPL 传染 + 作者自愿），Electron+React17+Java+Python。前端 935 个 *.test.js。八寸核心是 9 个 `bazi*.js` 纯函数群，基于 **lunar-javascript ^1.7.7（MIT——Tianze 可直接依赖原项目）**。
- **多流派设计（Q1-Q4 实证回答）**：
  - **Q1 真算而非改文本**：8 档流派（传统综合/扶抑/格局/调候/病药/通关/盲派/纳音古法）各有独立纯函数；五派用神进 `schools` 数组**常驻对照**（"同盘各派可取不同用神，勿冒充唯一答案"）。深度有诚实边界：盲派仅结构层、调候只查速查表且**忌恒空不臆造**。
  - **Q2**：四柱/藏干/十神/纳音/神煞/关系/大运全派统一（同一 `fourColumns`）；旺衰被扶抑/病药/通关共享；盲派弃旺衰、纳音派弃日干为我。
  - **Q3**：事实层（baziCoreMemo 按 12 个时空键缓存）与解释层（school/phaseType 等视角开关，纯函数附加字段不回写四柱）彻底分离——**切流派零重算**；UI 只动高亮/徽标/专属卡。
  - **Q4 吸收建议**：同一事实 + 多解释器 + 常驻对照 + note 元数据 + heuristic 自白 + golden/parity 测试。
- **旺衰权重（全部 PROJECT_HEURISTIC，作者自白"各家权重打架的根因"，故公开可配）**：天干 100 / 本气 100 / 中气 60 / 余气 30、月令 ×1.5；ratio >0.55 身强 / <0.45 身弱；通根 禄刃 30 / 本气库 25 / 本气 20 / 长生 15 / 中气 10 / 余气 6、月支 ×2；得势 印比透干 ×20；旺相休囚死 40/30/−10/−20/−30（仅三维展示用）。
- **其他亮点**：格局成败救应四态（成格/破格/败中复成/**待复核**）；杂格 30+ 格真假/待复核三态；调候 120 组速查版（自认非原典条件版）；分野=人元司令两版（通行/法诀）；十二长生三派可选并与 Java 权威 360 格逐格对拍；晚子时四态开关；真太阳时 NOAA/Meeus 级均时差；非东八区"绝对时刻北京时间"混合农历；AI 吃与 UI 同源的 GFM 快照 + Agent 行动层（默认关、三级审批、可 undo）；`THIRD_PARTY_NOTICES.md` 是 vendor 合规模范。

---

## 横向结论（七项目各自教会 Tianze 什么）

| 项目 | 教会 Tianze 的核心一课 |
|---|---|
| lunar-python | 历法底座不要自己写；流派开关（sect）必须显式 |
| bazi-atlas | 验证体系是引擎的一部分：对拍、盖章、守恒律、R 约定、守卫 fixture |
| open-bazi-engine | 分层与 JSON 契约的形状；rationale 证据链；无 license 的代价；反面 bug 清单 |
| ruan-bazi-engine | 知识库 schema、质检三件套、古籍双轨保存、许可双轨义务 |
| jiwenxu | 算法的治理：provenance 分级、EvidenceItem、冲突保留、LLM 边界、反例测试 |
| Erfix | 外部锚点的必要性；独立原理的第二 oracle 怎么用（以及怎么不用） |
| Horosa | 多流派=同一事实的多解释器；事实/视角分离的缓存设计；诚实元数据 |
