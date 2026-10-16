<script setup lang="ts">
/**
 * StrengthView — 旺衰。
 * 层级：结论摘要 → 三法并列（得令/得地/得势 → 计分 → 依据） → 多方法一致性。
 * 纪律：多方法并列展示，不裁决；分歧如实标注（服从后端 agreement 语义）。
 */
import { computed } from "vue";
import StatusBadge from "../components/StatusBadge.vue";
import { STATUS_MAP, ANALYZER_MAP } from "../presentation/vocab";
import type { StrengthMethodResult } from "../types/tianze";

const props = defineProps<{ strength: any }>();

const methods = computed<StrengthMethodResult[]>(() => props.strength?.methods ?? []);

/** 全部方法都进结论区：无强弱判定的方法如实标注，避免"3 种方法只列 2 条"的错觉 */
const verdicts = computed(() =>
  methods.value.map(m => ({
    name: ANALYZER_MAP[m.analyzerId]?.cn ?? m.name,
    verdict: m.verdict ?? "未判定强弱",
  })));

const agreementLabel = computed(() => {
  const a = props.strength?.agreement;
  return a ? (STATUS_MAP[a]?.label ?? a) : null;
});

function displayName(m: StrengthMethodResult): string {
  return ANALYZER_MAP[m.analyzerId]?.cn ?? m.name;
}
function rawName(m: StrengthMethodResult): string {
  return ANALYZER_MAP[m.analyzerId]?.method ?? m.analyzerId;
}

/** 得令/得地/得势三项（仅 dimension 分析器提供；其它分析器如实说明不适用） */
const dims = [
  { key: "deLing", label: "得令", hint: "日主在月令的当令状态" },
  { key: "deDi", label: "得地", hint: "日主在地支的通根状态" },
  { key: "deShi", label: "得势", hint: "同类五行的党众状态" },
] as const;
</script>

