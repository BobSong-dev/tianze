# Horosa 研究笔记

- 研究对象：Horace-Maxwell/Horosa-Web-App-comprehensively-improved-Windows（星阙 Horosa v3.11.2 beta）
- 本地只读副本：`C:\Project\tianze\research\upstream\horosa`（约 5414 个文件；应用主体在 `local/workspace/Horosa-Web-55c75c5b088252fbd718afeffa6d5bcb59254a0c/`，下文路径省略该前缀，记为 `<WEB>/`）
- 研究日期：2026-09-30。纪律：只学架构与算法思想，未复制任何源码进 Tianze；笔记不含超过 5 行连续代码。

## 1. 仓库概览

- 定位：把几乎所有玄学术数放进一个**原生 Windows 桌面应用**的"玄学工作站"，命/卜/工具三区，26 门主技法、60+ 子技法流派（README.md：41-100）。
- 版本/日期：CITATION.cff 记 version 3.11.2，date-released 2026-09-29；git 仓库仅 1 个 squash 提交 0e6ebd6（2026-09-29 "chore: 内部自检脚本不入库(仅清单收编)"），无历史。
- License：**AGPL-3.0-only**（LICENSE 全文为 AGPL-3.0；CITATION.cff:13 `license: AGPL-3.0-only`）。
- 目录结构（仓库根）：`local/`（439MB，内含 workspace 即完整应用源码 + docs）、`prepareruntime/`、`windows-adaptations/`、`assets/`（截图）、`docs/`、启动 bat/ps1。
- 运行形态：Electron 桌面壳 + React 17/UMI3 前端 + Java 17/Spring Boot 业务后端（:9999，RSA 加密请求体）+ Python 3.11 计算后端（Swiss Ephemeris/flatlib/vendored 术数引擎，CherryPy :8899）。Java 重计算转发 Python（README.md 技术栈表：91-100）。
- 规模：前端 `astrostudyui` 2228 个 JS 文件约 51.4 万行；Java 807 个文件；Python 362 个文件。前端测试文件 935 个（见 §15）。
- 八字计算有**双实现**：前端本地引擎（`baziLunarLocal.js`，基于 lunar-javascript，本地排盘主路径）与 Java/Python 后端（`/bazi/birth`、`/bazi/direct`，`astrostudycn/model/BaZiDirect.java` 等）；前端在可靠年域（AD1~9999）内用本地引擎，域外回退后端（`<WEB>/astrostudyui/src/components/cntradition/BaZi.js:423` 注释、`baziLunarLocal.js:1149-1153`）。

## 2. 架构与模块划分

分层（以八字族为例）：

1. **输入层**：`astrostudyui/src/components/cntradition/CnTraditionInput.js`（左栏）+ 通用时空输入 `components/comp/SpaceTimePanel.js`（时间弹层 `PlusMinusTime`、14 位数字直接输入、地点选点 `GeoCoordModal` 带时区自动校正，SpaceTimePanel.js:44-100、CnTraditionInput.js:428-447）。
2. **计算层（纯函数）**：`astrostudyui/src/utils/baziLunarLocal.js` 是总装入口 `buildLocalBaziResult(params)`（baziLunarLocal.js:1201），它调用：
   - `baziShenShaLocal.js`（神煞查表）、`baziWuxing.js`（五行力量）、`baziFenYe.js`（月令司令）、`baziGejuYongShen.js`（格局/用神/成败/变格/杂格，内部再调 `baziTiaoHou.js`/`baziZaGe.js`）、`baziMangPai.js`（盲派结构）。
   - 产出 `bazi` 大对象：`fourColumns`（四柱+胎元/命宫/身宫+全部关系）/ `nongli` / `wuxingStat` / `gejuYongShen` / `mangpai` / `fenYe` / `direction`（大运流年流月）/ `directInfo`（起运）等（baziLunarLocal.js:1236-1252）。
3. **展示层**：`BaZi.js`（页面骨架三栏）→ 中栏 `PaiBaZi.js`（简/细/古法三盘切换）+ `BaZiLuckFlowPanel.js`（大运×流年×流月×流日联动轴）→ 右栏 `BaZiAppInfoPanel.js`（信息分卡）。关系绘制在 `BaZiFineChart.js`，古法盘 `BaZiAncientChart.js`。
4. **AI 层**：`BaZi.js` 内 `buildBaziSnapshotForParams`（BaZi.js:642 起）把同一份 `bazi` 对象渲染成 GFM 文本快照供 LLM 挂载（§16）。
5. **缓存/性能层**：`baziCoreMemo` 8 桶 LRU 缓存"时空核心"（见 §7-Q3）。

bazi* 文件群与其它技法（紫微/六壬/奇门…）共享同一套四柱核心：`buildLocalNongliLite`（baziLunarLocal.js:1278）即为奇门择日扫描提供的轻量版；十二长生三档在缺省时钉死档 2 以免影响其它技法（baziLunarLocal.js:1208-1213）。

## 3. vendored/第三方依赖排查

`<WEB>/THIRD_PARTY_NOTICES.md` 是一份非常规范的第三方清单（含 License 与使用方式），要点：

