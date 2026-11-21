<script setup lang="ts">
/**
 * ElementBars — 五行结构。
 * 展示引擎 elementCounts（visible / hidden），8 格刻度可数。
 * 不改变任何计数口径，不做旺衰判断。
 *
 * 键名归一：引擎在 elementCounts 中用小写键（wood/fire/…），
 * 而柱位字段用大写（WOOD/…），统一经 normalizeElement 归一后再查表。
 */
import { computed } from "vue";
import { elementCn, elementVar, ELEMENT_ORDER } from "../presentation/vocab";
import { elementRows } from "../presentation/elementCounts";
import type { ElementCountsData } from "../types/tianze";

const props = defineProps<{ counts: ElementCountsData | null }>();

const rows = computed(() => {
  const counts = elementRows(props.counts);
  const max = Math.max(4, ...counts.map(row => row.visible));
  return counts.map(row => ({ ...row, color: elementVar(row.key), pct: row.visible / max * 100 }));
});

const total = computed(() =>
  rows.value.reduce((s, r) => s + r.visible + r.hidden, 0));

const missing = computed(() =>
  (props.counts?.missing ?? []).map(m => elementCn(m)));

const peak = computed(() => {
  const max = Math.max(...rows.value.map(r => r.visible));
  return rows.value.filter(r => r.visible === max && max > 0).map(r => r.cn);
});
</script>

<template>
  <div v-if="props.counts" class="el-bars">
    <div v-for="r in rows" :key="r.key" class="el-row">
      <span class="el-name" :style="{ color: r.color }">{{ r.cn }}</span>
      <div class="el-track">
        <div class="el-fill" :style="{ width: `${r.pct}%`, background: r.color }" />
      </div>
      <span class="el-count">
        显 <b>{{ r.visible }}</b> · 藏 <b>{{ r.hidden }}</b>
      </span>
    </div>

    <div class="el-notes">
      <span v-if="peak.length" class="note">
        最旺：{{ peak.join("、") }}（按显数计）
      </span>
      <span v-if="rows.length === ELEMENT_ORDER.length" class="note">合计 {{ total }} 字（显 + 藏）</span>
      <span v-else class="note">部分五行计数缺失</span>
      <span v-if="missing.length" class="note">
        命局未见：{{ missing.join("、") }}
      </span>
      <span class="note-sm">结构观察，不作吉凶判断</span>
    </div>
  </div>
  <p v-else class="empty">五行计数未包含在本次分析结果中。</p>
</template>

<style scoped>
.el-notes {
  display: flex;
  flex-wrap: wrap;
  gap: var(--s-1) var(--s-4);
  margin-top: var(--s-3);
  padding-top: var(--s-3);
  border-top: 1px solid var(--line-100);
}
</style>
