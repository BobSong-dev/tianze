# 08 · 命例审计（CASE AUDIT）

> 生成：`tools/normalize_cases.py`（确定性）；统计：`knowledge/normalized/cases-manifest.json`。
> 审计日期：2026-10-01。原始文件零修改。

## 一、实际统计（程序实测，不采信知识库自述数量）

| 项 | 值 |
|---|---|
| 结构化命例块（`## 命例ID：`） | 748 |
| 检索索引行（400 组，脚本提取的整理层） | 400 |
| **解析成功** | **1147**（结构化 748 + 索引 399，0 解析失败） |
| 四柱可解析（已跑引擎） | 1045 |
| 四柱 UNRESOLVED（OCR 不确定等） | 102 |
| CaseIdentity 候选重复组 | 60（125 例涉重复标记，未自动合并） |
| 跨文件 Case ID 冲突 | 27+（甲木分部一 vs 甲乙木复用 QBTM-甲-01…27，@2 后缀处理） |
| 唯一四柱+姓名+书籍键 | 980 |

知识库自述"530+ 则 + 400 组索引"——实测结构化块 748（含少量区间头/存目），
与自述不一致处已按程序实测为准。

## 二、两种来源格式

1. **结构化命例块**（12 字段：四柱/姓名/出处/徐乐吾最终判断/分析步骤/涉及规则/大运/流年/实际事件/用途）——质量 B（有页码）；
2. **检索索引行**（`- **姓名**｜四柱｜月节｜PDF页｜断语上下文`）——自述为"整理归纳"层，质量 C；
   OCR 错字照录（己/已/巳、壬/王）。

## 三、分层与分离（M7 核心）

- **Case Fact**（四柱/性别/生时原文）｜**Author Interpretation**（作者判断，AUTHOR_INTERPRETATION 层）｜
  **Historical Claim**（实际事件，全部 HISTORICAL_CLAIM——**不是已验证真事**）；
- **sourceAnalysis**（原书分析）与 **tianzeAnalysis**（引擎派生）两个独立字段，永不混合；
  命中校验：Case Separation Test（test_verification_cases.py）。

## 四、引擎派生（tianzeAnalysis）

1045 例可解析四柱已运行 Tianze 引擎（strength 三方法 / pattern / tiaohou——
全部基于干支，无需出生日期）。派生仅作"未来对比"素材，**不构成对原书判断的
评价**，也与监督学习无关（命例不是训练标签）。

## 五、Rule↔Case 关联（`knowledge/indexes/cases/byRule.json`）

| 关系 | 数量 | 语义 |
|---|---|---|
| EXPLICITLY_CITED | 17 个调候候选（95 处引用） | 命例块"涉及规则"明确引用（高信任） |
| ENGINE_TRIGGERED | 352 个规则键有触发 | **Tianze 引擎触发——不冒充"古人明确用了这条规则"** |
| INFERRED_MATCH | 0（预留，不自动填） | 结构推断（低信任） |

## 六、对比（CaseComparison，`case-comparisons.json`）

机械化可辩护对比仅一类：命例明确引用的规则效果干 vs 引擎触发目标干。
当前：426 例可比（**420 一致 / 24 差异**）；其余 721 例进 unresolved
（"语义级对比需人工复核"）。**不自动判定 Tianze 或古籍谁正确。**

## 七、已知问题

1. QBTM 跨文件 ID 复用（27+ 处）——@2 后缀，released 后冻结；
2. 102 例四柱 UNRESOLVED（OCR 错字如"己/已/巳"），保留不确定不猜测；
3. 命例引用的规则 ID 含非调候域（MLD-X01 等），validate_cases 登记不阻断；
4. 检索索引行的"断语上下文"为脚本截取，语义完整性弱（质量 C 的原因）。
