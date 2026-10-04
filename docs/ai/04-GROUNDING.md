# 04 · Grounding 校验（GROUNDING）

程序化检查 AI 输出是否有不存在的 ID/越界判断/伪造来源。

## 检查类型

| 类型 | 说明 |
|---|---|
| UNKNOWN_EVIDENCE_ID | evidenceId 不在 Context |
| UNKNOWN_SOURCE_ID | sourceId 不在 Context |
| UNSUPPORTED_PATTERN | 提及不在候选中的格局 |
| FABRICATED_CLASSICAL_SOURCE | 引用 Context 中不存在的古籍 |
| VERIFICATION_MISREPRESENTATION | 声称已人工核验但无 HUMAN_VERIFIED |
| UNRESOLVED_ASSERTED | 将 UNRESOLVED 写成确定性结论 |

## 处理

- grounding_issues 非空 → `grounding_passed=false` → UI 显示"存在 grounding 警告"
- 不自动 retry（第一版）；后续可加一次 retry