| 库 | 用途 | License | 备注 |
| --- | --- | --- | --- |
| **lunar-javascript ^1.7.7** | 八字/农历/节气/EightChar 核心（package.json:54） | 上游为 6tail/lunar 项目，MIT（npm 依赖，未列入 notices） | **Tianze 可直接依赖原项目** |
| kintaiyi / kinjinkou / kinwangji / kinwuzhao / kinastro / kinqimen | 太乙/金口诀/皇极经世/五兆/神数系/奇门引擎，vendor/ 整包快照 | MIT（kentang2017） | 有 LICENSE 文件随包保留 |
| taixuanshifa / jingjue / shenyishu | 太玄/荆诀/神易数引擎 | **无明确 License**，notices 如实标注"未贴标签" | 诚实处理的范例 |
| flatlib（fork `flatlib-ctrad2`） | 西方古典占星 | MIT | 可用上游 |
| Swiss Ephemeris（pyswisseph） | 天文星历 | **AGPL-3.0** | 这是全项目被迫 AGPL 的原因之一 |
| d3-celestial 数据 | 天球星座线/边界（重整为自有 JSON） | BSD-3 | 数据可用 |
| pdf-lib + @pdf-lib/fontkit | 离线 PDF | MIT | |
| dom-align 1.12.4 | 弹层定位（本地打了 zoom 补丁并按 MIT 要求在 notices 记录修改） | MIT | |
| Noto Sans CJK 子集 | PDF 内嵌字体 | OFL-1.1 | |
| Stellarium | 仅交互设计灵感，**无代码/资产** | （GPL-2，未引入） | 灵感引用的合规写法范例 |
| Taogram/taobi（MPL-2.0）、redrockhorse/qimenpaipan、qfdk/qimen（MIT） | 奇门置闰算法**研究对照标尺，明确声明未拷贝源文件** | — | 借鉴/自写的边界声明范例 |

关键结论：**lunar-javascript 是 MIT，Tianze 可以直接 npm 依赖它获得农历/节气/八字四柱/EightChar 能力**（Horosa 的 baziLunarLocal 就是在它之上做派生与多口径）；kentang2017 系列引擎均为 MIT，如 Tianze 未来做太乙/奇门等也可直接依赖原仓库而非 vendor。

## 4. 历法与排盘（baziLunarLocal.js，1317 行）

- **基础库**：`lunar-javascript`（import 于 baziLunarLocal.js:1：Solar/LunarUtil/Lunar/LunarMonth/EightChar）。节气表、藏干 `ZHI_HIDE_GAN`、十神 `SHI_SHEN`、纳音 `NAYIN`、旬空 `getXunKong` 均取自 LunarUtil（baziLunarLocal.js:85-92、661-668）。
- **年域硬挡**：lunar-javascript 可靠域 AD1~9999，域外其节气静默错位（月柱错干支）→ 抛错改走后端星历（baziLunarLocal.js:1149-1153，`lunarDomainGuard.js`）。
- **真太阳时/平太阳时**：`applyApparentSolarTime`（baziLunarLocal.js:297-335）。timeAlg=0 真太阳时＝经度差（(lon−zone×15)×4 分钟）+ 均时差 EoT；timeAlg=3 平太阳时＝仅经度差；其余档不调整。EoT 用 NOAA/Meeus 儒略世纪级数（equationOfTime，baziLunarLocal.js:278-295），自称误差 <15s（1800-2200），替换旧的 ±1-2 分钟教科书简式——注释里记录了实测 89 秒分歧导致时辰界骑线的案例。lon 缺失回退 gpsLon，再缺则静默退化钟表口径并告警（baziLunarLocal.js:303-314）。
- **非东八区**：lunar-javascript 的节气表按 UTC+8 排。若出生时区≠+8，直接喂当地钟表会让年/月柱在交节附近判错。修法是 `absoluteTimeLunar`（baziLunarLocal.js:341-409）构造一个 hybrid Lunar：**年柱/月柱及上一节/下一节 getter 改读"出生绝对时刻对应的北京时间"农历，日柱/时柱/农历日仍取当地钟表**；东八区原样返回零回归。交节时刻再折回当地钟表坐标算起运（baziLunarLocal.js:386-398）。
- **晚子时双开关（子时四态）**：
  - `after23NewDay`：日柱是否 23 点进位次日（eightChar.setSect(1) vs (2)，baziLunarLocal.js:1160-1165）；
  - `lateZiHourUseNextDay`：时干用次日干（默认，=lunar.js Exact）还是当日干（自算 override 并重算纳音/旬空，baziLunarLocal.js:672-698、746-765）。UI 语义单选四态"子初换日 1/1、子初换日·时干今日 1/0、夜子时 0/1、子正换日 0/0"（CnTraditionInput.js:370-397）。
  - 紫微所需农历随日柱进位另行同步（ziweiLunarFor，baziLunarLocal.js:1058-1067）。
