# TONGGUAN · 通关分析（M8.5）

> 实现位置：`tianze/analysis/special.py` → `analyze_tongguan()`。
> 通关**不是**"一句喜某五行"——而是明确哪两个力量形成对峙、什么因素桥接、桥是否实际存在。

## 1 · 定义

- **ConflictPair（对峙）**：两个五行 A 克 B，且力量显著不均（一方 ≥ 另一方 2 倍）。
- **BridgeCandidate（桥接候选）**：五行 C 满足 A 生 C 且 C 生 B 的生链路径。

## 2 · 口径（PROJECT_HEURISTIC）

| 项 | 阈值 | 说明 |
|---|---|---|
| 对峙准入 | 双方均有可见单位且一方 ≥ 另一方 2 倍 | 均衡不算对峙 |
| 桥检索 | A 生 C 且 C 生 B（五行生克图） | 复用 `_GEN` 图，非字符串规则 |
| 桥存在 | C 的 visible > 0 | 命局可见干支中有桥 |

## 3 · 结构

```json
{
  "conflictPairs": [
    {"conflict": {"from": "METAL", "to": "WOOD"},
     "evidence": ["金 4 字 vs 木 1 字（≥2 倍对峙）"]}
  ],
  "bridges": [
    {"conflict": {"from": "METAL", "to": "WOOD"}, "bridge": "WATER",
     "present": true, "positions": ["1"], "evidence": ["通关路径 金 → 水 → 木（桥已存在 2 字）"]}
  ],
  "provenance": [...]
}
```

## 4 · 算法

基于五行生克图（非字符串规则）：
```python
for a in Element:
    for b in Element:
        if _CTL[a] == b:  # A 克 B
            bridge = _GEN[a]  # A 所生 = 桥候选
            # A → bridge → B 路径验证：bridge 必须生 B
            if _GEN[bridge] == b and bridge != b:
                # 检查命局中 bridge 是否存在
```

## 5 · Provenance

- Tianze 元素图模型（ENGINEERING_HEURISTIC）
- jiwenxu `interactions.py` 贪生忘克概念 + Horosa 通关派（PROJECT_REFERENCE）
