# 07 · 借鉴矩阵（BORROWING MATRIX）

> Phase 0 产出 · 2026-09-30。策略词定义：`DEPEND`（直接依赖）· `ADAPT`（参考实现后改造移植，MIT 来源，保留声明）· `REWRITE`（学思想后自写，不搬代码）· `REFERENCE_ONLY`（仅研究，禁复制：AGPL/UNKNOWN）· `DATA_CROSSCHECK`（仅作数据交叉校验源，不直接入库）。

## 1. 模块级借鉴矩阵

| Tianze 模块 | Primary Reference | Secondary Reference | Strategy | 说明 |
|---|---|---|---|---|
| calendar/（历法·四柱·大运） | **lunar-python** | bazi-atlas（双轨道时间/DST/时区处理的问题定义）、Erfix（黄经直判思路）、jiwenxu（双时间线溯源） | **DEPEND + ADAPT** | lunar-python 依赖直用；适配器补双轨时间、DST、边界警告、TimeResolution 溯源 |
| calendar 验证 oracle | bazi-atlas crosscheck | Erfix（Meeus Ch.25 公式）、lunar-javascript | **ADAPT**（自写独立路径） | JDN `(JDN−2433191)%60` + 五时遁/五虎遁 + 黄经区间；日柱外部锚点三枚 |
| domain/（契约） | open-bazi-engine | jiwenxu（BirthTimeResolution） | **REWRITE** | frozen Pydantic + JSON Schema；OBE 形状自写实现（其无 License） |
| ganzhi/（干支表） | lunar-python 表 | bazi-atlas（表完备性断言法） | **DEPEND**（读库表）+ 自建缓存层 | 藏干/十神/纳音/长生直接读 lunar；加守恒律测试 |
| relation/（合冲刑害破三合三会） | bazi-atlas（表+不裁决原则） | Horosa（多重关系并存+拱）、jiwenxu（候选不化气+贪生忘克概念）、OBE（无序化教训） | **REWRITE** | 关系表为公版内容自录；扫描器无序化 + positions/adjacency/月令参与标注 |
| relation/roots（通根） | Horosa（禄刃/本气库/本气/长生/中气/余气六级 + 月支×2） | 传统禄刃长生表 | **REWRITE** | 事实层分级不赋分；分值由分析器参数提供 |
| analysis/strength | Horosa（权重框架） | OBE（四维划分）、Atlas（ratio+三口径）、jiwenxu（从格反条件/假生） | **REWRITE ×2 分析器** | Weighted + Dimensional 并行；参数全可配并标 PROJECT_HEURISTIC |
| analysis/pattern | jiwenxu（四档状态机+issues/supports） | Horosa（成败救应/待复核、比劫月令→建禄刃）、ruan（十格细分） | **ADAPT → REWRITE** | 《子平真诠》月令取用骨架（公有领域原文）；阈值全部显式参数 |
| analysis/climate（调候） | 《穷通宝鉴》原文（公有领域） | ruan shigan-lun.md（DATA_CROSSCHECK）、Horosa 120 速查（DATA_CROSSCHECK）、Atlas（"不假装完整"原则） | **SELF-compile（自录数据）** | 120 组结构化 + condition_grades 缺口标记；覆盖率测试锁 120/120 |
| rules/（知识库） | ruan（schema/质检三件套/drafts 工作流） | jiwenxu（rule-provenance 五级标签） | **REWRITE（schema）+ 自录数据** | condition 结构化 DSL；source 结构化；V1 不引入 CC BY-NC-SA 数据 |
| evidence/ | jiwenxu（EvidenceItem） | OBE（rationale）、Atlas（breakdown/conventionNote） | **REWRITE** | 结构化 + rule_id 溯源 + weight 公开 |
| schools/ | Horosa（8 派常驻对照） | jiwenxu（decision_policy 冲突保留）、Atlas（synthesis.agree） | **REWRITE**（V2 起） | 流派=纯解释器；schools[] 数组进 UnifiedResult |
| testing/ | **bazi-atlas**（整套验证哲学） | Horosa（选项矩阵审计/零回归锚）、jiwenxu（反例测试/校准双案例集）、ruan（质检三件套） | **ADOPT methodology** | 对拍+盖章+守恒律+守卫 fixture+R 断言+Windows CI |
| api/ | OBE（分层与 endpoint 形状） | jiwenxu（FastAPI 组织） | **REWRITE** | 输出 UnifiedResult JSON Schema |
| ai/（Prompt Builder） | OBE（prompt 分离+章节模板） | jiwenxu（LLM 只翻译+二道拦截+RAG 分级）、ruan（skill 边界纪律）、Horosa（单源快照） | **REWRITE** | LLM 零计算；provenance 分级注入；程序化校验 |

## 2. 文件级决策表（Tianze ← Repo/File/Function → Decision）

