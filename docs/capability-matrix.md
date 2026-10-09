# Tianze 能力覆盖矩阵（M38）

- 能力 36 项：BLOCKED 4、COMPLETE 25、EXPERIMENTAL 1、PARTIAL 4、UNSUPPORTED 2
- 证据指针验证：全部通过

| 能力 | 状态 | 证据 | 备注 |
|---|---|---|---|
| 排盘（四柱/藏干/十神/纳音） | **COMPLETE** | tests/test_cross_channel.py、tests/test_smoke.py |  |
| 节气边界/立春/晚子时/时区/DST | **COMPLETE** | tests/test_temporal_boundaries.py | R1/R4 口径；lunar-python 独立对账 |
| 真太阳时/地方时 | **PARTIAL** | tests/test_temporal_boundaries.py | 支持 clock/true_solar/mean_solar convention；经度输入依赖用户提供 |
| 大运起运/顺逆排 | **COMPLETE** | tests/test_temporal_boundaries.py、tests/test_timeline.py |  |
| 旺衰多方法（dimension/weighted/fuyi） | **COMPLETE** | tests/test_strength.py | R19 多方法并列不裁决（ADR-059 实证） |
| 通根透干/月令（RootEvidence） | **COMPLETE** | tests/test_relations.py、tests/test_special_patterns.py | R15 定性深度；M28 根气分级入假从说 |
| 格局（正格/评估/救应） | **COMPLETE** | tests/test_pattern.py | R25 评估状态 |
| 调候 | **COMPLETE** | tests/test_tiaohou.py | M6 desired/present 分离 |
| 刑冲合害破/三合三会/三刑 | **COMPLETE** | tests/test_relations.py | R9 多重并存不裁决 |
| 天干五合/化气候选（DTZ-47 真化条件） | **COMPLETE** | tests/test_special_patterns.py | 合而不化/隔位/印比/争合阻化（M35 三态结构化） |
| 争合（QBT-甲-20/QBT-乙-08/DTZ-47） | **PARTIAL** | tests/test_property_fuzz.py | 家族计数+岁运事件落地；「见辰化合」「破干从化」条件化变体待考证 |
| 虚神/拱夹/暗合/填实（DTZ-10/ZP-05/SPZY-34） | **COMPLETE** | tests/test_relations.py、tests/test_temporal_rules.py | 三态解释链；候选永不升格（ADR-062） |
| 空亡（六旬旬空） | **PARTIAL** | tests/test_property_fuzz.py | 表+差分验证落地；仅消费于贵人三要件——作用位置泛化待引文 |
| 天乙贵人/拱贵/六乙鼠贵（SS-R16/17/ZP-05/06） | **COMPLETE** | tests/test_property_fuzz.py | 三要件条件化；裸贵人不输出独立事实（ADR-064） |
| 暗冲格（飞天禄马/井栏叉/刑合） | **EXPERIMENTAL** | tests/test_special_patterns.py | xushiOuter 候选；外格说 vs 伤官变格说两注记（ADR-062/063） |
| 子邀巳（ZP-11） | **BLOCKED** |  | OCR 残缺（取印为用口径缺失）+ 泛化 ~27%——不落地引擎，待语料 |
| 从格（真从/假从 DTZ-49） | **COMPLETE** | tests/test_special_patterns.py | E1/E2/E3 结构化证据链；DISPUTED 保留（不因名造调参） |
| 专旺 | **COMPLETE** | tests/test_special_patterns.py |  |
| 化气（真化/假化） | **PARTIAL** | tests/test_special_patterns.py、tests/test_temporal_rules.py | 真化条件结构化（M35 三态）；假化岁运敏感；化成与否永不判定 |
| Temporal Delta（strength/pattern/tiaohou/special/bingyao/tongguan/tengod） | **COMPLETE** | tests/test_temporal_delta.py | EXPERIMENTAL/UNSUPPORTED 显式标注 |
| 流月/流日（节气窗口/JDN） | **COMPLETE** | tests/test_timeline.py、tests/test_temporal_boundaries.py |  |
| Temporal Replay（逐层快照/Theme Delta） | **COMPLETE** | tests/test_property_fuzz.py | M30-M33；SDK/CLI/API/Web/AI 五通道（include_temporal_replay） |
| 岁运规则（日犯岁君/刃头财/伏吟/反吟/天克地冲…） | **COMPLETE** | tests/test_temporal_rules.py |  |
| 争合岁运事件（TR-DTZ-47） | **COMPLETE** | tests/test_property_fuzz.py | M37 家族计数口径 |
| 关系解释链（三态/引文/条件） | **COMPLETE** | tests/test_property_fuzz.py | M25 三态 + M33 反查 + M36 合化状态（18 条引文注册表） |
| 合去/合绊/微根受制（E1/E2/E3×TR-SP-08） | **COMPLETE** | tests/test_special_temporal.py | E3 合去调制（M34）；文字注记→结构化依据（M35/M36） |
| 跨层一致性审计 C1-C8 | **COMPLETE** | tools/cross_layer_audit.py | 1045 例全 0；入质量门 |
| Grounded AI（claim/refId/状态保持） | **COMPLETE** | tests/test_ai.py、tests/test_ai_evaluation.py +1 | 真实 Provider 评测另见 BLOCKED 项 |
| AI 真实 Provider 评测 | **BLOCKED** |  | 无 API Key——mock 评测全绿，真实成绩不伪造 |
| raw OCR 原文核对 | **BLOCKED** | tools/source_coverage.py | 556/556 sourceFile 缺失（知识库 zip 未入库）——引用路径/页码可回溯 |
| 命例流年层回放 | **BLOCKED** | tools/state_replay_audit.py | 年锚多解（60 年周期）——UNRESOLVED，待唯一年份语料 |
| SDK/API/CLI/Web 跨渠道一致 | **COMPLETE** | tests/test_cross_channel.py | M38 四样本三通道核心语义字段一致 |
| Web（排盘/岁运工作台/知识图谱/回放时间轴） | **COMPLETE** | apps/web/e2e/ | 8 项 E2E；移动端/打印优化见 M39 |
| 报告（Markdown/HTML/打印） | **COMPLETE** | tests/test_export.py | 回放/解释链/未成立候选章节（M32/M36）；打印样式 M39 细化 |
| 自由人生事件预测/医疗寿命/投资赌博 | **UNSUPPORTED** |  | 任务书禁令（永不实现） |
| 流时（时辰以下粒度） | **UNSUPPORTED** |  | M12 起明确不做 |

> 「存在代码」不视为功能完整：COMPLETE 均有多层测试与跨层审计支撑；
> BLOCKED 项如实记录外部限制（raw OCR/API Key/年锚），不伪造覆盖。
