# Tianze 研究进度（research/progress.md）

> 长任务纪律文件。若任务中断，恢复后必须先读本文件再继续。

- 状态：**Phase 0 ✅；M0-M8.5 ✅；M8.6 ✅（252ebef）；M9 ✅（ff3dcfc）。266 测试全绿。**

## M8.6/M9 记录（2026-10-01）

### M8.6（252ebef）
- 从格 LIKELY 349 例审计：SOURCE_SUPPORTS 7 / SOURCE_DIFFERENT_PATTERN 8 / SOURCE_SILENT 118 / SOURCE_UNRESOLVED 216
- 阴阳干从格：知识库 73 条命中（滴天髓/子平粹言），证据不足实现差异 → UNRESOLVED
- 化气证据：100 条命中（DTZ 滴天髓补注）；专旺证据：47 条命中
- PopulationStats：totalCases 1147 / parseable 1045 / engineEligible 1045 / unresolved 102

### M9 SDK（ff3dcfc）
- `tianze.analyze(SimplifiedBirthInfo, AnalysisOptions) → SimplifiedResult`
- TianzeError 统一错误模型（INVALID_BIRTH_INFO/UNSUPPORTED_CONVENTION/…）
- Partial Result：未知时辰不 crash；ANALYSIS_SCHEMA_VERSION=1.0.0
- Deterministic：同输入+同版本 → 同 JSON（测试锁定）
- test_sdk.py 13 项（determinism/partial/error/options/version/canonical cases）
- docs/sdk/01-04 四份文档

## 下一步
- 从格 LIKELY 349 例人工逐条核验（review/cong-likely-cases.csv）
- 化气/专旺知识库证据逐条核对扫描件 → CLASSICAL_EXPLICIT 升级
- M10: FastAPI 封装 analyze() / Web UI**Phase 0 ✅；M0-M5 ✅；M4.2 ✅；K0/K1/M6 ✅；M6.1 ✅（ea29bb3/b9c4268）；M7 ✅（aa5144f/175823d）。232 测试全绿。**

## M6.1/M7 记录（2026-10-01）

### 诚实更正（M6.1 首务）
M6 报告的"人工复核 curation"实为 AI 完成 → 182 条全部重标 MACHINE_CURATED+ai_curation（ADR-029）；Schema 校验器拒绝 pipeline 署名的 HUMAN_*；HUMAN_VERIFIED=0 是诚实边界。

### M6.1
- VerificationStatus 六级 + AccuracyMatrix 四维（traceability/text/interpretation/engine 分别建模）+ ConflictKind 六类 + schema version（KNOWLEDGE=1.1.0）。
- audit_verification.py：验证矩阵 + Golden Set 43 条（十日主/四季/四库/冲突/OCR/条件规则）+ review/knowledge-review.csv 182 行（冲突>OCR>引文>条件>普通，不自动填 humanVerified）。
- A 级四要件升级规则（一手核对/OCR 核实/解释核实/页码核实）；机器上限 B。

### M7
- normalize_cases.py：748 块+400 索引行 → **1147 例 0 解析失败**；102 例 UNRESOLVED；60 组候选重复只登记；cases-manifest（输入 hash/pipeline/schema 版本）。
- derive_case_analysis.py：1045 例引擎派生（与原书分析严格分离）；byRule/byDayMaster/byMonthBranch/byBook 双向索引；EXPLICITLY_CITED 17 候选 95 处 / ENGINE_TRIGGERED 不冒充古法。
- compare_cases.py：426 机械化对比（420 一致/24 差异），721 例 unresolved 待人工，不裁决。
- validate_cases.py：ID 唯一/双分析分离/事件分层/无伪造 HUMAN_*。
- 命例引用正则含中文天干的修正（3 轮调试）；Case ID 跨文件冲突与规则同因（甲木分部一）。

## 下一步
真人核验队列（Golden 43 条优先）→ B→A 升级；命例语义级对比人工化；M8 API。

## K0/K1/M6 记录（2026-10-01）

