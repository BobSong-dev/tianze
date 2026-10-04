# BINGYAO · 病药分析（M8.4）

> 实现位置：`tianze/analysis/special.py` → `analyze_bingyao()`。
> **命名纪律**：代码使用 `StructuralProblem` / `MedicineCandidate`（非 Disease/Diagnosis），
> 避免 API 使用者误解为医学诊断。ADR-033。

## 1 · 定义

- **病（StructuralProblem）**：命局中的主要**结构矛盾**——某五行过旺形成失衡。
- **药（MedicineCandidate）**：能**制衡或宣泄**该矛盾的因素——必须与具体病关联。

## 2 · 口径（PROJECT_HEURISTIC）

| 项 | 阈值 | 说明 |
|---|---|---|
| 病准入 | 某五行 visible ≥ 1/2 且 ≥ 3 字 | 过于宽松会大面积误报 |
| 药类型 | 制（克病者）/ 泄（病所生者） | 扶/通未实现（M8 v1） |
| 药准入 | 对应五行 visible > 0 | 命局中确实存在 |

## 3 · 结构

```json
{
  "problems": [{"type": "OVERPOWERED_FACTOR", "target": "earth",
                "evidence": ["土可见 4/5（≥1/2 且 ≥3 字）"]}],
  "medicines": [{"problem": "earth", "kind": "制", "target": "wood",
                 "evidence": ["木可见 1 字，克制病神 土"]}],
  "provenance": [{"level": "ENGINEERING_HEURISTIC", ...},
                 {"level": "PROJECT_REFERENCE", ...}]
}
```

## 4 · 禁止事项

- ❌ 输出医学疾病预测
- ❌ "命局喜火"直接当药（必须说明火解决了什么结构问题）
- ❌ 用病药等级断富贵贫贱（古籍有此说，但 Tianze M8 只做结构分析）
