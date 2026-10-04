# Tianze 约定表（CONVENTIONS / R 表）

> 每条流派选择一个编号（R1…），与实现同址引用（代码里出现 `R1` 字样即指本表）。
> 规矩：**改 R 必须同时改相关 fixture 与测试**；分歧处写明两派内容与 Tianze 默认值；默认值不是"正确答案"，是"本引擎口径"。
> 状态：`LOCKED`（fixture 已锁）/ `OPEN`（尚未有测试锁定）。

## R1 · 晚子时（23:00-23:59）日柱归属 — `LOCKED`

- 流派 1：晚子时日柱算**明天**（子平"子初换日"派）。
- 流派 2（**Tianze 默认**，随 lunar-python 默认）：晚子时日柱算**当天**（"夜子时"派）。
- 补充口径：两派的**时柱天干基准都用次日日干**（五鼠遁按次日日干起子时）。该口径与 lunar-python 行为一致（实测 1988-02-15 23:30：sect2 → 庚子日/戊子时；sect1 → 辛丑日/戊子时），也与 bazi-atlas 对拍器注释一致。lunar-python 源码未注释此行为（见 ERRATA-01）。
- 输入参数：`birth.sect ∈ {1,2}`，默认 2。

## R2 · 时间算法 — `LOCKED`

- `clock`（默认）：直接用钟表时间。
- `true_solar` / `mean_solar`：真/平太阳时（M3 实现，接口先占位）。

## R3 · 双轨道时间 — `LOCKED`

- **年柱/月柱**按"绝对时刻"判定（`birth_instant_utc` 换算为北京时间后的节气边界）——节气是全球同一瞬间的天文事件。
- **日柱/时柱**按出生地钟表（标准时，DST 校正后，`pillar_dt`）判定。
- 农历日期回显跟随日柱轨道（pillar_dt）。

## R4 · 立春与交节按精确时刻 — `LOCKED`

- 年柱以立春**时刻**（非日期、非正月初一）切换；月柱以十二**节**（非中气）的精确时刻切换。
- 距节/立春交界 ≤30 分钟的排盘输出 `boundary_warnings`（不改变结果，只提示）。

## R5 · 十二长生 — `LOCKED`

- 默认火土同宫派（戊己随丙丁，lunar-python 口径）。水土同源/阳顺阴逆等派别差异记录在案，V1 不做开关。

## R6 · 月令旺相休囚死 — `LOCKED`

- 通行表："当令旺、我生相、生我休、克我囚、我克死"；土旺四季（四库月土旺）。

## R7 · 起运与大运 — `LOCKED`

- 顺逆：阳男阴女顺行，阴男阳女逆行。
- 起运折算：lunar-python `getYun(gender, sect=1)` 口径（3 天 = 1 岁，1 天 = 4 个月，1 时辰 = 10 天）。
- 性别未知或时辰未知时大运整体缺席（见 R11），不猜测。

## R8 · 藏干表 — `LOCKED`

- 通行子平表（本气/中气/余气），与 lunar-python `ZHI_HIDE_GAN`、bazi-atlas、Horosa、jiwenxu（丑支中余气排列除外，见 ERRATA-04）一致。测试与库表逐支对账。

## R9 · 刑组命名 — `LOCKED`（命名本身有流派分歧）

- Tianze 采用通行命名：**寅巳申 = 无恩之刑；丑戌未 = 恃势之刑；子卯 = 无礼之刑；辰午酉亥 = 自刑**。
- 分歧：义理派对前两组名称互换（bazi-atlas R18 记录"分组一致，名称互换"）。输出 `note` 字段会携带此分歧。

## R10 · 半三合 — `LOCKED`

- 三合局需三支齐全；仅两支时，**必须含中神（子/卯/午/酉）才报 `three_harmony_half`**，否则不报（拱/虚拱 V1 不实现）。
- 半合不判成败、不改力量，只作事实标注。

## R11 · 未知时辰 — `LOCKED`

- `time_known=false` 时：时柱为 `null`（缺席而非猜测）；命宫/身宫/大运缺席并在 `meta.fallbacks` 说明；胎元仍可给（只依赖月柱）。