- K0：`tianze/knowledge/models.py`（SourceKind 五级/Quote(OCR 照录+correctedText)/Commentary/RuleCandidate/ExecutableRule(conditions+effects+exceptions+normalizationNotes+conflictNote)/RuleConflict/CaseReference/QualityGrade A-D/KnowledgeStats）；KnowledgeSource/ProvenanceRef 上移 domain（避免循环导入）。
- K1：normalize_knowledge.py 解析 62 文件 **556 条规则 0 失败**；35 处跨文件 ID 冲突（甲乙木 vs 十干逐月复用 QBT-甲-01~13）加 @n 后缀登记；validate_knowledge.py（重复 ID/缺失来源/无效引用/CLASSICAL_EXPLICIT 无引文/覆盖/冲突 → stats.json，失败退出码 1）；审计报告 docs/knowledge/02。
- raw/ 只读不入库（ADR-026）：MANIFEST.sha256 锚定两个 zip；normalized/rules 入库可重建。
- M6：draft 启发式 103/120 → **人工复核 curation 表（120 格全锚定）** → 182 条 ExecutableRule（TH-{候选}-{月支} 格限定 ID）→ TiaoHouAnalyzer（desired/present 分离、条件休眠留痕、例外命中、UNRESOLVED 诚实、无吉凶字段）。冲突 3 组登记（甲未/己申/己未）。
- 调试教训：Position 是 Literal 别名（无 .value）；loader 产出 Pydantic 对象需属性访问；builder 新旧键并存导致 extra_forbidden——均被测试当场拦截。

## 下一步

- 命例结构化（CaseReference，530 则+400 组索引）作规则复核参照。
- 子平真诠 OCR 完成后：M5 格局规则 provenance 升级 CLASSICAL_EXPLICIT 的逐条核校。
- OCR 人工核对推进（B→A）；孙正治/赵嘉宁今译层与徐注层完全分层。
- M7：规则库扩展（格局/旺衰域知识规则）+ API。

## M4.2-M5 记录（2026-10-01）

### M4.2（1d2de8a weighted / 07f6f6c fuyi）
- weighted-v1：9 参数全参数化（WeightedStrengthParams，出处逐条标注 PROJECT_REFERENCE/ENGINEERING_HEURISTIC）；逐字单位计分 + 贡献明细可复现总分；**防重复计分（ADR-022）**：根/得令不设独立计分项并有守卫测试。
- 修复：日主自身天干误入计分单位（测试抓出，amend 修正）。
- fuyi-v1：派生特征计票 + 九条首中即停级联；UNCERTAIN（证据对冲不强判）；数学发现：得令⟹必有月令根（"得令+无根"不可达），R21-4 相应改为可达条件。
- agreement R22：UNCERTAIN 弃权；HIGH/PARTIAL/DISPUTED 三态。

### M5（c2ecb16）
- 取格 R23/R24：禄刃优先（禄位表 + 阳干帝旺，阴干无刃）→ 藏干透干优先（比劫不立格）→ 皆不透取本气；多候选并存（中余同透）；月劫无正格 → note。
- 评估 R25：supports/damages/rescues/conflicts 四组证据 + status（成立/有瑕/受损/破格/待定）；建禄/阳刃 v1 诚实输出"待定"；provenance 全部 PROJECT_REFERENCE，无古籍伪造。
- MonthCommand 预留 ruling_stem/jie_qi_depth_days（ADR-021）。

### 跨引擎差分（补欠账）
- **bazi-atlas 实跑对拍 5/5 通过**（node v24 + upstream clone + lunar-javascript@1.7.7 --no-save）：plan_2003/basic_1986/female_1983/晚子时 sect2/立春 2024 边界，四柱全部一致。
- 桥接：tools/atlas_differential.mjs（仅调用 atlas 公开入口 computeBazi）；测试环境缺失时 skip 留痕。

### 新文档
docs/STRENGTH.md、docs/PATTERN.md、CONVENTIONS R20-R25、DECISIONS ADR-021~025、SOURCES/ARCHITECTURE 同步。

## 下一步

- M6：调候 120 组（公有领域原文自录 + 交叉校验）。
- M4.3（可选）：weighted 参数标定实验（development/holdout）；格局规则古籍核校升级 provenance。
- 从格/专旺条件化接入（需 strength verdict 稳定后的阈值口径）。

