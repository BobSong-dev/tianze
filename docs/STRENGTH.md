# STRENGTH · 旺衰方法说明（dimension / weighted / fuyi）

> 原则：不存在"官方唯一旺衰真值"。三方法并列输出于 `strength.methods[]`，
> 每个结论都能回答：哪个方法、用了哪些参数、基于哪些事实、为什么得出该结果。
> dimension 无 verdict，不参与 agreement（R22）。

## 1 · dimension（dimensional_v1，M4.1）

- **是什么**：得令/得地/得势三维定性事实判定（`result: bool + reason[]`），零评分。
- **不是什么**：不给强弱结论、不算分、不参与 agreement。
- **规则**：得令 = 月令状态旺（R17，按月支本气五行）；得地 = 日主四支藏干有同字根（R15）；得势 = 年月时干印比透干 ≥2（`DE_SHI_THRESHOLD`，PROJECT_HEURISTIC）。
- **争议**：得势阈值 2 为作者口径；"相"不算得令是严格口径（宽松派以相为半得令）。

## 2 · weighted（weighted-v1，M4.2）

- **是什么**：逐字单位加权求和的工程量化方法。单位 = 可见天干（日主除外）+ 全部藏干；五行归类（比劫/印→support，食伤/财/官杀→drain）；月柱单位 ×`monthMultiplier`；`score = support/(support+drain)`；四级阈值映射五级 verdict。
- **不是什么**：不是传统命理公认算法；不存在"月令 ×1.5 是古法"这回事——全部权重是现代工程化方案。
- **参数（全部随结果输出于 `params`）**：

| 参数 | 默认 | 来源级别 | 出处 |
|---|---|---|---|
| visibleStemWeight | 1.0 | PROJECT_REFERENCE | bazi-atlas engine.mjs R20（Horosa 100 等比不同） |
| mainQiWeight | 1.0 | PROJECT_REFERENCE | Atlas 1.0 / Horosa 100 |
| middleQiWeight | 0.5 | PROJECT_REFERENCE | Atlas 0.5（Horosa 0.6） |
| residualQiWeight | 0.25 | PROJECT_REFERENCE | jiwenxu / ruan 0.25 |
| monthMultiplier | 1.5 | PROJECT_REFERENCE | Horosa/ruan ×1.5（Atlas ×2） |
| strongThreshold / weakThreshold | 0.55 / 0.45 | PROJECT_REFERENCE | Atlas:778 与 Horosa:148-149 同值 |
| extremeStrong/WeakThreshold | 0.65 / 0.35 | ENGINEERING_HEURISTIC | Tianze 五级扩展，无上游来源 |

- **防重复计分（ADR-022）**：通根、得令**不设**独立计分项——它们与藏干单位/月柱乘数是同一批事实。测试锁定：伪造不同根输入 → weighted 结果不变。
- **可解释性**：`contributions[]` 逐单位给出 factor/effect/value/reason，总分可完全复现。
- **争议**：ratio 模型对"虚浮无根"与"有根"的区分弱（只看元素分布）；日主自身不计分是口径选择。

## 3 · fuyi（fuyi-v1，M4.2）

- **是什么**：扶抑路径的**规则级联**：只消费派生特征（得令？根几处？印比几透？食伤财官几透？月令是否克日？），计票后按首中即停的九条规则给出 verdict + confidence；证据冲突时输出 **UNCERTAIN**。
- **不是什么**：不是 weighted 换参数（不逐字求和、无 ratio）；不是古籍的"扶抑法"原文。
- **计票表（R21，全部 +1 除月令克日 +2）**：
  - 支持票：得令 / 月令相 / 根≥1 / 根≥2 / 印比≥1 / 印比≥2
  - 克泄票：休 / 囚死(+2) / 食伤财官≥1 / ≥2 / 无根 / 无印比
- **级联（首中即停）**：R21-1 得令+多根+多印比→极强(high)；R21-2 失令+无根+无印比+月克日→极弱(high)；R21-3 失令+无根+无印比→极弱(medium)；R21-4 得令+仅月令单根+无印比+克泄重→**UNCERTAIN**(high)；R21-5 票差≥3→偏强(medium)；R21-6 →偏弱(medium)；R21-7 →偏强(low)；R21-8 →偏弱(low)；R21-9 均衡→中和(low)。
- **数学可达性注记**：得令 ⟹ 月支藏日主 ⟹ 必有月令根——"得令+无根"不可达，故 R21-4 捕捉的是"得令但仅月令单根+克泄重"的信号对冲。
- **争议**：计票与级联均为作者口径（ENGINEERING_HEURISTIC）；三外干全部分类为印比或克泄耗，无中间态。

## 4 · agreement（R22）

- 只比较带 verdict 且非 UNCERTAIN 的方法；UNCERTAIN = 弃权。
- 全部一致 → HIGH；存在相同对或全部落在相邻档 → PARTIAL；其余 → DISPUTED；有效 verdict <2 → 字段缺席。
- Tianze 不裁决——agreement 只描述方法间关系，不指定"正确答案"。
