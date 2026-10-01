# 05 · Tianze 总体架构（TIANZE ARCHITECTURE）

> Phase 0 最终产出 · 2026-09-30。基于 7 个上游项目的实证研究（见 01-04 文档与 research/notes/）。
> 本文回答任务的"十六、Architecture Recommendation"六问，并给出可直接施工的分层架构。

---

## 0. Architecture Recommendation（六问六答）

### Q1 · Tianze Core 用哪种语言？

**推荐：Python 3.12+ 作为 Core，配一个 Node 侧的差分验证脚本（可后置）。**

| 选项 | 评价 |
|---|---|
| **Python（推荐）** | lunar-python（MIT，历法底座最成熟）原生；jiwenxu（MIT）的算法与治理模式、OBE 的类型形状都是 Python，移植成本最低；FastAPI/Pydantic 生态成熟；研究代理与测试脚本同语言 |
| TypeScript | lunar-javascript 同样 MIT 可用，浏览器端执行是独特优势；但 tonight 六个参考实现中算法最全的两个（jiwenxu、OBE）是 Python，TS 需要全部翻译。若未来做浏览器内嵌引擎，再以"从单一真相源生成/绑定"的方式补 TS 层（吸取 Atlas 人肉 UMD 双胞胎的教训：**不做手工双实现**） |
| Java | Tianze 作者的主栈，强类型好；但六家参考实现零 Java，全部算法/规则需要重写，违背"最大复用"第一原则。定位：未来 Business Backend 通过 HTTP/RPC 调 Tianze Core，不承载命理算法 |

### Q2 · 哪些能力直接使用 dependency？

- **历法/四柱/大运底座：`lunar-python`**（公农历、节气到秒、四柱三口径、晚子时 sect、藏干、十神、纳音、十二长生、旬空、胎元命宫身宫、DaYun/LiuNian）。
- 未来扩展可直依赖：lunar-javascript（差分 oracle / 浏览器层）。

### Q3 · 哪些能力"参考开源实现后重新组织"？

- **关系引擎**（合冲刑害破三合三会）：表为传统公版内容（Atlas/Horosa/OBE 三家一致），扫描器自写并吸取 OBE 的无序化教训与 jiwenxu 的"候选不化气"原则。
- **旺衰**：以 OBE 的四维划分（得令/得地/得生/得助）+ Horosa 的通根分级 + Atlas 的 ratio 计票为参考，**自写两个以上分析器**（见 Q5）。
- **格局**：以 jiwenxu 四档状态机 + Horosa 成败救应/待复核三态为参考，按《子平真诠》月令取用自写。
- **知识库 schema**：以 ruan 的断语 schema 与质检三件套为参考自建；古籍内容从公有领域原文自录。

### Q4 · 哪些能力 Tianze 必须自己实现？

1. **Evidence Model**（结论必须能回答"为什么"）——没有一家有完整实现（OBE rationale 是纯字符串、jiwenxu EvidenceItem 最接近但只在流年层）。
2. **Source Provenance 全链路**（Tianze Rule → Reference Project → Classical Source 的机器可查追踪）。
3. **多流派并列输出框架**（Horosa 有 UI 层范式，但 Tianze 要做的是 API/数据层的 schools 数组）。
4. **验证网**（Atlas 的架构 + Tianze 补齐其缺的两块：仓内 methodology/errata、Windows CI）。
5. **统一 JSON 契约**（各家的输出形状都为自家 UI 服务，Tianze 需要中立契约）。

### Q5 · 哪些算法存在明显争议、应保留多实现？

1. **旺衰/强弱**——六家六套权重六套阈值，全部 [HEURISTIC]。→ `StrengthAnalyzer` 抽象 + 至少两个实现：
   - `WeightedStrengthAnalyzer`（透明计票：可见干支/藏干分级/月令加权 → ratio → 阈值；参数全可配，默认值标注 PROJECT_HEURISTIC）；
   - `DimensionStrengthAnalyzer`（定性四维：得令/得地/得生(得势)/得助，输出维度证据而非分数）；
   - 输出 `agreement: HIGH/MEDIUM/LOW/DISPUTED` + 逐 analyzer evidence。