- **南半球**：`southMonth='chong'` 且南纬时月支取对冲之支、月干按年干五虎遁重起（flipMonthPillar，baziLunarLocal.js:353-374）；仅在快照标注，不静默。
- **命宫/身宫两派**：默认"通行版"（lunar.js）；可选"子平数法"对照表法——命宫数=26−(月序+时序)、身宫基=32−(月序+时序)，月序寅=1、时序子=1，干由五虎遁推（computeMingShenShuFa，baziLunarLocal.js:700-730），与后端 bazi.py 口径一致。
- **大运/流年/流月/流日/流时**：大运 10 步（yun.getDaYun(10)），流年带流月（按节 `getNextJie` 枚举）与值年星宿（28 宿）；起运"3 天折 1 岁"，整数档就近进位（formatStartLuck，baziLunarLocal.js:1040-1051）。性能：只有"当前公历年所在大运"eager 算流月/星宿，其余惰性 on-demand（baziLunarLocal.js:963-995）。
- **每柱附加物**：纳音+纳音长生（NAYIN_PHASE 表，土随水长生在申，baziLunarLocal.js:18-24）、日干十二长生（星运）、本柱干自坐（自坐）、旬空、八卦（每柱干支各配八卦合成 64 卦，并算互卦=爻234/345、旁通=错卦全爻反转，baziLunarLocal.js:475-501）。
- **缓存**：`baziCoreMemo` 以 12 个核心参数（date/time/zone/ad/lon/lat/gpsLon/gpsLat/timeAlg/after23NewDay/gender/southMonth）为键缓存 solar/lunar/eightChar/大运/紫微农历整包，8 桶 LRU（baziLunarLocal.js:1129-1199）。

## 5. 干支模型

- **藏干/十神**：直接用 lunar-javascript 的 `ZHI_HIDE_GAN`（本气→中气→余气序）与 `SHI_SHEN` 查表；十神以短名存储（比/劫/食/伤/才/财/杀/官/枭/印，baziLunarLocal.js:110-122）。
- **十二长生（三派可选，§重点）**：`changShengOf`（baziLunarLocal.js:33-62）实现三档并与 Java 权威 `wuxingphase.json` 做 360 格逐格对拍金标锁定（baziLunarLocal.js:33-39 注释）：
  - 档 0 火土同：不分阴阳，阴干随其阳干搭档同起同顺，土随火（戊己与丙丁同起寅顺）；
  - 档 1 水土同：土寄水从申起顺（offset=4，baziLunarLocal.js:41）；
  - 档 2 阳顺阴逆：= lunar.js 现行口径（缺参恒此档，字节零回归）。
  - 这是真实流派差异（火土同源 vs 水土同源 vs 阳顺阴逆），非作者杜撰；作者还记录了"曾为半截接线、golden 锚住错值"的修复史（baziLunarLocal.js:36-39）。
- **纳音**：60 甲子纳音表来自 lunar-javascript/自备 ZWConst；另有纳音五行在十二支的长生表（baziLunarLocal.js:18-31）供纳音古法盘显示"纳音长生"。
- **神煞（baziShenShaLocal.js，668 行）**：纯查表制，8 张对照表 + 补充函数：
  - 规模：SHENSHA_GROUP_TAGS 收录 **49 条**（注释"全表 49 条"，baziShenShaLocal.js:438），另有金舆/灾煞/天医/月德合/天德合补充表与整盘级三奇/阴差阳错/十恶大败/八专/九丑/四废（baziShenShaLocal.js:613-628、463 起），合计约 55 个名目。
  - 表结构：日干年干系（天乙/太极/文昌）、日干系（学堂/词馆/禄神/羊刃/红艳/流霞/暗禄/沐浴/八专）、年日支系（驿马/华盖/桃花/劫煞/亡神/将星）、日支系（破碎）、年支系（红鸾/孤辰/寡宿/丧门/吊客/病符…）、月干月支系。
  - 分组开关：吉神(ji)/凶煞(xiong) × 月令系(yue)/日柱系(ri) 是**两个正交维度**，过滤用"维度内取或、维度间取与"（baziShenShaLocal.js:434-460）。
  - 主位开关 godKeyPos（年/日/年日）与 Java GodsHelper 对齐；日干系 A 基恒按日干查不随主位（baziShenShaLocal.js:563-565 裁决注释）。
  - 口径纪律："仅收录原书给全对照表者，不臆造残表"（baziShenShaLocal.js:463，来源标注为《八字大全》§5）。
  - 流运神煞 `calcFlowShenSha`：以本命年/月/日干支为基查大运/流年/流月/流日柱（baziShenShaLocal.js:633 起）。

## 6. 关系（合冲刑害破/三合三会）

规则表全部显式定义在 baziLunarLocal.js:124-197：

- 天干五合 5 组（甲己合土…戊癸合火）；天干四冲 4 组（甲庚/乙辛/丙壬/丁癸——戊己土无冲，传统口径）。
- 地支六合 6 组（含合化五行名）；**三合 4 组，两支即成（"拱"，minUniqueCount=2，baziLunarLocal.js:614）**；三会 4 组（需 3 支全）；六冲 6；三刑含自刑 7（寅巳申/丑戌未/子卯+辰午酉亥自刑）；六害（穿）6；相破 6。
- 匹配范围**含胎元/命宫/身宫**（collectRelationSources，baziLunarLocal.js:566-581），即七柱皆参与关系判定。
- 展示：细盘关系层按柱画横向连线+纵向连线（BaZiFineChart.js:542-628），开关"刑冲破害"仅对细盘/简盘生效，旧 UI/古法盘置灰并说明（CnTraditionInput.js:652-657 "死选项接线"模式）。
- 成败救应里另用六冲对/三刑组/五合对做"月令逢冲逢刑动摇格基"与"忌神被合去"判定（baziGejuYongShen.js:262-264、309-332）。

## 7. 多流派设计【重中之重】

