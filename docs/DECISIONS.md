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


## ADR-026 · 知识库 raw 不入库，以 MANIFEST 锚定（K1）

- **Context**：用户提供的知识库 zip 含现代今译（孙正治注译/赵嘉宁今译）与整理层，版权状态不适合再分发；但规范化流程需要可复现。
- **Decision**：`knowledge/raw/` 只读、gitignore；入库 `MANIFEST.sha256`（zip 哈希）+ README（重建步骤）；normalized/rules 为可再生的确定性产物入库。
- **Reason**：可复现性与版权谨慎兼得。
- **Tradeoff**：克隆仓库后需自行获取 zip 才能重跑 normalize（candidates JSON 已入库，日常开发/测试不受影响）。

## ADR-027 · 调候目标保留 specificStem，两说并存不裁决（M6）

- **Context**：穷通宝鉴逐月规则以具体天干表述（丙丁壬癸庚辛），且存在同格两说（己-申 标题 vs 正文）与合论/专论重叠（甲-未）。
- **Decision**：效果层保留 specificStem（element 为派生）；多候选并存；重叠登记 conflicts.json（resolution: specific-over-general / 从正文）并在结果 conflicts[] 可见；desired 与 present 分离。
- **Reason**：过早降维为五行会丢失原文信息；静默覆盖会伪装共识。
- **Tradeoff**：消费方需理解 priority 序列而非单一"用神"。

## ADR-028 · 调候规则层（ExecutableRule）由人工复核 curation 生成（M6）

- **Context**：启发式草案仅 103/120 命中且有错配（如 丙寅缺格、己未 primary 误判），程序不能自证 target 提取正确。
- **Decision**：`tools/build_tiaohou_rules.py` 内嵌人工复核后的 CURATION 表（每格引用候选 ID + targets + conditions/exceptions/notes），脚本负责引用完整性校验与结构化输出；草案保留作审计痕迹。
- **Reason**：两层规则模型中"人工/程序验证"步骤的落地；curation 即审计对象。
- **Tradeoff**：新格/修订需人工改 curation 并重建——这正是可追踪性的成本。

## ADR-029 · M6 curation 诚实降级为 MACHINE_CURATED（M6.1）

- **Context**：M6 报告称"人工复核 curation"，但实际由 AI（agent）完成——不满足 HUMAN_VERIFIED 定义。
- **Decision**：全部 182 条调候规则 verification 重标 `MACHINE_CURATED + ai_curation`，
  verifiedBy=tianze-pipeline:build_tiaohou_rules.py；新增 VerificationStatus 六级与
  AccuracyMatrix 四维；Schema 校验器拒绝 pipeline 署名的 HUMAN_*；人工升级走
  review/knowledge-review.csv 队列（182 行，冲突/OCR 优先）。
- **Reason**：第一原则"机器整理 ≠ 人工核验"；边界模糊即失信。
- **Tradeoff**：HUMAN_VERIFIED=0 的诚实边界——等待真人核验（Golden Set 43 条为首核集）。

## ADR-030 · 命例 system：三层分离 + 双分析分离 + 关系三态（M7）

- **Context**：知识库含 748 结构化命例块 + 400 索引行，混有事实/作者判断/历史事件；
  引擎可对四柱直接派生分析。
- **Decision**：CaseReference 严格分层（fact / AUTHOR_INTERPRETATION / HISTORICAL_CLAIM）；
  sourceAnalysis 与 tianzeAnalysis 独立字段；Rule↔Case 关系三态（EXPLICITLY_CITED /
  INFERRED_MATCH / ENGINE_TRIGGERED）；CaseIdentity 候选重复只登记不合并；对比只记录
  不裁决；命例不是训练标签。
- **Reason**：让每条数据都能回答"这是谁说的、机器还是人、验证到什么程度"。
- **Tradeoff**：语义级命例对比（721 例）留待人工——自动判对错必然越界。

