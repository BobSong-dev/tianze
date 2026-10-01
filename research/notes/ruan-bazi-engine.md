# ruan-bazi-engine 研究笔记

> 上游仓库：`C:\Project\tianze\research\upstream\ruan-bazi-engine`（GitHub: ruanxiaoer888/bazi-engine），只读研究，未修改其中任何文件。
> 下文所有文件路径均相对仓库根目录；行号/字节数为 2026-09-30 检出版本（HEAD `d752fbc`）实测。
> 核心结论前置：**这是一个"单文件引擎 + 中文条件键断语库（1000 条）+ 古籍 Markdown 汇编 + LLM Skill 包装"的项目，双许可（代码 MIT / 数据 CC BY-NC-SA 4.0）。Tianze（非商业）可合法使用其 KB 数据，但衍生数据必须同许可共享（SA 传染），且其断语库内嵌防盗用指纹水印（README 声明，具体位置不公开）。**

---

## 1. 仓库概览

| 项 | 值 | 来源 |
|---|---|---|
| 语言 | JS（引擎/UI/测试）+ Python（构建/质检）+ Markdown/JSON（知识库） | 目录实测 |
| 规模 | 共 88 个文件（不含 .git）；代码+数据约 2.3 MB，assets 截图另计 3.2 MB | `find`/`du` 实测 |
| 最后提交 | `d752fbc` 2026-08-29 "docs: HANDOFF §〇 冷启动速贴当前状态同步 v1.3.7"，作者 xiaoer <347431996@qq.com> | `git log` |
| 版本 | v1.3.7（HANDOFF.md 头部自述） | HANDOFF.md |

目录结构（各目录文件数 / 体积实测）：

```
engine/      1 文件  452K   engine.dist.js（构建产物，UMD 独立引擎库，101 个导出——已用 node require 实测确认）
kb/         31 文件  956K   知识库（本笔记重点）
skill/       1 文件   16K   SKILL.md（LLM Skill 定义）
tools/      27 文件  472K   构建脚本 build_ui.py(212K!) + 13 套 node 回归 + 质检/审计工具
ui/          2 文件  620K   index.html(593K 单文件成品) + jieqi.json(39K 节气表 1895–2100)
docs/        4 文件   44K   ENGINE-CHANGES.md + docs/history/ 验收记录
assets/     13 文件  3.2M   截图/logo（无代码价值）
.github/     1 文件         workflows/ci.yml（CI 门禁）
根目录                     README.md/.en.md、HANDOFF.md(80K 交接文档)、LICENSE、LICENSE-DATA、工作区说明.md
```

---

## 2. License 双轨制【重点】

### 2.1 LICENSE（代码轨）

- **MIT License，Copyright (c) 2026 ruanxiaoer**（LICENSE 全文 22 行，已完整阅读）。
- 覆盖范围以 LICENSE-DATA 的表格为准：排盘引擎、`ui/`、`tools/` 构建/测试/质检脚本、`skill/` Skill 定义（LICENSE-DATA 第 7 行）。

### 2.2 LICENSE-DATA（数据轨）

- **CC BY-NC-SA 4.0**（署名-非商业性使用-相同方式共享 4.0 国际），覆盖"知识库全部内容（含断语库、古籍汇编、规则手册、基础表）**及其内联产物（如 ui/index.html 中内嵌的断语数据）**"（LICENSE-DATA 第 8 行）。即：断语数据一旦被 build 进单文件 UI/dist，也随数据许可走。
- 对使用者的三条义务（LICENSE-DATA 第 27–34 行）：
  1. **署名（BY）**：保留"bazi-engine · ruanxiaoer"署名与出处标注，注明做了何种修改；**断语逐条标注的古籍出处（source 字段）必须原样保留，不得删改**。
  2. **非商业（NC）**：不得用于商业目的，包括"将断语库整体或实质部分嵌入付费产品/付费 Skill/付费 API"；个人学习、学术研究、非营利性传播不受限。
  3. **相同方式共享（SA）**：基于数据创作的衍生作品必须以**同样的 CC BY-NC-SA 4.0** 发布。
- 商业授权需联系作者；"未来新增的 Pro 断语库（800+ 条）默认闭源"（LICENSE-DATA 第 36–37 行）。
- **来源归属三层声明**（LICENSE-DATA 第 41–55 行，重要）：
  1. 古籍原文（《三命通会》《渊海子平》《滴天髓》《子平真诠》《穷通宝鉴》《黄帝内经》）= **公有领域**，本声明只保护"汇编、摘录、结构化与条件化编译"成果；
  2. 部分基础表/规则整理参考 **MIT 开源社区项目（如 jinchenma94/bazi-skill 等）**，该部分"保留其原始版权声明与 MIT 许可，不受 NC 限制"；
  3. 断语库的条件化规则、置信度标注、行动建议、质检流水线 = 本项目原创，受 CC BY-NC-SA 4.0 保护。

### 2.3 README / HANDOFF 的许可表述（与源文件交叉验证）

- README.md"License"章（第 201–212 行）与 LICENSE-DATA 一致，另加"市场分发"条款：Skill 市场（ClawHub/SkillHub）页面 License 字段与仓库不一致时以仓库 LICENSE/LICENSE-DATA 为准。
- **已证实的许可冲突**：HANDOFF.md 坑 #49（第 460 行）记录 ClawHub 平台强制所有 skill 以 **MIT-0**（免署名 MIT）显示，与数据 NC 条款"直接冲突，属法律风险点"，作者只能靠 SKILL.md frontmatter `description:` 声明双许可兜底（HANDOFF.md 第 192–196 行）。注意 `skill/SKILL.md` frontmatter 第 13 行写着 `license: MIT`——**只代表代码层，对数据有误导性**，引用其 skill 文件时要小心。
- README.md 第 197–199 行"数据溯源指纹"：rules.json 内含**隐藏水印句**，未经许可复用（尤其商用）可据此识别取证；"遵守 LICENSE/LICENSE-DATA 的正常使用不受任何影响"。配套工具 `tools/monitor_usage.js`（每月用 GitHub Code Search 搜指纹定位疑似盗用方）。
- 另有 C 端合规软化管线 `tools/compliance_soften.py`（术语替换：运势→能量、八字→出生信息等），说明作者对"数据出境/合规"有一套构建期处理思路。

