# lunar-python 研究笔记

> 研究对象：`C:\Project\tianze\research\upstream\lunar-python`（GitHub: 6tail/lunar-python），只读。
> 本地克隆为浅克隆（`git rev-list --count HEAD` = 1），无法查看完整提交历史。
> 所有行号均指本地克隆 HEAD（`448f397`）。文中"实测"指在本地用 `python -c` 实际运行验证过。
> 注：Phase 0 纪律——本文只研究，不实现 Tianze 业务代码。

## 1. 仓库概览（语言/规模/目录结构/最后提交/LICENSE/包版本）

- **语言**：Python 3（`requires-python = ">=3.8"`，pyproject.toml:32），**零第三方依赖**（README.md 自述，且 pyproject 无 dependencies，属实）。
- **规模**：`lunar_python/` 包共 **7096 行 Python**；核心单文件 `Lunar.py` 1418 行、`util/LunarUtil.py` 940 行、`util/ShouXingUtil.py` 667 行。
- **目录结构**：
  - `lunar_python/`：核心类（Solar/Lunar/LunarYear/LunarMonth/LunarTime/EightChar/JieQi/NineStar/ShuJiu/Fu/Foto/Tao/Holiday/SolarWeek 等 21 个文件）
  - `lunar_python/eightchar/`：大运体系（Yun/DaYun/LiuNian/LiuYue/XiaoYun，5 个文件）
  - `lunar_python/util/`：LunarUtil（静态表+老黄历编码数据）、ShouXingUtil（天文算法）、SolarUtil、HolidayUtil、FotoUtil、TaoUtil
  - `test/`：22 个测试文件；`demo.py`：示例脚本；`.github/workflows/test.yml`：CI
- **最后提交**：`448f397`，2026-01-24 11:07 +0800，"Merge pull request #29 from sjhddh/fix/validation-and-packaging"。
- **LICENSE**：MIT，版权行 `Copyright (c) 2020 6tail`（LICENSE:1-3）。
- **包版本**：`__version__ = '1.4.8'`（lunar_python/__init__.py:3）；CHANGELOG.md 最后一条 `[1.4.8] - 2025-11-05 新增：2026年法定假日`。
- **包名**：PyPI 名 `lunar_python`（pyproject.toml:7）；官网文档 https://6tail.cn/calendar/api.html（pyproject.toml:41）。

## 2. 架构与模块划分

| 模块 | 行数 | 职责（源码核实） |
|---|---|---|
| `Solar.py` | 477 | 公历日期时间；儒略日互转（getJulianDay:245-267，Fliegel-Van Flandern 式儒略日公式）；`fromBaZi()`（Solar.py:102-154）八字反查全部公历时刻 |
| `Lunar.py` | 1418 | 农历核心：三套干支口径（正月初一 / 立春当天 / 立春交接时刻）、日柱 Exact/Exact2 双口径、节气表、八字入口、老黄历门面（宜忌/神煞/冲煞/胎神/方位）。共 228 个方法 |
| `LunarYear.py` | 333 | 农历年：调 ShouXingUtil 算 26 个节气与 16 个合朔、排月、定闰月（LunarYear.py:53-137）；闰月特例表 `__LEAP_11/__LEAP_12`（:17-21） |
| `LunarMonth.py` | 173 | 农历月；**闰月用负数表示**（isLeap: `month < 0`，LunarMonth.py:79-80） |
| `LunarTime.py` | 171 | 时辰对象（干支/旬空/冲煞/时宜忌/时九星） |
| `EightChar.py` | 493 | 八字门面：四柱+各柱藏干/五行/纳音/十神/十二长生/旬空；胎元/胎息/命宫/身宫；流派 setSect；getYun |
| `eightchar/Yun.py` | 124 | 起运：顺逆判定 + 两种起运流派计算（:19-57） |
| `eightchar/DaYun.py` | 101 | 大运：index 0 为出生→起运前，其后每运 10 年 |
| `eightchar/LiuNian.py` | 61 | 流年（干支按立春口径年柱递推，LiuNian.py:27-36） |
| `eightchar/LiuYue.py` | 65 | 流月 |
| `eightchar/XiaoYun.py` | 55 | 小运（以**时柱**干支为基顺/逆递推，XiaoYun.py:26-40） |
| `JieQi.py` | 73 | 节气对象，isJie/isQi 区分"节"与"气"（:23-39） |
| `NineStar.py` | 115 | 紫白九星（年/月/日/时飞星） |
| `ShuJiu.py` / `Fu.py` | 32/33 | 数九、三伏 |
| `Foto.py`/`Tao.py` + util | 143/130 | 佛历、道历 |
| `Holiday.py` + `util/HolidayUtil.py` | 52/179 | 中国法定节假日+调休，**数据硬编码覆盖 2001-2026**（实测 2027-01-01 返回 None） |
| `util/LunarUtil.py` | 940 | 全部静态表：干支/藏干/十神/纳音/旬空/建除/十二天神/彭祖百忌/28宿/神煞/宜忌（宜忌为 hex 编码大字符串） |
| `util/ShouXingUtil.py` | 667 | **寿星天文历算法**：节气与朔的天文计算 |
| `util/SolarUtil.py` | 273 | 公历工具（各月天数/星期/节日名） |

