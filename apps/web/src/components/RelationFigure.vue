<script setup lang="ts">
/**
 * RelationFigure — 一组干支关系的横向示意 + 结构化事实。
 *
 * 边界：只消费后端 RelationData / RelationExplanationData。
 * 合化状态、邻位、月令、化神、阻化等**一律原样呈现**，前端绝不判定化成。
 */
import StatusBadge from "./StatusBadge.vue";
import { computed } from "vue";
import ConditionList from "./ConditionList.vue";
import Citation from "./Citation.vue";
import { relationTone, relationKindShort, relationKindCn, positionShortCn, elementCn, STATUS_MAP } from "../presentation/vocab";
import type { RelationData, RelationExplanationData } from "../types/tianze";

const props = defineProps<{
  relation: RelationData;
  explanation?: RelationExplanationData | null;
  /** 未成立的关系（blockedRelations）用弱化样式 */
  blocked?: boolean;
}>();

const emit = defineEmits<{ (e: "open-graph", id: string): void }>();

function tone(kind: string) {
  const t = relationTone(kind);
  return t === "plain" ? "is-harmony" : `is-${t}`;
}

/** 关系标签的中文键（后端 label 已含"甲己合"等表述，这里只做符号补充） */
const members = props.relation.members ?? [];

/** 柱位显示为「年·日」而不是 "year · day" */
function positionsText(): string {
  return (props.relation.positions ?? []).map(positionShortCn).join(" · ");
}

/** 连接线内的标签用关系短名（合 / 冲 / 三合 …），避免与行标题重复 */
const edgeLabel = computed(() => {
  const short = relationKindShort(props.relation.kind);
  return short || relationKindCn(props.relation.kind);
});
</script>

<template>
  <article class="row-item">
    <div class="row-item-head">
      <span class="row-item-title">{{ props.relation.label }}</span>
      <StatusBadge
        :label="positionsText()"
        :title="(props.relation.positions ?? []).join(' · ')"
        variant="mute"
      />
      <StatusBadge
        v-if="props.relation.adjacency"
        :label="props.relation.adjacency === 'ADJACENT' ? '贴邻' : '隔位'"
        :title="props.relation.adjacency"
        variant="mute"
      />
      <StatusBadge v-if="props.relation.monthInvolved" label="月令" variant="mute" />
      <StatusBadge v-if="props.relation.subType" :label="props.relation.subType" variant="mute" />
      <StatusBadge
        v-if="props.relation.transformCandidate"
        :label="`化${elementCn(props.relation.transformCandidate)}（候选）`"
        variant="warn"
        :title="`化神候选 (${props.relation.transformCandidate})：引擎给出的候选，未判定化成`"
      />
      <span class="grow" />
      <StatusBadge v-if="props.blocked" label="未成立" variant="neg" />
    </div>

    <!-- 横向示意：参与干支之间的线 + 关系标签 -->
    <div v-if="members.length" class="rel-link mt-3" style="max-width: 320px">
      <span class="rel-glyph">{{ members[0] }}</span>
      <span class="rel-edge" :class="tone(props.relation.kind)" :title="relationKindCn(props.relation.kind)">
        <span class="rel-edge-label">{{ edgeLabel }}</span>
      </span>
      <span v-if="members[1]" class="rel-glyph">{{ members[1] }}</span>
      <template v-if="members.length > 2">
        <span v-for="m in members.slice(2)" :key="m" class="rel-glyph">{{ m }}</span>
      </template>
    </div>

    <p v-if="props.relation.note" class="row-item-body">{{ props.relation.note }}</p>

    <details v-if="props.explanation" class="mt-3">
      <summary>
        解释链 · {{ props.explanation.status === "ESTABLISHED" ? "结构事实" : "候选关系" }}
        （{{ STATUS_MAP[props.explanation.status]?.label ?? props.explanation.status }}）
      </summary>

      <p v-if="props.explanation.boundary" class="note mt-2">{{ props.explanation.boundary }}</p>

      <div v-if="props.explanation.conditions?.length" class="mt-3">
        <div class="sec-sub" style="margin-top: 0">
          <h3 style="font-size: var(--t-sm)">成立条件</h3>
        </div>
        <ConditionList :items="props.explanation.conditions" />
      </div>

      <div v-if="props.explanation.schoolNotes?.length" class="mt-3 stack stack-1">
        <div class="sec-sub" style="margin: 0 0 var(--s-2)">
          <h3 style="font-size: var(--t-sm)">流派注记</h3>
        </div>
        <p v-for="(sn, i) in props.explanation.schoolNotes" :key="i" class="note">{{ sn }}</p>
      </div>

      <div v-if="props.explanation.exceptions?.length" class="mt-3">
        <div class="sec-sub" style="margin: 0 0 var(--s-2)">
          <h3 style="font-size: var(--t-sm)">例外</h3>
        </div>
        <p v-for="(ex, i) in props.explanation.exceptions" :key="i" class="note">{{ ex }}</p>
      </div>

      <div v-if="props.explanation.citations?.length" class="mt-3 stack stack-3">
        <div class="sec-sub" style="margin: 0">
          <h3 style="font-size: var(--t-sm)">古籍引文</h3>
        </div>
        <Citation
          v-for="(c, i) in props.explanation.citations"
          :key="i"
          :candidate-id="c.candidateId"
          :book="c.book"
          :title="c.title"
          :quote="c.quote"
          :source-kind="c.sourceKind"
          :ocr-risk="c.ocrRisk"
          linkable
          @open-graph="emit('open-graph', $event)"
        />
      </div>
    </details>
  </article>
</template>
