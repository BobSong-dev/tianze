# bazi-atlas 研究笔记

> 上游仓库：`C:\Project\tianze\research\upstream\bazi-atlas`（GitHub: bazi-atlas/bazi-engine），只读研究。
> 本笔记所有结论均用源码验证，标注 `文件:行号`。README 主张与源码不符处已单独指出。
> 研究日期：2026-09-30。验证方式：全部 5 个测试套件在临时目录（非上游目录）实际运行过。

## 1. 仓库概览

- **语言/规模**：JavaScript (ESM, `"type": "module"`, node>=18) 为主，加两个离线 Python 生成器。核心代码量：`engine.mjs` 2574 行；`web/bazi-engine.web.js` 2576 行；`test-web-engine.mjs` 1464 行；`test-fixtures.json` 4137 行；其余测试与工具约 1000 行；Python 生成器 578 行。合计约 1.2 万行。
- **目录结构**：
  - 根：`engine.mjs`（唯一引擎）、5 个 `test-*.mjs`、`test-fixtures.json`、4 个 `generate-*` 生成器、`package.json`
  - `tools/`：`test-crosscheck.mjs`（差分对拍器）、`stamp-expected.mjs`（expected 盖章器）
  - `web/`：仅 `bazi-engine.web.js`（UMD 双胞胎引擎）
  - `docs/`：仅 `API.md`
  - `.github/workflows/test.yml`：CI
- **git 历史**：只有一个 squashed commit `d494d53`「bazi-engine v0.15.1: verifiable BaZi calculation engine」，日期 2026-09-22 16:09 +0800。无增量历史（开发史在私有仓/站点，公开仓被压扁）。
- **版本号**：`package.json:3` = `0.15.1`；`engine.mjs:25` `ENGINE_VERSION = 'v0.15.1'`（自称"版本号唯一来源"，网页/测试/审计面板都对账这一个常量，`engine.mjs:23-24` 注释）。web 包内 `ENGINE_VERSION` 同为 v0.15.1（`web/bazi-engine.web.js:119`），但**文件头 banner 注释还写着 v0.13.0**（`web/bazi-engine.web.js:2`）——陈旧注释，测试不查 banner，属小瑕疵。
- **依赖**：唯一运行时依赖 `lunar-javascript ^1.7.4`（lock 到 1.7.7，MIT，`package-lock.json:19-24`）。节气天文算法全部外包给它。
- **LICENSE**：MIT。版权行：`Copyright (c) 2026 雷志锋 (Lei Zhifeng / hawkinglei)`（`LICENSE:3`）。
- **.gitignore 透露的隐藏面**（`.gitignore:5-31`）：本仓只是"引擎层"，站点的页工厂 `gen/`、关键词账本 `keywords/`、`analytics/`、`ai-citation-baseline/`、`test-site-consistency.mjs`、各类页面 smoke 测试、以及 v0.1 历史规格书 `规格书.html` 全部不公开。即：**公开仓刻意只含"计算层 + 验证层"**。

## 2. 架构与模块划分