流派入口：左栏"断命流派"下拉 **8 档**——传统综合(zonghe,默认)/扶抑派(fuyi)/格局派(geju)/调候派(tiaohou)/病药派(bingyao)/通关派(tongguan)/盲派(mangpai)/纳音古法(nayin)（CnTraditionInput.js:629-643）。

**Q1：是分别真正计算，还是只改 UI 文本？——真正计算，且是彼此独立的纯函数；但各派"计算深度"有差异。**

代码证据：
- 扶抑派：`computeFuyiYongShen`（baziGejuYongShen.js:58-76）由日主旺衰 verdict 直接派生喜忌集（身强喜食伤/财/官杀忌印比；身弱反之；中和给流通/从格/调候提示）。
- 格局派：`computeGeju`（baziGejuYongShen.js:30-55，月令定格）+ `computeGejuYong`（:238-259，顺用/逆用相神表 MAP：官格喜财印忌伤、杀格喜食印忌财、财格喜食官忌比劫、印格喜官忌财坏印、食格喜财忌枭、伤格喜印财忌官…）+ `computeChengBai`（:277-348，成败救应四态）。
- 调候派：`computeTiaoHou`（baziTiaoHou.js:29-43）查 120 组表；入对照表时**忌恒空并注明"调候以寒暖燥湿论急缓，不单列忌神"**（baziGejuYongShen.js:362-363）——不臆造。
- 病药派：`computeBingYao`（:188-209）"忌神最旺者为病，取克病之神为药"，病须 ≥15% 才立。
- 通关派：`computeTongGuan`（:212-234）两强相争取生化中介，忌"克通关神者"。
- 盲派：`computeMangPai`（baziMangPai.js:28-93）独立计算宾主/体用/做功/废神。
- 纳音古法：展示层计算纳音五行生克链+纳音长生（BaZiAppInfoPanel.js:13-26、352-397；BaZiAncientChart.js 同口径），**不以日干为我、以年柱纳音为命主之纲、胎元列第五柱**。
- 五派同时输出进 `schools` 数组做"多派对照"（baziGejuYongShen.js:358-365），注释明言"同盘各派可取不同用神，常驻对照、勿冒充唯一答案"。
- 深度差异（诚实边界）：盲派仅"结构·参考"（无换象/深象法）；纳音古法无古法断诀文本；作者全部标注 best-effort。

**Q2：哪些计算全流派统一？哪些独有？**
- 统一（事实层）：四柱干支、藏干、十神、纳音、星运/自坐、旬空、神煞、合冲刑害破会、大运流年——全部来自同一个 `fourColumns`，任何流派不改写它。
- 共享部分派：五行力量/旺衰（`wuxingStat`）被扶抑、病药、通关、变格判定共同消费；月令定格被格局派与杂格消费；调候只依赖四柱本身。
- 独有：盲派完全**弃旺衰废用忌**（computeMangPai 不接收 wuxingStat，baziMangPai.js:28）；纳音古法弃"日干为我"改用年柱纳音纲；分野加权(cangVersion='fenye')只改五行权重的月柱算法，不改变其它派。

**Q3：如何做到"基础事实不变 + 分析视角变化"？**
1. **纯函数派生层**：`computeWuxingStrength/computeGejuYongShen/computeMangPai/computeFenYe` 都以同一 `fourColumns` 为输入，输出是**附加字段**（wuxingStat/gejuYongShen/mangpai/fenYe），头注释反复强调"纯展示派生，不改四柱/大运/神煞""零回归"（baziWuxing.js:3、22-23、168；baziGejuYongShen.js:8）。
2. **核心缓存与派生开关分离**：baziCoreMemo 只按 12 个时空核心键缓存；minggongMethod/phaseType/godKeyPos/fenyeVersion/cangVersion/lateZiHourUseNextDay 等分析视角开关全部在核心之外——"用户在选项轴来回拨时核心层零重算"（baziLunarLocal.js:1129-1131）。这把"事实 vs 视角"直接做进了缓存键设计。
3. **UI 侧视角切换只动渲染**：school 只决定 (a) 右栏专属 section（盲派/纳音才有，BaZiAppInfoPanel.js:406-407）；(b) 多派对照表中哪一行置顶高亮为"主用"（:241-252）；(c) 盘面喜忌徽标层 buildSchoolMark（BaZiFineChart.js:353-431）——schools 数据本体与快照顺序不动（BaZiAppInfoPanel.js:241 注释）。综合/纳音"无单一喜忌口径"则不上徽标并置灰开关（CnTraditionInput.js:664-677）。
4. **每个派生输出自带 school/note 元数据**：如 `{school:'扶抑派', verdict, xi, ji, note}`，note 写明依据；AI 快照与 UI 消费同一对象。
5. **零回归纪律**：所有新派生以"纯新增字段/byte-perfect 锚"落地，golden 测试锁旧口径（见 §15）。

**Q4：Tianze 应该如何吸收？**
- 把"四柱事实对象"做成不可变纯数据，每流派是一个 `facts -> interpretation` 的纯解释器；解释结果带 `{school, verdict, xi, ji, note}` 且**多派常驻对照**而非切换替换。
- 缓存键=事实参数（时空/性别/口径基础项），分析视角参数绝不进核心缓存键——切流派免费。
- 每个流派输出必须附依据 note；不确定处给"待复核"态而非硬结论（成败救应/杂格的 真假/待复核 三态是极好的模式）。
- 调候派"忌恒空"这种"不臆造"的克制值得照抄：没有传统依据的字段留空并注明，而不是编一个。
- 权重/阈值集中为可配置 DEFAULT_* 常量并公开公式（面板+AI 快照都印公式文本）。

