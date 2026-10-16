<script setup lang="ts">
/**
 * StatusBadge — 后端受控状态词汇的唯一呈现出口。
 *
 * 纪律：
 *  - 中文受控词映射集中在 presentation/vocab.ts，本组件不新增语义；
 *  - 状态原码始终通过 title 悬停可核（可审计性）；
 *  - 未收录的 code 原样显示，绝不猜测含义、绝不升级为确定性结论。
 */
import { computed } from "vue";
import { statusMeta } from "../presentation/vocab";

const props = withDefaults(defineProps<{
  /** 受控状态原码（CANDIDATE / DISPUTED / BLOCKED / …） */
  code?: string | null;
  /** 语义变体：状态 / 规则号 / 证据方向 / 中性 / 警告 */
  variant?: "status" | "rule" | "pos" | "neg" | "mute" | "warn";
  /** 直接给中文标签（对非状态枚举，如领域名、来源层级） */
  label?: string;
  size?: "sm" | "md" | "lg";
  /** title 提示：默认给出「原码 + 状态边界说明」 */
  title?: string;
}>(), {
  variant: "status",
  size: "sm",
});

const meta = computed(() => statusMeta(props.code));
const isStatus = computed(() => props.variant === "status" && Boolean(props.code));

const classes = computed(() => [
  "badge",
  props.size === "lg" ? "badge-lg" : "",
  isStatus.value ? `st-${meta.value.tone}` : "",
  props.variant === "rule" ? "is-rule" : "",
  props.variant === "pos" ? "is-pos" : "",
  props.variant === "neg" ? "is-neg" : "",
  props.variant === "mute" ? "is-mute" : "",
  props.variant === "warn" ? "is-warn" : "",
]);

const text = computed(() => props.label ?? (isStatus.value ? meta.value.label : (props.code ?? "")));

const tip = computed(() => {
  if (props.title) return props.title;
  if (!isStatus.value) return undefined;
  const hint = meta.value.hint;
  return hint ? `${props.code} — ${hint}` : (props.code as string);
});
</script>

<template>
  <span :class="classes" :title="tip">{{ text }}</span>
</template>