2. **格局成败**——四家四种状态机。→ 正格判定用《子平真诠》骨架（唯一有古籍骨架的部分），成败输出采用"成格/破格/带忌(败中复成)/不成格/待复核"超集枚举，规则来源于声明。
3. **调候**——速查版 vs 条件分级版。→ V1 做 120 组速查（数据来自公有领域原文自录），**每格保留"原典条件分级"的缺口标记**，不假装完整。
4. **晚子时/午未合化/半合条件/阴干羊刃** 等流派点 → 全部做成显式配置（CONVENTIONS.md R 表），默认值注明流派归属，分歧处双派并列。

### Q6 · 哪些项目只应该研究、不应该复制？

- **Horosa（AGPL-3.0）**：只学思想（多流派解释器、事实/视角分离缓存、诚实元数据、测试文化）；代码与数据表达一律不碰。
- **open-bazi-engine（UNKNOWN）**：只学类型形状与分层；连表文件都不抄。
- **Erfix（MIT）**：技术许可允许复制，但代码质量（日柱 +11 天、起运退化）决定只移植 Meeus Ch.25 公式思路做独立 oracle，其余不参考。

---

## 1. 分层架构（12 层）

```text
┌─────────────────────────────────────────────────────────────────┐
│ L12 UI Layer        Web (Vue3/React) —— 命盘/分析/流派对照/证据树 │
│ L11 AI Layer        Prompt Builder → LLM（只翻译，不计算）        │
│ L10 API Layer       FastAPI：/chart /analysis /schools /evidence │
│ L9  Result Layer    UnifiedResult 组装（事实+分析+流派+证据+出处）│
│ L8  School Layer    扶抑/格局/调候/病药/通关/盲派/纳音 多解释器    │
│ L7  Analysis Layer  Strength* / Pattern / Climate / YongShen      │
│ L6  Evidence Layer  EvidenceItem / StrengthEvidence / rationale   │
│ L5  Rule Layer      rules/*.json + SourceReference + provenance   │
│ L4  Relation Layer  合冲刑害破/三合三会/通根/透干（候选不化气）      │
│ L3  Ganzhi Layer    干支/藏干/十神/十二长生/纳音 事实模型           │
│ L2  Domain Layer    BirthInfo/TimeResolution/BaziChart 契约        │
│ L1  Calendar Layer  lunar-python 适配器（口径开关/双轨时间）        │
└─────────────────────────────────────────────────────────────────┘
        ▲ 测试网（横切）：fixtures + 差分对拍 + 守恒律 + R 约定断言
```

**层级纪律（从 OBE 学到并加固）**：
- 依赖单向向下：上层可调下层，下层禁止 import 上层（OBE daily 反查原局的教训：分析层缺输入就显式传参，不准"猜"）。
- L1-L5 输出**纯事实/结构**，零命理观点；L7-L8 消费事实产出**结论+证据**；L9 只做组装；L11 只做翻译。
- 任何"回退默认值"必须显式上报（OBE 静默回退"休"/120.0 的教训）。

## 1.5 "事实—推论"四级边界（Level 0-4 映射）

| Level | 定义 | 落在 Tianze 哪层 | 可信度来源 |
|---|---|---|---|
| **L0 Calendar Fact** | 出生时间/节气/年月日时柱 | L1 Calendar + L2 Domain | lunar-python + crosscheck 双路径 + 外部锚点 |
| **L1 Derived Fact** | 甲=阳木、寅藏甲丙戊、甲见庚=七杀、子午=冲 | L3 Ganzhi + L4 Relation | 公版表 + 守恒律测试 |
| **L2 Structural Analysis** | 得令/得地/得势/通根/透干/五行力量 | L4 roots/month_command + L7 strength 的事实维度 | 结构规则，无权重争议的部分 |
| **L3 School Interpretation** | 扶抑喜忌、格局取用、调候优先、旺衰评分 | L7（分数部分）+ L8 School Layer | provenance 分级：classic/open_source/project_heuristic |
| **L4 Narrative Interpretation** | 性格/事业/婚姻/财运/健康 | L11 AI Layer（只翻译 L0-L3 结果） | 无独立可信度——继承上游事实 |

