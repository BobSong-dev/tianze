<script setup lang="ts">
/**
 * TimelineTrack — 逐层状态回放（纵向时间轴）。
 * 每层只显示该层**引入（+）/ 移除（−）**的状态事件与主题变化——
 * 全部来自后端 replay.steps，前端不计算层间差异。
 */
import StatusBadge from "./StatusBadge.vue";
import { LAYER_MAP, DELTA_KIND_MAP } from "../presentation/vocab";

const props = defineProps<{
  steps: any[];
}>();

defineEmits<{ (e: "open-rule", id: string): void }>();
</script>

<template>
  <div class="tl">
    <div
      v-for="(st, i) in props.steps"
      :key="`${st.layer}-${i}`"
      class="tl-step"
      :id="`temporal-layer-${st.layer}`"
      tabindex="-1"
      :class="{ 'is-first': i === 0, 'is-accent': (st.added?.length ?? 0) > 0 }"
    >
      <div class="tl-head">
        <span class="tl-layer">{{ LAYER_MAP[st.layer] ?? st.layer }}</span>
        <span v-if="st.ganzhi" class="tl-gz">{{ st.ganzhi }}</span>
        <StatusBadge
          v-if="st.relationCount"
          :label="`关系 ${st.relationCount}`"
          variant="mute"
        />
        <span class="tl-note">{{ st.note }}</span>
      </div>

      <div class="tl-body">
        <div
          v-for="(a, ai) in st.added ?? []"
          :key="`a${ai}`"
          class="ev evidence-item is-plus"
        >
          <span class="ev-mark">+</span>
          <span class="ev-body">
            <StatusBadge :label="DELTA_KIND_MAP[a.kind] ?? a.kind" variant="pos" :title="a.kind" />
            {{ a.label }}
          </span>
        </div>
        <div
          v-for="(rm, ri) in st.removed ?? []"
          :key="`r${ri}`"
          class="ev evidence-item is-minus"
        >
          <span class="ev-mark">−</span>
          <span class="ev-body">
            <StatusBadge :label="DELTA_KIND_MAP[rm.kind] ?? rm.kind" variant="neg" :title="rm.kind" />
            {{ rm.label }}
          </span>
        </div>

        <div
          v-for="(t, ti) in st.themeDelta ?? []"
          :key="`t${ti}`"
          class="ev evidence-item is-quiet"
        >
          <span class="ev-mark">·</span>
          <span class="ev-body">
            主题 <strong>{{ t.label || t.theme }}</strong>
            <span class="note-sm">（{{ t.direction }}）</span>
            <span v-if="(t.relatedEvents ?? []).length" class="note-sm">
              ← {{ (t.relatedEvents ?? []).join("、") }}
            </span>
            <span v-else-if="(t.basisRefs ?? []).length" class="note-sm">
              ← {{ (t.basisRefs ?? []).join("、") }}
            </span>
          </span>
        </div>

        <p
          v-if="!(st.added?.length) && !(st.removed?.length) && !(st.themeDelta?.length)"
          class="note"
        >本层无新增或移除事件（基线层）。</p>
      </div>
    </div>
  </div>
</template>