### 2.4 结论：Tianze（明确非商业）能否用其 kb 数据

**能。** 条件是履行：
1. 在 Tianze 文档/产品中保留"bazi-engine · ruanxiaoer"署名，注明所做修改；
2. 从 rules.json 提取的每条断语**逐条保留其 source 字段**（这本来就是 Tianze 想要的溯源设计）；
3. **衍生知识库整体需以 CC BY-NC-SA 4.0 发布**（SA 对"衍生数据"传染——Tianze 若把自己的规则混入提取数据并想用更严/更宽许可，需把上游提取部分独立成单独标注的数据层）；
4. 永久不商用该数据；警惕隐藏水印句的存在（提取后应做去重改写评估，且不可假设"拿走无痕"）。
5. 更安全的替代路径：只取 **古籍原文（公有领域）**——`kb/03-classics/` 中标注【原文】的部分可自由使用，避开编译层；或追查其引用的 MIT 社区来源（jinchenma94/bazi-skill）直接取原始 MIT 数据。
6. 代码层（engine.dist.js、测试、build 流程）MIT，可自由复用，仅需保留版权与许可声明。

---

## 3. 架构与模块划分

**架构真相（README 之外，以源码验证）**：真正的引擎源码不是独立文件，而是**内嵌在 `tools/build_ui.py`（212KB）的 Python 三引号字符串模板 TPL 内的 JS 代码**，用 7 对 `// [ENGINE:BEGIN]` / `// [ENGINE:END]` 注释界定"纯计算层"（build_ui.py 第 721/1281/1284/1540/1544/1574/1576/1627/2054/2079 行）：

```
tools/build_ui.py  ──读取──> ui/jieqi.json + kb/04-rules-db/rules.json
        │ 注入模板 TPL
        ├──> ui/index.html        593KB 单文件成品（内联节气 206 年 + 1000 条断语 + 全部引擎 JS）
        └──> engine/engine.dist.js 459KB UMD（抽取 [ENGINE:BEGIN/END] 区段拼装，101 个导出，实测确认）
```

