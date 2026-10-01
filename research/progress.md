# Tianze 研究进度（research/progress.md）

> 长任务纪律文件。若任务中断，恢复后必须先读本文件再继续。

- 状态：**Phase 0 ✅；M0-M2 ✅（10f98a8）；M3 ✅（29c078c）；M4 ✅（6038c4a）。151 测试全绿。**

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
