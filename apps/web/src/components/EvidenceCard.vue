<script setup lang="ts">
/**
 * EvidenceCard — 一条可追溯观察的最小单元。
 * tone 只影响左侧刻痕取色（正/负/冲突/救应/中性），不改变证据文本。
 */
withDefaults(defineProps<{
  title?: string;
  /** 证据方向 */
  tone?: "neutral" | "plus" | "minus" | "warn" | "conflict" | "rescue";
  /** 前置等宽小标（规则号、引用 id、分析域） */
  refId?: string;
}>(), { tone: "neutral" });
</script>

<template>
  <div class="ev-card" :class="`is-${tone}`">
    <div v-if="title || refId || $slots.head" class="ev-card-head">
      <slot name="head">
        <span v-if="refId" class="rule-card-id">{{ refId }}</span>
        <span v-if="title" class="ev-card-title">{{ title }}</span>
      </slot>
    </div>
    <div class="ev-card-body"><slot /></div>
    <div v-if="$slots.foot" class="mt-3"><slot name="foot" /></div>
  </div>
</template>