- **engine/**：构建副产物，"勿手改"（HANDOFF.md §2.1 表格；`tools/test_engine.js` 第 11–12 行甚至断言 dist 不含 DOM 引用）。真源在 build_ui.py，版本与 MD5 变更记录在 `docs/ENGINE-CHANGES.md`。
- **kb/**：数据层，五层结构（见 §5）。
- **skill/**：LLM 接入层。SKILL.md 是给 AI 助手（ClawHub/SkillHub 市场分发）的说明书+系统提示词，不参与 UI 构建。
- **tools/**：build_ui.py（构建）、gen_rules.py（断语批量扩充）、patch_suggestions.py（补 suggestion 字段）、audit_hit_distribution.js / check_dup_hits.js / check_conflicts.js（KB 质检三件套）、13 套 test_*/verify_* 回归、compliance_soften.py（C 端合规替换）、archive/（历史脚本，含 `gen_jieqi.py`——jieqi.json 的生成源头，用 lunar_python 生成并校验，已核实）。
- **ui/**：单文件离线成品 + jieqi.json 数据。
- **docs/**：ENGINE-CHANGES.md（引擎变更权威记录）+ docs/history/ 发布验收材料。

**数据流**：用户出生信息 → `applyDst`（夏令时回拨）→ `paipan()`（节气精确排盘，输出 ctx）→ `matchRules(ctx)`（1000 条断语线性条件匹配，按 category 分组返回）→ UI 面板渲染 / 专用时序匹配（matchDayun/matchLiuYue/matchLiuDay）→ 报告。LLM 侧（skill/SKILL.md）则是"引导式问询 → 打开 ui/index.html 或按 kb 表格推算 → 按 kb 规则解读"。

---

## 4. engine/ 概览（排盘/算法能力清单）

关键文件：`tools/build_ui.py`（引擎真源，[ENGINE] 区段）与 `engine/engine.dist.js`（同源产物）。以下函数均已在源码中定位验证：

- **历法排盘**：`paipan()`（build_ui.py:1130 起）——年柱按**立春精确时刻**、月柱按**十二节精确时刻**（数据 `ui/jieqi.json`，1895–2100，由 `tools/archive/gen_jieqi.py` 用 lunar_python 生成）；日柱基准递推；时柱五鼠遁 + 晚子时翻日；真太阳时校正（内置 724 城市经度表，HANDOFF 头部）；`applyDst()` 中国夏令时窗口表（1986–1991，DST_WINDOWS，build_ui.py ~1550）；`lunarToSolar`/`leapMonth` 农历模块。
- **十神**：`tenGod()`（build_ui.py:1030），以日干阴阳五行推五类十神。
- **藏干与五行量**：`computeFive()`（:1060）——天干 1.0；地支本气 1.0 / 中气 0.5 / 余气 0.25；**月令柱整体 ×1.5**（权重硬编码）。
- **旺衰**：帮扶（比劫+印）vs 克泄耗（食伤+财+官杀）比例 ratio：>0.6 强 / <0.4 弱 / 其余中和（build_ui.py:1180 附近）；专旺格双阈值（主导行 >0.75×总量 且 最强他行 ≤0.15，注释注明 2026-08-19 由 0.55 收紧）；从格 support<0.18×总量。
- **调候**：`TIAOHOU_MAP`（build_ui.py:1185 附近）——**日干 × 季节**（寅卯辰→春…）硬编码 10×4 表。⚠️ 粒度只到季节，比 kb 古籍（按月）粗，见 §5/§11。
- **格局**：`getPattern()`（:1102）——"《子平真诠》透干取格优先；不透干以月令本气定格"，映射 `PATTERN_NAME` 10 格（建禄/月劫/食神/伤官/正偏财/正官/七杀/正偏印）；细分专旺五格（曲直/炎上/稼穑/从革/润下）+ 从格（从财/从杀/从儿/从势）。
- **喜用神**：strength 三分支公式（强→克我/我克/我生；弱→同我/生我；中和按 ratio 细分偏强偏弱/真中和 xiYong=[]）。
- **病药**：maxExcess>1.3 判"病"，取克病者+生病者为药。
- **地支/天干关系**：`CHONG`(六冲)/`LIUHE`(六合)/`SANHE`(三合)/`XING_PAIRS`(刑 8 对)/`HAI_PAIRS`(害 12 对)/`WU_HE`(天干五合) 全部硬编码 JS 常量（build_ui.py:750–755）。
- **神煞**：`calcShenSha()`（:235），SHENSHA 表 24 项（天乙/文昌/禄神/学堂/金舆/天德/月德/龙德/将星/红鸾/华盖/驿马/桃花/羊刃/劫煞/亡神/灾煞/孤辰/寡宿/岁破/血刃/流霞/勾绞/天罗地网），每项带查法 lambda。
- **十二长生**：`calcChangSheng()`，CS_BASE 十干长生位（阳顺阴逆）。
- **断语匹配**：`matchRules()`（:1434）+ `evalState()`（:1286）状态语义机（40+ 个 case，见 §6）；时序类 `matchDayun`/`matchLiuYue`/`matchLiuDay`/`analyzeLiuDeep`（岁运并临/伏吟反吟）。
- **合婚**：`analyzeHe`（UI 层）七大维度加权（日柱关系25/五行互补25/纳音10/十神15/生肖10/大运10/用神5，kb/README.md 第 59 行 + build_ui.py）。

覆盖评价：排盘历法层扎实（有真值测试：马云盘四柱、lunar-python 交叉验证）；旺衰/喜用/调候是**阈值启发式**（无古籍出处标注，数值拍定，注释自述"大样本标定"）；格局只有月令透干十神格 + 特殊格大类，**没有成格/败格的完整判定链**（"成格"判定在 evalState 里只是"五行分≥0.8avg 且透干或二见"的简化）。

---

## 5. Knowledge Base 深度剖析【重点】

### 5.1 kb/ 目录树与文件清单（31 文件，956KB，全部实测）

```
kb/
├── README.md (8.8K)                    总索引：四层结构说明 + 引擎算法口径 + 使用约定
├── 01-basics/  (排盘静态查表, 5 文件)
│   ├── ganzhi-wuxing.md      15.0K     干支五行/天干五合/相克/地支六冲三合三会六合刑害破/十神定义与推导/
│   │                                   十神详解/五行生克/十二长生表/地支藏干表/空亡旬空表/命宫推算
│   ├── shichen.md             2.8K     十二时辰对照、早晚子时、五鼠遁
│   ├── wushuhun-wuhuhun.md   15.0K     五虎遁/五鼠遁完整映射与口诀
│   ├── najin.md               5.8K     六十甲子纳音五行表
│   └── shensha.md             8.2K     神煞参考大全（吉/凶/中性分组，逐个查法表，如天乙贵人年干日干查法表）
├── 02-rules/   (论命规则与流程, 6 文件)
│   ├── classical-rules.md    15.8K     九本典籍核心规则摘要（穷通/三命/滴天/渊海/千里命稿/协纪辨方/
│   │                                   子平真诠/神峰通考/果老星宗），格局逐条标注【三命通会·卷六】等
│   ├── dayun.md               6.4K     大运顺逆排、起运年龄规则表
│   ├── marriage.md            4.5K     合婚七大维度规则
│   ├── remedy.md              4.9K     五行补救（补金木水火土的颜色/方位/数字/行业/饰品/饮食）
│   ├── workflow.md            5.6K     九步算命完整流程
│   ├── example.md            10.0K     万年历推算完整案例与综合练习
│   └── bazi-mbti.md          11.2K     八字十神×MBTI 十六型映射（引潘子端 1937《命学新义》）
├── 03-classics/ (古籍, 10 文件 289KB)
│   ├── shigan-lun.md         20.9K     ★十干论：十天干×十二月【调候用神】+【原文】+性味宜忌（精编，检索友好）
│   ├── ziping-zhenquan.md     4.1K     ★《子平真诠》用神专论摘录：月令取用/八格/顺逆用/成败/真假纯杂
│   ├── yuanhai-geshi.md       4.6K     ★《渊海子平》格局歌诀+十神类象+藏干诀
│   ├── ditian-sui-zhushu.md   5.6K     ★《滴天髓》核心注疏：三元/十干性情/旺衰/调候/专旺（【原文】+【注】）
│   ├── qiongtong-baojian.md  41.3K     穷通宝鉴 docx 全文提取（493 段，十干×十二月调候完整原文+调候总表）
│   ├── sanming-tonghui.md    44.2K     三命通会 docx 全文提取（1513 段，格局/神煞/六亲/疾病）
│   ├── yuanhai-ziping.md    137.3K     渊海子平 docx 全文提取（1113 段，基础理论+78 表）——最大单文件
│   ├── ditian-sui.md         17.3K     滴天髓 docx 全文提取（652 段）
│   ├── bazi-wuxing-table.md   8.0K     生辰八字与五行对照表 docx 全文（35 段+10 表）
│   └── workflow-full.md       5.7K     算命流程 docx 全文（9 步）
├── 04-rules-db/ (结构化断语库)
│   ├── rules.json           389.1K     生产断语库（12195 行，1000 条——见 §5.2）
│   ├── rules-template.json    3.7K     规则 schema + 8 条示例 + usage_note
│   └── drafts/
│       ├── liuri-batch1.jsonl           14.8K, 45 行 = 流日批次 45 条（JSONL，每行一规则）
│       ├── liuri-batch1-sources.md       8.0K   取材清单：每条断语的古籍出处对照表（流水线 Step1/2 产物）
│       ├── liuyue-batch2.jsonl           8.7K, 25 行 = 流月批次 25 条
│       └── liuyue-batch2-sources.md      6.0K   同上
└── 05-reference/ (扩展参考)
    ├── prompt-template.md    40.3K     八字+紫微+面相+手相"四法合一"巨型提示词（未实现，仅参考；
    │                                   HANDOFF 坑 #49 记录 ClawHub 审计认定其面相/健康内容超范围）
    └── viz-spec.md           16.6K     SVG 可视化输出规范（排盘表/五行图/十神关系图，viewBox/配色标准）
```

### 5.2 古籍如何保存

- **格式：纯 Markdown**（不是 json/txt）。两种形态：
  1. **docx 自动提取全文层**（6 个大文件）：文件头是机器提取元数据，如 qiongtong-baojian.md 头部"> 来源：穷通宝鉴-AI知识库.docx / 段落数：493，表格数：1 / 自动提取时间：2026-08-11 15:44"。正文按 `## 一、` / `### （一）` 分章节，**未分句、未结构化**，整段白话转述与原文混排。yuanhai-ziping.md 达 137KB/3196 行，是知识库最大单文件。
  2. **人工精编摘录层**（4 个小文件，shigan-lun/ziping-zhenquan/yuanhai-geshi/ditian-sui-zhushu）：有明确的检索导向组织。如 shigan-lun.md 按日干分节，每一干下再按十二月列出"《穷通宝鉴》·调候用神（按月令）"，每条引 `> 【原文】"正月甲木，初春尚有余寒…"`（该文件"甲木"节）；ziping-zhenquan.md 用"【原文】…【注】…"双栏结构并给出引用格式示例。
- **体量**：03-classics 共 289KB（≈28.9 万字节，约 10 万汉字级）；kb/README.md 第 63 行自述"共 6 份 103K 字符"指的是 docx 提取正文部分。
- **溯源链**：精编层声明"主要素材已与本地古籍原文《滴天髓阐微》交叉核对"（ditian-sui-zhushu.md 头部）；drafts/*-sources.md 提供"断语 id → 书名·篇"的取材对照表。

### 5.3 规则如何表示（rules.json）

- 文件：`kb/04-rules-db/rules.json`，389KB/12195 行，顶层 `{schema_version, description, rules[], usage_note}`。
- **实测 1000 条**（python json 解析计数）。⚠️ **矛盾①**：description 自述"结构化规则 **789 条**（2026-08-19 清理 …，801→789）"，而 rules 数组实际 1000 条，kb/README.md 与 SKILL.md 均称 1000——description 元数据未随后续批次（流日 45 + 流月 25 + 六亲等）更新。
- 字段（schema 级说明，依据 rules-template.json + 1000 条全量统计）：

| 字段 | 类型 | 覆盖率 | 说明 |
|---|---|---|---|
| `id` | string | 1000/1000 | 语义前缀命名：`char_*`(97) `career_*`(112) `wealth_*`(57) `marriage_*`(67) `health_*`(62) `study_*`(56) `pattern_*`(56) `yongshen_*`(72) `combo_*`(65) `wuxing_*`(48) `shensha_*`(74) `kin_*`+`qinq_*`(64) `liuri_*`(50) `liuyue_*`(45) `liunian_*`+`liu_*`(30) `dayun_*`(20) `hehun_*`+`he_*`(20) `edu_*`(5) 等 |
| `category` | string | 1000/1000 | 17 类固定词表：事业112/性格97/神煞74/用神喜忌72/婚姻67/十神组合65/六亲64/健康62/学业61/财运57/格局56/流日50/五行生克48/流月45/流年30/合婚20/大运20 |
| `condition` | object | 1000/1000 | **扁平键值、中文键**。键全集（实测频次）：十神295、状态188、日主169、旺衰162、神煞150、组合138、位置117、五行86、格局62、性别54、流日45、流月25、流年20、生克检测15、合婚12、否决7、杀5、十神组合4。**没有"月令"键**（template 示例里有，生产库 0 条，引擎 matchRules 也未实现该键——格局条件靠引擎月令取格结果间接实现） |
| `conclusion` | string | 1000/1000 | 断语正文，通常 1 句（30–60 字） |
| `source` | string | 1000/1000 | 自由文本出处："《书名》篇名/条目名"。书名分布：《三命通会》371、《渊海子平》208、《滴天髓》180、《子平真诠》157、《黄帝内经》43（健康类）、《穷通宝鉴》39、其余 2 条 |
| `confidence` | enum | 1000/1000 | "高"75 / "中"845 / "低"80（低多为健康类免责断语） |
| `suggestion` | string | 1000/1000 | 行动建议；SKILL.md 自称 100% 覆盖（由 tools/patch_suggestions.py 补齐） |
| `advice` | string | 91/1000 | ⚠️ **矛盾②**：91 条规则多出 `advice` 字段，与 suggestion 并存——schema 漂移，未清理 |

- 脱敏示例（原文照录，各 1 条短引）：

```json
{"id":"char_jia","category":"性格","condition":{"日主":"甲木"},
 "conclusion":"如参天大树，仁德有担当，有领导气质；喜火通明、水木相滋，忌金重土埋。",
 "source":"《滴天髓》甲木参天 / 《穷通宝鉴》甲木","confidence":"高",
 "suggestion":"发挥领导才能，注意人际柔性，寒木需火暖局"}
```

```json
{"id":"pattern_qisha_zhi","category":"格局",
 "condition":{"格局":"七杀格","状态":"有制化"},
 "conclusion":"七杀得食神制或印星化，化杀为权，主权威魄力，大贵之象。",
 "source":"《子平真诠》七杀逆用","confidence":"中","suggestion":"以才制杀、以学化杀"}
```

```json
{"id":"wuxing_通关_木火土","category":"五行生克",
 "condition":{"五行":"木","生克检测":"通关"},
 "conclusion":"木火相生而土为中介…全局五行流通有情，为顺遂之象。",
 "source":"《滴天髓》流通论","confidence":"中",
 "suggestion":"五行流通顺遂，宜顺势而为…"}
```

- 特殊 condition 语义（在引擎 matchRules/evalState 中实现，而非 JSON 自描述）：`组合` = 十神数组必须全部存在；`否决` = 数组或 `true`，必须不存在（SKILL.md 第 136 行专门警告此键曾因实现错误导致 77% 误命中）；`生克检测` = "通关/制化/反克"运行时五行阈值检测；`杀:1` = 某行过旺且克行者太弱；`状态` 的 40+ 种取值由 evalState 大 switch 解释（见 §6）。
- 批量扩充管线：`tools/gen_rules.py`——种子规则 + Python 字典模板批量生成（如 10 日主 × 强/弱/中和 30 条性格规则），`add()` 按 id 幂等去重。**矛盾③**：gen_rules.py 头注释还写着"扩展至 200+ 条"，实际库已 1000 条。生成痕迹明显：`yongshen_jin_1`（庚金）与 `yongshen_jin_2`（辛金）conclusion 完全同文。新批次走 drafts 工作流：取材清单（sources.md）→ 条件化 JSONL → 入库 → 引擎适配 → 全套回归（liuri-batch1-sources.md 头部流程表）。

### 5.4 规则如何关联出处

- `source` 是**单一自由字符串**，非结构化对象：格式惯例为 `《书名》` 或 `《书名》篇名/条目`，双出处用 `" / "` 连接（如 char_jia 例）。**没有卷/页/句号、没有 JSON 化的 chapter/verse 字段**。
- 引用粒度到"书名·篇/句名"级（如"《三命通会》看命口诀"、《子平真诠》格局成败），可回溯到 03-classics 的对应文件，但要靠人/LLM 自己 grep 原文，无机器可校验的引用 ID。
- 辅助机制：drafts/*-sources.md 是"规则 id → 出处 → 原文摘句"的人读对照表；LICENSE-DATA 明文要求 source 字段"原样保留，不得删改"——出处即许可义务的一部分。

### 5.5 断语如何分类

- **一级分类**：`category` 17 类（领域维度：性格/事业/财运/婚姻/健康/学业/六亲/格局/用神喜忌/十神组合/五行生克/神煞/大运/流年/流月/流日/合婚）。
- **强度**：`confidence` 高/中/低三档——"高"只给日主本性类（char_*）和流月长生等教科书规则；健康类清一色"低"并附就医免责。
- **吉凶**：**没有显式吉凶/强度字段**，吉凶只藏在 conclusion 文案里（神煞在引擎 SHENSHA 表内有 type:'吉/凶/中'，但那是代码不是 KB）。
- **匹配位置/性别/状态**：由 condition 键（位置=日支/年月/日时/年干/月干/时干；性别=男/女；旺衰=强/弱/中和）承担。
- 主面板有命中密度预算：SKILL.md 第 123 行"主面板 6 类平均 23–30 条/盘"为健康区间——分类同时是渲染配额单位。

### 5.6 检索机制

- **没有索引、没有关键词倒排、没有向量、没有 RAG。** 两条检索路径都是暴力式：
  1. **运行时（UI/引擎）**：`matchRules(ctx)` 对 1000 条规则**线性遍历**，每条按 condition 键逐一比对 ctx（日主/旺衰/十神集合/五行分数/神煞数组/格局），O(n) 每盘一次，1000 条规模无所谓性能。
  2. **LLM 时（Skill）**：SKILL.md 给出文件级"按需读取"清单，让 AI 按分析阶段人肉打开对应 md；rules.json 对 LLM 主要作为"编写新规则参考"和 UI 渲染数据存在。
- 质检替代索引：audit_hit_distribution.js 用大样本随机盘统计每条命中率来找"条件过宽"的坏规则——用统计审计弥补静态检索层缺失。

### 5.7 如何给 AI 使用（skill/ 喂养方式）

- `skill/SKILL.md`（14.7K）= frontmatter（name/description/version 1.3.7/platforms/license）+ 系统提示词。结构：
  1. **核心原则四条**（第 21–30 行）：①排盘确定性——"四柱、大运、流年必须用代码/查表计算，绝不用 LLM 心算"；②论命有典——每条关键判断标注出处，"不允许凭语感下断语"；③克制建设性；④零门槛表达。
  2. **知识库检索清单**（第 32–70 行）：把 kb/ 每个文件 + tools/ 质检脚本列成带一句话说明的路径清单，让 Agent 按需 Read。这是"喂 KB"的全部机制——**不拼接、不注入，靠文件路径清单+Agent 自主读取**。
  3. **三阶段流程**：引导式收集信息（AskUserQuestion 逐项问）→ 排盘计算（读基础表按顺序推演或直接用 ui/index.html）→ 综合分析（8 点框架，每点至少一处古籍出处，含"提出 3–5 个已发生事件请用户验证"的历史校准法）。
  4. **断语库质量审查章**（第 117–136 行）：把"条件过宽=无条件命中"的坑、否决键语义、十神下标错位事故写成 Agent 自检手册——罕见的高质量 KB 维护经验。
- `kb/05-reference/prompt-template.md`（40K）是另一路喂法：完整系统提示词模板（角色定位/知识体系/服务流程/输出格式），面向"八字+紫微+面相+手相四法合一"咨询，但**未在本项目实现**，HANDOFF 坑 #49 记录其面相/健康内容被 ClawHub 审计判定超范围。
- `kb/05-reference/viz-spec.md`：规定 Agent 输出 SVG 图表的规范（viewBox、配色变量）——属于对 LLM 的输出格式约束层。

---

## 6. 关系与旺衰等命理数据的结构化程度

- **合冲刑害**：KB 侧（`kb/01-basics/ganzhi-wuxing.md`）有完整 Markdown 表（天干五合/天干相克/六冲/三合局/**三会局**/六合/相刑/相害/相破/天地合，第 102–153 行标题实测）；引擎侧是**硬编码 JS 常量**（build_ui.py:750–755：CHONG/LIUHE/SANHE/XING_PAIRS/HAI_PAIRS/WU_HE）。注意 md 表比引擎多三会局、相破、天地合——**KB 覆盖 > 引擎实现**。rules.json 中关系类断语以 `组合`/`生克检测`/`神煞:'空亡'` 等键间接表达，无独立的"关系规则"数据结构。
- **旺衰**：两级结构。①引擎数值层：帮扶/克泄耗 ratio 阈值 0.6/0.4 + 藏干加权（月令 ×1.5），输出 强/弱/中和；②KB/规则层：`旺衰` 条件键（162 条规则引用）取值仅 强/弱/中和；更细的命理状态（"偏枯有药""用神被冲克合""伤官佩印""成格"等）不是数据，而是 **evalState() 大 switch 里 40+ 个硬编码语义 case**（build_ui.py:1286–1378），每个 case 自带阈值（如偏枯=mx≥1.8×avg 且 mn≤0.4×avg 且药≥0.5×avg，注释"300 盘标定命中率约 28%"）。
- **格局**：引擎 `getPattern`（月令透干→10 格）+ 专旺/从格细分映射表 ZHW_MAP/CONG_DETAIL_MAP（build_ui.py:1210 附近）+ rules.json `格局` 条件键 62 条（取值实测：正官格8/七杀格7/专旺格7/伤官格5/从格5/建禄格3/月劫格3/从财格1 等）。
- **调候**：引擎 `TIAOHOU_MAP` = 日干×**季节** 10×4 硬编码（如 甲:{春:['火'],夏:['水'],秋:['水'],冬:['火']}）；而 KB 侧 shigan-lun.md/qiongtong-baojian.md 是日干×**月**（12 档）带原文——**引擎比古籍粗**，rules.json 无调候条件键（只有 evalState '调候' case：月支∈亥子丑/巳午未 即判需调候）。
- 总评：**"结构化"只在 condition 扁平键值这一层**；所有命理语义的深层判定逻辑都在 JS 代码里，不在数据里。数据无法脱离引擎独立解释。

