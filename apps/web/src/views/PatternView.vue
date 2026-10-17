<script setup lang="ts">
/**
 * PatternView — 格局。
 * 层级：结论摘要 → 格局候选（并列，不裁决） → 综合评估（支持 / 破坏 / 救应 / 冲突）。
 * 说明：evaluation.status 与 via 均为引擎给出的中文表述，原样呈现，前端不映射。
 */
import { computed } from "vue";
import StatusBadge from "../components/StatusBadge.vue";
import EvidenceCard from "../components/EvidenceCard.vue";
import type { PatternAnalysis } from "../types/tianze";

const props = defineProps<{ pattern: PatternAnalysis }>();

const candidates = computed(() => props.pattern?.candidates ?? []);
const evaluation = computed(() => props.pattern?.evaluation ?? null);

const primaryName = computed(() => {
  const i = props.pattern?.primaryIndex;
  if (i == null || i < 0) return null;
  return candidates.value[i]?.name ?? null;
});

const groups = computed(() => {
  const ev = evaluation.value;
  if (!ev) return [];
  return [
    { key: "supports", label: "支持因素", tone: "plus" as const, items: ev.supports ?? [] },
    { key: "damages", label: "破坏因素", tone: "minus" as const, items: ev.damages ?? [] },
    { key: "rescues", label: "救应", tone: "rescue" as const, items: ev.rescues ?? [] },
    { key: "conflicts", label: "冲突", tone: "conflict" as const, items: ev.conflicts ?? [] },
  ].filter(g => g.items.length);
});
</script>

<template>
  <div class="stack stack-5">
    <!-- 结论摘要 -->
    <section class="verdict">
      <span class="verdict-kicker">格局结论</span>
      <p class="verdict-text">
        <template v-if="primaryName">
          主取格局：{{ primaryName }}
        </template>
        <template v-else-if="candidates.length">
          共 {{ candidates.length }} 个格局候选，并列呈现，未指定唯一主格
        </template>
        <template v-else>本次分析未产生格局候选</template>
      </p>
      <div class="verdict-meta">
        <span v-if="evaluation">
          综合评估：<b>{{ evaluation.status }}</b>
        </span>
        <span v-if="candidates.length > 1">候选 {{ candidates.length }} 个 · 不裁决</span>
        <span v-if="candidates.length">格局名称：{{ candidates.map(c => c.name).join("、") }}
          <span class="note-sm">（候选，需复核）</span>
        </span>
      </div>
      <p v-if="props.pattern?.note" class="note mt-3">{{ props.pattern.note }}</p>
      <p class="note mt-2">格局候选为结构观察，需结合研究者判断复核。</p>
    </section>

    <!-- 候选并列 -->
    <section>
      <div class="sec-sub" style="margin-top: 0">
        <h3>格局候选</h3>
        <span class="sec-sub-note">取格路径与成立依据 · 并列呈现</span>
      </div>
      <div class="stack stack-3">
        <EvidenceCard
          v-for="(c, i) in candidates"
          :key="c.name + c.via + i"
          :title="c.name"
        >
          <template #head>
            <span class="ev-card-title">{{ c.name }}</span>
            <StatusBadge :label="c.via" variant="mute" />
            <StatusBadge :label="c.category" variant="mute" />
            <StatusBadge
              v-if="props.pattern.primaryIndex === i"
              label="主取"
              variant="warn"
            />
          </template>

          <dl class="report-dl">
            <dt>月支</dt><dd>{{ c.monthBranch }}</dd>
            <dt>取格干</dt><dd>{{ c.sourceStem }}（{{ c.tenGod }}）</dd>
          </dl>

          <div class="mt-3 stack stack-1">
            <div v-for="e in c.evidence" :key="e" class="ev evidence-item is-fact">
              <span class="ev-mark">·</span><span class="ev-body">{{ e }}</span>
            </div>
          </div>

          <details v-if="c.provenance?.length" class="mt-3">
            <summary>取格口径与溯源</summary>
            <div class="stack stack-1 mt-3">
              <div v-for="(p, pi) in c.provenance" :key="pi" class="ev evidence-item is-quiet">
                <span class="ev-mark">·</span>
                <span class="ev-body">
                  <StatusBadge :label="p.level" variant="mute" />
                  {{ p.concept }}
                  <span v-if="p.project" class="note-sm">（{{ p.project }}）</span>
                </span>
              </div>
            </div>
          </details>
        </EvidenceCard>
        <p v-if="!candidates.length" class="empty">无格局候选。</p>
      </div>
    </section>

    <!-- 综合评估 -->
    <section v-if="evaluation">
      <div class="sec-sub" style="margin-top: 0">
        <h3>综合评估</h3>
        <span class="sec-sub-note">{{ evaluation.candidate?.name }} · {{ evaluation.status }}</span>
      </div>
      <p v-if="evaluation.note" class="note" style="margin-bottom: var(--s-3)">{{ evaluation.note }}</p>

      <div class="stack stack-4">
        <div v-for="g in groups" :key="g.key">
          <div class="row row-3" style="margin-bottom: var(--s-2)">
            <h4 style="font-family: var(--font-display); font-size: var(--t-md)">{{ g.label }}</h4>
            <StatusBadge :label="String(g.items.length)" variant="mute" />
          </div>
          <div class="stack stack-2">
            <EvidenceCard
              v-for="f in g.items"
              :key="f.ruleId"
              :tone="g.tone"
              :ref-id="f.ruleId"
              :title="f.name"
            >
              {{ f.detail }}
              <div v-if="f.related?.length" class="note-sm mt-2">
                相关：{{ f.related.join("、") }}
              </div>
            </EvidenceCard>
          </div>
        </div>
        <p v-if="!groups.length" class="empty">综合评估未给出支持 / 破坏 / 救应 / 冲突因素。</p>
      </div>
    </section>

    <p v-if="!evaluation" class="note">
      本次分析未产生综合评估（可能因候选不足或评估模块未启用）。
    </p>
  </div>
</template>
