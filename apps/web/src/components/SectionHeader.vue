<script setup lang="ts">
/**
 * SectionHeader — 统一页面/小节标题层级。
 * 结构：编号 → 标题 → 右侧操作 → 导语 → 边界说明。
 * 「编号」是研究路径的定位符（非装饰），如 03 / 08。
 */
withDefaults(defineProps<{
  /** 研究路径序号，如 "03" */
  index?: string;
  title: string;
  lede?: string;
  /** 边界/纪律说明，等宽小字，置于导语下方 */
  note?: string;
  /** 标题层级：h1 用于独立页面，h2 用于工作区小节 */
  level?: 1 | 2;
}>(), { level: 1 });
</script>

<template>
  <header class="sec-head">
    <div class="sec-head-top">
      <span v-if="index" class="sec-head-idx" aria-hidden="true">{{ index }}</span>
      <component :is="`h${level}`">{{ title }}</component>
      <div v-if="$slots.aside" class="sec-head-aside"><slot name="aside" /></div>
    </div>
    <p v-if="lede" class="sec-head-lede">{{ lede }}</p>
    <p v-if="note" class="sec-head-note">{{ note }}</p>
  </header>
</template>