## 3. 数据结构（方法面）

- **Solar**：`fromYmdHms` / `fromJulianDay` / `getJulianDay` / `next(n, onlyWorkday)` / `nextYear/Month/Hour` / `getLunar` / `fromBaZi(年柱,月柱,日柱,时柱,sect=2,base_year=1900)` / `getFestivals`。
- **Lunar**（关键口径分层）：
  - 年柱三种：`getYearInGanZhi`（正月初一起）、`getYearInGanZhiByLiChun`（立春当天起）、`getYearInGanZhiExact`（立春交接时刻起）（Lunar.py:54-110）。
  - 日柱三种：`getDayInGanZhi`、`getDayInGanZhiExact`（晚子时算明天）、`getDayInGanZhiExact2`（晚子时算当天）（Lunar.py:146-172, 294-301）。
  - `getJieQiTable()`：30 项 `JIE_QI_IN_USE`（大雪→惊蛰跨年，Lunar.py:11, 47-52）；`getPrevJie/getNextJie(whole_day)`（:969-980，只含"节"不含"气"）。
  - `getTimes()`：返回 **13 个时辰**——00:00（早子）+ 1,3,…,23 点（23:00 为晚子）（Lunar.py:1394-1402）。
  - 老黄历：getDayYi/Ji、getDayJiShen/XiongSha、getDayChong*、getSha、getPosition*（喜/福/财/贵/太岁，带 sect）。
- **EightChar**：每柱 `get{Year,Month,Day,Time}()` + `get*HideGan` / `get*WuXing` / `get*NaYin` / `get*ShiShenGan` / `get*ShiShenZhi` / `get*DiShi` / `get*Xun(Kong)`；`getTaiYuan`（胎元）/`getTaiXi`（胎息）/`getMingGong`（命宫）/`getShenGong`（身宫）及其纳音；`setSect(sect)`；`getYun(gender, sect=1)`。
- **Yun**：`getStartYear/Month/Day/Hour`、`isForward()`、`getStartSolar()`（起运阳历时刻）、`getDaYun(n=10)`。
- **DaYun**：`getStartYear/EndYear`、`getStartAge/EndAge`、`getGanZhi()`（index 0 返回空串）、`getLiuNian(n=10)`、`getXiaoYun(n=10)`。
- **LiuNian**：`getYear/getAge/getGanZhi/getLiuYue()`（12 个流月）。

## 4. 历法与排盘

**节气是实时天文计算，不是查表**（仅历史时段回退到参数表+修正位）：

