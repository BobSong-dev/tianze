# 08 · 架构决策日志（DECISION LOG / ADR）

> Phase 0 产出 · 2026-09-30。每条 ADR：Context → Options → Decision → Reason → Tradeoff。状态均为 `Accepted (Phase 0)`；推翻时在文末追加 Supersede 记录，不删原文。

---

## ADR-001 · Tianze Core 语言 = Python 3.12+（Node 仅作差分 oracle，Java 为未来业务后端）

- **Context**：历法底座、算法参考、治理模式分散在 Python（lunar-python/jiwenxu/OBE）与 JS（lunar-javascript/Atlas/Horosa/ruan）之间；作者主栈为 Java；Tianze 需要最大复用现有开源成果。
- **Options**：A. Python Core；B. TypeScript Core；C. Java Core。
- **Decision**：**A**。B 作为后置的浏览器层选项（用绑定/生成而非手工双实现）；C 通过 HTTP/RPC 调 Python Core，不承载命理算法。
- **Reason**：算法最全的两个参考（jiwenxu、OBE）为 Python；lunar-python 是唯一"天文节气+双流派+大运+零依赖+活跃维护"全满足的库；FastAPI/Pydantic/pytest 生态成熟。
- **Tradeoff**：放弃浏览器原生执行（Atlas/Horosa 的强项）；将来需要时用 WASM/生成方式补，不维护第二份手写引擎（Atlas 人肉 UMD 双胞胎不可持续）。

## ADR-002 · 历法层直接依赖 lunar-python；不自己实现任何天文/历法算法

- **Context**：四柱/节气/农历是"基础设施"而非 Tianze 竞争力；六家中三家（Atlas/OBE/Horosa）也直接复用 lunar 系。
- **Decision**：`pip install lunar_python`（MIT）；Tianze 只写适配器（口径开关、双轨时间、TimeResolution 溯源、边界警告）。
- **Reason**：1~9999 年实测可用、节气到秒、晚子时 sect 双派、DaYun 完整；自写会重蹈 Erfix 覆辙（其日柱锚点 +11 天、二分器全坏）。
- **Tradeoff**：承担上游风险 → 缓解：锁定版本 + 上游缺陷清单 + 边界 fixture 回归（闰月干支 1.4.7 曾修 bug）+ 两条独立 oracle（crosscheck 与 Meeus 黄经域）。

## ADR-003 · 旺衰不做单一算法：`StrengthAnalyzer` 抽象 + ≥2 实现 + agreement 字段

- **Context**：六家六套权重六套阈值，全部 PROJECT_HEURISTIC（03 文档 §1）；任务明令"不要立刻决定旺衰算法"。
- **Decision**：定义 `StrengthAnalyzer` 协议；V1 交付 `WeightedStrengthAnalyzer`（透明计票，参数可配）与 `DimensionStrengthAnalyzer`（得令/得地/得生/得助定性四维）；`StrengthReport` 输出各 analyzer 结果 + `agreement: HIGH/MEDIUM/LOW/DISPUTED` + 事实维度描述。
- **Reason**：把"争议"作为一等公民输出，而非偷偷选边；atlas/Horosa 已证明"双派并列"可行。
- **Tradeoff**：输出更冗长；UI 需要呈现多结论。收益是诚实性与可演进性（新算法加入不需要改下游）。

## ADR-004 · 流派 = 同一事实的纯解释器，常驻并列输出（不切换替换）

- **Context**：Horosa 实证 8 派真算可行（Q1-Q4）；ruan/jiwenxu 用单一答案+优先级。
- **Decision**：`SchoolResult{school, verdict, xi, ji, note, provenance}` 数组进 `UnifiedResult`；流派参数不进事实缓存键；V1 只实现扶抑/格局/调候三派（病药/通关/盲派/纳音 V2）。
- **Reason**：符合"不假设命理存在唯一算法"的项目原则；Horosa 的缓存键设计使切流派零成本。
- **Tradeoff**：初版无"最终答案"字段，用户可能不适应 → 用 note 与 UI 高亮引导（Horosa 置顶主用派模式）。

## ADR-005 · LLM 永不参与确定性计算；只做已算事实的翻译

- **Context**：jiwenxu（硬约束+二道拦截）、ruan（"绝不用 LLM 心算"）、OBE（prompt 分离）、Horosa（单源快照）四家一致；任务原则"LLM 不参与确定性计算"。
- **Decision**：Prompt Builder 只消费 UnifiedResult；LLM 输出做程序化校验（禁止新增结论/反转方向/引用不存在证据）；注入内容按 provenance 分级标注（古籍摘要/工程启发式/案例观察）。
- **Reason**：幻觉防控的唯一有效位置是引擎侧事实完整 + 侧向校验，不是提示词措辞。
- **Tradeoff**：解读的"生动性"受限——接受，Tianze 定位是引擎不是占卜师。

## ADR-006 · Evidence 是一等公民：无证据的结论不许出 API

- **Context**：OBE rationale 纯字符串（不可机检）；jiwenxu EvidenceItem 最完整但只在流年层；Atlas breakdown 证明"逐字可复核"可行。
- **Decision**：`EvidenceItem{rule_id, statement, positions, effect, weight?, source}` 全层通用；`UnifiedResult` 顶层聚合 evidence；测试断言每个 verdict 至少 1 条 evidence。
- **Reason**：项目原则"算法必须可解释、规则必须可追踪"的落点。
- **Tradeoff**：数据体积变大；可按 layer 过滤输出。

## ADR-007 · 约定编号化（R 表）+ 仓内 methodology/errata