## R12 · 时区与夏令时 — `LOCKED`

- `tz_offset_hours` 必须按**标准时**偏移理解，缺省 8。非东八区出生按 R3 双轨道处理。
- 中国 1986-1991 夏令时窗口自动校正（钟表 −1h；跨零点回滚到前一日）。窗口表为公共事实数据，标记 `needs-verification`（见 ERRATA-05）。其他国家的 DST 暂由调用方自行换算。

## R13 · 合化只报候选 — `LOCKED`

- 关系层输出 `transform_candidate`（如"甲己合，化土候选"），**不判定化气是否成立**（成立与否留给分析层：月令/通根等条件 V2 再议）。
- 六合化气表默认值：子丑土、寅亥木、卯戌火、辰酉金、巳申水、**午未土**（火说/日月说分歧 → `note` 携带）。

## R14 · 天干四冲 — `LOCKED`

- 甲庚、乙辛、丙壬、丁癸 4 对（戊己土居中不冲）。输出 `stem_opposition`。

## R15 · 通根（M3） — `LOCKED`

- 事实定义：天干 X 通根于地支 B ⟺ B 的藏干含同字之干。
- 深度分级 = **定性映射**：本气→`strong`、中气→`medium`、余气→`weak`。**不引入任何数值权重**——M3 只回答"有没有根、多深的根"。
- `isMonthRoot` = 根在月支；`isDayMaster` = 被通根者为日主。日支坐根照常计入。

## R16 · 五行统计（M3） — `LOCKED`

- 两个**独立视图**，不加权不给分：`visible` = 4 干 + 4 支主气（8 字）；`hidden` = 全部地支藏干（含本气，与 visible 的支主气有意重叠——两视图各自成立，类似 bazi-atlas 的"多口径并列"）。
- `missing` = 两视图皆 0。key 用小写五行名（wood/fire/earth/metal/water）。

## R17 · 月令旺相休囚死与得令（M3，替代 R6 的实现细则） — `LOCKED`

- 判定按**月支本气五行**（非季节）：当令者旺、我生者相、生我者休、克我者囚、我克者死。
- 四库月（辰戌丑未）本气属土 → 土日主自动"旺"（"土旺四季"由此成立，非额外特判）。
- **得令严格 = 旺**；"相"（月令所生）不得令，但在证据中注明。
- 旺相休囚死是**传统定性表**（有出处）；不得把它加权成分数。

## R18 · 透干（M3） — `LOCKED`

- 事实定义：藏干 X 透出 ⟺ 同字之干出现在任一天干位置。只记录（位置/来源/距离/月令相关/日主相关），不判吉凶。
- `distance` = |支位置序 − 干位置序|（0-3）。
- `dayMasterRelated` = 藏干字即日主（月令藏日主是建禄/得令类判定的事实基础）；透出位置是否日干由 `position=="day"` 表达。

## R19 · 旺衰评估框架（M4） — `LOCKED`（架构） / `OPEN`（阈值）

- **不存在唯一旺衰算法**：多个 `StrengthAnalyzer` 并列输出到 `strength.methods[]`，Tianze 不裁决。
- M4.1 仅内置 `dimension`（dimensional_v1）：得令/得地/得势三维**定性**输出（`result: bool + reason[]`），**无分数、无 verdict**。
- 得令严格 = 旺（同 R17）；"相"不得令但注明。
- 得地 = 日主在四支藏干中有同字之根（R15）。
- **得势 = 年/月/时天干中印比（比肩/劫财/正印/偏印）透干 ≥2**。⚠️ 阈值 2 是**结构规则（作者口径），非古籍量化**——标 `PROJECT_HEURISTIC`，常量 `DE_SHI_THRESHOLD` 公开可配；别柱同干比肩必须计入（2003 盘年干癸案例为守卫 fixture）。
- `agreement` 仅当 ≥2 个带 verdict 的方法并存时输出（HIGH/DISPUTED）；单方法时缺席并在 note 说明。
- 后续 weighted/fuyi 等计分制方法加入时：权重必须全部进 `params` 输出并标 `PROJECT_HEURISTIC`。