## ADR-031 · Case Regression 统计口径分离（M8.0）

- **Context**：此前报告"426 例机械化对比、420 一致、24 差异"——420+24>426，案例数与比较项数混用。
- **Decision**：`caseCount`（案例数）与 `comparisonItemCount` / `agreementItemCount` / `differenceItemCount`（比较项数）严格分离；一例可同时含一致与差异项。
- **Reason**：统计诚实。
- **Tradeoff**：数字变大但准确（当前 426 例 → 837 项）。

## ADR-032 · 从格复用 StrengthAnalyzer，不复制旺衰算法（M8.1）

- **Context**：从格判断需要日主旺衰，但 M4 已有三个分析器。
- **Decision**：从格以 `strength_verdicts`（weighted/fuyi）为输入之一；两方法方向冲突 → DISPUTED；score 仅作 evidence，不单独决定从格。
- **Reason**：避免同一逻辑写两遍；多分析器分歧直接映射为从格 DISPUTED。
- **Tradeoff**：从格精度受限于上游分析器精度。

## ADR-033 · 病药命名 StructuralProblem / MedicineCandidate（M8.4）

- **Context**：任务书明令"病药不是健康疾病预测"。
- **Decision**：代码使用 StructuralProblem/MedicineCandidate；API/文档避免 Disease/Diagnosis；禁止输出个人健康预测。
- **Reason**：避免 API 使用者误解。
- **Tradeoff**：与传统术语"病药"不完全对应——文档已说明。

## ADR-034 · Case Regression Snapshot Contract（M8.0）

- **Context**：1147 例的完整 JSON 过大，但需要能检测所有行为变化。
- **Decision**：Snapshot 只保留可判断行为变化的稳定字段（strength 三方法/pattern/tiaohou/triggeredRuleIds/specialPattern/bingYao/tongGuan/chartFingerprint），不含完整推荐 evidence。
- **Reason**：性能 + 可 diff。
- **Tradeoff**：新增字段须更新 snapshot 代码。

## ADR-037 · AI 位于确定性分析之后（M11）

- **Context**：AI 可能幻觉（编造格局/伪造古籍/忽略分歧），必须约束在确定性结果之内。
- **Decision**：AI 永远消费 `AnalyzeResult → InterpretationContext → Prompt → LLM → InterpretationResult → Grounding Validator`。AI 不参与排盘/旺衰/格局/调候/特殊格局的任何计算。
- **Reason**：确定性引擎是唯一真相源。
- **Tradeoff**：AI 只能解释引擎已算出的内容，不能"发现"引擎遗漏的东西——这正是设计意图。

## ADR-038 · Grounding Validator 程序化检查（M11）

- **Context**：LLM 输出不可信任，需要程序化校验。
- **Decision**：六类检查（evidenceId/sourceId 存在性、格局候选一致性、古籍来源存在性、验证状态不越界、UNRESOLVED 不裁决）。检查结果记入 `grounding_issues[]` + `grounding_passed`。
- **Reason**：规则式检查比 LLM-as-judge 更可靠、更快、可测试。
- **Tradeoff**：检查有假阴性（如同义改写）——后续可加 LLM-as-judge 第二层。

## ADR-039 · Temporal Delta 的适用性三标（M13）

- **Context**：岁运是否参与旺衰计分/从格判定/化气判定存在真实流派分歧；硬算会把一种口径伪装成真理。
- **Decision**：每条 DeltaItem 标 SUPPORTED（规则驱动无分歧）/ EXPERIMENTAL（有分歧，如实计算并标注）/
  UNSUPPORTED（理论不应变化，只给 note 不计算）。前端与 AI 必须保留标注。
- **Reason**：把分歧显式化比隐藏分歧更诚实；engine 不裁决流派。
- **Tradeoff**：EXPERIMENTAL 条目对新手可能造成困惑——通过 note 与文档缓解。

## ADR-040 · 岁运规则进入 Knowledge Framework（M13）