---

# 以下为 M3-M4 记录（存档）

## M3-M4 记录（2026-10-01）

### M3（提交 29c078c）
- R15 通根：`analysis/roots.py`，10 干×12 支穷举不变式；定性深度 strong/medium/weak（ADR-016，零权重）；月令通根/日主标记 + 证据语句。
- R18 透干：`analysis/visibility.py`，来源支/藏干类型/距离/月令相关/日主相关（dayMasterRelated=藏干即日主）。
- R17 月令：`analysis/month_command.py`，**按月支本气五行**判旺相休囚死（修正了最初按季节查表的口径错误——丑月壬水应为"死/囚域"而非季节表"旺"；OBE 同口径）；四库月土旺自然成立；得令严格=旺；藏干优先级含透出标记；120 组合用测试内独立生克环交叉验证。
- R16 五行统计：`analysis/element_counts.py`，visible(8 字)/hidden(全部藏干) 两独立视图 + missing，零加权。

### M4（提交 6038c4a）
- `analysis/strength/`：StrengthFacts（与 BaziChart 解耦，ADR-020）+ StrengthAnalyzer Protocol + run_strength 注册表；agreement 仅在 ≥2 个带 verdict 方法时输出（HIGH/DISPUTED），单方法缺席+note 说明（ADR-019）。
- M4.1 `methods/dimensional.py`：得令/得地/得势三维定性（result+reason，零评分）；得势 = 年月时干印比 ≥2（DE_SHI_THRESHOLD 公开常量，标 PROJECT_HEURISTIC）。
- 修复 run_strength 对去重 verdict 集合计数的逻辑 bug（FakeA/FakeB 双方法测试抓出）。
- 教训守卫：2003 盘年干癸对癸日主是**比肩**——"别柱同干比肩必须计入"（jiwenxu 同款教训）成为 fixture 级断言。

### 测试
151 全绿（新增 33 项：通根穷举/透干四位置/月令 120 组合/五行金标/旺衰阈值边界/JSON 形状/agreement 语义）。

### 发现与修正（Coding Night 累计）
- oracle 锚点自检抓到 jdn 漏减 32045。
- 2003-08-18 实盘 癸未 庚申 癸亥 己未（任务书示意图非实盘）。
- 旺相休囚死口径修正（季节→月支本气）。
- 三次"金标错误、引擎正确"案例：丑未=冲+刑并存、藏干总数 11、别柱比肩计入——测试侧期望值错误被引擎+守恒律反驳，最终以传统口径为准复核。

## 下一步

- M4.2：weighted / fuyi 计分制分析器（权重全部入 params 并标 PROJECT_HEURISTIC）。
- M5：格局（月令透干定格 + 成败状态机，ADR 参照 jiwenxu 四档 + Horosa 待复核三态）。
- M6：调候 120 组自录（公有领域原文）。
- 可选：GitHub 远程仓库创建 + push（本地 git 已就绪，3 个里程碑提交）。

---

# 以下为 Coding Night M0-M2 记录（存档）

## Coding Night 记录（M0-M2）

1. M0：venv + lunar-python 1.4.8 / pydantic 2.13.5 / pytest 9.1.1；pyproject（requires-python>=3.12）；CI（ubuntu/windows × 3.12/3.13）；`docs/CONVENTIONS.md`（R1-R14）+ SOURCES + ERRATA。
2. M1：`tianze/domain/models.py`（Pydantic camelCase 契约）、`tianze/ganzhi/tables.py`（十神推导，测试与 lunar 100 条表全矩阵对账）、`tianze/calendar/`（双轨道 R3 + 中国 DST R12 + 节气边界警告 R4 + 节气表拼音/中文归一化 ERRATA-07）、`tianze/pipeline.py`（build_chart）。
3. **crosscheck oracle**（`tests/crosscheck/oracle.py`）：JDN `(JDN-2433191)%60` 日柱（三枚外部锚点自检）+ 五鼠遁/五虎遁 + Meeus Ch.25 黄经定年/月柱（精度承诺：距交节 >12 分钟；交界窗口样本跳过留痕）。**oracle 自检当场抓到 jdn 漏减 32045 的 bug**——守恒律/锚点自检的价值实证。
4. `tools/stamp_expected.py`：40 个 fixture 全部由 oracle 盖章（含立春 2024/2025、小暑 2025 ±25 分钟夹逼、冬至中气反例、晚子时 sect1/2 成对、DST 1988 跨零点、乌鲁木齐/纽约/伦敦/印度/洛杉矶、闰日、未知时辰、十日主覆盖）。
5. M2：`tianze/relation/`（公版关系表 + 扫描器：多重关系并存 R9、半合需中神 R10、合化只报候选 R13、天干四冲 R14；三合/三会/三刑按传统顺序输出）。
6. 测试 118 全绿：fixture 回归 40 + 差分对拍 40+50+锚点 + 十神矩阵 100 断言 + 藏干对账 + 关系完备性/守恒律/金测盘/反例（OBE 刑漏检守卫）。