## R20 · weighted 参数（M4.2） — `LOCKED`（结构） / `OPEN`（数值）

- 逐字单位计分：可见天干（**日主除外**）+ 全部藏干；比劫/印 → support，食伤/财/官杀 → drain；月柱单位 ×`monthMultiplier`；score = support/(support+drain)。
- **防重复计分（ADR-022）**：通根/得令不设独立计分项；测试锁定"伪造根输入不改变结果"。
- 默认值与出处详见 `docs/STRENGTH.md` 参数表；改默认值 = 改 OPEN 数值，须记 DECISIONS。

## R21 · fuyi 计票级联（M4.2） — `LOCKED`（结构） / `OPEN`（数值）

- 支持票：得令/相 +1、根≥1 +1、根≥2 +1、印比≥1 +1、印比≥2 +1；
  克泄票：休 +1、囚死 +2、食伤财官≥1 +1、≥2 +1、无根 +1、无印比 +1。
- 级联九规则（首中即停）见 `docs/STRENGTH.md`；R21-4 为信号对冲 → **UNCERTAIN**。
- 数学注记：得令 ⟹ 必有月令根（月支藏日主），"得令+无根"不可达。

## R22 · agreement 语义（M4.2） — `LOCKED`

- 只比较带 verdict 且非 UNCERTAIN 的方法（UNCERTAIN=弃权）。
- 全同 → HIGH；存在相同对或全部相邻档 → PARTIAL；其余 → DISPUTED；有效 <2 → 缺席。
- dimension 永不参与。Tianze 不裁决。

## R23 · 格局候选生成（M5.1） — `LOCKED`

- 优先级：禄刃 → 月令藏干透干（本→中→余，比劫跳过）→ 皆不透取本气。
- 多候选按优先级排序并存；评估仅针对首选，其余保留并记 PAT-MULTI 冲突。

## R24 · 建禄 / 阳刃（M5.1） — `LOCKED`（口径） / `OPEN`（流派）

- 禄位表（临官）：甲寅 乙卯 丙巳 丁午 戊巳 己午 庚申 辛酉 壬亥 癸子。
- 阳刃仅阳干（帝旺位）：甲卯 丙午 戊午 庚酉 壬子；**阴干无刃**（少数派不立，记录争议）。
- 流派差异：Horosa 要求月令本气为比劫方论禄刃（戊日巳月不作建禄）；Tianze 采用禄位表口径（戊日巳月 → 建禄候选），差异写入候选 evidence。

## R25 · 格局评估状态（M5.2） — `LOCKED`

- 无 damage → 成立；damage 全有救应 → 有瑕；1 个未救 → 受损；≥2 → 破格；
  候选缺失或禄刃格（v1 未配置规则）→ 待定。
- status 不取代证据；救应以 `related=[damage rule_id]` 关联，damage+rescue 允许并存。

## R26 · 知识库来源与质量（K0/K1） — `LOCKED`

- 来源五级（SourceKind）不可混写：CLASSICAL_TEXT / COMMENTARY / MODERN_BOOK /
  OPEN_SOURCE_PROJECT / TIANZE_HEURISTIC。徐乐吾原著（命理一得等）归 COMMENTARY；
  孙正治注译、赵嘉宁今译归 MODERN_BOOK（不入 provenance 主链）。
- 两层规则：RuleCandidate（文献候选）→ 人工复核 → ExecutableRule（可执行）；
  禁止"一句古籍立即变 if"。转换必须携带 normalizationNotes。
- OCR 错字照录（rawText 不可变），修订走 correctedText+correction。
- 数据质量等级 A-D 进入运行时 provenance；当前最高 B（OCR 未全核，A 为零是诚实边界）。
- raw/ 只读不入库（MANIFEST.sha256 锚定）；normalized/rules 可再生。

## R27 · 调候规则口径（M6） — `LOCKED`

