<script setup lang="ts">
/**
 * TemporalView — 岁运时序工作台。
 *
 * 层级：时间轨道（原局→大运→流年→流月→流日） → 岁运上下文 →
 *       规则触发 → 新增关系 / 结构现象 → 状态回放 → 完整 Delta → 事件主题与解释链。
 *
 * 纪律：全部内容为**结构变化描述**，不构成吉凶或事件预测；
 *       所有状态码与规则号原样来自引擎。
 */
import { computed } from "vue";
import TimeRail from "../components/TimeRail.vue";
import TimelineTrack from "../components/TimelineTrack.vue";
import EvidenceCard from "../components/EvidenceCard.vue";
import StatusBadge from "../components/StatusBadge.vue";
import { DELTA_KIND_MAP, LAYER_MAP, VIEW_MAP, STATUS_MAP, deltaTitle, positionCn } from "../presentation/vocab";

const props = defineProps<{
  temporal: any;
  luckOptions: any[];
  yearOptions: number[];
  monthOptions: { n: number; label: string; jie: string }[];
  timeStops: any[];
  matchedRules: any[];
  deltaGroups: Record<string, any[]>;
  selection: { luckIndex: number | null; year: number | null; month: number | null; day: string; withReplay: boolean };
  loading: boolean;
  error: string;
}>();

const emit = defineEmits<{
  (e: "run"): void;
  (e: "luck", v: number | null): void;
  (e: "year", v: number | null): void;
  (e: "month", v: number | null): void;
  (e: "day", v: string): void;
  (e: "toggle-replay", v: boolean): void;
  (e: "open-rule", id: string): void;
}>();

/** 当前分析到达的最深层级（由后端回显的 context 决定，前端不推断） */
const activeLayer = computed(() => {
  const c = props.temporal?.context;
  if (!c) return null;
  if (c.dailyStem) return "daily";
  if (c.monthlyStem) return "monthly";
  if (c.annualStem) return "annual";
  if (c.luckStem) return "luck";
  return "natal";
});

const replaySteps = computed(() => props.temporal?.replay?.steps ?? []);
const explanations = computed<Record<string, any>>(() => props.temporal?.eventThemes?.explanations ?? {});
const themes = computed(() => props.temporal?.eventThemes?.themes ?? []);
const delta = computed(() => props.temporal?.delta);

/** 岁运层级的中文名（引擎给 natal/luck/annual/monthly/daily） */
const LAYER_CN: Record<string, string> = {
  natal: "原局", luck: "大运", annual: "流年", monthly: "流月", daily: "流日",
};
function layerCn(l?: string | null): string {
  if (!l) return "";
  return LAYER_CN[l] ?? l;
}

/** sources: ["natal","annual"] → "原局 · 流年" */
function sourcesText(sources?: string[]): string {
  return (sources ?? []).map(layerCn).join(" · ");
}

/** positions: "natal:year" → "原局年柱"；未知层级原样返回 */
function positionText(p: string): string {
  const [layer, pos] = String(p).split(":");
  if (!pos) return layerCn(layer);
  return `${layerCn(layer)}${positionCn(pos)}`;
}

/** 结构现象类型（引擎用 fuyin / fanyin 等标识） */
const STRUCTURE_TYPE_CN: Record<string, string> = {
  fuyin: "伏吟", fanyin: "反吟", "suiyun-binglin": "岁运并临",
  "tiake-dichong": "天克地冲", "tiandi-hede": "天地合德",
};
function structureTypeCn(t?: string | null): string {
  if (!t) return "";
  return STRUCTURE_TYPE_CN[t] ?? t;
}

const contextChips = computed(() => {
  const c = props.temporal?.context;
  if (!c) return [];
  const out: { cls: string; label: string; text: string }[] = [];
  const natal = (c.natalStems ?? []).map((s: string, i: number) =>
    `${s ?? ""}${(c.natalBranches ?? [])[i] ?? ""}`).filter(Boolean).join(" ");
  if (natal) out.push({ cls: "natal", label: "原局", text: natal });
  if (c.luckStem) out.push({ cls: "luck", label: "大运", text: `${c.luckStem}${c.luckBranch}` });
  if (c.annualStem) out.push({ cls: "annual", label: "流年", text: `${c.annualStem}${c.annualBranch}` });
  if (c.monthlyStem) {
    out.push({
      cls: "monthly", label: "流月",
      text: `${c.monthlyStem}${c.monthlyBranch}${props.temporal?.monthWindow ? `（${props.temporal.monthWindow.jieName}起）` : ""}`,
    });
  }
  if (c.dailyStem) out.push({ cls: "daily", label: "流日", text: `${c.dailyStem}${c.dailyBranch}` });
  return out;
});