## 8. 旺衰体系【重中之重】—— baziWuxing.js 深读（176 行）

**总原则（作者自白，baziWuxing.js:1-3）**："通行示例方案，权重可配置、公式公开；各家权重/阈值无统一标准（这是不同软件『自动喜用神』打架的根因），故默认给一组透明的通行权重，opts.weights 可整组覆盖，面板与 AI 均附公式。"

### 五行权重表（DEFAULT_WEIGHTS，baziWuxing.js:12-18）

| 项 | 值 | 位置 | 定性 |
| --- | --- | --- | --- |
| 天干透出 | +100 | baziWuxing.js:13 | PROJECT_HEURISTIC（通行示例，无古籍依据） |
| 地支本气藏干 | +100 | :14 | PROJECT_HEURISTIC |
| 地支中气藏干 | +60 | :15 | PROJECT_HEURISTIC |
| 地支余气藏干 | +30 | :16 | PROJECT_HEURISTIC |
| 月令乘数 | ×1.5（整月匀加） | :17 | PROJECT_HEURISTIC（"通行版"） |

- 分野加权档（cangVersion='fenye'，baziWuxing.js:121-125）：月柱藏干不再整月×1.5，仅"当令司令"之干吃月乘，其余月支藏干×1；司令干来自 baziFenYe.ruler.gan；节气边缘算不出司令时退回通行版防塌 0。
- 日主强弱（baziWuxing.js:140-160）：同党=印(生我)+比劫(同我) 分数，ratio=same/total；**ratio>0.55 身强、<0.45 身弱、其间中和**（strongCut/weakCut 可配，:148-152）→ PROJECT_HEURISTIC 阈值。异党=食伤+财+官杀。

### 旺相休囚死（baziWuxing.js:31-39）

- 季节表 SEASON_STATE 按"当令旺·我生相·生我休·克我囚·我克死"（真实传统规则，标 §1.4）；月支→季节 BRANCH_SEASON（:25-30，三会口径）；**土日主逢四库月特判"四季土旺"**（:56，土旺四季通行口径）。
- 打分 STATE_SCORE：旺 40、相 30、休 −10、囚 −20、死 −30（:39）——PROJECT_HEURISTIC。注意：此分**只用于"得令"三维展示，不参与 scores/percent 主计算**（:22-23 明示零回归设计）。

### 得令/得地/得势（三维分列，computeDimensions，baziWuxing.js:50-94）

- **得令**：月支定季→查旺相休囚死→got = 旺或相；输出状态+分。
- **得地（通根分级）**：逐支找藏干中含日主五行者，按序定级（:66-78）：
  - 禄刃根（十干禄支 LU_ZHI :41 / 阳刃支 REN_ZHI :42，仅五阳干）→ **30 分**；
  - 本气库根（辰戌丑未）→ **25**；本气根 → **20**；长生根（CHANG_SHENG_ZHI :43）→ **15**；中气根 → **10**；余气根 → **6**（ROOT_SCORE :46）——全部 PROJECT_HEURISTIC，自称参考 §9.1.1；
  - **月支根分数 ×2**（:75）。
- **得势**：年/月/时透干中的印枭/比劫计数 ×20 分（:88）——PROJECT_HEURISTIC。
- 三维只做展示派生，不回写主评分（"纯新增，零回归"，:22-23、49）。

注：禄刃/长生支表本身是传统数据；分值是作者工程化。

## 9. 格局与用神（baziGejuYongShen.js，380 行）

- **取格（正格）**：月令定格优先级（baziGejuYongShen.js:29-55）——月令本气为比→建禄格、为劫→阳刃格（不以比劫为格，不再看透干）；否则本气透干→本气十神格；本气不透而中/余气透→透出者；皆不透→本气暗藏。八正格名表 GE_NAME（:18-21）。（学理标 §9.2.1，属传统机械规则。）
- **成格/破格/救应（computeChengBai，:277-348）**：
  - 破格判据 GE_JI 表（:265-273）：官格忌伤透（伤官见官）、财才忌比劫、印忌财、食忌枭、伤忌官、枭忌食；杀格另判"财党生杀无食制"；阳刃"刃旺无制"；建禄"比劫成群"；月令逢对冲/三刑 → 破格（:309-315）。
  - 救应：忌神干被五合合去、或被透干克制 → "败中复成"（:324-332）。
  - 四态输出：成格/破格/败中复成/待复核，附 reason 与"会合牵制之细致变化请人工复核"note（:334-347）。
- **用神产出形态：枚举+字符串喜忌，非权重**。每派输出 `{school, xi[], ji[], note}` 五行中文短名；调候派输出天干序列（主用+辅用）。
- **变格候选（computeBianGe，:91-179，量化近似全部 PROJECT_HEURISTIC）**：专旺/从强（同党 ≥85% 且有本气根，:103）；从弱（同党 ≤12% 且无本气根，:109）下再分从势（食伤财官杀三势均停：最小 ≥15% 且极差 ≤12%，:115）与从儿/从财/从杀（取占比最大者，:123-124）；两神成象（第二行 ≥35% 且前两行 ≥85% 且第三行 ≤8%，:138；相生两象取流通、相克两象取通关）；化气（日干与月干/时干五合 + 化神是否得令判真假化，:162-177）。全部只作"疑似候选+若成立用某忌某+请复核"提示，不覆盖扶抑用神。