- **Context**：伏吟/反吟/岁运并临/天克地冲等概念在知识库中部分有引文（日犯岁君、刃头财、
  杂气引出、冲为重、流年太岁），部分只有通说概念。
- **Decision**：统一走 Source → Quote → RuleCandidate → ExecutableRule(domain=temporal) →
  TemporalEvidence；有引文链标 CLASSICAL_EXPLICIT，无引文链标 PROJECT_REFERENCE/ENGINEERING_HEURISTIC
  并使用 TIANZE-ENGINEERING-* 候选 ID。规则未触发保留 matched=false。缺执行器的规则使引擎抛错。
- **Reason**：与 M6/M8 同一纪律；岁运规则不因"新领域"而降低 provenance 标准。
- **Tradeoff**：100% 触发的定义性规则（TR-SPZY-28 流年即太岁）会在每个流年出现——
  它是术语框架说明而非断言，已在 label/note 中声明。

## ADR-041 · TemporalCaseReference 三层分离（M13）

- **Context**：原书岁运分析（大运序列、事件断言）OCR 噪声大，且历史事件不是 truth。
- **Decision**：sourceTemporalAnalysis（原样保留 + 干支序列一致性校验：同向 ±1、年龄 +10）/
  tianzeTemporalAnalysis（缺出生信息显式 not_computed）/ historicalClaims（仅 claim）。
  不为迎合古籍案例调整引擎规则。
- **Reason**：M7 三层分离在岁运维度的直接推广。
- **Tradeoff**：101/1147 例可结构化大运，覆盖率有限——如实报告而非夸大。

## ADR-042 · Event Theme 是主题候选而非事件预测（M14）

- **Context**：结构主题（官杀/印星增强等）离现实事件还有多层距离；直接输出事件断言
  会把命理规则包装成现实必然，违反项目红线。
- **Decision**：事件层输出 EventThemeCandidate（7 主题 × CANDIDATE/LIKELY/DISPUTED/
  BLOCKED/UNRESOLVED），绝无 CONFIRMED；每条候选必须带支持/反对证据与流派视角。
- **Reason**：为后续事件推理保留中间层，同时不越过「不做人生预测」的边界。
- **Tradeoff**：用户可能期望明确答案——UI/报告/AI 处处标注「候选，非预测」缓解。

## ADR-043 · School-aware Reasoning：流派方向显式保留（M14）

- **Context**：同一结构在不同体系下方向相反（如官星透出：traditional 支持 career、
  伤官见官反对；神煞驿马被子平派删除）。
- **Decision**：每条规则带 view（traditional/pattern/strength/tiaohou/special_pattern/
  shensha/temporal_rule）；聚合按 view 记录方向（support/oppose/both），agreement=
  HIGH/PARTIAL/CONFLICT；CONFLICT 不裁决，status=DISPUTED。
- **Reason**：任务书要求「禁止为了漂亮答案隐藏冲突」。
- **Tradeoff**：DISPUTED 候选对普通用户较难读——Web 用徽章+分组证据缓解。

## ADR-044 · Confidence 是透明加权而非概率（M14）

- **Context**：多规则/多视角支持强度需要一个可比标量；但 ML 式概率会造成伪精度。
- **Decision**：confidence = 证据 provenance 权重和 × 流派一致性加成 − 反向惩罚，
  scale 0.3、cap 1.0，全部参数随结果输出并标 ENGINEERING_HEURISTIC；
  grounding 拦截「概率为/80% 会」类表述。
- **Reason**：可审计性优先于表面精度。
- **Tradeoff**：数值跨度较粗（0.3/0.6/0.975 等档位）——是刻意选择，拒绝伪连续。

## ADR-045 · 冲突解释是上下文相关的，不建立全局优先级（M15）

- **Context**：同主题规则可同盘反向命中（官星支持 vs 伤官见官反对）；简单的全局 A>B
  会把流派差异压成单一答案。