| Tianze 目标模块 | Repo | 参照 File | 参照函数/段 | Decision | 备注 |
|---|---|---|---|---|---|
| calendar/four_pillars | lunar-python | lunar_python/EightChar.py | getYear/Month/Day/Time | **DEPEND** | sect 开关透出为 R1 |
| calendar/late_zi | lunar-python | Lunar.py:146-177 | getDayInGanZhiExact2 | **DEPEND** + 补测试 | 上游无 setSect 直接测试，Tianze 补 |
| calendar/dayun | lunar-python | eightchar/Yun.py, DaYun.py | getYun/getDaYun | **DEPEND** | 起运两流派透出为 R7 |
| calendar/time_track | bazi-atlas | engine.mjs:149-176 | 双轨道组装 | **ADAPT**（REWRITE） | MIT，但重写以贴合 Pydantic 模型 |
| calendar/dst | bazi-atlas | engine.mjs:59-67,136-147 | CN_DST_RANGES + 跨零点回滚 | **ADAPT** | 官方 DST 表自录（公共事实） |
| calendar/eot | jiwenxu | time_resolution.py:71-141 | NOAA 均时差 + 双时间线 | **ADAPT** | MIT；公式为 NOAA 公共算法 |
| crosscheck/day_pillar | bazi-atlas | tools/test-crosscheck.mjs:33-159 | JDN 公式+锚点 | **ADAPT** | 锚点换为已验证三元组（1949-10-01=甲子 等） |
| crosscheck/solar_boundary | Erfix | astro.py:82-92 | Meeus Ch.25 黄经级数 | **ADAPT（重写 ~20 行）** | 只用黄经域；勿带 term_crossing_jd；勿用其日柱锚点 |
| ganzhi/hidden_stems | lunar-python | LunarUtil.ZHI_HIDE_GAN | — | **DEPEND** + 守恒律测试 | 与 Horosa/jiwenxu 表一致（通行子平表） |
| relation/tables | bazi-atlas | engine.mjs:596-616 | 关系表段 | **REWRITE（自录公版表）** | 内容为传统公版；参考其"锁死重合项"测试 |
| relation/scan | open-bazi-engine | analyzer.py:237-396 | 配对扫描 | **REWRITE** | 无序化（修其刑漏检 bug）；带 adjacency |
| relation/half_combination | jiwenxu | _constants.py:91-104, interactions.py:94-103 | 半合 8 组 | **REFERENCE** | 其无"中神"限定与传统冲突——Tianze 半合需含中神并标 R |
| strength/weighted | Horosa | baziWuxing.js:12-94 | DEFAULT_WEIGHTS/computeDimensions | **REFERENCE_ONLY**（AGPL）+ REWRITE | 权重数值是事实常量可记录；代码不抄，参数另定默认值并标 heuristic |
| strength/dimensional | open-bazi-engine | analyzer.py:399-481 | _assess_strength 四维 | **REWRITE** | 思想：得令/得地/得生/得助分列输出 |
| strength/three_measure | bazi-atlas | engine.mjs:784-879 | computeFavorableElement ratio | **ADAPT** | ratio+breakdown 逐字可复核模式 |
| strength/cong_ge | jiwenxu | yongshen.py:103-178 | _detect_cong_ge 反条件 | **ADAPT** | "有明根/暗根即不从"底线条件 |
| pattern/derive | jiwenxu | pattern.py:15-60 | determine_pattern | **ADAPT → REWRITE** | 框架《子平真诠》；修其月令冲合未处理问题 |
| pattern/validate | jiwenxu | pattern.py:63-313 | validate_pattern 四档 | **ADAPT** | issues/supports 双列表形态 |
| pattern/chengbai | Horosa | baziGejuYongShen.js:262-348 | GE_JI/救应/四态 | **REFERENCE_ONLY + REWRITE** | "败中复成/待复核"形态 |
| climate/data | 穷通宝鉴（ruan shigan-lun.md 仅校验） | kb/03-classics/shigan-lun.md | 十干×十二月 | **SELF-compile + DATA_CROSSCHECK** | 原文公有领域自录；CC 数据不入库只对答案 |
| rules/schema | ruan | kb/04-rules-db/rules-template.json | 字段设计 | **ADAPT** | + source 结构化 + condition DSL 化 |
| rules/QA | ruan | tools/audit_hit_distribution.js 等 | 质检三件套 | **ADAPT（REWRITE）** | MIT 代码可移植但与 Tianze 栈不同，重写更干净 |
| evidence | jiwenxu | liunian/signal.py:15-39 | EvidenceItem | **ADAPT** | 全层通用化（不限流年） |
| schools/output | Horosa | baziGejuYongShen.js:358-365 | schools 数组 | **REFERENCE_ONLY + REWRITE** | 形态；实现自写 |
| ai/llm_boundary | jiwenxu | llm_review.py:366-371,669-699 | 硬约束+二道拦截 | **ADAPT** | schema 校验替代其正则拦截 |
| ai/rag_grading | jiwenxu | rag.py:44-54 | provenance 分级注入 | **ADAPT** | 防止 heuristic 被说成古籍 |
| testing/invariants | bazi-atlas | test-web-engine.mjs:661-670 | 四类断言法 | **ADOPT** | 含外部锚点（Unicode/历书） |
| testing/option_matrix | Horosa | baziOptionMatrixAudit 等 | 选项接线审计 | **ADOPT methodology** | 防"死选项"（OBE zi_hour_rule 教训） |
| testing/negative | jiwenxu | test_rule_regressions.py | 反例断言 | **ADOPT** | "不允许引擎说什么" |

## 3. 明确不borrow清单

1. Horosa 任何源码/数据文件表达（AGPL）——只允许本报告级别的思想转述。
2. open-bazi-engine 任何文件（UNKNOWN）。
3. Erfix 的 `_DAY_ANCHOR_JDN=2433180`、`term_crossing_jd`、大运起运、旺衰——日柱域整体验证无效。
4. jiwenxu 的 `_MONTH_PATTERN_BASE` 死表（内容有错）、调候 11 条副本、从旺死分支、theme_weight 等"注释≠实现"段落。
5. ruan 的单体构建制（212KB 模板内嵌 JS）、水印/防盗用机制、营销叙事；其 CC 数据 V1 默认不引入。
6. Atlas 的手工 UMD 双胞胎与单文件巨石（模式不可持续）。
7. lunar-python 的宜忌 hex 数据、佛历道历九星（超出 Tianze 范围）。