- 核心在 `util/ShouXingUtil.py`（"寿星天文历"算法移植）：
  - 太阳视黄经 `saLon(t) = eLon(t,n) + nutationLon2(t) + gxcSunLon(t) + PI`（ShouXingUtil.py:472-473）——地球运动用 **VSOP87 截断级数表 `__XL0`**（:63 起，数千项三角级数）+ 黄经章动（`__NUT_B` 表 :16-27）+ 光行差修正。
  - 求节气时刻：`saLonT(w)` 牛顿迭代解 `视黄经 = w`（:506-513）；`qiHigh`（:550-556）为高精度版。
  - **ΔT（TD-UT1）用插值表 `__DT_AT`**（:30-62，覆盖 -4000 至 2050 年，2018 后参数多次更新见 CHANGELOG 1.4.1/1.4.5），2050 年后用 `(y-1820)²×31` 二次式外推（`dtExt` :476-478）。
  - 分段策略 `calcQi(jd)`（:618-651）：① 早于前 221 年或晚于 JD 2436935（约 1959 年末）→ 高精度天文计算（:630-632，注释"1999.3.21 太阳视黄经为 0 春分 定气计算"）；② 前 221—1645 年 → **`__QI_KB` 古历参数表**（:325-362，逐朝代历法记录儒略日锚点+回归年长度，如"太初历 平气平朔 365.25000"）；③ 1645—1960 年 → 低精度式 + **`__QB` 修正位串（7567 个节气修正，自 1645-09-23 起）**（:363-364, 642-651）。农历朔日 `calcShuo`（:584-615）同构：`__SHUO_KB`（自前 722 年）+ `__SB` 16598 朔日修正位（自 619-01-21 起）。
- **精度声明**：源码无明确精度注释；测试期望精确到**秒**（test/JieQiTest.py:6-13，如"2012-09-07 13:29:01 白露"、"2050-12-07 06:41:54 大雪"）。README/CHANGELOG 亦无量化精度声明（矛盾点：这类库通常宣传分钟级，仓库内无可验证依据）。
- **排月**（LunarYear.py:53-137）：以冬至锚定（`w = floor((jd-355+183)/365.2422)*365.2422+355`，:67）→ 连续 26 个节气 `jq`（:71-72）→ 30 项 `JIE_QI_IN_USE` 精确儒略日（:75-82）→ 首朔 `calcShuo` → 16 个合朔递推（:85-90）→ 15 个月段按**无中气置闰**（:103-107），命中 `__LEAP_11/__LEAP_12` 特例表（:17-21，如 **2033 闰 11 月**，实测 `LunarYear.fromYear(2033).getLeapMonth()` = 11 正确）则强制置闰。
- **支持年份范围**：代码无硬性边界；**实测公元 0001 与 9999 年均能出农历与节气**（如 0001 年立春 0001-02-05、9999-01-31）。仓库内无官方范围声明；ΔT 表只到 2050，更远年份靠外推，极远年份精度未验证。
- **四柱计算**（均按 Exact 口径，即节气交接时刻）：
  - 年柱：以立春交接时刻比较（Lunar.py:78-101）。
  - 月柱：以节交接时刻定位月序，月干用五虎遁 `g_offset = ((年干序%5+1)*2)%10`（Lunar.py:112-144）。
  - 日柱：按当天正午儒略日 `int(noon.getJulianDay()) - 11` 模 60 定甲子（Lunar.py:146-153），再做晚子时 Exact/Exact2 修正（:158-172）。
  - 时柱：地支按 23:00-00:59 属子、单数小时起（LunarUtil.getTimeZhiIndex:674-690）；时干五鼠遁 `(日干Exact序%5*2 + 时支序)%10`（Lunar.py:174-177）。

## 5. 干支模型

