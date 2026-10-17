<script setup lang="ts">
/**
 * TimeRail — 岁运时间研究轨道（原局 → 大运 → 流年 → 流月 → 流日）。
 * 只呈现后端回显的岁运上下文干支；未到达的层级保持禁用态而非隐藏。
 */
export interface TimeStop {
  key: string;
  layer: string;
  label: string;
  ganzhi: string;
  sub: string;
  enabled: boolean;
}

const props = defineProps<{
  stops: TimeStop[];
  /** 当前完成分析的层级 key（来自后端回显的 context 最深层） */
  activeKey?: string | null;
}>();

const emit = defineEmits<{ (e: "focus", key: string): void }>();
</script>

<template>
  <div class="time-rail" role="list" aria-label="岁运时间轨道">
    <button
      v-for="s in props.stops"
      :key="s.key"
      type="button"
      role="listitem"
      class="time-stop"
      :class="{ 'is-active': props.activeKey === s.key, 'is-natal': s.key === 'natal' }"
      :disabled="!s.enabled"
      :aria-current="props.activeKey === s.key ? 'step' : undefined"
      @click="emit('focus', s.key)"
    >
      <span class="time-stop-layer">{{ s.layer }}</span>
      <span class="time-stop-gz">{{ s.ganzhi || "—" }}</span>
      <span class="time-stop-sub">{{ s.sub }}</span>
    </button>
  </div>
</template>
