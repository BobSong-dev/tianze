# 06 · 调候引擎（TIAOHOU）

> M6 交付：`tianze/analysis/tiaohou.py` + `knowledge/rules/tiaohou/rules.json`
> （182 条 ExecutableRule，10 日主 × 12 月支全覆盖）。

## 定位

调候**不是**旺衰换一套名字——它是独立的观察维度：
寒暖燥湿的体系认为该格需要什么干（desired）、命局是否已有（present）、
条件与例外如何改变作用、依据是哪条规则哪句原文。

## 数据来源

- 主源：徐乐吾八字知识库（用户提供 zip）之《穷通宝鉴评注》逐月规则
  （QBT 213 条 + ZHY 66 条候选）。
- 流程：normalize（556 条全解析）→ draft（启发式 103/120 命中）
  → **人工复核**（对照候选原文逐格定 targets）→ 182 条 ExecutableRule
  → 校验（validate_knowledge.py）→ 测试（test_tiaohou.py 14 项）。

## 结果结构（TiaoHouResult）

```json
{
  "dayMaster": "甲", "monthBranch": "寅", "resolved": true,
  "recommendations": [
    {"targetStem": "丙", "element": "火", "priority": "primary",
     "present": true, "positions": ["hourStem"],
     "ruleIds": ["TH-QBT-甲-01-寅"],
     "quote": "春月之木，渐有生长之象…",
     "source": {"book": "穷通宝鉴评注", "chapter": "…", "pages": [34, 35]}}
  ],
  "evidence": ["…需要 丙（火·primary）— 命局已见（hour）"],
  "conflicts": ["甲-未：五六月合论与六月专论重叠（specific-over-general）"],
  "conditions": [...], "exceptions": [...], "ruleIds": [...]
}
```

## 关键设计

1. **desired ≠ present**：体系认为需要的干与命局实有严格分离；
   present 检查四柱可见天干（含日主），positions 精确到柱位。
2. **specificStem 优先**：规则保留丙/丁/壬/癸等具体天干，
   `element` 是派生字段——不过早降维成五行。
3. **条件可表达**：卯月（雨水后）、酉月（白露/秋分）、未月（大暑分界）、
   午月（建禄）、辰月（清明/谷雨）等节气与结构条件进入 conditions；
   条件未满足 → 规则休眠并写明原因（不静默）。
4. **例外可表达**：乙子忌癸出干、丁子无比印从杀、辛申忌戊透——
   avoidStem 效果 + exceptions；命中时写入 evidence。
5. **冲突不静默**：甲未（specific-over-general）、己申（从正文）登记
   conflicts.json 并在结果 conflicts[] 中可见。
6. **UNRESOLVED 诚实**：知识库缺格时 `resolved=false`（当前 120/120 无缺格）。
7. **反查链完整**：recommendation → ruleIds → ExecutableRule → candidateId →
   原文引文 → 书名/章节/PDF 页码（测试逐一断言）。

## 边界（禁止事项）

不输出吉凶（"因此富贵"不存在于本模块）；不做用神综合决策（那是后续
里程碑的融合层）；不因追求 120/120 而编造无出处规则。