## 10. 调候（baziTiaoHou.js，45 行）

- 数据：**十天干×十二月支 = 120 组完整速查表**（TIAOHOU，baziTiaoHou.js:7-18），每组 [主用, 辅用…] 天干序列。
- **诚实标注**：头注释自认"此为流通甚广的『速查版』；原典对每格有多种有无配置（丁庚两透/有庚无丁等分级），同干月在不同条件下用神不同。本表仅作默认初值并标版本"（:1-5）。即**不是《穷通宝鉴》原文的分组条件版**，是简化速查；version 字段就写"速查版"（:37）。
- 来源标注：《八字大全》§6.3（现代汇编书），未直标《穷通宝鉴》原典条目；另有月令寒暖燥湿 CLIMATE 表（:21-26，如亥子丑=寒、午未=燥热）。
- 消费方式：与扶抑/格局派并列进多派对照；忌恒空（见 §7）。

## 11. 杂格（baziZaGe.js，193 行）

规约：正格能取者优先，正格不成方论杂格；逢填实/刑冲破多破格（baziZaGe.js:1-6）。

- 第一组（结构匹配）：天元一气（四干同）、地支一气（四支同）、两干不杂（四干仅两种）、五行俱足（五行齐）、日德（甲寅/丙辰/戊辰/庚辰/壬戌）、日贵（丁酉/丁亥/癸卯/癸巳，日坐天乙）、福德秀气（乙巳/乙酉/乙丑）、金神（时柱癸酉/己巳/乙丑）（baziZaGe.js:11-14、157-187）。
- 第二组（虚邀暗冲 13 格，判据全部机械化，"多X"=X 支 ≥2 含日支）：飞天禄马（庚子/壬子 ≥2 子冲午官；辛亥/癸亥 ≥2 亥冲巳官）、井栏叉（庚子/庚申/庚辰+申子辰全）、壬骑龙背、六乙鼠贵（乙日丙子时）、六阴朝阳（辛日戊子时）、子遥巳（甲子日甲子时）、丑遥巳、合禄（戊/癸日庚申时）、拱禄、拱贵（日时支隔位虚拱禄/天乙位，:96-114）、刑合（癸日甲寅时）、趋乾（甲日 ≥2 亥）、趋艮（壬日 ≥2 寅）；另收月库杂气财官格（辰戌丑未月中气/余气见财官印，透出或库逢冲为真，:130-144）。
- 每格输出 quality 三态：真（判据成立无破）/假（命中破格条件，broken 列明）/待复核（库气未开类），破格条件逐格枚举（填实/冲/合绊/官杀明现）（baziZaGe.js:35-37 及各格）。

## 12. 盲派（baziMangPai.js，95 行）

- 做了什么：**宾主/体用/做功/废神的结构标注**。主=日柱（自己），宾=年/月/时（他人外物）；体=日主/比劫/印枭/食（及禄），用=财/才/官/杀/伤；做功=主位之"体"去取宾位之"用"（生用/克取，逐柱逐干支枚举，baziMangPai.js:63-81）；废神=出现的体/用十神中未参与做功者（:84）。
- 覆盖程度：仅结构层。头注释自认 best-effort、全标"结构·参考"；"刑冲合害为『动』之开关（此处仅结构标注，动的细判归关系层）"（:6）；无做功效率/宾主互换/象法深判/换日主等高阶内容。UI 上明确打"象法·参考"标签（BaZiAppInfoPanel.js:297）。

## 13. 分野（baziFenYe.js，72 行）

- **不是地理分野**！是"月律分野（人元司令）"：月令藏干非整月匀力，按**节后第几天**轮值司令（baziFenYe.js:1-4）。这回答了"节后第几天出干当令"的传统问题。
- 两版并列（中性命名）：
  - 通行版 FENYE_COMMON（:7-20）：每月恰 30 日，序=余气→中气→本气。如寅=戊7/丙7/甲16；末段 catch-all 承接余日至下节。
  - 法诀版 FENYE_FAJUE（:21-34）：古法诀差异点——寅余气作己（己7/丙5/甲18）、卯中气见癸（甲9/癸3/乙18）、申分四段（己7/戊3/壬3/庚17）、酉见丁（庚7/丁3/辛20）、子见辛（壬9/辛3/癸18）等。
- 用法一（独立展示）：右栏"月令司令"卡显示节后天数+当令司令干+轮值表（BaZiAppInfoPanel.js:325-350）。
- 用法二（接入旺衰）：cangVersion='fenye' 时司令干独得月令×1.5（§8）。fenyeVersion（common/fajue）是独立开关（CnTraditionInput.js:594-598）。
- 传统依据：司令分野是真实传统概念（子平真诠等论人元司令），两版日数对照标注出自《八字大全》§月律分野；具体日数各坊本有出入。

## 14. UI 表达