---

## 7. 测试体系

- **13 套 node 回归 + CI 门禁**（`.github/workflows/ci.yml` 完整阅读）：build → rules.json JSON 有效性（打印规则数）→ 13 套回归（test_engine 28 项/test_lunar 27 项/test_ui/test_eval_state 旺衰状态机/test_p1_fixes/verify_sleep_rules 十二长生/test_ux_e2e 端到端/test_dst/test_liuri_v2/test_liuyue_v2/verify_edu_rules/test_xiyong/check_conflicts）→ compliance_soften 合规检查 → audit_hit_distribution --sample=100 --seed=42（固定种子命中分布审计）。
- 测试理念上最有价值的三件（SKILL.md 第 119–136 行 + 工具源码）：
  1. **命中率审计**：100% 命中=坏规则（条件必有过宽/字段引用 undefined 恒真），>80% 人工复核，单盘 0 命中也异常；
  2. **反义矛盾检测**（check_conflicts.js）：40 对反义规则（char_日主_强/弱 等）1000 盘实测 0 同盘双命中；
  3. **重复命中检测**（check_dup_hits.js）：同文案规则对同盘双命中率。
- 真值锚定：test_engine.js 用名人盘（马云 1964-09-10 → 甲辰/癸酉/壬戌/丙午）+ lunar-python 口径；kb/README.md 第 86 行称与《新历农历对照表.xlsx》逐日交叉验证。
- 局限：verify_ux_e2e 等脚本用 node vm 沙箱动态执行（HANDOFF 坑 #49：静态扫描误报 Critical）；测试全部针对引擎/UI，**对 03-classics 古籍内容本身零测试**（无从测起）。

