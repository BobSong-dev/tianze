# 06 · Evaluation（EVALUATION HARNESS）

## 规则式检查（非 LLM-as-judge）

- test_grounding_pass_clean_result: 清洁结果 → 0 issues
- test_grounding_detects_unknown_source: 伪造来源 → FABRICATED_CLASSICAL_SOURCE
- test_grounding_detects_wrong_pattern: 错误格局 → UNSUPPORTED_PATTERN
- test_grounding_detects_verification_misrepresentation: 验证状态越界
- test_grounding_detects_unresolved_asserted: UNRESOLVED → 确定性

## Mock Provider E2E

- test_mock_provider_interpret_passes_grounding: 全链路通过
- test_mock_provider_e2e: metadata 版本信息完整

CI 只使用 Mock Provider，不依赖付费模型 API。