- **BaZi.js（1355 行，页面容器）**：三栏网格——左栏输入（MemoCnTraditionInput）、中栏盘+行运（PaiBaZi+BaZiLuckFlowPanel）、右栏信息（BaZiAppInfoPanel）（BaZi.js:1300-1348）。双后端：本地引擎优先，域外/BC 年合入 Java /bazi/direct 结果（memoChartBazi，:1275 注释）。右栏不内嵌 Tab 而是纵向卡片流；"行运选择"（flowSelection）只喂神煞卡——按输入依赖切成 3 个 sCU 子块防止整树重渲（BaZiAppInfoPanel.js:72-86）。另有旧星阙 UI（uiMode=legacy）兼容层。
- **PaiBaZi（盘样式单源）**：三档盘样式按钮 **简盘/细盘/古法盘**（PaiBaZi.js:42-43、179-181），样式持久化 localStorage。
- **BaZiFineChart.js（细盘 710 行）**：行式四柱表：流派标记条（school bar：派名+身强身弱判语+喜/忌五行）→ 表头 → 主星 → 天干（横连合冲覆盖线）→ 地支（横连+关系层 刑冲合害会）→ 副星 → 藏干 → 纳音 → 星运（日干十二长生）→ 自坐 → 空亡 → 神煞（BaZiFineChart.js:677-704）。流派标记层：school→schools 对应行喜忌集合，逐格/逐字命中上 is-yong/is-ji 徽标；**调候派以天干论（支不标）**；盲派上宾主标记（:353-431）。
- **BaZiAncientChart.js（古法盘 129 行）**：纳音古法（禄命派）专属视图：五列=年月日时+**胎元第五柱**，年柱标"命主·纲"，纳音生克链箭头（生→/克→/被生←），纳音长生行，古法神煞（BaZiAncientChart.js:1-60）。学理标《八字大全》§6.8。
- **BaZiAppInfoPanel.js（右栏 518 行）**：卡片序＝起盘信息（阳历/阴历/生肖/直接时间/真太阳时/计算基准/节气/起运/交运）→ 四柱信息 → 藏干 → 五行力量（色条+百分比+日主判语+三维分列 pill+**权重公式原文上屏**，:204-206）→ 格局·用神（格局行+成败四态徽标+**多派对照表**+疑似变格+杂格）→ 盲派结构（仅 school=mangpai）→ 纳音古法（仅 school=nayin）→ 月令司令 → 神煞（所选大运/流年/流月/流日）→ 三元宫位（胎元/命宫/身宫/串宫）。
- **CnTraditionInput.js（输入 727 行）**：输入不直接做公农历切换——时间用 SpaceTimePanel（弹层编辑：PlusMinusTime 支持 14 位数字直接输入，CITATION 摘要亦提"fourteen-digit direct time entry"）；八字特有选项全部落在此栏：性别（未知按男排）、时间算法 0 真太阳/1 直接/2 春分定卯/3 平太阳（BaZiAppInfoPanel.js:103 名称表）、长生三派 phaseType、命宫起法两派、分野两版、藏干加权两版、生肖归属（立春/正月初一，纯展示）、断命流派 8 档、流派标记开关、神煞分组、年龄虚岁/周岁、界面新/旧。**"死选项接线"纪律**：某开关在当前盘式/流派下无消费面时置灰+title 说明而不是装作生效（CnTraditionInput.js:476-478、652-657）。

## 15. 测试体系

- 规模惊人：`astrostudyui/src` 下 **935 个 *.test.js**（Jest），几乎每个算法文件都有同名 golden 测试；Java 侧另有 BaZiDirectBcYearTest/BaZiEraBoundaryTest/BaZiLichunWindowTest/BaZiSolarDayPillarTest/BaZiSouthMonthTest 等（astrostudycn/src/test）。
- 形式特征：
  1. **Golden 值锁定**：baziWuxing.test.js 用手算独立核算锁默认权重派生值（如"2026-06-22 18:00 → 火45%·身强·同党65%"，baziWuxing.test.js:33-38）。
  2. **跨引擎对拍**：十二长生三档与 Java wuxingphase.json **360 格逐格对拍金标**（baziLunarLocal.js:33-39）；奇门扫描 lite 版与全量版一致性由 parity 网格钉死（baziLunarLocal.js:1275-1277）；"约一千个 cell-by-cell parity 测试"锁十二长生/六亲表（CITATION.cff:55-58）。
  3. **零回归锚**："纯新增字段不改旧值"用字节级锚测试（baziZhangShengTruth、golden 是法律错了重生成 纪律，baziLunarLocal.js:38-39）。
  4. **选项矩阵审计**：baziOptionMatrixAudit、baziNeedRefetchCompleteness——枚举每个开关组合验证接线（防"死选项"回归）。
  5. **AI round-trip**：baziMountSnapshot.test.js 验证多运限选择改变 AI 快照输出且默认逐字不变。
  6. 压测：baziOverhaulStress、baziStress、baziZeriStress。

## 16. AI 接入方式