- 调候为独立分析维度，非旺衰换名；只输出 desired/present/条件/例外/出处。
- specificStem 优先（丙丁壬癸不降维成五行）；element 为派生字段。
- 10×12 覆盖：每格有规则或显式 UNRESOLVED；禁止编造。
- 条件重叠不静默覆盖：conflicts.json 登记 + resolution 策略
  （specific-over-general / 从正文）+ 结果 conflicts[] 可见。
- 规则 ID：`TH-{候选ID}-{月支}`，格限定；released 后冻结。

## R28 · 验证状态与命例纪律（M6.1/M7） — `LOCKED`

- 机器流程不得产生 HUMAN_* 验证状态（Schema 校验器 + Status Test 双保险）；
  M6 curation 已诚实降级 MACHINE_CURATED/ai_curation。
- 四维准确度分别建模：traceability / textAccuracy / interpretationAccuracy /
  engineAccuracy，禁止互相冒充。
- Rule↔Case 三态：EXPLICITLY_CITED / INFERRED_MATCH / ENGINE_TRIGGERED；
  引擎触发不冒充"古人明确用了这条规则"。
- 命例三层：Case Fact / AUTHOR_INTERPRETATION / HISTORICAL_CLAIM；
  sourceAnalysis 与 tianzeAnalysis 永久分离；命例不是训练标签。
- 冲突六类（TEXT/COMMENTARY/RULE/CONDITION_OVERLAP/SCHOOL_DIFFERENCE/OCR_AMBIGUITY），
  禁止 last-rule-wins。
- Schema 版本：KNOWLEDGE=1.1.0 / CASE=1.0.0；字段变更必须显式 migration。

## R29 · 特殊格局候选口径（M8.1/M8.2） — `LOCKED`

- 从格四型（从财/从官杀/从儿/从强）；专旺五格（曲直/炎上/稼穑/从革/润下）。
- 状态永不 CONFIRMED：CANDIDATE/LIKELY/BLOCKED/DISPUTED/UNRESOLVED。
- 从格复用 M4 strength 三方法；weighted/fuyi 方向冲突 → DISPUTED。
- 从格阻断：有根（jiwenxu 反条件）/印比透干。
- 专旺阻断：官杀透干 / 同党占比 <60% / weighted 不支持。
- `schoolVariants` 保留 Horosa/ruan 口径差异。

## R30 · 化气候选（M8.3） — `LOCKED`

- 五组合（甲己/乙庚/丙辛/丁壬/戊癸）；干合 ≠ 化（R13 延伸）。
- 化神得令 → season_support；藏干含化神 → root_support。
- 有争合或缺季节支持 → UNRESOLVED；大量 UNRESOLVED 是正确行为。

## R31 · 病药与通关（M8.4/M8.5） — `LOCKED`

- 病药：StructuralProblem/MedicineCandidate（非医学疾病）；病准入 ≥1/2 且 ≥3 字；
  药 = 制（克病者）/ 泄（病所生），必须关联具体病。
- 通关：ConflictPair（一方 ≥ 另一方 2 倍对峙）+ BridgeCandidate（A→C→B 五行生链）；
  桥存在 = C 可见 >0。
- Case Regression：severity 四级（BREAKING/REVIEW/EXPECTED/INFO）；caseCount 与
  comparisonItemCount 口径分离（ADR-031）。

## 维护记录

| 日期 | 变更 | 原因 |
|---|---|---|
| 2026-10-01 | 初版 R1-R14 | M0 |
| 2026-10-01 | 新增 R15-R18（通根/五行统计/月令细则/透干） | M3 |
| 2026-10-01 | 新增 R19（旺衰框架 + 得势阈值声明） | M4 |
| 2026-10-01 | 新增 R20-R25（weighted/fuyi/agreement/取格/禄刃/评估状态） | M4.2-M5 |
| 2026-10-01 | 新增 R26-R27（知识库来源质量/调候口径） | K0/K1/M6 |
| 2026-10-01 | 新增 R28（验证状态/命例纪律/schema 版本） | M6.1/M7 |
| 2026-10-01 | 新增 R29-R31（特殊格局/化气/病药通关/回归） | M8 |