- **Decision**：`ConflictExplanation` 三类——SPECIFIC_EXCEPTION（仅当 conflicts.json
  显式声明 specificity，引擎绝不猜测）、SCHOOL_DIFFERENCE（不同 view，no-adjudication）、
  CONDITION_OVERLAP（keep-both，status=DISPUTED）。声明文件与 tiaohou conflicts.json 同构。
- **Reason**：任务书要求「不简单建立全局 A > B」「precedence/specificity 透明可审计」。
- **Tradeoff**：v1 无已实现的 specific-over-general 对（救应/喜神判定未做），全部走
  keep-both/no-adjudication——SPECIFIC_EXCEPTION 路径由单测锁定待未来启用。

## ADR-046 · 特殊格局岁运专题的上下文相关流派权重（M15）

- **Context**：从格岁运破格与否，古典依据本身分阴阳两说（DTZ-04：阳干绝处逢生不从、
  阴干从势无情义）。
- **Decision**：TR-SP-02 按日主阴阳给「破格说/顺势说」分配权重（阳干→破格说优先，
  阴干→顺势说优先），双方证据全部保留、不裁决；化气（TR-SP-04）永远携带
  DTZ-18「合≠化」警示，候选永不升级。
- **Reason**：流派权重随上下文（日主阴阳）变化，这正是「上下文相关优先级」的实例。
- **Tradeoff**：权重表述为文字依据而非数值——数值化需更多文献支撑，暂缓。

## ADR-047 · 救应/例外是声明驱动的条件谓词，不是硬编码优先级（M16）

- **Context**：伤官见官有财/印救应（DTZ-39/43）、财印不容有官星通关、比劫夺财须察
  财为喜神（SS-R10）——「规则是否适用」取决于可判定的结构条件。
- **Decision**：救应谓词（rescues.py）全部复用现有 Engine 事实（十神分布、weighted
  verdict），一次评估多处引用；rescues.json 声明谁救谁；conflicts.json 的
  specificCondition 引用谓词 → SPECIFIC_EXCEPTION 只在条件成立时启用，
  否则回落 keep-both。ENGINEERING 映射（如 偏强→财为喜神方向）显式标注。
- **Reason**：上下文相关优先级替代全局 A>B；命中仍保留（rescueApplied 随结果输出）。
- **Tradeoff**：强度到「喜神」的映射是粗粒度 heuristic——需要更细时按规则逐条精化。

## ADR-048 · Migration 不静默修改历史数据（M16）

- **Context**：schema 版本增多（knowledge/analysis/delta/event/replay/interpretation），
  直接改写规则文件会破坏可追溯性。
- **Decision**：migrate_knowledge.py 默认 dry-run（只打印变更摘要）；--write 只产出
  .migrated 副本，由人工确认后替换；迁移函数为纯函数且幂等（二次迁移 0 变更）。
- **Reason**：机器流程不得伪造「历史即已如此」；审计要求新旧可对照。
- **Tradeoff**：升级需要一步人工确认——刻意为之。

## ADR-049 · 多方法一致才启用强度类救应（M17）

- **Context**：v1 的「财为喜神」是单一 weighted 布尔映射——任务书禁止把喜神简化成万能布尔量。
- **Decision**：强度类谓词（wealth_favorable/wealth_unfavorable）收集全部可用旺衰读数
  （weighted/fuyi/dimension 得势），全部同向才启用；读数分歧 → 救应不激活并如实记录
  「口径分歧」，不裁决。两方向互斥。
- **Reason**：项目核心纪律「多方法并列、不裁决」在救应层的直接推广。
- **Tradeoff**：救应激活率下降（保守）——宁缺毋滥。

## ADR-050 · Audit Gates 是常驻质量门（M17）

- **Context**：规则/图/链路/状态纪律越来越多，靠人记不可靠。
- **Decision**：10 个确定性门（candidate 引用、classical→source、rescue 边、图完整性、
  evaluator↔JSON、未触发清单、异常触发、链路无断链、无 CONFIRMED、无机器 HUMAN）
  每次构建出 regression/audit-gates.json；coverage 段供 Workbench。