---

## 8. 边界情况

处理清单（skill/SKILL.md 第 138–148 行边界表 + verify_ux_e2e A–E 组 + 引擎注释）：
- 出生时辰完全未知：明确**拒绝心算排盘**，引导查证或选代表性时辰双盘并强制标注"估算"；
- 只知大概时段：时段→代表时辰映射；阳历农历双未知：无法排盘；
- 节气交界：按节气精确时刻切分，距交节 <1 小时提示"换柱临界"；立春前后年柱精确归属；
- 夜子时 23–24 点：按次日日干起时柱；真太阳时校正后落入晚子时会标注；
- 数据起点 1895 年小寒前：月柱兜底 丙子月（verify_ux_e2e B 组）；
- **中和命局**：xiYong 为空 → 所有"用神被冲克合/用神假"类条件一律不命中（evalState 中 `ctx.xiYong.length===0` 守卫，注释记录 2026-08-19 修复"原 length>=5 永不成立"的死代码）；
- 空亡死规则：日支不可能逢本柱旬空 → 改为"命局任一柱地支逢日柱旬空"（matchRules 神煞分支注释）；
- 夏令时窗口边界日（1986-05-04 02:00 前后）、跨天回退（test_dst.js 29 项）；
- 无效日期/超范围年份/非法时刻/性别非法：paipan 入口校验并 alert。

