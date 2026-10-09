# Tianze v0.4.0 Release Notes（相对 v0.3.0）

版本：0.4.0（开发线 0.4.0.dev0，M23-M40 期间形成）。
上一正式基线：v0.3.0（tag 冻结于 5821c84）。

## 规模与规模口径

- 可执行规则 218 → **223**（temporal 16→20：TR-SP-08 假从岁运敏感、
  TR-DTZ-47 争合、TR-DTZ-10 扩展、TR-DTZ-11 旺衰冲；event 20→21：
  EV-REL-06 婚变之微）。
- Python 测试 525 → **641**；浏览器 E2E 8 → **11**；质量门 20 → **23 步**。
- 引文注册表新增（DTZ-47/DTZ-18/SS-R16/SS-R17/ZP-06 等，13→18 条）。

## 新能力（按里程碑）

- **M23** DTZ-47 真化条件（隔位/印比阻化/逢龙而运）、TR-DTZ-11 旺者冲衰、
  EV-REL-06 婚变之微、版本纪律（tag 冻结 + dev 线）。
- **M24-M26** 拱夹/虚神/暗合关系引擎（arch/hidden_combination）、
  未成立候选（blockedRelations）、填实/拱破状态机、天乙贵人表与拱贵、
  六乙鼠贵三要件、旬空引擎（六旬表，lunar-python 差分验证）、
  跨层一致性审计 C1-C5。
- **M27-M28** 来源治理（source_coverage，raw 缺失如实 BLOCKED）、
  真从/假从两说（SP-CG-E2 + 根气分级）、假从岁运敏感（TR-SP-08）。
- **M29-M30** 旬空差分锁定、微根受制、逐层岁运状态机 temporal_replay
  （出现→填实→拱破→去填→再次填实）。
- **M31-M33** Replay 全链产品化（SDK 选项/CLI --replay/Web 时间轴/AI
  replay:* Grounding）、Theme Delta（主题→事件反查）、悬空引用审计 C7。
- **M34-M37** 合去调制、合化状态结构化（三态+引文）、争合结构化推理
  （zhenghe_families + TR-DTZ-47）、C8 同构审计。
- **M38-M40** 能力覆盖矩阵（36 项证据指针验证）、跨渠道一致性
  （SDK=CLI=API）、21 场景端到端验收、产品体验（报告封面/摘要/术语/
  A4 打印、Web 总览摘要、移动端适配、用户指南）。

## 修复的重要缺陷

- E2E 摘要卡类名冲突（6 项基线失败当场捕获）；HTML 报告 ev-None 崩溃；
  争合审计匹配规则（首候选 vs 最少阻化）；replay 自对伏吟误判刑冲；
  release_check 陈旧 wheel 遮蔽；dev 版本 bump 规则错算（ADR-060）。

## 已知限制（Known Limitations）

见 `docs/known-limitations.md`。

## 升级与迁移

- Schema：knowledge 1.1.0 / case 1.0.0 / analysis 1.0.0 / delta 1.0.0 /
  event 1.0.0 / interpretation 1.1.0——**无 breaking**（全部 additive 字段：
  blockedRelations / relationExplanations / replay / xushiOuter /
  specialFindings.label / themeDelta 等）。
- 数据路径：`tianze/paths.py`（TIANZE_DATA_DIR → repo knowledge/ → 打包
  _data）；安装模式 manifest 自检。

## 免责

本引擎输出为命理结构分析与古籍知识展示，候选状态与流派分歧如实保留，
**不构成任何吉凶或现实事件预测**。