纪律：**L0-L2 的输出不允许携带任何流派观点**；L3 的每个量化常数必须标 provenance；L4 永不反向写入 L0-L3。V1 交付 L0-L3 全部 + L4 的 Prompt Builder（M8 之后）。

## 2. 数据流（Mermaid）

```mermaid
flowchart TD
    A[BirthInfo<br/>date/time/gender/place/tz/sect/口径] --> B[Calendar Engine<br/>lunar-python 适配器<br/>双轨: 绝对时刻 vs 出生地真太阳时]
    B --> C[BaziChart<br/>四柱/藏干/十神/纳音/十二长生/旬空]
    C --> D[Ganzhi Facts<br/>干支五行阴阳事实表]
    C --> E[Relationship Engine<br/>五合/六合/六冲/三合/三会/刑/害/破<br/>+ 通根/透干/月令 | 候选不化气]
    D --> F[Evidence Pool]
    E --> F
    F --> G[Analysis Engines<br/>StrengthAnalyzer×N / Pattern / Climate]
    F --> H[School Layer<br/>扶抑/格局/调候/病药/通关/盲派/纳音<br/>facts → {school, verdict, xi, ji, note}]
    G --> I[Unified Result<br/>facts + analyses + schools + evidence + sources]
    H --> I
    I --> J[API / Web]
    I --> K[Prompt Builder → LLM<br/>只解读, 不重算; provenance 分级注入]
    T[Test Net<br/>fixtures+盖章 / 差分对拍 / 守恒律 / R 断言] -.横切.-> B
    T -.-> C
    T -.-> E
    T -.-> G
```

要点：
- **同一个 `BaziChart` 事实对象**喂所有分析器与流派（Horosa Q3 的"基础事实不变 + 分析视角变化"）。
- 分析视角参数（school、权重档、流派开关）**绝不进入事实缓存键**。
- LLM 输入 = 与 UI/API 完全同源的结构化快照（Horosa 单源快照原则），并带 provenance 分级（jiwenxu RAG 注入原则）。

## 3. 仓库结构（V1 目标形态）

```text
tianze/
├── pyproject.toml                  # Python 3.12+；deps: lunar-python, pydantic
├── docs/
│   ├── CONVENTIONS.md              # R 约定表（R1…每条流派选择一个编号+分歧说明）
│   ├── SOURCES.md                  # 依赖与规则来源（ 许可义务载体 ）
│   ├── ERRATA.md                   # 勘误（Atlas 站外模式的补课：仓内一等文档）
│   └── research/                   # Phase 0 九份文档（本目录）
├── tianze/                         # 核心包
│   ├── calendar/                   # L1: lunar_adapter.py + time_resolution.py（双轨时间）
│   ├── domain/                     # L2: models.py（Pydantic 契约）
│   ├── ganzhi/                     # L3: stems.py branches.py hidden_stems.py ten_gods.py nayin.py changsheng.py
│   ├── relation/                   # L4: stem_relations.py branch_relations.py roots.py combinations.py
│   ├── analysis/                   # L7: strength/ (base.py weighted.py dimensional.py) pattern.py climate.py
│   ├── schools/                    # L8: fuyi.py geju.py tiaohou.py bingyao.py tongguan.py …（V2）
│   ├── evidence/                   # L6: evidence.py provenance.py
│   ├── rules/                      # L5 loader（数据在仓库 rules/ 数据层）
│   ├── pipeline.py                 # build_chart → analyze → result
│   └── api/                        # L10 FastAPI（M8 才建）
├── rules/                          # 数据层（许可分层！）
│   ├── classical/                  # 公有领域古籍结构化（穷通宝鉴120组/子平真诠取用…）→ 开放许可
│   └── derived/                    # （如引入 CC BY-NC-SA 数据，独立目录+声明，SA 隔离）
├── tests/
│   ├── fixtures/                   # charts.json（expected 由 crosscheck 盖章）
│   ├── crosscheck/                 # 独立算法路径对拍器（JDN 公式+五时遁+五虎遁+立春判年）
│   ├── invariants/                 # 守恒律：藏干↔60甲子反推、禄=临官、关系表对称性…
│   └── disputed/                   # 分歧命例档案（不静默选边）
└── tools/
    ├── stamp_expected.py           # expected 盖章器
    └── js_oracle.mjs               # （后置）lunar-javascript 第三 oracle
```