- **干支表**：`GAN`(LunarUtil.py:16)、`ZHI`(:35)、`JIA_ZI` 六十甲子(:36)；甲子序查 `getJiaZiIndex`(:714-723)。
- **藏干表** `ZHI_HIDE_GAN`（LunarUtil.py:656-669）：子[癸]；丑[己,癸,辛]；寅[甲,丙,戊]；卯[乙]；辰[戊,乙,癸]；巳[丙,庚,戊]；午[丁,己]；未[己,丁,乙]；申[庚,壬,戊]；酉[辛]；戌[戊,辛,丁]；亥[壬,甲]。为通行"本气/中气/余气"表，有传统依据（地支藏干通例，与《三命通会》等主流一致）。
- **十神** `SHI_SHEN`（LunarUtil.py:553-654）：**100 条硬编码字典**（日干×他干 10×10），键如 "甲庚"→"七杀"；地支十神对每个藏干分别取（EightChar.py:96-108）；日柱天干十神直接返回"日主"（EightChar.py:236-241）。
- **十二长生（地势）**：名称 `CHANG_SHENG`（EightChar.py:12）+ 十干起点偏移 `__CHANG_SHENG_OFFSET`（:14-25）：甲1、丙10、戊10、庚7、壬4；乙6、丁9、己9、辛0、癸3。计算 `index = 偏移 ± 支序`（日干阳顺阴逆，EightChar.py:116-122）。验证：甲长生在亥、丙生寅、庚生巳、壬生申、乙生午——即通行**阳生阴死**长生诀，有传统依据；但土寄生于寅（火土同宫），火土同源的学术分歧未注释。
- **纳音** `NAYIN`（LunarUtil.py:490-552）：**60 条全量**甲子纳音（实测数了 60 条），传统依据充分。
- **神煞**：`__SHEN_SHA` 158 项名称表（LunarUtil.py:42）+ `__DAY_SHEN_SHA` 12 个字符串（按月支分组，hex 编码每 60 日干支的吉凶神位串，:43-44 起），`getDayJiShen/getDayXiongSha`（:794-845）解码，**index≥60 判为凶神**（:841）。注意：这是**老黄历的"日吉神/日凶神"**（天恩、母仓、月破、大耗之类），不是八字命理神煞。**八字神煞（天乙贵人/桃花/华盖/羊刃/禄神等）完全不存在**（全包 grep 为空）。
- **旬空**：`XUN`/`XUN_KONG` 表（LunarUtil.py:11-12），`getXunIndex` = (干序-支序 mod 12)/2（:901-922）；EightChar 为年/月/日/时柱各提供 getXun/getXunKong（EightChar.py:439-493），日柱口径随 sect。
- **建除十二值星** `ZHI_XING`（:37）、**十二天神黄黑道** `TIAN_SHEN`（:38，配 `ZHI_TIAN_SHEN_OFFSET`）、**彭祖百忌** `PENG_ZU_GAN/ZHI`、**28 宿吉凶歌**（:294 起）：均为老黄历内容，查表。
- **宜忌数据**：`__DAY_YI_JI`/`__TIME_YI_JI`（LunarUtil.py:40-41）为 **hex 压缩字符串**（日干支序=月份集:宜集,忌集），解码见 getDayYi（:726-757）。数据来源（哪部通书）无任何注释——**PROJECT_HEURISTIC（无来源说明的编码数据）**。

## 6. 关系（合冲刑害破/通根/透干）

- **冲**：地支六冲表 `CHONG`（LunarUtil.py:330，子↔午起）；天干冲 `CHONG_GAN`(:331)、`CHONG_GAN_TIE`(:333)、`CHONG_GAN_4`(:336，**定义后全库未使用**，死表)。使用点：`Lunar.getDayChong/ChongGan/ChongGanTie/ChongShengXiao/ChongDesc`（Lunar.py:515-566）、`LunarTime.getChong*`（LunarTime.py:63-80）、`Lunar.getDaySha`（煞方表 `SHA`，LunarUtil.py:342）。
- **合**：天干五合 `HE_GAN_5`（LunarUtil.py:338）、地支六合 `HE_ZHI_6`(:340)。使用点：仅 `EightChar.getTaiXi`（胎息=与日柱天合地合的对柱，EightChar.py:340-347）。
- **刑、害、破**：**无独立表、无 API**（grep 无），仅在宜忌文案与 28 宿歌诀中作为文字出现。
- **三合局/三会局**：无（"三合"只是日神煞名称字符串）。
- **通根、透干**：未发现。
- 结论：lunar-python 的"关系"层只服务于老黄历展示（日冲/时冲/胎息），**不提供供命理推理的结构化关系模型**。

