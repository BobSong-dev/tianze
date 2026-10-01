# 04 · 来源与溯源（SOURCE PROVENANCE）

## 来源五级（SourceKind，domain.models）

| 级别 | 定义 | 当前知识库映射 |
|---|---|---|
| CLASSICAL_TEXT | 古籍原文（含原书引述的更早古籍） | 穷通宝鉴/造化元钥原文、滴天髓原文、子平真诠原文 |
| COMMENTARY | 注家评注 | 徐乐吾评注/补注/原著（命理一得、子平粹言、守素室丛谈、子平一得）；**孙正治注译、赵嘉宁今译属 MODERN_BOOK，不得标此级** |
| MODERN_BOOK | 现代著作/整理本/今译 | 孙正治注译、赵嘉宁今译（未进入 provenance 主链） |
| OPEN_SOURCE_PROJECT | 开源项目经验 | Horosa/jiwenxu/ruan/atlas/SOP 附表（Phase 0 已核实源码行号者） |
| TIANZE_HEURISTIC | Tianze 工程化推导 | 如辛-子月 need=丙（由"困丙"反推） |

## 规则来源分级（RuleLevel，规则 provenance.level）

| 级别 | 定义 | 当前数量 |
|---|---|---|
| CLASSICAL_EXPLICIT | 已核实古籍原文（须携带引文，Quote Test 强制） | 182（调候规则第二级 provenance——引文即候选原文） |
| PROJECT_REFERENCE | 参考某项目/知识库的整理（须写明 project） | 182（调候规则第一级：徐乐吾知识库条目） |
| ENGINEERING_HEURISTIC | 工程化量化/推导（无传统出处） | 按需（如辛-子月） |
| UNVERIFIED | 未验证 | 占位 |

> 注：CLASSICAL_EXPLICIT 的准入 = 知识库已提供"原文+章节+PDF 页码"三要素。
> 但 **人工逐句核对原书扫描件尚未完成**（OCR 未全核），故数据质量等级最高只给 B；
> 引文层面 provenance 与质量等级是两个独立维度。

## 数据质量等级（QualityGrade）

| 级 | 定义 | 当前数量（556 候选） |
|---|---|---|
| A | 古籍原文+明确版本+页码+**已人工核对** | 0（诚实边界） |
| B | 原文+页码，OCR 未完全人工复核 | 227 |
| C | 现代注家/评注/整理（有页码或引文） | 329 |
| D | 来源不完整 | 0 |

## 可追溯链示例（真实数据）

```text
TiaoHouRecommendation(target=丙, present=false)
 └ ruleIds: ["TH-QBT-甲-01-寅"]
    └ ExecutableRule TH-QBT-甲-01-寅
       ├ candidateId: QBT-甲-01
       │   └ originalQuotes[0]: "春月之木，渐有生长之象，春初，犹有余寒，当以火温暖…"
       │   └ source: 《穷通宝鉴评注》·卷一·三春甲木总论/正月甲木；PDF第34-35页
       └ provenance: [PROJECT_REFERENCE 徐乐吾八字知识库,
                      CLASSICAL_EXPLICIT 原文引文（经评注本页码定位）]
```

任何调候建议都能沿此链反查到：具体规则 → 候选 → 原文 → 书名/章节/页码。