## 4. 六条架构原则（每条都有上游事故背书）

1. **事实与解释分离**（Horosa Q3；OBE 分层）：L1-L5 无观点，L7+ 才有观点；流派=纯解释器。
2. **候选不化气 / 不裁决**（jiwenxu test_rule_regressions + Atlas R18/R19）：关系层只报"检出+位置+相邻性"，合化成立与否是分析层的事；多重关系并存（巳申=合+刑+破）全量输出。
3. **每个结论带 Evidence**（OBE rationale → jiwenxu EvidenceItem → Tianze 结构化）：`{rule_id, statement, pillars, effect, source_ref}`；无 evidence 的结论不允许出 API。
4. **权重/阈值 = 公开可配常量 + PROJECT_HEURISTIC 标注**（Horosa 自白 + Atlas R 自白）：公式随输出上屏。
5. **流派分歧显式化**（Atlas 双派并列 + R 编号 + conventionNote 随数据走）：CONVENTIONS.md 的 R 表是测试断言的对象，不是死文档。
6. **真值来自外部**（Erfix 21 个自引用测试全绿的教训 + Atlas 外部锚点）：日柱锚定 1949-10-01=甲子 / 2000-01-01=戊午 / 2024-01-01=甲子（三者主会话已经 lunar-python 实测互证）；节气锚定公开天文时刻。

## 5. 验证网（Tianze 版"可验证八字引擎"九要素）

1. `CONVENTIONS.md` R 约定表（Phase 0 末定稿 R1-R2x，逐条标注流派分歧与取舍）。
2. **主引擎 + 独立推导层**两条路径：排盘走 lunar-python；crosscheck 走 JDN 整数公式（`(JDN−2433191) mod 60`，锚点已验证）+ 五时遁 + 五虎遁 + 立春/节黄经区间判定（移植 Meeus Ch.25 思路自写，仅年/月柱域）。
3. 35+ 边界 fixture：立春 ±30min、交节 ±30min、晚子时两派成对、00:00 边界、DST 1988、乌鲁木齐/纽约/伦敦时区、闰日、未知时辰、1965/2025 年份两端。
4. expected 由对拍器盖章 + 人工复核记录字段。
5. 结构不变量套（守恒律/互证）+ 关系表完备性断言（六合恰 6 对、五合恰 5 对、寅亥既合又破不许删）。
6. 上游库缺陷清单（lunar-python sect=2 时柱日干口径、`getYun` 23 点档、宜忌 hex 无出处…）。
7. 每个输出带 `conventions` 与 `evidence` 字段。
8. CI：Linux + Windows 双矩阵（Atlas 的 crosscheck 在 Windows 崩溃的教训）。
9. `ERRATA.md` 仓内勘误 + disputed/ 分歧档案。

## 6. 技术栈与依赖清单（V1）

| 层 | 选择 | License | 理由 |
|---|---|---|---|
| 语言 | Python ≥3.12 | — | 复用面最大（见 Q1） |
| 历法 | lunar-python | MIT | 唯一同时满足"天文级节气+双流派+大运+零依赖+活跃维护"的库 |
| 契约 | Pydantic v2 | MIT | frozen dataclass + JSON Schema 双轨（OBE 模式） |
| API | FastAPI + uvicorn | MIT | M8 |
| 测试 | pytest | MIT | fixtures/参数化/快照 |
| 差分 oracle（后置） | lunar-javascript via node 脚本 | MIT | 第三意见，跨原理（JS 实现） |
| 节气 oracle | 自写 Meeus Ch.25 移植（~20 行，MIT 来源 Erfix 但重写） | — | 仅年/月柱域（Erfix 日柱锚点 +11 天，不可用其日柱代码） |
| UI（M9） | Vue 3 + TS + Vite | MIT | 与原计划一致 |

明确**不引入**：任何 AGPL 代码（Horosa/Swiss Ephemeris）、无 License 代码（OBE、taixuanshifa 系）、ruan CC 数据（V1 默认不引入；若引入必须独立 derived/ 数据层并全链署名）。