- **Reason**：断链/伪造在进入产出物之前被拦截。
- **Tradeoff**：G6（未触发）是审计列表不是失败门——探针覆盖有限属正常。

## ADR-051 · Graph/Rule Audit 只报告不调参（M18）

- **Context**：SPECIFIC_EXCEPTION 声明可能名不副实、救应可能过度激活、规则可能异常泛化。
- **Decision**：graph-audit（A1 specificity 佐证/A4 specific 链循环/A2 救应激活率 80 随机盘/
  B1 heuristic-only 规则）与 rule-audit（逐规则 replay 样本/relation 分布/异常泛化信号）
  只生成报告；发现信号进 REVIEW 清单，绝不据此自动调参迎合历史。
- **Reason**：任务书「禁止根据历史案例自动调参」。
- **Tradeoff**：信号需要人读——正是 Review Queue 的用途。

## ADR-052 · 一键质量门是发布前置条件（M18）

- **Context**：质量栈 14 步靠手工执行容易漏。
- **Decision**：quality_gate.py 顺序运行全部步骤并产出 quality-summary.json/md；
  回归步骤 exit 1 特判（无 BREAKING 的 REVIEW 级变化视为通过）；任一硬失败 → 退出码 1。
- **Reason**：发布前可重复、可审计的一键入口。
- **Tradeoff**：summary 本身不入 git 历史的语义（每次运行覆盖）——history 由各工件自带。

## ADR-053 · Release Metadata 全部来自真实运行（M18）

- **Context**：人工统计 commit/规则数/测试数容易出错且会过期。
- **Decision**：release_metadata.py 从 git、模块常量、真实 pytest 采集、工具工件读取，
  生成 release-metadata.json + release-report.md；无任何硬编码统计。
- **Reason**：「所有统计都来自真实数据」原则的发布维度落地。
- **Tradeoff**：生成需数秒（pytest 采集）——可接受。

## ADR-054 · 救应谓词五读数一致（M19）

- **Context**：v2 救应强度读数为 weighted/fuyi/得势 三路；得令/得地同样是 Engine 事实。
- **Decision**：读数扩展为五路（weighted/fuyi/得势/得令/得地），仍要求全部同向才启用；
  分歧 → 不激活并记录。EventContext 复用 chart.strength 全部输出，不重算。
- **Reason**：更少依赖单一 weighted verdict 映射（任务书：减少过粗映射）。
- **Tradeoff**：五路全同向更保守；激活率下降是刻意选择。

## ADR-055 · 质量门 17 步（M19）

- **Context**：coverage/dead-rule 分析、评估历史对比、release automation 就绪但未入质量门。
- **Decision**：质量门 14→17 步（+rule_coverage_audit/ai_eval_compare/
  release_automation_dryrun）；release_automation 默认 dry-run（不建 tag 不 push）。
- **Reason**：发布链路（metadata→notes→tag-prep）纳入一键验证。
- **Tradeoff**：总时长 ~26s——可接受。

## ADR-056 · Release Chain 的自指死锁与解法（M20）

- **Context**：quality gate 内的 pytest 会运行读取 quality-summary 的测试；
  gate 内的 release_automation 要求 summary ALL PASS——而 gate 尚未完成，
  形成「门必须先通过才能通过」的死锁（实测连续两轮 FAIL 才暴露）。
- **Decision**：
  - test_quality_gate 只验 summary 结构，不断言 allPass（freshness 由
    release_check P0 与发布流程负责）；
  - release_automation 增加 `--skip-gate-check`，quality_gate 内部调用时使用，
    外部用户运行仍强制要求 ALL PASS summary；
  - release_check P0 对 stale summary 只 WARN 不 FAIL（发布前重跑 gate）。
