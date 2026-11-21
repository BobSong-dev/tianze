<script setup lang="ts">
/**
 * RelationsView — 干支关系。
 * 层级：关系总览 → 已成立关系（含解释链） → 合化状态（三要素候选） → 未成立候选。
 *
 * 纪律：合化状态永不判定化成；三要素（邻位 / 月令化神 / 阻化）原样呈现；
 *       CANDIDATE / DISPUTED 等状态语义完全服从后端。
 */
import { computed } from "vue";
import RelationFigure from "../components/RelationFigure.vue";
import ConditionList from "../components/ConditionList.vue";
import Citation from "../components/Citation.vue";
import StatusBadge from "../components/StatusBadge.vue";
import { STATUS_MAP, relationKindCn } from "../presentation/vocab";
import type { AnalyzeResponse, RelationData } from "../types/tianze";

const props = defineProps<{
  result: AnalyzeResponse;
  relationChains: Map<string, any>;
  combinationStates: any[];
}>();

const emit = defineEmits<{ (e: "open-graph", id: string): void }>();

const relations = computed<RelationData[]>(() => props.result.relations ?? []);
const blocked = computed<RelationData[]>(() => props.result.blockedRelations ?? []);

const kindGroups = computed(() => {
  const g = new Map<string, number>();
  for (const r of relations.value) g.set(r.kind, (g.get(r.kind) ?? 0) + 1);
  return [...g.entries()].map(([k, v]) => ({ kind: k, label: relationKindCn(k), count: v }));
});

const statusCounts = computed(() => {
  const g = new Map<string, number>();
  for (const e of props.combinationStates) g.set(e.status, (g.get(e.status) ?? 0) + 1);
  return [...g.entries()].map(([k, v]) => ({ code: k, count: v }));
});
</script>

<template>
  <div class="stack stack-5">
    <!-- 关系总览 -->
    <section class="verdict">
      <span class="verdict-kicker">关系总览</span>
      <p class="verdict-text">
        刑冲合害破与天干五合共 {{ relations.length }} 条成立<template v-if="blocked.length">，
        另有 {{ blocked.length }} 条候选未成立</template>。合化状态
        {{ props.combinationStates.length }} 项均为候选，不判定化成。
      </p>
      <div class="verdict-meta">
        <StatusBadge
          v-for="g in kindGroups"
          :key="g.kind"
          :label="`${g.label} × ${g.count}`"
          :title="g.kind"
          variant="mute"
        />
        <StatusBadge
          v-for="s in statusCounts"
          :key="s.code"
          :code="s.code"
          :label="`${STATUS_MAP[s.code]?.label ?? s.code} × ${s.count}`"
          with-hint
        />
      </div>
      <p class="note mt-3">
        点开任意关系可查看成立条件、流派注记与古籍引文。
      </p>
    </section>

    <!-- 已成立关系 -->
    <section>
      <div class="sec-sub" style="margin-top: 0">
        <h3>已成立关系</h3>
        <span class="sec-sub-note">刑 · 冲 · 合 · 害 · 破 · 三合三会 · 天干五合</span>
      </div>
      <div class="rows rows-ledger">
        <RelationFigure
          v-for="(r, i) in relations"
          :key="`${r.label}-${i}`"
          :relation="r"
          :explanation="props.relationChains.get(r.label)"
          @open-graph="emit('open-graph', $event)"
        />
        <p v-if="!relations.length" class="empty">本命局在原局层面无已成立关系。</p>
      </div>
    </section>

    <!-- 合化状态 -->
    <section v-if="props.combinationStates.length">
      <div class="sec-sub" style="margin-top: 0">
        <h3>合化状态</h3>
        <span class="sec-sub-note">
          三要素候选：邻位 / 月令化神 / 阻化 —— 永不判定化成
        </span>
      </div>
      <div class="rows">
        <article
          v-for="e in props.combinationStates"
          :key="e.refId"
          class="row-item relation-item"
        >
          <div class="row-item-head">
            <span class="row-item-title">{{ e.label }}</span>
            <StatusBadge :code="e.status" with-hint />
            <StatusBadge :label="e.kindCn ?? e.kind" variant="mute" />
          </div>
          <p v-if="e.boundary" class="row-item-body">{{ e.boundary }}</p>
          <div v-if="e.evidence?.length" class="stack stack-1 mt-3">
            <div v-for="(ev, i) in e.evidence" :key="i" class="ev evidence-item is-quiet">
              <span class="ev-mark">·</span><span class="ev-body">{{ ev }}</span>
            </div>
          </div>

          <details class="mt-3">
            <summary>成立条件与引文</summary>
            <div class="mt-3">
              <ConditionList :items="e.conditions ?? []" />
            </div>
            <div v-if="e.schoolNotes?.length" class="stack stack-1 mt-3">
              <p v-for="(sn, i) in e.schoolNotes" :key="i" class="note">流派：{{ sn }}</p>
            </div>
            <div v-if="e.citations?.length" class="stack stack-3 mt-3">
              <Citation
                v-for="(c, i) in e.citations"
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
      </div>
    </section>

    <!-- 未成立候选 -->
    <section v-if="blocked.length">
      <div class="sec-sub" style="margin-top: 0">
        <h3>未成立的关系候选</h3>
        <span class="sec-sub-note">「为什么不成立」——仅解释，不参与推理</span>
      </div>
      <div class="rows rows-ledger">
        <RelationFigure
          v-for="(r, i) in blocked"
          :key="`b-${r.label}-${i}`"
          :relation="r"
          :explanation="props.relationChains.get(r.label)"
          blocked
          @open-graph="emit('open-graph', $event)"
        />
      </div>
    </section>

    <p class="note">
      关系判定与合化候选均为引擎输出；本页仅做组织与呈现，前端不新增任何关系推导。
    </p>
  </div>
</template>