### Coding Night 发现

- 任务书示例盘（2003-08-18 14:30）实际为 **癸未 庚申 癸亥 己未**（任务书 web 示意图中的"甲寅日"仅为示意）；地支未申亥未 → 唯一关系 = 申亥害（月-日贴邻）。
- jdn 公式漏 -32045 常数 → 被锚点自检拦截（已修）。
- 测试期口径错误 3 处（丑未=冲+刑部分对并存；三合/三会成员须按传统序 申子辰/寅卯辰；亥子丑的库支丑排序位置）——均属"期望值写错"，引擎行为经核对为正确。
- 未解决：Windows 下 CI 未实测（本地仅单机跑通）；`docs/ERRATA-05` DST 表待逐条核对。

---

# 以下为 Phase 0 研究记录（存档）



## 已完成

1. 环境检查：`C:\Project\tianze` 起始为空目录；git 2.55 可用；GitHub 连通。
2. 脚手架：`research/upstream/`、`research/notes/`、`research/matrices/`、`docs/research/`。
3. 克隆 7 个上游仓库（浅克隆，全程只读，git status 干净）：lunar-python / bazi-atlas / open-bazi-engine / ruan-bazi-engine（首次 SSL 失败重试成功）/ jiwenxu-bazi-engine / erfix-bazi-engine / horosa（5385 文件）。
4. 7 个研究代理并行精读，产出 `research/notes/{lunar,bazi-atlas,open-bazi-engine,ruan-bazi-engine,jiwenxu-bazi-engine,erfix-bazi-engine,horosa}.md`（全部带 文件:行号 溯源；Horosa 19 章、jiwenxu 16 章）。
5. 主会话交叉验证（防笔记失真）：
   - OBE 全库 find+grep 无 LICENSE → UNKNOWN_LICENSE 确认；
   - lunar-python `EightChar.py:28` 默认 sect=2、`:44 setSect` 确认；
   - Horosa baziWuxing 权重表逐项确认（100/60/30、×1.5、40/30/−10/−20/−30、通根 30/25/20/15/10/6、0.55/0.45）；
   - jiwenxu `yongshen.py:252` 阈值"≥3.5=强, ≤1.5=弱"确认；
   - ruan rules.json 恰 1000 条确认；atlas test-fixtures.json 35 case 确认；
   - **Erfix 日柱锚点 bug 实跑复现**：`engine.py:22 _DAY_ANCHOR_JDN=2433180`（真实 JDN(1949-10-01)=2433191），2003-08-18 Erfix 排甲戌 vs lunar-python 癸亥，系统性 +11 位；年柱/月柱域两边一致 → Erfix 仅可作年/月柱验证源。
   - lunar-python 实测：1949-10-01=甲子、2000-01-01=戊午、2024-01-01=甲子、2003-08-18=癸亥日（三枚外部锚点互证成立）。
