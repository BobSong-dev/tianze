<script setup lang="ts">
/**
 * RuleCard — 知识库规则条目（只读导航）。
 * 展示后端返回的规则元数据与冲突/救应邻接；不复制任何推理逻辑。
 */
import StatusBadge from "./StatusBadge.vue";
import { VIEW_MAP, PROVENANCE_MAP } from "../presentation/vocab";

const props = defineProps<{
  rule: any;
  selected?: boolean;
  compact?: boolean;
}>();

const emit = defineEmits<{ (e: "select", id: string): void }>();

function provenanceLabel(lv: string): string {
  return PROVENANCE_MAP[lv] ?? lv;
}
</script>

<template>
  <article
    class="rule-card"
    role="button"
    tabindex="0"
    :aria-pressed="Boolean(props.selected)"
    :aria-label="`${props.rule.id} ${props.rule.label}`"
    :class="{ 'is-selected': props.selected }"
    @click="emit('select', props.rule.id)"
    @keydown.enter.prevent="emit('select', props.rule.id)"
    @keydown.space.prevent="emit('select', props.rule.id)"
  >
    <div class="rule-card-head">
      <span class="rule-card-id">{{ props.rule.id }}</span>
      <StatusBadge :code="props.rule.domain" variant="mute" />
      <StatusBadge
        v-if="props.rule.view"
        :label="VIEW_MAP[props.rule.view] ?? props.rule.view"
        variant="mute"
        :title="props.rule.view"
      />
      <span class="grow" />
      <span v-if="props.rule.quality != null" class="note-sm mono">Q{{ props.rule.quality }}</span>
      <StatusBadge
        v-if="props.rule.verification?.status"
        :code="props.rule.verification.status"
        variant="mute"
      />
    </div>

    <div class="rule-card-label">{{ props.rule.label }}</div>

    <div v-if="!compact" class="rule-card-meta">
      <StatusBadge
        v-for="lv in props.rule.provenanceLevels ?? []"
        :key="lv"
        :label="provenanceLabel(lv)"
        :variant="lv === 'ENGINEERING_HEURISTIC' ? 'warn' : 'mute'"
        :title="lv"
      />
      <span v-if="props.rule.randomTriggerRate != null" class="note-sm mono">
        随机盘触发 {{ (props.rule.randomTriggerRate * 100).toFixed(1) }}%
      </span>
    </div>

    <p v-if="props.rule.conflictNote" class="note mt-2">⚠ {{ props.rule.conflictNote }}</p>
  </article>
</template>