## 7. 旺衰与五行力量

**不存在**（确认）。`grep -rn "旺衰|格局|用神|调候|score|力量|强弱" lunar_python/` 结果为空。仅有把干支五行字符串拼接输出的 `get*WuXing`（如 EightChar.py:75-80）和 `getBaZiWuXing`（Lunar.py:695）。无任何量化权重/评分。

## 8. 格局/用神/调候

**不存在**（确认）。grep 同上为空；EightChar/Lunar 类的方法面中亦无对应概念。

## 9. 大运流年（DaYun 用法 + demo 例子）

- **顺逆**（eightchar/Yun.py:14-16）：`阳年男 / 阴年女 → 顺行`，`阴年男 / 阳年女 → 逆行`（阳=年干序号为偶数即甲丙戊庚壬）。有传统依据。
- **起运**（Yun.py:19-57）：顺行取出生→下一"节"，逆行取上一"节"→出生。
  - `sect=1`（默认，`getYun(gender, sect=1)`，EightChar.py:429-437）：按天数/时辰数折算——**3 天=1 年，1 天=4 个月，1 时辰=10 天**（Yun.py:40-53；时辰差跨日处理 :41-48）。传统依据：通行"三天一岁"起运法。
  - `sect=2`：按**分钟数连续折算**：`4320 分钟=1 年（即 3 天）、360 分钟=1 个月、12 分钟=1 天、余数×2=小时`（Yun.py:31-39）。与 sect=1 同一传统规则的连续化，代码无注释说明常数含义（4320=3×1440，360=4320/12，12=360/30，自洽，PROJECT_HEURISTIC 之列——纯工程换算）。
- **大运**（DaYun.py:11-27）：`index=0` 为出生年到起运年前的"小运前置段"（干支为空）；`index≥1` 每运 10 年；干支=**月柱在甲子表中 ± index**（顺加逆减，DaYun.py:47-61）；每运提供旬/旬空、流年、小运。
- **流年**（LiuNian.py:27-36）：干支以 `立春节气对应农历年的 getYearInGanZhiExact` 为基 + (startAge-1) + index。
- **小运**（XiaoYun.py:26-40）：以**出生时柱**干支为基，每年 +1/-1 递推（1.3.12 曾修复小运干支错误，CHANGELOG）。
- **demo.py 中的例子**（demo.py:51-88，Solar(1983,2,15,20,0,0) 女命）。实测输出：
  ```
  八字: 癸亥 甲寅 甲戌 甲戌
  起运: 6年2个月20天后 顺逆: 顺行
  大运[0] 1983年 1岁 （无干支）
  大运[1] 1989年 7岁 乙卯
  大运[2] 1999年 17岁 丙辰
  ...
  大运[9] 2069年 87岁 癸亥
  大运[1] 流年: 1989 己巳 / 1990 庚午 / 1991 辛未
  ```

## 10. 测试体系

- `test/` 共 **22 个文件**，全部基于 `unittest.TestCase`（无 pytest fixture、无参数化、无 setUp/tearDown），**241 个 test 方法**，约 **332 行 assertEqual**。
- 风格：每个方法内联构造输入 + 硬编码 golden 值断言，断言消息常带中文说明（如 `self.assertEqual(8, yun.getStartYear(), "起运年数")`）。
- 例 1（test/EightCharTest.py:7-15）：
  ```python
  solar = Solar.fromYmdHms(2005, 12, 23, 8, 37, 0)
  lunar = solar.getLunar()
  eight_char = lunar.getEightChar()
  self.assertEqual("乙酉", eight_char.getYear())
  self.assertEqual("戊子", eight_char.getMonth())
  ```