function analysisLabel(key: string): string {
  const map: Record<string, string> = {
    strength: "旺衰", pattern: "格局", tiaohou: "调候", relations: "关系",
    structure: "结构", element: "五行", tenGod: "十神", special: "特殊结构",
  };
  return map[key] ?? key;
}
</script>

<template>
  <div class="stack stack-6">
    <!-- 时间研究轨道 -->
    <section>
      <div class="sec-sub" style="margin-top: 0">
        <h3>岁运时间轨道</h3>
        <span class="sec-sub-note">
          逐层展开：岁运不替换原局月令；未到达的层级保持空缺而非隐藏
        </span>
      </div>
      <TimeRail :stops="props.timeStops" :active-key="activeLayer" />
    </section>

    <!-- 选择与执行 -->
    <section class="surface">
      <div class="sec-sub" style="margin-top: 0; border-bottom: none; padding-bottom: 0">
        <h3 style="font-size: var(--t-md)">选择分析目标</h3>
      </div>
      <div class="toolbar mt-3 temporal-controls" style="border: none; background: none; padding: 0">
        <label class="field">
          <span class="field-label">大运</span>
          <select
            :value="props.selection.luckIndex"
            :disabled="!props.luckOptions.length"
            @change="emit('luck', ($event.target as HTMLSelectElement).value === '' ? null : Number(($event.target as HTMLSelectElement).value))"
          >
            <option value="">选择大运</option>
            <option v-for="d in props.luckOptions" :key="d.index" :value="d.index">
              {{ d.ganZhi }}（{{ d.startYear }}–{{ d.endYear }}，{{ d.startAge }} 岁起）
            </option>
          </select>
        </label>

        <label class="field">
          <span class="field-label">流年</span>
          <select
            :value="props.selection.year ?? ''"
            :disabled="!props.yearOptions.length"
            @change="emit('year', ($event.target as HTMLSelectElement).value === '' ? null : Number(($event.target as HTMLSelectElement).value))"
          >
            <option value="">选择年份</option>
            <option v-for="y in props.yearOptions" :key="y" :value="y">{{ y }}</option>
          </select>
        </label>

        <label class="field">
          <span class="field-label">流月</span>
          <select
            :value="props.selection.month ?? ''"
            :disabled="props.selection.year === null"
            @change="emit('month', ($event.target as HTMLSelectElement).value === '' ? null : Number(($event.target as HTMLSelectElement).value))"
          >
            <option value="">（不选）</option>
            <option v-for="m in props.monthOptions" :key="m.n" :value="m.n">
              {{ m.label }}（{{ m.jie }}）
            </option>
          </select>
        </label>

        <label class="field">
          <span class="field-label">流日 <span class="mono">可选</span></span>
          <input
            type="date"
            :value="props.selection.day"
            :disabled="props.selection.month === null"
            @change="emit('day', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <label class="check-row" style="padding-bottom: 6px">
          <input
            type="checkbox"
            :checked="props.selection.withReplay"
            @change="emit('toggle-replay', ($event.target as HTMLInputElement).checked)"
          />
          状态回放
        </label>

        <button class="btn-primary" type="button" :disabled="props.loading" @click="emit('run')">
          {{ props.loading ? "分析中…" : "分析" }}
        </button>
      </div>

      <p v-if="!props.luckOptions.length" class="note mt-3">
        该命例无大运数据（性别或时辰未知时大运缺席，R7/R11）。
      </p>
      <p v-if="props.error" class="error" role="alert">
        <span class="mono" aria-hidden="true">ERR</span><span>{{ props.error }}</span>
      </p>
    </section>

    <template v-if="props.temporal">
      <!-- 岁运上下文链 -->
      <section>
        <div class="sec-sub" style="margin-top: 0">
          <h3>岁运上下文</h3>
          <span class="sec-sub-note">参与本次判定的干支层级</span>
        </div>
        <div class="temporal-context">
          <template v-for="(c, i) in contextChips" :key="c.cls">
            <span v-if="i > 0" class="arrow" aria-hidden="true">→</span>
            <span class="ctx-chip" :class="c.cls">
              <span class="ctx-chip-label">{{ c.label }}</span>
              <span class="ctx-chip-gz">{{ c.text }}</span>
            </span>
          </template>
        </div>
      </section>

      <!-- 规则触发 -->
      <section>
        <div class="sec-sub" style="margin-top: 0">
          <h3>岁运规则触发</h3>
          <span class="sec-sub-note">
            ExecutableRule(domain=temporal) → 结构观察，不含吉凶
          </span>
          <span class="sec-sub-aside">
            <StatusBadge
              :label="`命中 ${props.matchedRules.length} / ${props.temporal.ruleTriggers?.length ?? 0}`"
              variant="mute"
            />
          </span>
        </div>

        <div class="rows" data-testid="rule-triggers">
          <article v-for="t in props.matchedRules" :key="t.ruleId" class="row-item">
            <div class="row-item-head">
              <span class="row-item-title">{{ t.label }}</span>
              <StatusBadge :code="t.ruleId" variant="rule" />
              <StatusBadge v-if="t.category" :label="t.category" variant="mute" />
              <button class="btn-link" style="margin-left: auto" type="button"
                      @click="emit('open-rule', t.ruleId)">在知识图谱中查看</button>
            </div>
            <div class="stack stack-1 mt-2">
              <div v-for="(o, i) in t.observations" :key="i" class="ev evidence-item is-fact">
                <span class="ev-mark">·</span><span class="ev-body">{{ o }}</span>
              </div>
            </div>
          </article>
          <p v-if="!props.matchedRules.length" class="empty">
            无规则触发（全部 {{ props.temporal.ruleTriggers?.length ?? 0 }} 条规则已参与判定，
            matched=false 保留可审计）。
          </p>
        </div>
      </section>

      <!-- 新增关系与结构现象 -->
      <section>
        <div class="sec-sub" style="margin-top: 0">
          <h3>新增关系</h3>
          <span class="sec-sub-note">原局不存在、由岁运引入</span>
        </div>
        <div class="rows">
          <article v-for="(r, i) in props.temporal.relations" :key="i" class="row-item">
            <div class="row-item-head">
              <span class="row-item-title">{{ r.label }}</span>
              <StatusBadge
                v-if="r.sources?.length"
                :label="sourcesText(r.sources)"
                :title="(r.sources ?? []).join(' + ')"
                variant="mute"
              />
              <StatusBadge v-if="r.completesHarmony" label="补齐三合" variant="pos" />
              <StatusBadge
                v-if="r.transformCandidate"
                :label="`化 ${r.transformCandidate}（候选）`"
                variant="warn"
              />
            </div>
            <p v-if="r.positions?.length" class="row-item-body mono">
              {{ (r.positions ?? []).map(positionText).join(" ↔ ") }}
            </p>
            <p v-if="r.note" class="row-item-body">{{ r.note }}</p>
          </article>
          <p v-if="!(props.temporal.relations ?? []).length" class="empty">无新增关系。</p>
        </div>
      </section>

      <section>
        <div class="sec-sub" style="margin-top: 0">
          <h3>结构现象</h3>
          <span class="sec-sub-note">伏吟 / 反吟 / 岁运并临 / 天克地冲等</span>
        </div>
        <div class="rows">
          <article v-for="(s, i) in props.temporal.structures" :key="i" class="row-item">
            <div class="row-item-head">
              <span class="row-item-title">{{ s.label }}</span>
              <StatusBadge
                v-if="s.type"
                :label="structureTypeCn(s.type)"
                :title="s.type"
                variant="mute"
              />
              <StatusBadge
                v-if="s.sources?.length"
                :label="sourcesText(s.sources)"
                :title="(s.sources ?? []).join(' + ')"
                variant="mute"
              />
            </div>
            <p class="row-item-body">{{ s.description }}</p>
          </article>
          <p v-if="!(props.temporal.structures ?? []).length" class="empty">无结构现象。</p>
        </div>
      </section>

      <!-- 逐层状态回放 -->
      <section v-if="replaySteps.length">
        <div class="sec-sub" style="margin-top: 0">
          <h3>逐层状态回放</h3>
          <span class="sec-sub-note">
            原局 → 大运 → 流年 → 流月 → 流日；每层只显示该层引入（+）或移除（−）的事件
          </span>
        </div>
        <div class="surface">
          <TimelineTrack :steps="replaySteps" @open-rule="emit('open-rule', $event)" />
          <p class="note mt-4">
            结构候选事件回放，不构成吉凶或事件预测。相关规则：
            <button class="btn-link" type="button" @click="emit('open-rule', 'TR-DTZ-10')">
              TR-DTZ-10（虚神交互）
            </button>
          </p>
        </div>
      </section>

      <!-- 完整 Temporal Delta -->
      <section v-if="delta">
        <div class="sec-sub" style="margin-top: 0">
          <h3>完整 Temporal Delta</h3>
          <span class="sec-sub-note">
            相对原局的状态差异；EXPERIMENTAL = 岁运参与该计算存在流派分歧
          </span>
        </div>

        <div class="stack stack-4">
          <div v-for="(items, analysis) in props.deltaGroups" :key="analysis">
            <div class="note-sm" style="margin-bottom: var(--s-2)">
              {{ analysisLabel(String(analysis)) }}
              <span class="mono"> · {{ items.length }} 项</span>
            </div>
            <div class="stack stack-2">
              <EvidenceCard
                v-for="it in items"
                :key="it.refId + it.kind"
                :ref-id="it.refId"
                :title="deltaTitle(it.subject)"
                :tone="it.kind === 'strengthened' || it.kind === 'added' ? 'plus'
                     : it.kind === 'weakened' || it.kind === 'removed' || it.kind === 'blocked' ? 'minus'
                     : 'neutral'"
              >
                <p class="note-sm mono" style="margin-bottom: var(--s-1)">{{ it.subject }}</p>
                <div class="row row-2">
                  <StatusBadge
                    :label="DELTA_KIND_MAP[it.kind] ?? it.kind"
                    :variant="it.kind === 'added' || it.kind === 'strengthened' ? 'pos'
                            : it.kind === 'removed' || it.kind === 'weakened' ? 'neg' : 'mute'"
                    :title="it.kind"
                  />
                  <StatusBadge
                    v-if="it.supportLevel === 'EXPERIMENTAL'"
                    code="EXPERIMENTAL"
                    with-hint
                  />
                  <StatusBadge v-else-if="it.supportLevel" :label="it.supportLevel" variant="mute" />
                </div>

                <div
                  v-if="it.natalValue !== null || it.temporalValue !== null"
                  class="delta mt-2"
                >
                  <span class="delta-from">{{ JSON.stringify(it.natalValue) }}</span>
                  <span class="delta-arrow">→</span>
                  <span class="delta-to">{{ JSON.stringify(it.temporalValue) }}</span>
                  <span v-if="it.trigger" class="note-sm">（{{ it.trigger }}）</span>
                </div>

                <div v-if="it.evidence?.length" class="stack stack-1 mt-2">
                  <p v-for="(e, i) in it.evidence" :key="i" class="note">{{ e }}</p>
                </div>
              </EvidenceCard>
            </div>
          </div>

          <p v-if="!Object.keys(props.deltaGroups).length" class="empty">
            相对原局无状态差异。
          </p>
        </div>

        <div v-if="delta.unsupportedNotes?.length" class="stack stack-1 mt-4">
          <p v-for="(n, i) in delta.unsupportedNotes" :key="i" class="note">
            UNSUPPORTED：{{ n }}
          </p>
        </div>
      </section>

      <!-- 结构主题 -->
      <section v-if="delta">
        <div class="sec-sub" style="margin-top: 0">
          <h3>结构主题</h3>
          <span class="sec-sub-note">
            十神主题 / 冲突关系 / 结构波动 —— 中间描述层，不是事件预测
          </span>
        </div>
        <div class="rows">
          <article v-for="(t, i) in delta.themes ?? []" :key="i" class="row-item">
            <div class="row-item-head">
              <span class="row-item-title">{{ t.label }}</span>
              <StatusBadge :label="t.direction" variant="mute" />
              <StatusBadge
                v-if="t.supportLevel === 'EXPERIMENTAL'"
                code="EXPERIMENTAL"
                with-hint
              />
              <StatusBadge v-else-if="t.supportLevel" :label="t.supportLevel" variant="mute" />
            </div>
            <p v-if="t.note" class="row-item-body">{{ t.note }}</p>
            <details v-if="t.basis?.length" class="mt-2">
              <summary>依据</summary>
              <div class="stack stack-1 mt-2">
                <p v-for="(b, j) in t.basis" :key="j" class="note mono">{{ b }}</p>
              </div>
            </details>
          </article>
          <p v-if="!(delta.themes ?? []).length" class="empty">无结构主题。</p>
        </div>
      </section>

      <!-- 事件主题 -->
      <section v-if="props.temporal.eventThemes">
        <div class="sec-sub" style="margin-top: 0">
          <h3>事件主题</h3>
          <span class="sec-sub-note">
            结构层面的「值得关注」候选 —— 不是预测事件；无 CONFIRMED 状态
          </span>
        </div>

        <div class="stack stack-4" data-testid="event-themes">
          <article v-for="t in themes" :key="t.theme" class="row-item">
            <div class="row-item-head">
              <span class="row-item-title">{{ t.themeCn || t.theme }}</span>
              <StatusBadge :code="t.status" with-hint />
              <StatusBadge
                v-if="t.agreement === 'CONFLICT'"
                code="CONFLICT"
                with-hint
              />
              <StatusBadge
                v-else-if="t.agreement === 'HIGH'"
                code="HIGH"
                with-hint
              />
              <StatusBadge :label="`置信 ${t.confidence}`" variant="mute" title="ENGINEERING_HEURISTIC 加权，非概率" />
              <span class="note-sm">（ENGINEERING_HEURISTIC 加权，非概率）</span>
            </div>

            <div v-if="Object.keys(t.schoolViews ?? {}).length" class="stack stack-1 mt-2">
              <p v-for="(v, k) in t.schoolViews" :key="k" class="note">视角 {{ k }}：{{ v }}</p>
            </div>

            <div class="mt-3">
              <div class="note-sm" style="margin-bottom: 4px">
                支持证据（{{ t.supportingEvidence?.length ?? 0 }}）
              </div>
              <div class="stack stack-1">
                <div v-for="(e, i) in t.supportingEvidence" :key="i" class="ev evidence-item is-plus">
                  <span class="ev-mark">+</span><span class="ev-body">{{ e }}</span>
                </div>
                <p v-if="!t.supportingEvidence?.length" class="note">无</p>
              </div>
            </div>

            <details v-if="t.opposingEvidence?.length" class="mt-3">
              <summary>反对证据（{{ t.opposingEvidence.length }}）</summary>
              <div class="stack stack-1 mt-2">
                <div v-for="(e, i) in t.opposingEvidence" :key="i" class="ev evidence-item is-minus">
                  <span class="ev-mark">−</span><span class="ev-body">{{ e }}</span>
                </div>
              </div>
            </details>

            <details v-if="t.conflictExplanations?.length" class="mt-3">
              <summary>冲突解释（上下文相关，无全局优先级）</summary>
              <div class="stack stack-2 mt-2">
                <div v-for="(c, i) in t.conflictExplanations" :key="i" class="ev evidence-item is-warn">
                  <span class="ev-mark">⚠</span>
                  <span class="ev-body">
                    <StatusBadge :label="DELTA_KIND_MAP[c.kind] ?? c.kind" variant="mute" />
                    {{ c.explanation }}
                  </span>
                </div>
              </div>
            </details>

            <details v-if="t.triggeredRules?.length" class="mt-3">
              <summary>触发规则（{{ t.triggeredRules.length }}）</summary>
              <div class="stack stack-1 mt-2">
                <div v-for="h in t.triggeredRules" :key="h.ruleId" class="ev evidence-item is-fact">
                  <span class="ev-mark">·</span>
                  <span class="ev-body">
                    <StatusBadge :code="h.ruleId" variant="rule" />
                    <StatusBadge
                      v-if="h.view"
                      :label="VIEW_MAP[h.view] ?? h.view"
                      variant="mute"
                      :title="h.view"
                    />
                    {{ h.label }}
                  </span>
                </div>
              </div>
            </details>

            <!-- 解释链 -->
            <details v-if="explanations[t.theme]" class="mt-3">
              <summary>解释链（Event Theme → Rule → 救应 → Evidence → Quote → Source）</summary>
              <div class="mt-3">
                <p class="verdict-text" style="font-size: var(--t-md)">
                  {{ explanations[t.theme].reasoning?.verdictStatement }}
                </p>

                <div class="sec-sub" style="margin-top: var(--s-4)">
                  <h4 style="font-size: var(--t-sm)">支持链</h4>
                  <StatusBadge
                    :label="String(explanations[t.theme].reasoning?.supportingChain?.length ?? 0)"
                    variant="mute"
                  />
                </div>
                <div class="stack stack-2">
                  <EvidenceCard
                    v-for="h in explanations[t.theme].reasoning?.supportingChain ?? []"
                    :key="h.ruleId"
                    tone="rescue"
                    :ref-id="h.ruleId"
                  >
                    <template #head>
                      <StatusBadge :code="h.ruleId" variant="rule" />
                      <StatusBadge
                        v-if="h.view"
                        :label="VIEW_MAP[h.view] ?? h.view"
                        variant="mute"
                        :title="h.view"
                      />
                      <StatusBadge
                        v-if="h.rescueApplied"
                        :label="`救应：${h.rescueApplied.id}`"
                        variant="pos"
                      />
                    </template>
                    <div v-for="(e, i) in h.evidence ?? []" :key="i" class="note">{{ e }}</div>
                    <figure v-if="h.quote" class="cite mt-2">
                      <blockquote style="margin: 0">{{ h.quote }}</blockquote>
                      <figcaption class="cite-src">
                        <span v-if="h.source?.book">《{{ h.source.book }}》</span>
                      </figcaption>
                    </figure>
                    <p v-if="h.rescueApplied" class="note mt-2">{{ h.rescueApplied.note }}</p>
                  </EvidenceCard>
                </div>

                <div class="sec-sub" style="margin-top: var(--s-5)">
                  <h4 style="font-size: var(--t-sm)">反对链</h4>
                  <StatusBadge
                    :label="String(explanations[t.theme].reasoning?.opposingChain?.length ?? 0)"
                    variant="mute"
                  />
                </div>
                <div class="stack stack-2">
                  <EvidenceCard
                    v-for="h in explanations[t.theme].reasoning?.opposingChain ?? []"
                    :key="h.ruleId"
                    tone="minus"
                    :ref-id="h.ruleId"
                  >
                    <template #head>
                      <StatusBadge :code="h.ruleId" variant="rule" />
                      <StatusBadge
                        v-if="h.view"
                        :label="VIEW_MAP[h.view] ?? h.view"
                        variant="mute"
                        :title="h.view"
                      />
                      <StatusBadge
                        v-if="h.rescueApplied"
                        :label="`被救应削弱：${h.rescueApplied.id}`"
                        variant="warn"
                      />
                    </template>
                    <div v-for="(e, i) in h.evidence ?? []" :key="i" class="note">{{ e }}</div>
                    <figure v-if="h.quote" class="cite mt-2">
                      <blockquote style="margin: 0">{{ h.quote }}</blockquote>
                      <figcaption class="cite-src">
                        <span v-if="h.source?.book">《{{ h.source.book }}》</span>
                      </figcaption>
                    </figure>
                  </EvidenceCard>
                </div>
              </div>
            </details>
          </article>

          <p v-if="!themes.length" class="empty">当前岁运上下文无事件主题候选。</p>
        </div>
      </section>

      <!-- 边界声明 -->
      <section class="notice is-boundary">
        <span class="notice-key">边界</span>
        <span>
          以上全部内容为结构变化描述，不构成任何吉凶或事件预测。
          「事件主题」为结构层面的关注候选，无 CONFIRMED 状态；
          置信度为工程启发式加权，不是概率。
        </span>
      </section>
    </template>

    <p v-else-if="!props.loading" class="note">
      选择大运与流年后点击「分析」，即可展开该时间点的结构变化与证据链。
    </p>
  </div>
</template>