- **单源快照挂载**：`buildBaziSnapshotForParams`（BaZi.js:642 起）把与 UI 完全同源的 bazi 对象渲染成 GFM 文本：[四柱与三元]（9 列表：柱/干支/藏干/十神/纳音/纳音长生/星运/自坐/空亡）、[神煞]、[五行力量]（含权重公式与三维分列）、[格局·用神]（当前主用流派+**多派用神对照表**+变格+杂格）、[盲派结构]、[月令司令（分野）]、[干支合冲]、[大运]（GFM 表）、[流年行运概略]、[多运限·指定时段]（用户勾选流年×流月笛卡尔等，BaZi.js:408-560；快照存 localStorage `horosa.ai.snapshot.module.v1.*`，moduleAiSnapshot.js:9）。
- **AI 分析页**（components/aianalysis/AIAnalysisMain.js，6625 行）+ services/aianalysis.js：多 LLM 供应商、流式、best-of-N 对比、每任务模型路由与四方言结构化输出；v3.11.2 升级为 **Agent**：可行动层（默认关）——创建盘/案例、无头排盘、改盘口径与显示偏好，只读或 append-only，三级审批、行动台账一键 undo、前后 diff 预览、目标/定时/自动化任务（CITATION.cff:14-27）。另有本地 MCP server、外部 MCP 只读准入、五引擎 web 搜索、API key 加密。
- 要点：AI 不自算命理，**吃的是同一份引擎输出快照**（含"请复核"提示与权重公式），保证 UI 与 LLM 看到的事实一致。

## 17. License 与可复用性评估

- 主体 **AGPL-3.0-only**（受 Swiss Ephemeris AGPL 传染 + 作者自愿）：Tianze **不可复制/改编其源码**（含那 9 个 bazi*.js 与 BaZi*.js）到非 AGPL 项目；即使 Tianze 采用 AGPL，直接拷码也会引入"结构雷同"，建议一律只学思想+自写。
- 可直接依赖的**上游库**（绕开 Horosa 代码本身）：lunar-javascript（MIT）、pdf-lib（MIT）、flatlib（MIT）、kentang2017 系列（MIT，若做太乙/奇门等）、d3-celestial 数据（BSD-3）。taixuanshifa/jingjue/shenyishu 无明确 License，慎用。
- 事实性数据表（藏干表、神煞对照、调候 120 组、分野日数、合冲刑害清单）本身是传统术数公有内容，可自行整理录入，但**照抄其文件中的表达/注释/组织方式风险高**——Tianze 应从古籍原文重新校勘。
- 该仓的 THIRD_PARTY_NOTICES.md 本身是"如何合法 vendor + 声明"的优秀模板（含"参考未拷贝"声明）。

## 18. Tianze 应该借鉴什么 / 不应该借鉴什么

**应该借鉴（思想/模式）**：
1. 事实层/解释层彻底分离 + 纯函数派生（§7-Q3），多派=同事实的多解释器，schools 常驻对照。
2. 缓存键只含事实参数，分析视角开关零成本切换（baziCoreMemo 设计）。
3. 诚实元数据：每派输出带 school/note/"请复核"；无依据字段留空（调候忌恒空）；PROJECT_HEURISTIC 自白（"各家权重打架的根因"）。
4. 权重集中常量、可配置、公式上屏（UI+AI 都印公式）。
5. golden/parity 测试体系：数值锁、跨引擎对拍、选项矩阵审计、零回归字节锚。
6. "死选项置灰+说明"、变格/杂格的真/假/待复核三态、AI 快照与 UI 单源。
7. 非东八区绝对时刻农历、真太阳时 NOAA/Meeus 级 EoT、晚子时四态、南半球对冲——这些边界处理的**问题定义**值得抄（实现自写）。
8. THIRD_PARTY_NOTICES 的合规姿势。

**不应该借鉴**：
1. 任何源码/整段实现（AGPL）。
2. 其权重具体数值当作"标准"——作者本人都声明无统一标准（Tianze 应自定并同样标注 heuristic）。
3. 前端单文件巨型类（BaZi.js 1355 行、AIAnalysisMain 6625 行）的组件组织方式；React 17 + class 组件 + sCU 手工 memo 的复杂度不值得模仿，Tianze 可用现代框架但吸收其"按输入依赖切分重渲"的思路。
4. 速查版调候表当作终稿（应按《穷通宝鉴》原文带条件分级重录）。

## 19. 未解疑问

1. 《八字大全》具体是哪本书？各文件仅标 §9.1.1/§9.2.1/§6.3/§6.4/§6.8/§5 等节号，仓内未见书名全称与作者——待外部考证（可能是作者自汇编讲义）。
2. Java 端 `bazi.properties`/`dlbazifeature.properties`、`BaZiPredictHelper`/`bazipred.json`、`BaziPattern.java`（commtools/BaziPattern.js）疑似另有一套"格局预测"体系，本次未深挖（属 Java 侧，与前端多派并行的第四实现？）。
3. `baziCalibreScope.js`（校准范围/patch 拆分）与 `splitBaziCalibrePatch` 的完整语义未读（BaZi.js:1 引用）。
4. "串宫"（four.ming12）十二串宫的星/神煞来源只在后端盘带，前端本地路径为空壳（BaZi.js:427-434）——其数据链未追。
5. 调候速查表 120 组与《穷通宝鉴》通行本（如"甲用酉月"类）逐格吻合度未逐格校勘。
6. 时间算法 timeAlg=2"春分定卯时"的确切算法未在 baziLunarLocal 中找到（疑似在 PlusMinusTime/后端）。
7. 三合"拱"允许两支（无中神）是否含"虚拱待填"的进一步判定，未见后续逻辑（关系层只标拱）。