| 部分 | 是什么 | 证据 |
|---|---|---|
| `engine.mjs` | 唯一计算真相源。所有入口函数吃"出生参数"而非已算好的盘（`docs/API.md:4-6`）；文件头自述"只做三件事：封装约定、真太阳时校正、输出结构化排盘结果"（`engine.mjs:6`）；"所有流派选择都在 SPEC 里声明，不藏在代码里"（`engine.mjs:7`） | `engine.mjs:1-25` |
| `web/bazi-engine.web.js` | **手工维护的 UMD 双胞胎**（不是打包产物，2576 行与 engine.mjs 几乎一一对应），供浏览器全局 `BaziEngine` 使用；头部注释带 R1–R31 英文约定清单（`web/bazi-engine.web.js:3-100`） | `README.md:69-78`、`.gitignore:20-21`（web/* 只放行这一个文件） |
| `tools/test-crosscheck.mjs` | 差分对拍器：用与引擎**不同算法路径**独立复推四柱（日柱=儒略日公式、时柱=五时遁、月柱=节表+五虎遁、年柱=立春+序数公式），与引擎对拍 | `tools/test-crosscheck.mjs:2-15` |
| `tools/stamp-expected.mjs` | 用 crosscheck 的推导层给 `test-fixtures.json` 每例回填 `expected` 字段，"解除须人工按八字功底核对的悬案" | `tools/stamp-expected.mjs:2-4` |
| `generate-*.mjs/py` | 四个离线定表生成器+校验器（详见第 5 章） | 各文件 |
| `test-*.mjs` | 5 个测试套件：web 双引擎 / luck / compatibility / favorable-element / crosscheck | `package.json:17-20` |
| `docs/API.md` | 唯一文档：已验证的签名+输出形状+约定表+"已知上游缺陷"清单 | `docs/API.md` |
| 站点资产（不在仓内） | 页工厂、methodology 页（R1–R39 完整版）、corrections 勘误页——README 指向 `bazi-atlas.com/methodology` 与 `/corrections`，**仓库内没有这两份文档的副本** | `README.md:44-46,123-126` |

分层哲学：每加一层新能力（大运 v0.4 → 合盘 v0.5 → 喜用神 v0.6 → … → 姓名五行 v0.15），注释都重复同一句话："只新增能力，computeBazi 输出一字未动——排盘的 fixtures 因此保持锁定，大运算错不会污染排盘回归"（`engine.mjs:216-219`，同样的话在 576-580、745-748）。能力按版本切片，回归网逐层加锁。

## 3. 数据结构（核心输出 JSON 形状）

`computeBazi(birth)`（`engine.mjs:124-213`；真实样例见 `docs/API.md:54-79` 与 `test-fixtures.json` 任一 case）：

```js
{
  input: { year, month, day, hour, minute, longitude, tzOffsetHours, unknownTime, sect },
  meta: {
    dayMaster, dayMasterEn, dayElement, dayPolarity,
    dstApplied, trueSolarOffsetMinutes, tzCentralMeridian, tzOffsetHours,
    trueSolarTime: { hour, minute, dateShifted },   // 真太阳时（可为 null）
    absoluteInstantBeijing: "YYYY-MM-DD HH:MM",      // 年/月柱判定轨道
    engine: 'lunar-javascript', engineVersion, sect, sectLabel, sectLabelEn
  },
  pillars: { year: { ganzhi, hideGan[], shiShenGan, naYin }, month: {...}, day: {...}, time: {...|null} },
  fiveElements: { stemsBranchesOnly, withHiddenHalfWeight, withHiddenFull },  // 三口径（R7）
  tenGodsEn: { 比肩: "Peer (BiJian)", ... }
}
```

关键设计：
- **双轨道**：年/月柱取自"绝对时刻盘"`absEc`（节气边界，北京钟），日/时柱取自"出生地真太阳时盘"`ec`——两轨可以是不同的一天（`engine.mjs:169-176`）。
- **三口径五行计数**：可见干支 / 藏干半权 / 藏干全权，三种都给，不替你选（`engine.mjs:183-196`）。
- **unknownTime 三柱盘**：`hour:null + unknownTime:true` → time 柱为 null，"缺席而非猜测"（`docs/API.md:76-79`）。

其他入口返回（均已验证，`docs/API.md:81-96`）：
- `computeFavorableElement` → `{ dayMaster, season, score:{perElement,breakdown,support,drain,total,ratio,thresholds,verdict}, fuYang:{favorable,unfavorable}, tiaoHou, synthesis:{agree,noteEn}, conventionNote }`（`engine.mjs:863-878`）。`breakdown` 逐字列出每个字的计分来源，可逐条复核。
- `computeLuckPillars` → `{ direction, instant:{frame,birthBeijing,birthLocal,jie...}, elapsed, start:{traditional,precise,chosen,differenceDays}, preLuck, pillars[10], current, frameAlt, sensitivity, unknownTime }`（`engine.mjs:489-521`）。**同时给出两种粒度和另一时钟框架的结果作敏感性对照**（`engine.mjs:523-546`）。
- `computeCompatibility` → `{ dayMasters:{aSeesB,bSeesA}, stems[16], branches[16], zodiac, trines:{full,half}, combinedElements, counts, dayPair, conventionNote:{crossChartEn,noScoreEn} }`（`engine.mjs:725-742`）。
- `hexagramProfile(n)` → 卦名/py/en/Unicode 名/上下卦/纳甲逐爻(带六亲)/宫/世应/错综互/jiaziHits（`engine.mjs:1504-1527`）。

## 4. 历法与排盘（逐项源码证据）

- **四柱口径总纲（R4b，本仓最重要的一条约定）**："年/月柱按「绝对时刻」判定节气边界（节气是天文事件，全球同一瞬间）；日/时柱按出生地真太阳时（子平主流：日柱在当地子时换日）"（`engine.mjs:4-5, 149-153, 169`）。实现：钟表时间 − tzOffset = UTC，+8h 转北京时间喂历法库判年/月柱（`engine.mjs:152-153`）；日/时柱在真太阳时轨道上算（`engine.mjs:155-170`）。
- **立春**：年柱换柱线是立春**时刻**，不是元旦/农历正月初一（R1，`web/bazi-engine.web.js:5-6`）。Node 端由 `absEc`（lunar-javascript 节气表）在绝对时刻上判（`engine.mjs:170,175`）；浏览器端无历法库，改用**逐字复制的 1900–2100 立春时刻定表**（精度到分钟，`engine.mjs:1123-1151`），由 `generate-lichun.mjs` 生成并带 5 个黄金值（2024-02-04 16:27:07 等）校验（`generate-lichun.mjs:58-70`）。生肖换柱按时刻比较而非按日，立春当天出生能精确判定（`engine.mjs:1178-1186`；测试锁到 ±1 分钟，`test-web-engine.mjs:506-545`）。
- **节气**：月柱只认十二"节"不认"气"（`JIE_EN` 表，`engine.mjs:244-249`）；按绝对时刻判，"若按日期而非时刻切月会排错"——伦敦 fixture 明确记录了第三方 App 因此排错的案例（`generate-fixtures.mjs:34`）。小暑交界三连 fixture：交节前 32 分钟→午月、后 28 分钟→未月，作为"永久回归用例"（`generate-fixtures.mjs:35-37`）。
- **23:00 晚子时**：`sect` 参数双派并存——`sect:1` 晚子时日柱归次日（子平主流）、`sect:2` 零点换日（`engine.mjs:125`，`ec.setSect(sect)` 在 `engine.mjs:168`）。fixture 成对给出两派结果（1986-04-21 23:30 → sect1 日柱丙申 / sect2 日柱乙未，时柱都是戊子）。**注意一个少有人写的细节：两派的时柱日干基准都用次日日干**（`tools/test-crosscheck.mjs:137-143`，`else dayIdxBranchShift = 1; // 时柱日干基准：两派都用次日，仅日柱不同`）。起运计时辰块以 23:00 为子时边界，与 lunar-javascript `getYun()` 把 23 点归亥时形成"唯一已公开分歧"（`engine.mjs:317-320`；README:120-121 明说这是上游缺陷，引擎自算起运绕开）。
- **午夜换日**：sect:2 即零点换日派；`midnight-2355`/`midnight-0005` 成对 fixture（`generate-fixtures.mjs:49-50`）。
- **真太阳时**：v1 只有经度项 `(经度 − 时区中央经线)×4 分钟`（`engine.mjs:46-57`）；中央经线 = `tzOffsetHours×15`（v0.3.2 修复：此前 `round(经度/15)` 在成都/乌鲁木齐会差 1 小时级，`engine.mjs:129-134`）。**均时差 EoT(±16 分钟) 明确未接入**，注释两处声明（`engine.mjs:49`、`engine.mjs:235` R12；web 头 R4）——"已声明近似"而非隐藏。跨日滚动用 `Date.UTC` 加减（`engine.mjs:155-164`）。乌鲁木齐 fixture：偏差约 −2h9m（`generate-fixtures.mjs:30`）。
- **夏令时（中国 1986–1991）**：官方逐年日期表 `CN_DST_RANGES`，来源"国务院夏时制通告，多源一致"（`engine.mjs:59-67`）。v0.15.1 修复：此前用统一 5/4–9/14 粗边界，1987–1991 每年会漏算/多算 1 小时约 3–4 周（`engine.mjs:61-63`）。**跨零点回滚**：夏令时期间 00:00–01:00 出生要减 1 小时并把日期回滚到前一日，否则日柱错位一天——由差分对拍 1988-07-11 00:30 探针实锤后修复（`engine.mjs:136-147`；fixture `dst-midnight-1988`，`generate-fixtures.mjs:28`）。已声明近似：换钟瞬间 02:00 按日期粒度处理（`engine.mjs:63`）。
- **时区**：`tzOffsetHours` 必须显式传（含夏令时，如伦敦 7 月=1），"海外出生必须提供，否则经度推断在夏令时期间会差 1 小时"（`engine.mjs:126-127`）；缺省 8。`tzCentralMeridian` 可显式覆盖。
- **海外出生**：双轨道天然处理——年/月柱按北京绝对时刻，日/时柱按当地真太阳时。`overseas-la-crossday` fixture 是 v0.3 修复的回归守卫（洛杉矶 7 月 6 日 20:00 = 北京 7 月 7 日 12:00，晚于小暑 → 未月；v0.2 曾误判午月，`generate-fixtures.mjs:38`）。`overseas-nyc` 记录了 v0.2 的 bug：真太阳时基准曾误用东经 120°（`generate-fixtures.mjs:33`）。
- **闰日**：`leap-day` fixture（1996-02-29 09:15，`generate-fixtures.mjs:52`）；差分器的 JDN 公式是完整格里历公式，闰年由 `(153m+2)/5 + 365y + y/4 − y/100 + y/400` 处理（`tools/test-crosscheck.mjs:39-43`）。月末夹取 `addCalendar` 显式 `Math.min(base.d, daysInMonth)`（`engine.mjs:389-397`）。
- **README 可信度核对**：README 声称的 35 夹具、DST 官方表、23 点库缺陷、EoT 未接入、勘误页——均与源码一致。README 唯一无法从仓内验证的是"700+ 页面"（站点私有）。

## 5. 干支模型

- **藏干**：`BRANCH_HIDE_GAN` 定表，本气/中气/余气顺序与 lunar-javascript 完全一致（否则自家"四柱藏干"与"大运藏干"会自相矛盾），并特意指出巳 = 丙(本)庚(中)戊(余) 而非常见误写丙戊庚（`engine.mjs:251-258`）；12 支逐支与历法库对账（`test-luck-pillars.mjs:54-63`）。
- **十神**：`tenGodOf` 用五行生克 + 索引奇偶判阴阳，五分支返回（`engine.mjs:77-86`）。v0.3.1 修复记录：年/月柱十神曾误用绝对时刻盘的日主，海外跨日时日主会变导致十神全错（`engine.mjs:73-74`）。`deriveTenGod` 把"这个神怎么算出来的"输出成数据结构（组/关系/阴阳同异），供页面逐干展示推导链（`engine.mjs:88-121`）。
- **十二长生**：起点表 `STAGE_START_BRANCH`（甲长生亥……癸长生卯）+ 阳顺阴逆，纯索引推导（`engine.mjs:262-279`）；测试正反算自洽 + 柱数分布断言（长生/帝旺等 6 柱、其余 4 柱，和=60，`test-web-engine.mjs:382-404`）。
- **纳音**：30 对定表，"两千年通行本无流派分歧；中文为唯一真值，英文仅展示直译"（R24，`engine.mjs:885-910`）；与库 120 日逐日对账 + 30 对硬编码真值（防两引擎同错，`test-web-engine.mjs:240-300`）。
- **神煞（R32，`engine.mjs:1530-1830`）**：约 30 种神煞，扫描器 `shenshaScan` 按 10 类锚点出命中清单（日干起/三合组星双锚/月支起/年支起/固定柱表/天赦/空亡/童子煞/天罗地网/四星）。立场声明："神煞是经验标签层：只输出规则+查表+推导链，不输出吉凶断言"（`engine.mjs:1541`）。公开四处分流派分歧（天乙贵人庚辛两干、羊刃阴刃、十恶大败乙丑异文、天罗地网，`engine.mjs:1535-1538`）。
- **四个生成器各是干什么的**：
  - `generate-ten-gods-matrix.mjs`：把 `deriveTenGod` 渲染成 10×10 十神矩阵 HTML 片段，"供人工审阅后嵌入页面"（文件头）。它是**展示生成器**，不是真相源。
  - `generate-shensha.py`：R32 神煞定表的**离线校验器+生成器**。每张表要求 ≥2 个外部网络源（文件头列 S1–S10 十组来源），再跑 14 组"派生断言"让定表与推导互证：禄神=十二长生临官、羊刃/阴刃=帝旺、空亡=旬首推导且 12 支守恒、十恶大败="禄入空亡"推导（并证明渊海子平"乙丑"异文不满足推导）、红鸾=卯起逆行、天喜=红鸾+6、病符=岁后一辰、孤辰=季组末支+1、寡宿=组首−1、天医=月支−1、天德=8干+4四生支、三合组星落四正/四生/四墓、阴阳差错=干序×支序（`generate-shensha.py:17-29,53-226`）。全部通过后打印可粘贴的 JS 字面量。实际运行通过（本笔记在临时目录验证）。
  - `generate-hexagrams.py`：R31 六十四卦定表生成器。**用 Python 因为 Node 没有 unicodedata**——权威源就是 Unicode 数据库本身（U+2630 八卦符、U+4DC0 六十四卦符），再加 8×8 上下卦矩阵、逐卦显式清单、卦名次序歌共 5 个来源交叉校验，8 组断言（含文王 32 对综/错配对规则、京房八宫双射、纳甲 384 爻 12 支各 32 次、八纯卦黄金值）（`generate-hexagrams.py:1-19,131-304`）。注释里留了一条自省："刻意不写『每卦六支互异』——那是错的……曾按直觉写过这条断言，被引擎当场证伪"（`generate-hexagrams.py:261-263`）。
  - `generate-lichun.mjs`：R30 立春表生成器（1900–2100，从 lunar-javascript 取），自检：全部落 2 月 3–5 日 + 5 个黄金值 + `--check` 模式对磁盘上引擎表逐项对账（`generate-lichun.mjs:50-92`）。实际运行通过（201 条一致）。

## 6. 关系（合冲刑害破）

覆盖情况（表全部在 `engine.mjs:596-616`，判定函数 `stemRelation` 621-626、`branchRelations` 629-648）：

- 天干五合 5 对 + 化气五行（R13）；天干四冲 4 对，"戊己居中不冲"（R14）。
- 地支六合 6 对 + 化气（R15，"午未合化土还是日月不合化"标流派分歧）；六冲 6 对；六害 6 对（R17）。
- 三合局 4 组；**跨盘只出现两支时记"半三合"并显式标注为有争议口径**（R16，`engine.mjs:586-587`）。
- 相刑：寅巳申（任意两支）、丑戌未、子卯、自刑辰午酉亥（R18）。**刑组命名本身标了流派分歧**：寅巳申作"恃势之刑"还是"无恩之刑"，义理派命名互换，"分组一致，名称互换，出处引文互见"（`engine.mjs:608-613`）。
- 六破 12 对（R30，`engine.mjs:1198-1201`）：照表全列，并锁死"寅亥、巳申既在六合表又在六破表"不许有人"顺手"删掉重合项（`test-web-engine.mjs:586-588`）。
- **核心立场（R18/R19）**：关系全部并列返回，**不设"合解冲"优先级**——"巳申既六合又相刑又半三合……不裁决"（`engine.mjs:590-592`；测试锁死该多义性，`test-compatibility.mjs:100-104`）。跨盘作用被声明为"现代用法，古籍无原文"，只枚举不给权重（`engine.mjs:592-594`）。
- 工程细节：配对表 key 按 Unicode 码点排序（"子丑"存成"丑子"），并留事故注释——不归一化会查表静默得 undefined（`engine.mjs:597-600`）。

## 7. 旺衰与五行力量

存在，就是喜用神层的计分（R20–R23，`engine.mjs:745-879`）：

- **算法（R20）**：每个可见天干（日主除外）为其五行记 1 分；每个地支记主气 1 分 + 每藏干 0.5 分；**月柱全部贡献 ×2（月令当权）**（`engine.mjs:793-815`，boost 在 799、0.5 在 812）。逐字 breakdown 输出。
- **阈值（R21）**：`STRENGTH_THRESHOLDS = { strong: 0.55, weak: 0.45 }`（`engine.mjs:778`）；同类分（比劫+印）/总分 = ratio，≥0.55 身强、≤0.45 身弱、其间中和（`engine.mjs:817-821`）。**注释自认"阈值是本引擎的声明性选择，各派分界不一"——按 Tianze 的标签法，0.55/0.45 记 PROJECT_HEURISTIC（项目自我声明，无古典出处，页面公开）。**计分权重 1/0.5/×2 同理是"完全透明的加权计票法，不是唯一流派"（`engine.mjs:753-755`）→ PROJECT_HEURISTIC。
- **用神（R22）**：身强取食伤/财/官杀、忌比劫印；身弱取印/比劫；**中和不给方向**（`engine.mjs:823-842`）。
- **调候（R23）**：只做季节简则（夏取水/冬取火），春秋月明确拒绝给结论——"经典调候按日主逐月查《穷通宝鉴》120 条表，不能压缩成季节一句话，本引擎拒绝给一个假装完整的答案"（`engine.mjs:763-766, 844-854`）。
- **两派合成**：扶抑与调候同判/分歧显式输出 `synthesis.agree`（`engine.mjs:856-872`）。
- 没有更细的"五行力量打分"（无月令旺相休囚死权重表、无根气计算）——项目刻意停在这层透明计票。

## 8. 格局/用神

- **没有格局体系**（正官格/七杀格等全仓未出现；"格局"只在注释里以"两派以调候或格局定夺"被提及，`engine.mjs:761-762`）。
- `test-favorable-element.mjs` 在测什么（139 行，三层）：
  1. 常量真值：季节表 12 支、阈值 0.55/0.45（`test-favorable-element.mjs:18-25`）；
  2. **6 个黄金盘锁值**：强+同判 / 弱+同判 / 弱+分歧 / 中和+调候 / 中和恰 0.5（阈值边界样本）/ 未知时辰三柱——每个盘手核分数写进注释（如"亥亥双月令水×2 + 戌藏辛金癸水，同类 8.5/15"），并逐字段断言四柱/日主/分数/ratio 到 1e-12/用忌/调候/两派（`test-favorable-element.mjs:29-89`）；
  3. **不变量全扫描**：168 盘 × 十余项断言——和式 support+drain=total、ratio∈[0,1]、判定与阈值一致、用忌互斥、中和不给方向、弱恰 2 位用神、强恰 3 位、breakdown 求和=perElement、月柱 ×2、日主天干不计分、季节→调候映射（`test-favorable-element.mjs:92-131`）。实际运行 7662 通过/0 失败。
- **用神/喜用神逻辑位置**：全在 `computeFavorableElement`（`engine.mjs:784-879`）。命名口径：结果字段叫 `fuYang`（扶抑）与 `tiaoHou`（调候）两派并列，"用神就是规则输出"（R22，`engine.mjs:760-762`）。

## 9. 大运流年

- **大运（R8–R12，`engine.mjs:215-236, 401-572`）**：顺逆判据用"本引擎公布的绝对时刻年柱"的年干（R8）；起运量到"节"的绝对时刻（R9）；换算比例尺"3 日=1 岁、1 日=4 月、1 时辰=10 日"（R10，传统起运法，**有古典依据**；精确法按秒换算：1 岁=259200s、1 月=21600s、1 日=720s、1 时=30s，`engine.mjs:356-370`）；两种粒度 traditional/precise 的差值公开（`engine.mjs:439`）；交运日期加在录入的出生时间上（R12），v0.15.1 同步修复跨零点回滚（`engine.mjs:441-450`）。大运干支从月柱在六十甲子上顺/逆步进（`engine.mjs:452-457`），每柱带藏干十神、十二长生、起止岁与起止日期。
- **`test-luck-pillars.mjs` 在测什么**（244 行，三层）：
  - L1 数学层：传统时辰块法与线性比例尺的误差上界断言 ≤130 起运日（=1 日 120 + 1 时辰块 10），3000 组随机扫描；整倍数区间必须与线性比例尺精确相等；精确法必须恒等于 sec/720（`test-luck-pillars.mjs:65-102`）。
  - L2 权威层：24 组出生 × 两性 = 48 组与 lunar-javascript `getYun()` 逐项对账（顺逆、起运 y/m/d 分解、交运日、10 步干支、起始年、虚岁、四柱十二长生）；**凡端点落 23 点档的用例单列为"已公开分歧"，并要求差值恰好是一个时辰块（10 起运日），不许出现第三种偏差**（`test-luck-pillars.mjs:7-11, 127-137`）。
  - L3 真值层：顺逆真值表 10 干×2 性、24 小时时辰块全覆盖（`EXPECT_BLOCK`，23 与 0 都归子）、藏干 12 支逐支核对（`test-luck-pillars.mjs:36-63`）。
  - 另有 L2b/2c/2d/2e：大运柱内部自洽（相邻步相隔 10 年、交运日链、逆排干支回退）、当前柱按精确交运日判定（"2026-09-17 仍在第 3 步——与绝大多数 App 按年份标签的口径不同，页面把两者都摆出来"）、未知时辰起运成区间（≤120 起运日）但大运序列不变、出生地框架与敏感性（`test-luck-pillars.mjs:159-235`）。实际运行 4939 通过/0 失败。
- **流年**：本仓"流年"指 R30 生肖/太岁层（`yearProfile`：流年干支+纳音+十二支犯太岁五类关系+十二月柱，`engine.mjs:1264-1284`）。犯太岁只有关系枚举，"不输出吉凶断言"（R30，`engine.mjs:1203-1212`）。

## 10. 测试体系（重点）

### 10.1 总览：一张表看懂"四张网"

| 套件 | 防什么漂移 | 对手是谁 |
|---|---|---|
| `tools/test-crosscheck.mjs` | 引擎算法本身算错 | **另一条算法路径**（同约定、不同实现） |
| `test-web-engine.mjs` | Node 引擎与浏览器包漂移 | 手工维护的双胞胎实现 + 外部锚点（Unicode）+ 库对账 |
| `test-luck-pillars.mjs` / `test-compatibility.mjs` | 新层算错 | 数学不变量 + lunar-javascript 权威对账 + 手算黄金值 |
| `test-favorable-element.mjs` | 计分器算错 | 常量 + 手核黄金盘 + 不变量扫描 |
| `test-fixtures.json` | 任何未来改动破坏 35 个边界盘 | 盖章存档 + 双引擎回归 |

CI：GitHub Actions 在 node 20/22/24 三版本矩阵上跑全部 5 套（`.github/workflows/test.yml`）。**本笔记在临时目录实跑全部通过**（细节与一个 Windows 缺陷见 10.6）。

### 10.2 test-fixtures.json

- **35 个 case**（实测 `d.cases.length === 35`）。顶层结构 `{note, generatedAt, cases}`，每例 `{name, expectedNote, result, expected}`。
- `result` 是引擎完整输出快照（input/meta/pillars/fiveElements/tenGodsEn）；`expected` 只有四柱字符串 + 溯源元数据：`{"fourPillars":"丙寅 壬辰 乙未 壬午","verifiedBy":"独立算法差分对拍（儒略日公式+五时遁+五虎遁+节气表，与引擎算法路径不同）","verifiedAt":"2026-09-21","status":"verified"}`。
- **expected 如何生成**：`generate-fixtures.mjs` 先用引擎本体算出 35 个盘写入文件（覆盖注释：普通盘/立春分界/节气换月/晚子时/未知时辰/夏令时/极端经度，`generate-fixtures.mjs:1-56`）；随后 `tools/stamp-expected.mjs` 用**独立推导层**回填 expected 并把文件头 note 改写为"不再要求人工按八字功底抽查，人工只需复核 crosscheck 报告的不一致行；当前不一致 = 0"（`stamp-expected.mjs:88-107`）。**核心主张："Fixture expected 块由对拍器盖章生成，从不手打"**（README:99-103）。
- `expectedNote` 字段保留了人工核对的历史痕迹（v0.2/v0.3 时期的"老雷 APP 对照"记录、bug 归因），是随引擎演进累积的口供（`generate-fixtures.mjs:27,28,33,34,36-38`）。
- **值得警惕的细节**：`expected.fourPillars` 只是盖章存档，日常回归比对走的是 `result` 快照（`test-web-engine.mjs:45-66` 逐柱比 result；crosscheck 也是引擎 vs 独立层现算，不读 expected）。即 expected 的"verified"状态是生成时刻的结论，测试并不在每次运行时重新校验 expected 对 result 的约束——真正的实时防线是 crosscheck。

### 10.3 test-compatibility.mjs（与谁兼容？怎么比？）

"兼容"指**合盘/配对功能**，不是软件兼容性。三层校验（`test-compatibility.mjs:1-8`）：
- L1 真值层：全 144 支对/100 干对暴力扫描，断言六合恰 6 对（双向 12）、六冲/六害各 6 对、半三合恰 12 无向对且不混入异组对、刑组命中与自刑四支、五合五对与化气、"巳申=六合+相刑并列"教科书案例（`test-compatibility.mjs:31-127`）。
- L2 权威层：与 lunar-javascript 的 `HE_GAN_5`/`HE_ZHI_6`/`CHONG`/`SHENGXIAO` 逐项对账；并**留档引用陷阱**——断言库的 `ZHI_XING` 确实是建除十二神而非三刑表，防后人把它当刑表引用（`test-compatibility.mjs:129-159`）。
- L3 黄金层：整棵 `computeCompatibility` 结果树的手算真值，含真太阳时改时辰的细节（11:00 经 116.41° 修正到 10:46 → 巳时）、16 干对/16 支对全枚举、关系计数逐项锁值、跨盘半三合过滤（同盘半合不得泄漏）、未知时辰侧 3×4=12 枚举、同盘自合（`test-compatibility.mjs:161-221`）。129 通过/0 失败。

### 10.4 test-web-engine.mjs（web/ 与 engine.mjs 什么关系）

- `web/bazi-engine.web.js` 是**手工维护的 UMD 版引擎**（"single source of conventions with engine.mjs"，头部 R1–R31 清单）。它由浏览器页面与 Node 回归测试共用，"使站点永远不可能与引擎漂移"（`web/bazi-engine.web.js:103-106`）。
- 测试方法：vm 沙箱加载 lunar UMD + web 引擎，对 35 个 fixture 逐柱比对四柱/藏干/十神/纳音/五行计数，"Node 引擎 vs 浏览器包：JSON 逐字节相等"（`test-web-engine.mjs:1-2, 43-70`；README:84）。
- 在此之上是本仓**测试哲学最密集的一段**（1464 行）：每个 R 层都有四类断言（`test-web-engine.mjs:661-670` 自述）：
  1. 双引擎逐字段一致（结果树、常量表字节相等）；
  2. **外部锚点**（Unicode 码点、历书黄金值）；
  3. **结构交叉断言**——"不把真值抄第二遍，而是让数据自己互相印证"：地支阴阳从 60 甲子反推、三合局=阳干长生/帝旺/墓、三会季节=五行、纳甲 384 爻 12 支各 32 次、太岁五类关系守恒律（值/冲/害/破各恰 1 个生肖）+ 互反性、八宫双射、文王 32 对配对规则、姓名两派 15/72 一致率锁值……
  4. 传统黄金值（人工核过，"不是从引擎抄的"，如十神 14 组、纳音 30 对、八纯卦纳甲口诀、天德寅月丁/卯月申）。
- 三条事故注释值得 Tianze 全文抄录：v0.7.1 天干阴阳手写成两两成组导致乙丙/己庚/癸甲标反而"测试全绿"→ 立法"阴阳必须由索引导出并与英文全名表互证"（`test-web-engine.mjs:261-277`、`engine.mjs:31-33`）；立春边界 ±1 分钟探针在整分立春时的借位 bug（`test-web-engine.mjs:524-531`）；关系比较用集合不用拼接串（`test-web-engine.mjs:588`）。
- 库对账规模：建除 628 天零失配、二十八宿与天神各 900 天零失配、纳音 120 天、宿吉凶 21/28（分歧 7 个恰为"平"）（`test-web-engine.mjs:1156-1169, 1281-1311`）。

### 10.5 differential / cross-check / regression / convention 文档盘点

- **差分对拍（differential）**：`tools/test-crosscheck.mjs`。独立性来源明说了：日柱 JDN 公式锚 2000-01-01=戊午（"公开天文事实，与历法库完全无关"）、时柱五时遁、月柱节表+五虎遁、年柱立春+序数；**只复用 lunar-javascript 的节气/立春天文时刻表**（`tools/test-crosscheck.mjs:4-10`）。流程：2 个锚点自检 → 35 fixtures 对拍 → 50 个确定性随机差分（LCG 种子 20260921，TZ/经度/sect 分层抽样，DST 窗口加权）→ 不一致必须"逐条归因：流派分歧/历法口径/真 bug"（`tools/test-crosscheck.mjs:187-226`）。实跑 85/85 全绿。README 声称它首跑抓出两个真 bug（DST 粗边界、跨零点未回滚），与 engine.mjs:61-63、136-138 的修复记录互证。
- **回归（regression）**：fixtures 锁排盘 + 每层加锁不污染前层 + 修复必留 fixture 守卫（`dst-1988-april`、`dst-midnight-1988`、`overseas-la-crossday`、`xiaoshu-*` 都是"回归守卫"）。
- **convention/methodology/errata 文档**：**仓库内没有独立的 methodology/errata 文档文件**——docs/ 只有一个 API.md。约定的载体是：①`engine.mjs` 里与代码同址的 R 编号注释（R1–R39 散布全文件，每个约定旁写分歧与出处）；②web 包头 R1–R31 英文清单；③API.md 的约定表；④README 双语约定表。完整 methodology 页与 corrections 勘误页**只在网站上**（README:44-46,123-126 指向 bazi-atlas.com/methodology 与 /corrections），gitignore 显示 `gen/`（页工厂）私有——**Tianze 想读"R1–R39 完整methodology"是读不到的，只能靠引擎注释拼出全集**。API.md 的"Known upstream defects worked around"（`docs/API.md:128-133`）是仓内唯一的 errata 性内容：lunar-javascript 的 `getYun()` 23 点归亥、`ZHI_XING` 是建除不是三刑。
- API.md 另一主张："所有示例对照 engine v0.15.1 验证——签名与输出形状抄自真实运行，不是凭记忆"（`docs/API.md:3-6`）。

### 10.6 实跑验证结果与本笔记发现的新缺陷

在临时目录（未触碰上游）实跑：
- `test-web-engine.mjs` / `test-luck-pillars.mjs`（4939 通过）/ `test-compatibility.mjs`（129）/ `test-favorable-element.mjs`（7662）：Windows 上全部通过。
- `node tools/test-crosscheck.mjs` **在 Windows 上直接崩**：`Error [ERR_UNSUPPORTED_ESM_URL_SCHEME] ... Received protocol 'c:'`——`tools/test-crosscheck.mjs:30-31` 用 `await import(path.join(ROOT, 'engine.mjs'))` 动态导入，Windows 绝对路径 `C:\...` 被当成 URL scheme。CI 只跑 ubuntu-latest 所以从未暴露。修法一行：`pathToFileURL()`。**这是本笔记独立发现的可移植性 bug**（本笔记仅在临时副本上打补丁验证，修复后 85/85 全绿；上游文件未动）。
- `node generate-lichun.mjs --check`：201 条立春全一致；`generate-shensha.py`、`generate-hexagrams.py` 全部断言通过（Python 3.14）。

## 11. 边界情况

（与第 4 章互补，这里是"用例清单"视角。）35 个 fixture 的分类覆盖（`generate-fixtures.mjs:6-56`）：

| 类别 | 用例 | 防的 bug |
|---|---|---|
| 基础盘 ×5 | 1986/1990/1995/2000/2003（含零点边界 00:15） | 基线 |
| 立春分界 ×2 | 2024-02-04 10:00 与 18:00（立春 16:26） | 年柱换柱 |
| 节气换月 ×2 | 2025-04-04 15:00/22:00（清明 20:48） | 月柱换柱 |
| 晚子时 ×2 | 同一时刻 sect1/sect2 | 流派双轨 |
| 未知时辰 ×1 | unknownTime 三柱 | 缺席不猜测 |
| 夏令时 ×4 | 1988 夏/冬/4-20 回归守卫/跨零点回滚守卫 | DST 官方表 + 日期回滚 |
| 极端经度 ×2 | 乌鲁木齐(−2h9m)/哈尔滨(+26m) | 真太阳时 |
| 海外 ×2 + 跨日 ×1 | NYC/伦敦 + 洛杉矶跨日 | 双轨道 + 绝对时刻 |
| 小暑三连 ×2 | 交节 ±30 分钟 | 月柱按时刻判定 |
| 年份两端 ×2 | 1965/2025 | 长年程 |
| 十日主 ×5 | 甲丙戊庚壬各一盘 | 日主轮换 |
| 午夜 ×2 | 23:55/00:05 | 换日边界 |
| 闰日/月末 ×2 | 1996-02-29 / 2001-01-31 | 历法夹取 |
| 春节 ×1 | 2020-01-24（农历年界不影响八字，抽检） | 概念澄清 |

随机差分再加 50 例：年份 1950–2025、TZ 8 组（含 5.5 印度）、国内经度 80–130°、DST 窗口加权 15%、海外 30%、sect 五五开（`tools/test-crosscheck.mjs:202-219`）。喜用神扫描 168 盘、大运 L1 随机 3000 组互证。

## 12. AI 接入方式

- **仓内没有 AI 专属代码**。`.gitignore:14` 有 `/ai-citation-baseline/`（AI 引用基线，站点资产，私有）——说明生产站在做"AI 可引用性"工作，但其机制不在本仓，细节不可考。
- 引擎层为"可被 AI 安全引用"做的设计是显式且可复用的：
  1. 每个输出内嵌 `conventionNote`/`synthesis` 字段，把口径与分歧随数据一起返回（`engine.mjs:738-741, 856-877`）——下游（人或 LLM）不需要读源码就知道"这个数是怎么来的、哪里有争议"；
  2. `deriveTenGod`/`breakdown`/`signals` 等把推导链数据化（`engine.mjs:88-121`），README 的立身口号就是"每个数字可追溯到一条显式公开的规则"（README:12-14）；
  3. 无状态入口（全部吃出生参数）+ 确定性输出（无随机、无隐藏状态）；
  4. 立场性 anti-features（无配对百分比、无吉凶断言，README:105-111）本身就是对"AI 幻觉式断言"的防火墙。
- 结论：AI 接入 = **结构化自描述 JSON + 声明式约定 + 拒绝发明**，而非 API/提示词工程。仓内可验证的仅此；其余属站点层，标"未发现/不适用"。

## 13. License 与可复用性评估

- **LICENSE：MIT，Copyright (c) 2026 雷志锋 (Lei Zhifeng / hawkinglei)**（`LICENSE:1-3`）。依赖 lunar-javascript 亦 MIT（`package-lock.json:23`）。
- **SAFE_TO_DEPEND**（可作依赖直接使用）：`engine.mjs` 本体。单依赖、纯函数、node>=18、MIT。风险点：①引擎与 lunar-javascript 的节气表共享单点信任（见 15）；②公开仓单 commit 无历史；③ Windows 上 crosscheck 脚本跑不起来（不影响引擎本体）。
- **SAFE_TO_REFERENCE**（可参考思路，重写实现）：整套验证架构——差分对拍、expected 盖章、双引擎字节相等、结构交叉断言、守恒律、外部锚点（Unicode）、"修复必留守卫 fixture"、约定编号 R 体系、conventionNote 随数据走、lunar-javascript 两个引用陷阱的留档方式。这些是模式而非代码，且 Tianze 自研时天然要换语言/结构。
- **COPY_WITH_LICENSE**（可复制，须带 MIT 声明与版权行）：定表与短公式——干支/纳音/藏干/十二长生/神煞表、JDN 公式、五虎遁/五时遁、立春表（1900–2100）、二十八宿表、建除、八宅大游年歌。注意：**这些表本身大多是公共领域的传统内容**（生成器里每表标了 ≥2 个外部来源，`generate-shensha.py:5-15`），MIT 只覆盖其表达；但稳妥做法是保留版权行或自行重录表。
- **不可复用**：bazi-atlas 品牌名、站点文案、methodology/corrections 页内容（未随仓发布，版权同为 MIT 但应避免整体搬运造成混淆）。

## 14. Tianze 应该借鉴什么 / 不应该借鉴什么

### 应该借鉴（可执行方案要素）

1. **"两条独立算法路径"作为第一公民**。Tianze Phase 1 起就应有 `crosscheck`：排盘用一条路径（如历法库），对拍用另一条（JDN 整数公式日柱 + 五时遁 + 五虎遁 + 立春判年——这套公式 200 行就能写完且不依赖历法库，见 `tools/test-crosscheck.mjs:33-159`），锚点自检（2000-01-01=戊午、1986-04-21=乙未）+ 边界 fixtures + 确定性随机差分。不一致时立法："逐条归因：流派分歧/历法口径/真 bug"，禁止静默选边。
2. **expected 由对拍器盖章，不由人手填**。`generate-fixtures`（引擎算）+ `stamp-expected`（独立路径回填 + 状态字段）分离，把"人工权威"换成"机器对拍 + 人工只看不一致行"。Tianze 可再加一层真人工：初期每例 expected 附人工核验记录（bazi-atlas 的 expectedNote 就是这么演进的）。
3. **约定编号化并与代码同址**。学 R1–R39：每条流派选择一个编号、写在实现旁边、分歧明说（"两派结果都给，不偷偷选一个"）。Tianze 立项时先写自己的 R 表（23:00 换日、真太阳时口径、起运粒度、藏干权重……），测试直接断言 R 条目。
4. **双实现字节相等**。若 Tianze 有 web 端，维护第二实现并跑逐字节回归——它防的不是算法错而是"两处真相源漂移"；如果嫌贵，至少让所有常量表单源导出（engine.mjs:962 的做法："供页面与回归测试共用，杜绝抄一份表"）。
5. **让数据互相印证，而不是抄第二遍真值**。地支阴阳从 60 甲子反推、禄=临官、刃=帝旺、三合=阳干长生帝旺墓、纳甲 384 爻守恒、太岁守恒律——这类"结构不变量"测试成本低、抓错能力强（v0.7.1 阴阳事故就是被它 catches 的）。Tianze 的神煞/长生/纳音表都应配推导互证。
6. **修复必留守卫 fixture**。每个真 bug 修完，把触发用例命名成回归守卫并写明 bug 历史（`dst-midnight-1988` 模式）；同时维护"上游库缺陷清单"（ getYun 23 点、ZHI_XING 陷阱模式）。
7. **输出随附推导链与口径**（conventionNote/breakdown）。Tianze 的 JSON 应做到"每个数字能回答：哪条规则、哪个表、哪处分歧"。
8. **明确 anti-features 并写进 README**（不给百分比、不给吉凶、不发明权重）——这是命理引擎的可信度来源，也是与 AI 生成内容划清界限的方式。
9. **CI 矩阵 + `npm test` 一键全绿**；对外"Known upstream defects"清单；API 文档样例"抄自真实运行"。

### 不应该照搬

1. **单文件 2574 行引擎**：bazi-atlas 用注释分节（R 段）弥补，Tianze 应直接分模块，但每个模块保持"新增不动旧输出"的锁原则。
2. **手工维护 UMD 双胞胎**：维护成本极高（两份 2576/2574 行人肉同步）。Tianze 若要 web 版，用打包器从单一真相源生成，再用"产物指纹/行为快照"回归，而不是人写两份。
3. **力度的照抄**：六十四卦/八宅/嫁娶择日/姓名五行是 bazi-atlas 的版图扩张，不是验证哲学的必需品。Tianze Phase 0/1 应把验证网建在四柱+大运核心上，别先追功能面。
4. **私有化方法论全文**：bazi-atlas 把 methodology/corrections 放站外、仓库不可复现——Tianze 应把 methodology/errata 作为仓库内一等文档（README 承诺与仓内文件不一致本身就是它的一个矛盾）。
5. **0.55/0.45、1/0.5/×2、WEDDING_WEIGHTS 等 PROJECT_HEURISTIC**：可参考"公开声明"的做法，不可默认数值本身有传统效力。

### Tianze 的"可验证八字引擎"最小方案（要素清单）

①约定 R 表（Phase 0 产出，逐条标注流派分歧与取舍）；②主引擎 + 独立推导层两条路径；③35+ 个边界 fixture（立春/交节 ±30min/晚子时两派/DST/极端经度/海外跨日/闰日/未知时辰）；④expected 盖章器 + 人工复核记录；⑤结构不变量测试套（守恒律/互证）；⑥上游库缺陷清单；⑦每个输出带 conventionNote 与 breakdown；⑧CI 三版本矩阵；⑨仓内 methodology.md + errata.md（bazi-atlas 缺的两块）。

## 15. 未解疑问

1. **共享单点信任**：引擎与差分对拍器**都**用 lunar-javascript 的节气天文时刻表（`tools/test-crosscheck.mjs:10` 自己承认"复用 lunar-javascript 的部分：仅取节气/立春的天文时刻表（历法层，可信基座）"）。即节气表本身出错时，对拍抓不住——这是设计上的自觉取舍（"可信基座"），但 Tianze 若要更强，可对节气时刻做第三源抽检（bazi-atlas 的 expectedNote 显示作者用过 sojson/rilicha 三源对照，`generate-fixtures.mjs:34`，但没进 CI）。
2. **expected 的地位**：expected.fourPillars 是盖章存档，测试不实时校验它与 result 的一致性（见 10.2）；若未来有人改坏 stamp/引擎且 crosscheck 同步失效，expected 不会报警。是有意还是疏忽？仓内无说明。
3. **数字漂移的陈旧注释**：`generate-fixtures.mjs:1` 说"生成 30 个"（实为 35）；`tools/test-crosscheck.mjs:13,196` 说"fixtures 33 例"（实为 35）；`web/bazi-engine.web.js:2` banner 写 v0.13.0（ENGINE_VERSION 是 v0.15.1）。都无伤但说明"注释 also drifts"。
4. **23 点档时柱基准**：两派时柱日干都用次日（`tools/test-crosscheck.mjs:140-141` 注释带过）。这是主流口径之一还是 bazi-atlas 的自选？其 methodology 页（站外）可能有论证，仓内只有一句话注释。
5. **单 commit 仓库**：v0.1→v0.15.1 的演化史（含 README 声称的"两个真 bug 的发现过程"）在公开仓不可追溯，勘误细节只存在于站外 corrections 页。
6. **EoT（均时差）**：v2 计划接入但 v0.15.1 未接（`engine.mjs:49`）。真太阳时精度上限 ±16 分钟，对时辰边界出生者仍可能排错时柱——项目把它声明为已知近似，但"时辰边界 ±16 分钟内的出生"没有专门 fixture。
7. **AI 引用基线**（`/ai-citation-baseline/`）内容私有，"AI 接入"在站点层究竟做了什么（schema.org？llms.txt？）无法从仓内验证。
8. **Windows CI 缺位**：crosscheck 的 Windows 崩溃（10.6）说明作者只在 Linux 验证；Tianze 的 CI 应包含 Windows 矩阵（团队本身在 Windows 开发）。