- 例 2（test/JieQiTest.py:6-8）：`lunar = Lunar.fromYmd(2012, 9, 1)` → `self.assertEqual("2012-09-07 13:29:01", lunar.getJieQiTable()["白露"].toYmdHms())`（节气期望值精确到秒）。
- 覆盖的边界：2033 闰月与闰月干支（LunarMonthTest，`fromYm(2023, -2)` 闰二月 index=3）；起运（YunTest，含 1981-01-29 23:37 晚子时案例）；2050 年节气（JieQiTest.test8）；旬/旬空（XunTest）；节假日调休（HolidayTest）；近期 PR 还加了 JieQi.setName 状态重置的行为测试（JieQiTest.py:36-49）。
- CI：GitHub Actions `test.yml`，matrix Python 3.8-3.12。
- 局限：**没有 setSect 的直接测试**（`grep -rn setSect test/` 为空），晚子时双流派仅靠默认口径的 golden 值间接覆盖。

## 11. 边界情况（重点：晚子时 / 节气边界 / 闰月）

### 晚子时（核查项 a）

- 代码位置：`EightChar.setSect`（**EightChar.py:44-45**），默认值 `self.__sect = 2`（**EightChar.py:28**）；`getSect()`（:41-42）。
- 两派的确切语义（实现在 Lunar.py:146-172）：
  - **sect=2（默认，"流派2"）**：晚子时（23:00-23:59）**日柱算当天**。对应 `getDayInGanZhiExact2` 系（Lunar.py:158-160，注释"八字流派2，晚子时（夜子/子夜）日柱算当天"；EightChar.py:111/114/199/206/213/345-346/472/477 按 `2 == self.__sect` 分派）。
  - **sect=1（"流派1"）**：晚子时**日柱算明天**。Lunar.py:162-172，注释"八字流派1，晚子时（夜子/子夜）日柱算明天"，实现在 `"23:00" <= hm <= "23:59"` 时干支序号 +1。
  - 细节坑：该比较用 `"HH:MM"` 字符串（Lunar.py:163-164），**秒不参与**；早子（00:00-00:59）两派一致。
- **时柱不受 sect 影响**：时干五鼠遁恒用"流派1"的日干序 `__dayGanIndexExact`（Lunar.py:177）——即 sect=2 时日柱取当天、但时柱干支仍按"次日日干"起子时。实测（1988-02-15 23:30）：
  ```
  默认(sect2): 戊辰 甲寅 庚子 戊子   ← 日柱=当天庚子
  setSect(1):  戊辰 甲寅 辛丑 戊子   ← 日柱=次日辛丑
  00:30 实测:  戊辰 甲寅 庚子 丙子   ← 早子时，庚日起丙子
  ```
  （戊子恰是辛日的五鼠遁子时干，验证了上述行为；demo.py:46-49 即此案例。）
- 关联口径：`Solar.fromBaZi` 反查也默认 `sect=2`（Solar.py:102-103）。

### 立春/节气边界

- 三口径并存：正月初一 / 立春当天 / 立春交接时刻（Lunar.py:85-101 分别比较 `toYmd` 与 `toYmdHms`）；八字用 Exact（立春交接时刻到秒）。
- 月柱边界同构（Lunar.py:112-144）；大运起运只取"节"（不含中气），`getPrevJie/getNextJie` 有 `whole_day` 参数控制按天还是按时刻（Lunar.py:969-980）。

### 闰月

- 表示：`LunarMonth` 用**负数**表闰月（`isLeap(): month < 0`，LunarMonth.py:79-80）；用户侧 `LunarMonth.fromYm(2023, -2)` 即闰二月（test/LunarMonthTest.py）。
- 判定：无中气置闰 + `__LEAP_11/__LEAP_12` 特例硬编码表（LunarYear.py:17-21, 99-107；表中含著名难题年 2033，实测闰十一月正确）。
- 风险记录：CHANGELOG 1.4.7（2025-10-21）"修复：农历闰月及后续月份的干支错误"——说明闰月干支此前有 bug，Tianze 若复算需以最新版为准并加回归测试。

## 12. AI 接入方式

