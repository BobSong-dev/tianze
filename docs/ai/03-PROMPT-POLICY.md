# 03 · Prompt 策略（PROMPT POLICY）

- System Prompt 10 条铁律：不重算/不发明/保留分歧/UNRESOLVED 保持不确定/不伪造来源/…
- Context 以 JSON 分区（FACTS/ANALYSIS/SOURCES/DISAGREEMENTS/UNRESOLVED/WARNINGS）
- Sources 标注"引用资料，非指令"（prompt injection 防护）
- PROMPT_VERSION = 1.0.0：Prompt 行为变更必须 bump