---

## 9. AI 接入方式

**是的，这是标准的"确定性规则引擎 + LLM"双层架构**，且边界画得非常自觉：

- **确定性层（代码，不许 LLM 碰）**：历法换算、四柱、大运、神煞查表、五行加权、旺衰阈值、格局取法、断语 condition 匹配（matchRules/evalState）。SKILL.md 核心原则 1："排盘必须用代码/查表计算，绝不用 LLM 心算"；时辰未知时"不可用心算六字代替"。
- **LLM 层（允许发挥）**：引导式信息收集、术语通俗化、报告组织与语气、综合分析叙事、可视化描述、历史事件校准对话。输入素材 = 引擎/KB 命中的结构化断语 + 古籍摘录。
- **纪律带**：①"未命中规则的不得强行断语"（kb/README.md 使用约定 3 + rules-template usage_note）；②每条输出必须带 source；③断语库本身由代码消费（1000 条全量进 UI 引擎），LLM 不直接对着 rules.json 挑规则——**规则命中是代码的活，解释命中结果才是 LLM 的活**。
- 双入口：C 端（ui/index.html 全本地渲染，断语即最终输出）与 B 端/Agent（SKILL.md 引导 LLM 调用引擎 + 读 KB 撰写报告）。另有一个纯 LLM 极端形态（prompt-template.md 四法合一提示词，零引擎），被项目自己标记为"未实现/超范围"。
- 特色工程：`compliance_soften.py` 把"命理表述→合规表述"做成构建期术语替换管线（含 --check 残留检测）——C 端风险控制的代码化。

