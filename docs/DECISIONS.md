# Tianze 设计决策（DECISIONS）

> Coding Night 起的新决策登记于此（Phase 0 的 ADR-001~015 见 `docs/research/08-DECISION-LOG.md`）。格式沿用：Context / Options / Decision / Reason / Tradeoff。

## ADR-016 · 通根只做定性深度，不引入权重（M3）

- **Context**：上游六家的旺衰权重全部是 PROJECT_HEURISTIC（Phase 0 结论）；任务书明令 M3 只回答"有没有根"。
- **Options**：A. 直接给每根赋分（Horosa 式 30/25/20/15/10/6）；B. 定性深度枚举。
- **Decision**：**B**。`RootDepth = strong/medium/weak`，与本气/中气/余气一一映射（R15）；分值留给 M4+ 各 StrengthAnalyzer 的公开 params。
- **Reason**：把"根的分级"（传统有据）与"根值多少分"（现代发明）拆开，前者进事实层，后者留分析层并标注 heuristic。
- **Tradeoff**：分析器需要自己把深度映射为分数——正是我们想要的显式化。

## ADR-017 · 月令按月支本气五行判旺相休囚死；得令严格=旺；得势阈值=2（M3/M4）

- **Context**：实现时最初按"季节"查旺相休囚死表，导致丑月壬水被误判"旺"（冬季水旺），而通行口径按月支本气（丑=土 → 土克水为死/囚域）；OBE 的月令表同为月支口径（"四土月土旺金相"）。得令各派宽严不一；得势无现成定义。
- **Decision**：
  1. 旺相休囚死按**月支本气五行**判定（R17）；四库月土旺由此自然成立，不做特判分支。
  2. **得令严格 = 旺**；"相"（月令所生）不得令但写入证据。
  3. **得势 = 年/月/时干印比透干 ≥2**（`DE_SHI_THRESHOLD` 公开常量，标 PROJECT_HEURISTIC）。
- **Reason**：与通行教材及上游主流对齐；阈值公开声明优于隐藏。
- **Tradeoff**：得势阈值 2 是作者口径——fixture 守卫（2003 盘年干癸计比肩）锁定行为，未来可依校准数据修订（修订须改 R 表+测试）。

## ADR-018 · 五行统计 = 两个独立视图，不加权（M3）

- **Context**：任务书要求"显性/潜在"统计但禁止打分；Atlas 的三口径并列是最透明的先例。
- **Decision**：`visible`（4 干 + 4 支主气 8 字）与 `hidden`（全部藏干，含本气）两视图并列输出 + `missing`（两视图皆零）；key 用小写五行名（与任务书示例一致；其余 JSON 的 Element 枚举仍为大写）。
- **Reason**：不替用户选口径；hidden 含本气造成的"重叠"是两视图各自成立的代价，已在 R16 声明。
- **Tradeoff**：消费方不能把 visible+hidden 当总量相加——文档明确警告。

## ADR-019 · 旺衰多分析器框架：单方法也不假装有 agreement（M4）

- **Context**：Phase 0 结论"六家六套权重六套阈值"；任务书要求 `StrengthAnalyzer` 抽象且禁止唯一答案。
- **Decision**：`StrengthAnalyzer` Protocol + `run_strength` 注册表；`StrengthReport.methods[]` 并列；`agreement` 仅当 ≥2 个带 verdict 的方法存在时输出（HIGH/DISPUTED），单方法时**字段缺席**并在 note 说明；M4.1 只内置 `dimension`（定性三维，verdict=None）。
- **Reason**：诚实原则——一个实现不是共识；JSON 的 exclude_none 契约天然表达"缺席"。
- **Tradeoff**：M4.1 的输出没有"偏强/偏弱"结论（要等 M4.2 weighted 加入后并排呈现）。
- **附带修复**：run_strength 初版对去重后的 verdict 集合计数导致单方法误判——被 FakeA/FakeA 双方法测试当场抓出，已修。

## ADR-020 · 分析器输入用 StrengthFacts 而非 BaziChart（M4）