- **Context**：Atlas R1-R39 与代码同址是最佳实践，但其 methodology/corrections 只在站外（仓内不可复现）——研究期发现的矛盾。
- **Decision**：`docs/CONVENTIONS.md` 承载 R1…Rn（每条流派选择：编号、内容、分歧、默认值、涉及的 fixture）；`docs/ERRATA.md` 记录勘误；测试直接断言 R 条目。
- **Reason**：约定必须是可执行文档。
- **Tradeoff**：维护成本；用"改 R 必须同时改 fixture+测试"的纪律约束。

## ADR-008 · 许可策略：代码 MIT；数据分层（公有领域自录 + 可选 CC 层物理隔离）

- **Context**：ruan 数据 CC BY-NC-SA（SA 传染）；Horosa AGPL；OBE 无许可；古籍原文公有领域。
- **Decision**：Tianze 代码 MIT；`rules/classical/`（自录自公有领域古籍）开放许可；V1 **不引入** ruan CC 数据；若未来引入，置于 `rules/derived/` 独立目录、整层 CC BY-NC-SA 4.0、逐条保留 source 并署名，与 classical 层不混写。SourceReference.type 中的 `project_heuristic` 不得冒充 classic。
- **Reason**：保持 Tianze 核心数据最大开放；义务可机器执行（source 字段即许可载体）。
- **Tradeoff**：调候 120 组需自己录（工作量 ~数天）而非直接搬 ruan 精编——换取许可洁净。

## ADR-009 · 验证网 = Atlas 架构 + 三处补强

- **Context**：Atlas 四张测试网实跑 85/85 绿；但 methodology 站外、Windows CI 缺失、与对拍器共享节气表单点信任。
- **Decision**：九要素（05 文档 §5）：R 表 / 双路径对拍 / 35+ 边界 fixture / 盖章 expected / 守恒律 / 上游缺陷清单 / conventions 随输出 / Linux+Windows CI / 仓内 ERRATA。节气第三源抽检（lunar-javascript oracle）作为后置项。
- **Reason**：Erfix 证明"没有外部真值的测试 = 全绿的自欺"。
- **Tradeoff**：测试代码量约占 V1 三分之一——这是设计意图，不是浪费。

## ADR-010 · 时间口径：双轨道 + 显式时区 + 可选真太阳时

- **Context**：Atlas 双轨道（绝对时刻判年月柱 / 出生地时间判日时柱）解决了海外跨日与节气换月的互斥；jiwenxu 双时间线溯源最完整；lunar-python 默认东八区。
- **Decision**：R3 = 年/月柱按 birth_instant_utc；日/时柱按 pillar_dt；tz 必须显式（缺省 +8 并入 meta）；time_alg ∈ clock/true_solar/mean_solar（V1 默认 clock，真太阳时 M3）；所有校正明细入 TimeResolution。
- **Reason**：口径选择是流派问题，实现必须支持口径而不是把口径埋进实现。
- **Tradeoff**：适配器复杂度高于"一个 datetime 进、四柱出"的朴素 API。

## ADR-011 · 关系层：多重关系并存、候选不化气、半合需中神

- **Context**：Atlas/Horosa 并存不裁决；jiwenxu "候选不化气"写进反例测试；jiwenxu 半合无中神限定与传统冲突；OBE 有序对漏检 bug。
- **Decision**：关系表公版自录；扫描无序化；输出 `Interaction` 全量（合/冲/刑/害/破可同对并存）；合只给 `transform_candidate`；`半合` 仅当中神（子午卯酉）参与时成立并标注 [R]；V1 不判化气成立与否（留给分析层）。
- **Reason**：保守事实层 + 开放解释层。
- **Tradeoff**：V1 的合冲信息对普通用户显得"没有结论"——用 schools/分析层补足。

## ADR-012 · Source Provenance：三级模型（Tianze Rule → Reference Project → Classical Source）

- **Context**：任务要求每个重要模块可追踪；ruan 把 source 写进许可义务是最强实践。
- **Decision**：`SourceReference{type: classic/open_source/project_heuristic/tianze_original, ...}`；rules/ 每条必带；模块文档头部声明借鉴矩阵条目（07 文档）。
- **Reason**：溯源同时服务许可合规、可信度与调试。
- **Tradeoff**：数据录入稍慢。

## ADR-013 · 调候数据：从《穷通宝鉴》原文自录 120 组，禁缺省=无忧

- **Context**：jiwenxu 11 条且缺省误当"无忧"；Horosa 120 速查但自认非条件分级版；ruan KB 最全但 CC BY-NC-SA；Atlas 拒绝假装完整。
- **Decision**：自录 10 日主×12 月令 = 120 组 `{priority_stems, condition_grades?, source}`；`coverage` 字段三值（full/quick_lookup/missing）；missing 时输出为空并注明；用 ruan 精编层与 Horosa 表做 DATA_CROSSCHECK。
- **Reason**：数据驱动（原计划 §12）；许可洁净；诚实分级。
- **Tradeoff**：初录工作量集中在一个里程碑（M6）。

## ADR-014 · 未知时辰：缺席而非猜测

- **Context**：Atlas unknownTime → hour:null + 三柱盘；ruan 拒绝心算排盘；OBE 无处理。
- **Decision**：`time_known=false` 时 hour 柱为 null、大运输出区间（精确起运不可得）、hour 相关分析标注缺位；不提供"默认正午"静默代算。
- **Reason**：宁缺毋假。
- **Tradeoff**：功能降级——显式降级优于错误结论。

## ADR-015 · Phase 0 遗留 → M1 优先事项

1. 先写 `docs/CONVENTIONS.md`（R1-R12 起步）再写代码（约定先于实现）。
2. crosscheck 与主引擎同里程碑交付（M1），不允许"以后补"。
3. `research/upstream/` 保持只读；Tianze 仓库不 vendor 任何上游源码。