6. 九份正式文档全部写入 `docs/research/`：
   - 01-UPSTREAM-PROJECTS.md（7 项目总览与评价）
   - 02-FEATURE-MATRIX.md（30 功能 × 7 项目矩阵 + 5 条关键观察）
   - 03-ALGORITHM-COMPARISON.md（旺衰六实现/五行力量/通根/月令/格局/用神/调候 + 神秘常数总登记表）
   - 04-LICENSE-AUDIT.md（全项目许可审计 + 组合风险 + SOURCES 种子）
   - 05-TIANZE-ARCHITECTURE.md（六问六答 + 12 层 + Mermaid 数据流 + 仓库结构 + 六原则 + 验证网九要素 + L0-L4 映射）
   - 06-TIANZE-DOMAIN-MODEL.md（领域类型详设 + 7 条不变式 + 与上游差异表）
   - 07-BORROWING-MATRIX.md（模块级 + 文件级决策表 + 不borrow清单）
   - 08-DECISION-LOG.md（ADR-001~015）
   - 09-V1-ROADMAP.md（M0-M9 施工顺序 + 与原 M1 20 项映射）
7. `research/matrices/README.md` 指路文件（矩阵唯一权威版在 docs/research/，防双份漂移）。

## 重要发现（TOP 10）

1. **历法层不要写**：lunar-python（MIT）覆盖四柱/节气到秒/晚子时双派/大运；Atlas、OBE、Horosa 三家也全部复用 lunar 系。Tianze 只写适配器。
2. **旺衰无共识**：六家六套权重六套阈值，全部 PROJECT_HEURISTIC（03 文档总登记表）；唯一交集是定性维度（得令/得地/得势）。→ ADR-003 多分析器 + agreement。
3. **验证哲学可以直接继承**：Atlas 四张测试网（独立路径对拍 85/85、expected 盖章、守恒律、守卫 fixture）+ jiwenxu 反例测试 + Horosa 选项矩阵审计。
4. **Erfix 只能当半个 oracle**：Meeus Ch.25 节气公式可用（偏早 1.3-5.9 min），但日柱锚点 +11 天实锤——日柱/时柱/大运域禁用其任何代码。
5. **Horosa 证明多流派真算可行**：8 派独立纯函数、事实层/解释层缓存键分离、调候"忌恒空不臆造"——AGPL 所以只抄思想。
6. **知识库方法论比数据值钱**：ruan 的断语 schema + 质检三件套（命中率/矛盾/重复）+ drafts 工作流；其 CC BY-NC-SA 数据 V1 不引入（许可洁净化，ADR-008）。
7. **治理模式**（jiwenxu，MIT 可移植）：rule-provenance 五级标签、EvidenceItem、decision_policy 冲突保留不翻转、LLM 只翻译+二道拦截、RAG 分级注入、development/holdout 校准。
8. **反面教材集**：OBE 无 LICENSE + 6 处真 bug（生我/我生反转、日支反查歧义、刑漏检）；jiwenxu README 与实现多处脱节；Erfix 21 个自引用测试全绿放行三个重大 bug → "真值必须来自外部"。
9. **调候数据格局**：ruan KB 精编最全（但 CC）、Horosa 120 速查、jiwenxu 仅 9%、Atlas 诚实拒绝 → Tianze 从公有领域原文自录 120 组（ADR-013）。
10. **Horosa 的 lunar-javascript 底座是 MIT**——Tianze 未来 TS/浏览器层与第三差分 oracle 可直接依赖原项目，无需碰 Horosa。

## 存在疑问（带入 M1+）

- lunar-python sect=2 时时柱日干仍用次日日干（Lunar.py:177）无注释——Tianze 需自行论证口径并在 R 表固化。
- ruan rules.json 内嵌水印句未定位；若未来引入其数据需逐条人工排查。
- Atlas methodology/corrections 仅站外；其 23 点档时柱基准（两派都用次日日干）是否主流口径待考。
- jiwenxu JDN offset 注释自相矛盾（2000-01-01=戊午 vs 1900-01-01=甲戌）——Tianze 移植前用 1900-2100 万年历全域核对。
- Horosa《八字大全》具体书目待外部考证。

## 下一步（明天 Coding Night）

按 `docs/research/09-V1-ROADMAP.md` 执行 M0（脚手架+R 约定表）→ M1（排盘+crosscheck+fixtures）→ M2（关系引擎）。开工前先读本文件与 08-DECISION-LOG.md。