- **Context**：分析器需要月令/通根/四干事实；直接吃 BaziChart 会造成组装顺序耦合（strength 依赖 chart，chart 又要装 strength）。
- **Decision**：`StrengthFacts`（frozen dataclass：日主/月令/日主根/他干）作为分析器输入；pipeline 负责从事实层裁剪装配。
- **Reason**：单测可直接构造 facts（阈值边界测试无需真实排盘）；未来流派层复用同一 facts。
- **Tradeoff**：新增一层轻量 DTO。（M4.2 补充：新增 `pillar_units` 字段供 weighted 逐字计分，dimension/fuyi 不读它。）

## ADR-021 · MonthCommand 预留司令分野扩展字段（M5 前）

- **Context**：Horosa 的人元司令分野（baziFenYe 两版口径）与节气深度是"完整月令体系"的一部分；当前 MonthCommand 只绑定月支本气。
- **Decision**：新增 `main_qi`（本气便捷引用）与预留字段 `ruling_stem`、`jie_qi_depth_days`（恒 None，V2 填充）；不做分野实现。
- **Reason**：数据模型不为未来扩展设障，也不提前实现未验证口径。
- **Tradeoff**：两个常为 None 的字段。

## ADR-022 · weighted 防重复计分：根/得令不独立计分（M4.2）

- **Context**：月令乘数、藏干单位、通根、得令在上游多家实现中互相叠加（同一事实计 2-3 次）；任务书明令检查重复计分。
- **Decision**：weighted 的计分单位只有"逐字"一种（可见干+藏干），月柱单位统一 ×乘数；通根与得令**不是**计分项（它们是 dimension/fuyi 的特征）。测试锁定：伪造不同 roots 输入 → weighted 输出不变。
- **Reason**：根 = 藏干中含日主 = 已被计入的同一批单位；再加分即同一事实双计。
- **Tradeoff**：weighted 对"根的深度"不敏感于"藏干权重之外"的细分——如需可另立 features 型分析器。

## ADR-023 · fuyi = 特征计票级联，允许 UNCERTAIN（M4.2）

- **Context**：weighted 是连续 ratio；扶抑传统是"规则+证据"式判断；任务书要求两方法路径不同且允许证据不足时不强判。
- **Decision**：fuyi 只读派生特征（得令/根数/印比数/克泄数/月克日），计票后按九条首中即停规则映射五级 verdict；信号对冲（得令但仅月令单根+无印比+克泄重）→ UNCERTAIN；UNCERTAIN 在 agreement 中弃权。
- **Reason**：与 weighted（连续逐字 ratio）构成真正的方法多样性；UNCERTAIN 优于伪精确。
- **Tradeoff**：计票表与级联阈值是作者口径（ENGINEERING_HEURISTIC），已公开于 R21/STRENGTH.md。附带数学发现：得令⟹必有月令根，"得令+无根"不可达——规则表据此修正（测试覆盖九条路径）。

## ADR-024 · agreement 引入 PARTIAL（M4.2）

- **Context**：三方法并存后，两两一致的中间态出现（如 偏强 vs 极强）。
- **Decision**：HIGH（全同）/ PARTIAL（存在相同对或全部相邻档）/ DISPUTED（其余）；UNCERTAIN 弃权；有效 verdict <2 时字段缺席。
- **Reason**：五级量表上"相邻档"与"完全一致"的分歧程度不同，二值 HIGH/DISPUTED 丢失信息。
- **Tradeoff**：PARTIAL 的语义较软——已在 R22 写明判定规则。

## ADR-025 · 格局：多候选并列 + 首选评估；特殊格不做伪检测（M5）

- **Context**：中余气同时透时取格存在真实的多个合理答案；从格/专旺/化气需要旺衰条件支撑，M5.1 证据尚不足以诚实判定。
- **Decision**：`PatternAnalysis.candidates[]` 按优先级并列；评估仅针对首选，多候选记 PAT-MULTI 冲突；特殊格完全不实现、文档声明，不做"检测到但不支持"的伪输出。
- **Reason**：诚实原则——伪检测比不检测更糟；候选结构为 M6+ 从格接入留好接口。
- **Tradeoff**：比劫月令（月劫）当前无候选输出，只有 note 解释。