---

## 10. License 与可复用性评估

**代码线（MIT）——可复用度高：**
- `engine/engine.dist.js`（101 导出，Node/浏览器双端）、`tools/` 全部构建与质检脚本、`skill/SKILL.md` 结构本身：MIT，保留版权声明即可自由使用/修改/商用。注意 dist 是构建产物，若要改动需从 build_ui.py 源头改。
- 风险提示：SKILL.md frontmatter `license: MIT` 只对代码成立；ClawHub 页面 MIT-0 与数据许可冲突是作者自认的未决法律风险（HANDOFF 坑 #49）。

**数据线（CC BY-NC-SA 4.0）——非商业可用，义务明确：**
- 可做：Tianze（明确非商业）复制/提取/改编 kb/ 全部内容 + ui/index.html 内嵌数据。
- 必做：署名"bazi-engine · ruanxiaoer"、注明修改、**逐条保留 source 字段**、衍生数据整体以 CC BY-NC-SA 4.0 再发布（SA 传染数据衍生品）。
- 不可做：任何商业用途（付费产品/付费 API/售卖数据）；删除水印句（README 称其存在但位置不公开——**实际用关键词扫描 rules.json 未定位到**，提取时应假设其存在并人工复核）。
- 合规捷径：只用 03-classics 中标注【原文】的古籍引文（公有领域）或回溯 jinchenma94/bazi-skill 等 MIT 社区来源，则完全绕开 NC/SA；一旦使用其"条件化+置信度+建议"编译成果（来源 3），CC BY-NC-SA 全套义务触发。

---

## 11. Tianze 应该借鉴什么 / 不应该借鉴什么

### 11.1 Tianze 第一阶段目标内容的精确定位（天干/地支/月令/十神/旺衰/格局/调候/生克制化）

| 内容 | 所在文件 | 体量 | 提取难度 |
|---|---|---|---|
| 天干地支阴阳五行、十神定义/推导、藏干表、十二长生表、空亡表、地支关系表 | `kb/01-basics/ganzhi-wuxing.md` | 15KB | **低**——规范 md 表格，机器可解析 |
| 同上（纳音/时辰/遁干） | `kb/01-basics/najin.md`(5.8K)、`shichen.md`(2.8K)、`wushuhun-wuhuhun.md`(15K) | 23.6K | 低 |
| 月令取用/八格/顺逆用/格局成败/真假纯杂 | `kb/03-classics/ziping-zhenquan.md` | **4.1K** | **极低，价值密度最高**——精编【原文】+【注】，含月令优先原则与取格七误 |
| 格局歌诀/十神类象 | `kb/03-classics/yuanhai-geshi.md` | 4.6K | 低 |
| 调候（十干×十二月+原文） | `kb/03-classics/shigan-lun.md` | 20.9K | 低——按"日干→月"两级标题结构化 |
| 调候全文（十干×十二月完整） | `kb/03-classics/qiongtong-baojian.md` | 41.3K | 中——docx 转储需清洗，但含调候用神总表 |
| 旺衰三法/十干性情/滴天髓通则 | `kb/03-classics/ditian-sui-zhushu.md` | 5.6K | 低 |
| 生克制化关系表（含三会/相破等引擎没有的） | `ganzhi-wuxing.md` §地支关系 + `02-rules/classical-rules.md` | 15.8K | 低 |
| 旺衰/格局/用神/五行生克**结构化断语子集** | `kb/04-rules-db/rules.json`：pattern_* 56 + yongshen_* 72 + wuxing_* 48 + combo_* 65 + char_*（日主×旺衰）97 ≈ **338 条**，另 162 条规则带 `旺衰` 条件、295 条带 `十神` 条件 | ~130K（按占比） | **低**——JSON 规整，按 category/id 前缀过滤即可 |
| 九典籍规则摘要（格局论断带卷号出处） | `kb/02-rules/classical-rules.md` | 15.8K | 低 |