不适用/未发现。纯确定性历法计算库，无 CLI、无 HTTP 服务、无持久化；grep `openai|gpt|llm|embed|vector|chat` 全空。对 Tianze 的唯一接入方式是**作为 Python 依赖（pip 包 `lunar_python`）直接调用其 API**，或按 MIT 抄录所需代码/表。

## 13. License 与可复用性评估

- **MIT**（LICENSE:1-3，`Copyright (c) 2020 6tail`），可商用、可闭源衍生，仅需保留许可与版权声明；引用 ≤5 行短代码段符合 Phase 0 规则。
- **可复用性高**：零依赖、纯 Python、包结构干净（`lunar_python` 单包可整体引入）；类 API 稳定（v1.4.8，2019 至今持续维护）。
- **复用风险**：
  1. 老黄历宜忌/神煞数据为手工 hex 压缩串，不可读、无出处注释（LunarUtil.py:40-44）；
  2. 闰月/历史节气含大量硬编码修正表，跨版本曾出 bug（1.4.7）；
  3. 无精度/适用年份的官方声明；
  4. `LunarYear.fromYear` 用类级缓存+锁（LunarYear.py:23-25, 42-51），多线程安全但**同时只缓存一个年份**，批量排盘性能受影响。

## 14. Tianze 应该借鉴什么 / 不应该借鉴什么

**可作为依赖直接用（MIT）**：
- 农历/公历/儒略日互转、节气（精确到秒的天文计算）、闰月、数九/三伏/物候。
- 四柱排盘全套：三口径干支、藏干、十神、纳音、十二长生、胎元/胎息/命宫/身宫、旬空。
- 大运/流年/流月/小运排布 + 两种起运流派；晚子时双流派（setSect）；八字反查公历（Solar.fromBaZi）。
- 法定节假日 2001-2026（如 Tianze 需要排"当前日期"类功能）。

**Tianze 必须自建（上游根本没有）**：
- 五行力量量化/旺衰评分（第 7 节：无）。
- 格局判定、用神、调候（第 8 节：无）。
- 刑/害/破、三合局/三会局、通根、透干等结构化关系模型（第 6 节：仅有老黄历展示用冲/合表）。
- 八字神煞（天乙贵人/桃花/华盖/羊刃等）（第 5 节：无）。
- 流派参数化扩展框架（lunar 的 sect 只有两处布尔分叉，不成体系）。

**不建议借鉴**：老黄历宜忌/日神煞 hex 编码数据（与八字分析无关、不可维护）；佛历/道历/九星/彭祖百忌/28宿（超出 Tianze 四柱核心）；`LunarYear` 单年份缓存策略（批量场景需自建缓存）。

## 15. 未解疑问

1. `calcQi/calcShuo` 的高精度分支阈值 `f3 = 2436935`（ShouXingUtil.py:595, 629）对应公历哪一天（约 1959 年末/1960 年初）未逐一验证；1645-1960 用"低精度+修正位"而非天文计算的原因（性能？与史实一致？）无注释。
2. sect=2 时时柱干仍用流派 1 日干（Lunar.py:177）：是 6tail 的刻意设计（"夜子时干支归次日"派）还是疏漏？源码无注释，其官网文档亦未在本仓库内说明——Tianze 若实现晚子时需自行论证并与测试对齐。
3. `__CHANG_SHENG_OFFSET` 中土干（戊己）寄生于火宫（丙10/丁9）——火土同宫派；其他土寄申/寄西南的长生派别未支持，属流派选择但无注释。
4. `CHONG_GAN_4`（LunarUtil.py:336）定义后从未使用，用途（疑似天干四冲/克冲）不明。
5. 宜忌编码数据（`__DAY_YI_JI` 等）的典籍出处、覆盖年份范围均无说明。
6. 节气/朔精度无量化声明；ΔT 外推在 2050 年后的误差量级未评估（对远景排盘的节气交接时刻有影响）。
7. 本地为浅克隆，未核实 `__LEAP_11/__LEAP_12` 特例表的完整性与推导过程（表中列出 30 项 6xxx-9999 年的闰 11/12 月，超出实测能力）。