<template>
  <div class="stack stack-5">
    <!-- 结论摘要 -->
    <section class="verdict">
      <span class="verdict-kicker">旺衰结论</span>
      <p class="verdict-text">
        <template v-if="verdicts.length">
          {{ verdicts.map(v => `${v.name}：${v.verdict}`).join("　·　") }}
        </template>
        <template v-else>本次分析未给出旺衰判定</template>
      </p>
      <div class="verdict-meta">
        <StatusBadge
          v-if="agreementLabel"
          :code="props.strength?.agreement"
          :label="`多方法一致性：${agreementLabel}`"
          with-hint
        />
        <span>分析方法 {{ methods.length }} 种 · 并列展示，不裁决</span>
      </div>
      <p v-if="props.strength?.note" class="note mt-3">{{ props.strength.note }}</p>
    </section>

    <!-- 三法并列 -->
    <section
      v-for="m in methods"
      :key="m.analyzerId"
      class="method-block surface"
    >
      <div class="sec-sub" style="margin-top: 0">
        <h3>{{ displayName(m) }}</h3>
        <StatusBadge :label="rawName(m)" variant="rule" />
        <StatusBadge v-if="m.verdict" :label="m.verdict" variant="mute" />
        <StatusBadge
          v-if="m.confidence"
          :label="`置信 ${m.confidence}`"
          variant="mute"
          title="引擎给出的定性置信标注，非概率"
        />
        <span class="sec-sub-aside">
          <span v-if="m.score !== null && m.score !== undefined" class="mono note">
            score {{ m.score }}
          </span>
        </span>
      </div>

      <!-- 得令 / 得地 / 得势 -->
      <template v-if="m.strengthEvidence">
        <div class="dim-grid">
          <div
            v-for="d in dims"
            :key="d.key"
            class="dim-cell"
            :class="(m.strengthEvidence as any)[d.key]?.result ? 'is-met' : 'is-unmet'"
          >
            <div class="dim-head">
              <span class="dim-name">{{ d.label }}</span>
              <span class="dim-mark" aria-hidden="true">
                {{ (m.strengthEvidence as any)[d.key]?.result ? "✓" : "✗" }}
              </span>
            </div>
            <p class="note-sm">{{ d.hint }}</p>
            <ul v-if="(m.strengthEvidence as any)[d.key]?.reason?.length" class="dim-reasons">
              <li
                v-for="(r, i) in (m.strengthEvidence as any)[d.key].reason"
                :key="i"
              >{{ r }}</li>
            </ul>
          </div>
        </div>
      </template>

      <!-- 加权计分贡献 -->
      <details v-if="m.contributions?.length" class="mt-4">
        <summary>计分贡献（{{ m.contributions.length }} 项）</summary>
        <div class="stack stack-1 mt-3">
          <div
            v-for="c in m.contributions"
            :key="c.factor"
            class="ev evidence-item"
            :class="c.effect === 'support' ? 'is-plus' : 'is-minus'"
          >
            <span class="ev-mark">{{ c.effect === "support" ? "+" : "−" }}</span>
            <span class="ev-body">
              {{ c.reason }}
              <span class="mono note-sm">（{{ c.factor }} = {{ c.value }}）</span>
            </span>
          </div>
        </div>
      </details>

      <!-- 扶抑用神证据 -->
      <details v-if="m.supportEvidence?.length || m.drainEvidence?.length" class="mt-4">
        <summary>扶抑依据</summary>
        <div class="stack stack-1 mt-3">
          <div v-for="e in m.supportEvidence ?? []" :key="e" class="ev evidence-item is-plus">
            <span class="ev-mark">+</span><span class="ev-body">{{ e }}</span>
          </div>
          <div v-for="e in m.drainEvidence ?? []" :key="e" class="ev evidence-item is-minus">
            <span class="ev-mark">−</span><span class="ev-body">{{ e }}</span>
          </div>
        </div>
      </details>

      <!-- 通用依据 -->
      <details v-if="m.evidence?.length" class="mt-4">
        <summary>全部依据（{{ m.evidence.length }} 条）</summary>
        <div class="stack stack-1 mt-3">
          <div v-for="e in m.evidence" :key="e" class="ev evidence-item is-fact">
            <span class="ev-mark">·</span><span class="ev-body">{{ e }}</span>
          </div>
        </div>
      </details>

      <!-- 参数与溯源 -->
      <details v-if="m.params" class="mt-4">
        <summary>方法参数与溯源</summary>
        <div class="mt-3">
          <pre class="code-block">{{ JSON.stringify(m.params, null, 2) }}</pre>
          <div v-if="m.provenance?.length" class="stack stack-1 mt-3">
            <div v-for="(p, i) in m.provenance" :key="i" class="ev evidence-item is-quiet">
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

      <p v-if="m.note" class="note mt-3">{{ m.note }}</p>
    </section>
  </div>
</template>

<style scoped>
.dim-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(196px, 1fr));
  gap: var(--s-3);
}
.dim-cell {
  border: 1px solid var(--line-100);
  border-top: 2px solid var(--line-200);
  border-radius: 0 0 var(--r-sm) var(--r-sm);
  background: var(--paper-050);
  padding: var(--s-3) var(--s-4);
}
.dim-cell.is-met { border-top-color: var(--wx-wood); }
.dim-cell.is-unmet { border-top-color: var(--wx-fire); }
.dim-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--s-2);
  margin-bottom: 3px;
}
.dim-name {
  font-family: var(--font-display);
  font-size: var(--t-lg);
  font-weight: 600;
  color: var(--ink-900);
}
.dim-mark { font-family: var(--font-mono); font-weight: 700; }
.dim-cell.is-met .dim-mark { color: var(--wx-wood); }
.dim-cell.is-unmet .dim-mark { color: var(--wx-fire); }
.dim-reasons {
  margin: var(--s-2) 0 0;
  padding-left: 1.1em;
  font-size: var(--t-xs);
  color: var(--ink-500);
  line-height: var(--lh-snug);
}
.code-block {
  margin: 0;
  padding: var(--s-3);
  background: var(--paper-100);
  border: 1px solid var(--line-100);
  border-radius: var(--r-sm);
  font-family: var(--font-mono);
  font-size: var(--t-2xs);
  color: var(--ink-700);
  overflow-x: auto;
  max-height: 240px;
}
</style>