- **Reason**：门内自证与门外验证的职责分离。
- **Tradeoff**：release_check P0 可能放过 stale summary——由显式 WARN 与
  VERSIONING 文档约束。

## ADR-057 · 数据路径双模式与单一版本事实源（M20）

- **Context**：loader 用 `Path(__file__).parents[2]` 定位数据，安装到
  site-packages 后失效；pyproject version 0.1.0 与 `__version__` 0.2.0 并存
  （release automation 真实暴露的不一致）。
- **Decision**：`tianze/paths.py` 统一解析（TIANZE_DATA_DIR → repo knowledge/ →
  打包副本 tianze/_data/knowledge，manifest 哈希自检）；全部 loader 改延迟函数；
  pyproject `dynamic = ["version"]` 绑定 `tianze.__version__` 为唯一事实源。
- **Reason**：可安装性与版本一致性。
- **Tradeoff**：发布前必须运行 sync_package_data.py（已入 release_check P1 流程）。

## ADR-058 · 化神所忌逐干映射与从格所从受克（M22）

- **Context**：DTZ-48 有逐干所忌的完整引文（乙庚忌丙丁巳午/丙辛忌戊土/丁壬忌庚金/
  戊癸忌壬癸）与「克抑则万不能用」总纲——可诚实结构化为岁运受阻规则。
- **Decision**：TR-SP-05（化神所忌，逐干映射表直接译自引文；支藏干仅乙庚取巳午）与
  TR-SP-07（从格所从之神受克：从财忌比劫/从官杀忌食伤/从儿忌印）均输出两说观察，
  候选不因单条岁运引文改判。
- **Reason**：「还原非大忌、忌逆旺气」是引文原意，映射无引申。
- **Tradeoff**：岁运支藏干取用保守（只取引文点名的巳午）。

## ADR-059 · 五读数救应的保守性是正确行为（M22 实证）

- **Context**：100 随机盘实测五读数 mixed 占 66%——weighted 全局计分与得令纯月令
  在 15/60 例方向相反，为真实方法论分歧而非映射错误。
- **Decision**：维持「全部同向才激活」（激活率 ~8%）；分歧状态不激活并如实记录；
  反向误判（weighted 明确偏弱却激活喜神方向）由测试锁定为 0。
- **Reason**：R19 多方法并列不裁决在救应层的自然结果；宁缺毋滥。
- **Tradeoff**：救应覆盖面小——用 rule-audit/rescue-coverage 报告持续观察。

## ADR-060 · Tag 冻结与 dev 线版本纪律（M23）

- **Context**：v0.3.0 tag 指向 5821c84（RC 审计点），而 HEAD 已含 4+ 个后续 commit
  且同为 0.3.0——滚动工件（release/*、dist/）会被门流程不断刷新，若版本号不动，
  新代码会"冒充"已审计的 RC 状态；同时 release_automation 的 bump 规则对
  PEP 440 dev 版本会算错（0.4.0.dev0 minor → 0.5.0）。
- **Decision**：
  - tag v0.3.0 冻结（tagFrozen=true，永不移动）；RC 全套工件快照归档
    `release/rc/0.3.0/`（wheel/sdist/metadata/check/notes/tag-prep）；
  - 开发线进入 `__version__ = "0.4.0.dev0"`：滚动工件明确反映"未发布"状态；
  - release_automation 感知 dev 线：`.dev` 版本的下一个 tag 即
    `v{major}.{minor}.{patch}`（0.4.0.dev0 → v0.4.0，PEP 440 序 dev < 正式）；
  - READY_FOR_RELEASE.json 保留 RC 证据（gateEvidenceAtRc）并注明归档位置。
- **Reason**：发布工件的可追溯性——任何 wheel 都必须能对应到确定的 commit 与门状态。
- **Tradeoff**：开发期 release-check/metadata 显示 0.4.0.dev0 属预期（非回归）；
  正式 v0.4.0 发布时重跑全套门流程产出最终工件。