**要避开的（Tianze 第一阶段不需要，且恰是上游原创编译密度最高的部分）：**
- **神煞**：`kb/01-basics/shensha.md`(8.2K) + rules.json `shensha_*` 74 条 + 引擎 SHENSHA 24 项查法（build_ui.py:908 起）；
- **婚姻/合婚**：`02-rules/marriage.md`(4.5K) + rules.json marriage_*/hehun_*/he_* 共 ~87 条 + 引擎 analyzeHe；
- **流年/流月/流日事件类**：rules.json liunian_*/liu_*/liuyue_*/liuri_* 共 145 条 + `kb/04-rules-db/drafts/`（全部）+ 引擎 matchLiuDay/matchLiuYue/analyzeLiuDeep；
- **六亲/健康/学业**：kin_*/qinq_* 64、health_* 62、study_*/edu_* 61 条 + `《黄帝内经》`source 的 43 条健康断语；
- **五行补救/开运**：`02-rules/remedy.md` + 引擎 getRemedy（颜色/方位/数字/行业/饰品/饮食——商业化最强、命理价值最低的部分）；
- **MBTI 映射**：`02-rules/bazi-mbti.md`（11.2K）；**四法合一提示词**：`05-reference/prompt-template.md`（40.3K，超范围）。

### 11.2 应该借鉴

1. **断语 schema 极简设计**（id/category/condition/conclusion/source/confidence/suggestion）+ "未命中不强行断语"纪律 + source 字段强制化（且被写进许可证义务）——与 Tianze 溯源目标完全同构，可直接作为 Tianze 规则格式的起点再增强。
2. **KB 质量保障方法论**（比数据本身更值钱）：命中率审计（100% 命中=坏规则）、反义规则同盘矛盾检测、重复命中检测、"组合/否决"键语义写成测试。Tianze 建规则库时照抄这套三件套即可少踩一年的坑。
3. **drafts 批次工作流**：取材清单（每条标注书名·篇）→ 条件化 JSONL → 入库 → 引擎适配 → 全套回归（liuri-batch1-sources.md 是范本）。
4. **古籍"精编层/全文层"双轨保存**：shigan-lun.md 式的"按日干×月令组织、【原文】/【注】分离、给出引用格式"的精编层，比 6 份 docx 全文转储有用一个数量级；Tianze 应从精编层形态起步。
5. **evalState 的教训（反面教材的正向用法）**：把"状态"语义写成 40+ case 的大 switch，导致语义散落代码、阈值无出处、多次返工（0.55→0.75 专旺阈值、length>=5 死代码等）——Tianze 应把这些状态判定**做成显式结构化 condition DSL/数据**，而不是硬编码。
6. **CI 门禁把数据当一等公民**：连 rules.json 合法性、断语命中分布都进 CI（.github/workflows/ci.yml）。

### 11.3 不应该借鉴

1. **单体构建制**：212KB Python 字符串内嵌全部 JS + 593KB 单文件 UI——不可维护，是 Skill 市场分发形态的历史包袱；Tianze 用正常的模块化工程即可。
2. **阈值型旺衰/喜用公式当作权威**：0.6/0.4 旺衰、1.5 月令加权、0.75/0.15 专旺双条件均为拍定值（部分有"大样本标定"注释但无古籍依据），Tianze 若引用必须自己重新论证。
3. **调候只到季节粒度**：引擎 TIAOHOU_MAP（build_ui.py:1185 附近）比其自家古籍 shigan-lun.md（按月）粗——Tianze 做月粒度调候数据即可超越。
4. **指纹水印 + monitor_usage 防盗用机制**：与 Tianze 的开源定位相悖，不学（但要 awareness：从它提取数据时水印声明存在）。
5. **坑式交接文档（HANDOFF 80K）的体量**：信息密度极低、强人格化，Tianze 研究笔记不需要模仿其文档文化。
6. **商业生态耦合**：README 一半篇幅在推 C 端付费产品"本初"和微信引流，研究时注意剥离营销叙事（如"1000 条断语"的含金量需按 §11.1 的分类自行评估，其中 ~660 条属于 Tianze 不需要的领域）。

---

## 12. 未解疑问

1. **rules.json description 与实际条数矛盾**（789 vs 1000）究竟是版本滞后还是两次清理有合并冲突？git 历史可查但未深入。
2. **溯源指纹句**具体内容/位置未找到：README 声称内嵌于 rules.json，用 "bazi-engine/ruanxiaoer/指纹/本断语库" 等关键词扫描 conclusion/suggestion/source 均未命中。可能藏在某条正常断语文案中（这正是水印设计目的）——若 Tianze 决定提取，需要人工逐条比对以排除。
3. **"advice" 字段 91 条**与 suggestion 并存的 schema 漂移何时引入、patch_suggestions.py 是否该负责清理，未验证。
4. `rules-template.json` 的 `月令` condition 键在生产库与引擎中均不存在——是早期设计残留，还是计划中未实现的能力？（若实现，调候/月令类规则会需要它。）
5. 03-classics 六份 docx 的**原始 docx 文件不在仓库**，提取工具 `tools/archive/extract_docx.py` 存在但输入缺失——古籍全文无法在本仓库内复现提取质量，只能信任现有 md。
6. jinchenma94/bazi-skill 的具体贡献边界（LICENSE-DATA 称"部分基础表与规则整理"参考它）没有逐文件标注——01-basics 哪些表来自 MIT 社区、哪些是本项目原创，无法从仓库内区分；若 Tianze 想走"MIT 来源"合规捷径，需另行研究该上游仓库。
7. 断语生成由 gen_rules.py 模板批量产出（同文案复用如 yongshen_jin_1/2），其 conclusion 与古籍原文的贴合度有多少经过人工核对，只有 drafts-sources.md 覆盖流日/流月两批，其余批次无取材清单存档。
