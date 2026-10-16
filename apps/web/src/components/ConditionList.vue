<script setup lang="ts">
/**
 * ConditionList — 成立条件核查表。
 * 直接消费后端 conditions[{text, satisfied}]，前端不做条件求值。
 */
defineProps<{ items: { text: string; satisfied: boolean }[] }>();
</script>

<template>
  <div v-if="items?.length" class="cond-list">
    <div
      v-for="(c, i) in items"
      :key="i"
      class="cond"
      :class="c.satisfied ? 'is-met' : 'is-unmet'"
    >
      <span class="cond-mark" aria-hidden="true">{{ c.satisfied ? "✓" : "✗" }}</span>
      <span class="cond-text">{{ c.text }}</span>
      <span class="sr-only">{{ c.satisfied ? "条件成立" : "条件未成立" }}</span>
    </div>
  </div>
  <p v-else class="note">该关系未附成立条件。</p>
</template>
