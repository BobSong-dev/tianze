<script setup lang="ts">
/**
 * TiaoHouView — 调候。
 * 层级：结论摘要 → 目标干候选（含在场性） → 依据（规则 / 引文 / 出处 / 溯源） → 冲突。
 * 保留既有引文与页码信息，不删减。
 */
import { computed } from "vue";
import StatusBadge from "../components/StatusBadge.vue";
import Citation from "../components/Citation.vue";
import EvidenceCard from "../components/EvidenceCard.vue";
import { elementCn } from "../presentation/vocab";
import type { TiaoHouResult } from "../types/tianze";

const props = defineProps<{ tiaohou: TiaoHouResult }>();

const recs = computed(() => props.tiaohou?.recommendations ?? []);
const present = computed(() => recs.value.filter(r => r.present));
const elCn = elementCn;

const PRIORITY_CN: Record<string, string> = {
  primary: "首选", secondary: "次选", tertiary: "再次", auxiliary: "辅助",
};
</script>

<template>
  <div class="stack stack-5">
    <!-- 结论摘要 -->
    <section class="verdict">
      <span class="verdict-kicker">调候结论</span>
      <p class="verdict-text">
        <template v-if="!props.tiaohou.resolved">
          资料不足，未能确定调候目标（UNRESOLVED）
        </template>
        <template v-else-if="recs.length">
          候选目标干：{{ recs.map(r => r.targetStem).join("、") }}
        </template>
        <template v-else>本命局月令无对应调候规则命中</template>
      </p>
      <div class="verdict-meta">
        <StatusBadge :label="`日主 ${props.tiaohou.dayMaster}`" variant="mute" />
        <StatusBadge :label="`月支 ${props.tiaohou.monthBranch}`" variant="mute" />
        <StatusBadge
          :label="props.tiaohou.resolved ? '已定' : '未定'"
          :variant="props.tiaohou.resolved ? 'pos' : 'warn'"
          :title="props.tiaohou.resolved ? 'RESOLVED' : 'UNRESOLVED'"
        />
        <span v-if="present.length">
          命局已有 {{ present.map(r => r.targetStem).join("、") }}
        </span>
      </div>
      <p v-if="props.tiaohou.note" class="note mt-3">{{ props.tiaohou.note }}</p>
    </section>

    <!-- 目标干候选 -->
    <section>
      <div class="sec-sub" style="margin-top: 0">
        <h3>调候目标干</h3>
        <span class="sec-sub-note">按引擎给出的优先级排列</span>
      </div>

      <div class="tiaohou-grid">
        <article
          v-for="rec in recs"
          :key="rec.targetStem + rec.priority"
          class="tiaohou-item surface"
        >
          <div class="tiaohou-head">
            <span class="tiaohou-glyph">{{ rec.targetStem }}</span>
            <div class="stack stack-1">
              <StatusBadge :label="elCn(rec.element)" variant="mute" />
              <StatusBadge
                :label="PRIORITY_CN[rec.priority] ?? rec.priority"
                :title="rec.priority"
                variant="mute"
              />
            </div>
            <StatusBadge
              :label="rec.present ? '命局已有' : '命局未见'"
              :variant="rec.present ? 'pos' : 'neg'"
            />
          </div>

          <div v-if="rec.positions?.length" class="tiaohou-pos">
            位置：{{ rec.positions.join(" · ") }}
          </div>

          <details class="mt-3">
            <summary>查看依据（规则 / 引文 / 出处 / 溯源）</summary>

            <div v-if="rec.quote" class="mt-3">
              <Citation :quote="rec.quote" />
            </div>

            <dl v-if="rec.source" class="report-dl mt-3">
              <dt>出处</dt>
              <dd>
                《{{ rec.source.book }}》<template v-if="rec.source.chapter"> · {{ rec.source.chapter }}</template>
                <template v-if="rec.source.pages?.length"> · PDF 第 {{ rec.source.pages.join("-") }} 页</template>
              </dd>
              <dt v-if="rec.source.commentator">评注者</dt>
              <dd v-if="rec.source.commentator">{{ rec.source.commentator }}</dd>
              <dt v-if="rec.source.sourceKind">来源类型</dt>
              <dd v-if="rec.source.sourceKind" class="mono">{{ rec.source.sourceKind }}</dd>
              <dt v-if="rec.quality">引文质量</dt>
              <dd v-if="rec.quality" class="mono">{{ rec.quality }}</dd>
            </dl>

            <div v-if="rec.ruleIds?.length" class="mt-3">
              <div class="note-sm" style="margin-bottom: 4px">命中规则</div>
              <div class="row row-2">
                <StatusBadge
                  v-for="rid in rec.ruleIds"
                  :key="rid"
                  :code="rid"
                  variant="rule"
                />
              </div>
            </div>

            <div v-if="rec.provenance?.length" class="mt-3">
              <div class="note-sm" style="margin-bottom: 4px">溯源层级</div>
              <div class="stack stack-1">
                <div v-for="(p, i) in rec.provenance" :key="i" class="ev evidence-item is-quiet">
                  <span class="ev-mark">·</span>
                  <span class="ev-body">
                    <StatusBadge :label="p.level" variant="mute" />
                    {{ p.concept }}
                    <span v-if="p.project" class="note-sm">（{{ p.project }}）</span>
                  </span>
                </div>
              </div>
            </div>
          </details>
        </article>
      </div>

      <p v-if="!recs.length" class="empty">无调候候选。</p>
    </section>

    <!-- 通用依据 -->
    <section v-if="props.tiaohou.evidence?.length">
      <div class="sec-sub" style="margin-top: 0">
        <h3>调候依据</h3>
      </div>
      <div class="stack stack-2">
        <EvidenceCard
          v-for="(e, i) in props.tiaohou.evidence"
          :key="i"
          tone="neutral"
        >{{ e }}</EvidenceCard>
      </div>
    </section>

    <!-- 冲突 -->
    <section v-if="props.tiaohou.conflicts?.length">
      <div class="sec-sub" style="margin-top: 0">
        <h3>冲突与例外</h3>
        <span class="sec-sub-note">调候与旺衰 / 格局取向不一致之处，如实并列</span>
      </div>
      <div class="stack stack-2">
        <EvidenceCard
          v-for="(c, i) in props.tiaohou.conflicts"
          :key="i"
          tone="conflict"
          title="冲突"
        >{{ c }}</EvidenceCard>
      </div>
    </section>
  </div>
</template>

<style scoped>
.tiaohou-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--s-3);
}
.tiaohou-head {
  display: flex;
  align-items: center;
  gap: var(--s-3);
  flex-wrap: wrap;
}
.tiaohou-glyph {
  font-family: var(--font-display);
  font-size: var(--t-3xl);
  font-weight: 700;
  line-height: 1;
  color: var(--ink-900);
}
.tiaohou-pos {
  margin-top: var(--s-3);
  font-size: var(--t-xs);
  color: var(--ink-400);
  font-family: var(--font-mono);
}
</style>
