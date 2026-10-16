<script setup lang="ts">
/**
 * KnowledgeView — 知识工作台。
 *
 * 定位：Source ↔ Rule ↔ Conflict ↔ Case 的**只读导航**。
 * 纪律：不复制推理逻辑；规则图与命例索引均来自后端；
 *       冲突密度、覆盖率、审计门等指标原样呈现，不做解读性加工。
 */
import { computed, onMounted, ref, watch } from "vue";
import GraphPanel from "../components/GraphPanel.vue";
import RuleCard from "../components/RuleCard.vue";
import StatusBadge from "../components/StatusBadge.vue";
import { loadKnowledgeBundle, loadKnowledgeGraph } from "../api/tianze";
import { VIEW_MAP, PROVENANCE_MAP } from "../presentation/vocab";

const props = defineProps<{
  /** 由关系 / 时序页跳转注入的规则号 */
  focusId?: string | null;
  searchSeed?: string;
}>();

const bundle = ref<Awaited<ReturnType<typeof loadKnowledgeBundle>> | null>(null);
const graph = ref<any>(null);
const search = ref(props.searchSeed ?? "");
const domain = ref("all");
const selectedId = ref<string | null>(props.focusId ?? null);
const loading = ref(false);
const graphRef = ref<InstanceType<typeof GraphPanel> | null>(null);

const rules = computed(() => bundle.value?.rules ?? []);
const stats = computed(() => bundle.value?.stats ?? null);
const funnel = computed(() => bundle.value?.funnel ?? null);
const coverage = computed(() => bundle.value?.coverage ?? null);
const release = computed(() => bundle.value?.release ?? null);
const evalCompare = computed(() => bundle.value?.evaluationCompare ?? null);
const review = computed(() => bundle.value?.review ?? []);

const domains = computed(() => {
  const s = new Set(rules.value.map((r: any) => r.domain).filter(Boolean));
  return [...s].sort();
});

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase();
  return rules.value.filter((r: any) => {
    if (domain.value !== "all" && r.domain !== domain.value) return false;
    if (!q) return true;
    return [r.id, r.label, r.theme, r.category, r.candidateId]
      .filter(Boolean)
      .some((v: string) => String(v).toLowerCase().includes(q));
  });
});

const selectedRule = computed(() =>
  rules.value.find((r: any) => r.id === selectedId.value) ?? null);

/**
 * 分页：默认只渲染一屏可见量。
 * 数百条规则一次性铺开会把页面拉成长卷，反而降低"快速找到目标"的能力；
 * 这里以检索为主、翻页为辅。
 */
const PAGE_SIZE = 36;
const visibleCount = ref(PAGE_SIZE);
const pagedRules = computed(() => filtered.value.slice(0, visibleCount.value));
const hasMore = computed(() => filtered.value.length > visibleCount.value);

// 检索条件变化时回到第一页
watch([search, domain], () => { visibleCount.value = PAGE_SIZE; });

async function load() {
  if (bundle.value) return;
  loading.value = true;
  const [b, g] = await Promise.all([loadKnowledgeBundle(), loadKnowledgeGraph()]);
  bundle.value = b;
  graph.value = g;
  loading.value = false;
}

onMounted(load);
watch(() => props.focusId, (v) => {
  if (v) {
    selectedId.value = v;
    search.value = v;
    void load();
  }
});
watch(() => props.searchSeed, (v) => { if (v) search.value = v; });
watch(() => selectedId.value, (v) => {
  if (v) search.value = v;
});

function onSelect(id: string | null) {
  selectedId.value = id === selectedId.value ? null : id;
}
</script>

<template>
  <div class="stack stack-6">
    <!-- 知识库规模 -->
    <section v-if="stats">
      <div class="sec-sub" style="margin-top: 0">
        <h3>知识库规模</h3>
        <span class="sec-sub-note">
          候选规则与可执行规则是不同口径，此处分别列出，不做合并
        </span>
      </div>
      <div class="metrics">
        <div class="metric">
          <span class="metric-key">可执行规则</span>
          <span class="metric-val">{{ stats.executableTotal }}</span>
          <span class="metric-sub">ExecutableRule</span>
        </div>
        <div
          v-for="(v, k) in stats.executableByDomain"
          :key="k"
          class="metric"
        >
          <span class="metric-key">{{ k }}</span>
          <span class="metric-val">{{ v }}</span>
          <span class="metric-sub">domain</span>
        </div>
        <div v-if="stats.candidateTotal != null" class="metric">
          <span class="metric-key">候选规则</span>
          <span class="metric-val">{{ stats.candidateTotal }}</span>
          <span class="metric-sub">候选 ≠ 可执行</span>
        </div>
      </div>
    </section>

    <!-- 规则检索 -->
    <section>
      <div class="sec-sub" style="margin-top: 0">
        <h3>规则检索</h3>
        <span class="sec-sub-note">按 id / 标签 / 主题 / 候选号检索</span>
        <span class="sec-sub-aside">
          <StatusBadge :label="`${filtered.length} / ${rules.length}`" variant="mute" />
        </span>
      </div>

      <div class="toolbar" style="margin-bottom: var(--s-4)">
        <label class="field grow">
          <span class="field-label">检索</span>
          <input v-model="search" type="search" placeholder="例如 EV-CAR-01 / 官星 / career" />
        </label>
        <label class="field">
          <span class="field-label">领域</span>
          <select v-model="domain">
            <option value="all">全部</option>
            <option v-for="d in domains" :key="d" :value="d">{{ d }}</option>
          </select>
        </label>
        <button v-if="search || domain !== 'all'" class="btn-sm" type="button" @click="search = ''; domain = 'all'">
          清除
        </button>
      </div>

      <p v-if="loading" class="empty">正在载入知识库…</p>
      <div v-else class="rule-list">
        <RuleCard
          v-for="r in pagedRules"
          :key="r.id"
          :rule="r"
          :selected="selectedId === r.id"
          @select="onSelect"
        />
      </div>
      <p v-if="!loading && !filtered.length" class="empty">无匹配规则。</p>
      <div v-if="hasMore" class="row row-3 mt-4">
        <button
          class="btn-sm"
          type="button"
          @click="visibleCount += PAGE_SIZE"
        >再显示 {{ Math.min(PAGE_SIZE, filtered.length - visibleCount) }} 条</button>
        <span class="note">
          已显示 {{ pagedRules.length }} / {{ filtered.length }} 条
        </span>
      </div>
      <p v-else-if="filtered.length" class="note mt-3">
        已显示全部 {{ filtered.length }} 条。
      </p>
    </section>

    <!-- 规则关系图 -->
    <section>
      <div class="sec-sub" style="margin-top: 0">
        <h3>规则关系图</h3>
        <span class="sec-sub-note">
          节点按 domain 分层铺设；边为后端声明的 conflict / rescues / school-conflict
        </span>
      </div>

      <div class="graph-split">
        <GraphPanel
          ref="graphRef"
          :graph="graph"
          :selected-id="selectedId"
          @select="onSelect"
        />

        <!-- 节点研究成果面板 -->
        <aside class="graph-detail">
          <template v-if="selectedRule">
            <div class="row row-2">
              <StatusBadge :code="selectedRule.id" variant="rule" />
              <StatusBadge :label="selectedRule.domain" variant="mute" />
            </div>
            <p class="rule-card-label" style="font-size: var(--t-md); color: var(--ink-900)">
              {{ selectedRule.label }}
            </p>

            <dl class="report-dl mt-4">
              <dt>来源</dt>
              <dd>{{ selectedRule.source?.book || "—" }}</dd>
              <dt>主题</dt>
              <dd>{{ selectedRule.theme || "—" }}</dd>
              <dt v-if="selectedRule.candidateId">候选号</dt>
              <dd v-if="selectedRule.candidateId" class="mono">{{ selectedRule.candidateId }}</dd>
              <dt v-if="selectedRule.quality != null">质量</dt>
              <dd v-if="selectedRule.quality != null" class="mono">Q{{ selectedRule.quality }}</dd>
            </dl>

            <div v-if="selectedRule.provenanceLevels?.length" class="mt-3">
              <div class="note-sm" style="margin-bottom: 4px">溯源层级</div>
              <div class="row row-1">
                <StatusBadge
                  v-for="lv in selectedRule.provenanceLevels"
                  :key="lv"
                  :label="PROVENANCE_MAP[lv] ?? lv"
                  :variant="lv === 'ENGINEERING_HEURISTIC' ? 'warn' : 'mute'"
                  :title="lv"
                />
              </div>
            </div>

            <div v-if="selectedRule.normalizationNotes" class="notice mt-4">
              <span class="notice-key">归一化口径</span>
              <span>{{ selectedRule.normalizationNotes }}</span>
            </div>

            <div v-if="selectedRule.conflictNeighbors?.length" class="mt-4">
              <div class="note-sm" style="margin-bottom: 4px">冲突 / 救应邻接</div>
              <div class="stack stack-1">
                <div
                  v-for="(c, i) in selectedRule.conflictNeighbors"
                  :key="i"
                  class="ev evidence-item is-quiet"
                >
                  <span class="ev-mark">·</span>
                  <span class="ev-body">
                    <StatusBadge :label="c.edgeType" :variant="c.edgeType === 'conflict' ? 'neg' : 'pos'" />
                    <span class="mono">{{ (c.related ?? []).join(", ") }}</span>
                    <span v-if="c.resolution" class="note-sm"> · {{ c.resolution }}</span>
                  </span>
                </div>
              </div>
            </div>

            <p v-if="selectedRule.conflictNote" class="note mt-3">⚠ {{ selectedRule.conflictNote }}</p>

            <details v-if="selectedRule.conditions?.length" class="mt-4">
              <summary>成立条件（ExplanationChain 条件层）</summary>
              <div class="stack stack-1 mt-2">
                <p v-for="(cd, i) in selectedRule.conditions" :key="i" class="note mono">
                  {{ cd.field }} {{ cd.operator }}
                  {{ Array.isArray(cd.value) ? cd.value.join("/") : cd.value }}
                </p>
              </div>
            </details>

            <details v-if="selectedRule.replaySamples?.length" class="mt-4">
              <summary>重放命例（Rule → Case，最多 {{ selectedRule.replaySamples.length }} 条）</summary>
              <div class="stack stack-2 mt-2">
                <div v-for="(rc, i) in selectedRule.replaySamples" :key="i" class="ev evidence-item is-quiet">
                  <span class="ev-mark">·</span>
                  <span class="ev-body">
                    <span class="mono">{{ rc.caseId }}</span>
                    <span class="note-sm">（{{ rc.book }}·{{ rc.luck || "原局" }}{{ rc.annual ? "→" + rc.annual : "" }}）</span>
                    <div class="mt-2 row row-1">
                      <StatusBadge :label="rc.theme" variant="mute" />
                      <StatusBadge
                        :label="rc.relation"
                        :variant="rc.relation === 'SOURCE_SUPPORTS' ? 'pos'
                                : rc.relation === 'SOURCE_DIFFERS' ? 'neg' : 'mute'"
                      />
                    </div>
                  </span>
                </div>
                <div v-if="Object.keys(selectedRule.relationDistribution ?? {}).length" class="note">
                  分布：{{
                    Object.entries(selectedRule.relationDistribution)
                      .map(([k, v]) => `${k}:${v}`).join("、")
                  }}
                </div>
              </div>
            </details>

            <p v-if="selectedRule.randomTriggerRate != null" class="note mt-3">
              随机盘触发率 {{ (selectedRule.randomTriggerRate * 100).toFixed(1) }}%
            </p>
          </template>

          <div v-else class="stack stack-2">
            <p class="note">
              点击图中节点或左侧规则卡，可在此查看该规则的身份、溯源层级、
              冲突邻接与重放命例。
            </p>
            <p class="note-sm">
              颜色对应 domain（事件 / 岁运 / 调候 / 救应谓词），线的样式对应边型。
            </p>
          </div>
        </aside>
      </div>
    </section>

    <!-- 质量与覆盖 -->
    <section v-if="funnel || coverage">
      <div class="sec-sub" style="margin-top: 0">
        <h3>质量与覆盖</h3>
        <span class="sec-sub-note">知识库漏斗、未触发规则与审计门（原样呈现）</span>
      </div>

      <div v-if="funnel?.funnel" class="funnel">
        <div class="funnel-stage">
          <div class="funnel-key">Source</div>
          <div class="funnel-val">{{ funnel.funnel.sources }}</div>
          <div class="funnel-sub">古籍来源</div>
        </div>
        <div class="funnel-stage">
          <div class="funnel-key">Candidate</div>
          <div class="funnel-val">{{ funnel.funnel.candidates }}</div>
          <div class="funnel-sub">候选规则</div>
        </div>
        <div class="funnel-stage">
          <div class="funnel-key">Executable</div>
          <div class="funnel-val">{{ funnel.funnel.executable }}</div>
          <div class="funnel-sub">可执行规则</div>
        </div>
        <div class="funnel-stage">
          <div class="funnel-key">未用候选</div>
          <div class="funnel-val">{{ funnel.candidatesUnused }}</div>
          <div class="funnel-sub">尚未进入引擎</div>
        </div>
        <div class="funnel-stage">
          <div class="funnel-key">未触发</div>
          <div class="funnel-val">{{ funnel.neverTriggered }}</div>
          <div class="funnel-sub">never-triggered</div>
        </div>
        <div class="funnel-stage">
          <div class="funnel-key">冲突密度</div>
          <div class="funnel-val">{{ funnel.conflictDensity }}</div>
          <div class="funnel-sub">conflict density</div>
        </div>
      </div>

      <div v-if="coverage?.gates" class="surface mt-4">
        <div class="row between" style="margin-bottom: var(--s-3)">
          <h4 style="font-family: var(--font-display)">审计门</h4>
          <StatusBadge
            :label="coverage.allPass ? 'ALL PASS' : 'FAIL'"
            :variant="coverage.allPass ? 'pos' : 'neg'"
          />
        </div>
        <div class="stack stack-1">
          <div v-for="(g, k) in coverage.gates" :key="k" class="gate-row">
            <span class="gate-name">{{ k }}</span>
            <span class="gate-verdict" :class="g.pass ? 'is-pass' : 'is-fail'">
              {{ g.pass ? "PASS" : "FAIL" }}
            </span>
          </div>
        </div>
      </div>

      <div v-if="coverage?.coverage" class="surface mt-4">
        <h4 style="font-family: var(--font-display); margin-bottom: var(--s-3)">Rule → Case 覆盖</h4>
        <div class="stack stack-2">
          <p class="note">
            {{ Object.entries(coverage.coverage.ruleCaseCoverage ?? {})
                .map(([k, v]) => `${k}:${v}`).join("、") || "无" }}
          </p>
          <p class="note">
            未触发（never-in-replay）：
            {{ (coverage.coverage.eventRulesNeverInReplay ?? []).join("、") || "无" }}
          </p>
        </div>
      </div>
    </section>

    <!-- 评估对比：只展示最近若干次运行，避免历史记录把页面拉成长卷 -->
    <section v-if="evalCompare?.comparisons?.length">
      <div class="sec-sub" style="margin-top: 0">
        <h3>AI 评估对比</h3>
        <span class="sec-sub-note">
          确定性指标回归对比（无 LLM-as-judge）· 默认显示最近 12 次
        </span>
        <span class="sec-sub-aside">
          <StatusBadge :label="`共 ${evalCompare.comparisons.length} 次`" variant="mute" />
        </span>
      </div>
      <div class="stack stack-2">
        <details
          v-for="(c, i) in evalCompare.comparisons.slice(-12).reverse()"
          :key="i"
          class="surface"
        >
          <summary>
            <span class="mono">{{ c.metrics.provider }}/{{ c.metrics.model }}</span>
            <span class="note-sm">（prompt {{ c.metrics.promptVersion }}）</span>
            — pass {{ c.metrics.verdictPass }}/{{ c.metrics.verdictTotal }}
            <StatusBadge
              v-if="Object.keys(c.regressionAgainstPrevious ?? {}).length"
              label="回归"
              variant="neg"
            />
          </summary>
          <div class="metrics mt-3">
            <div class="metric">
              <span class="metric-key">grounding</span>
              <span class="metric-val">{{ c.metrics.groundingIssueTotal }}</span>
            </div>
            <div class="metric">
              <span class="metric-key">banned</span>
              <span class="metric-val">{{ c.metrics.bannedTotal }}</span>
            </div>
            <div class="metric">
              <span class="metric-key">disagreement 缺失</span>
              <span class="metric-val">{{ c.metrics.disagreementMissingCount }}</span>
            </div>
            <div class="metric">
              <span class="metric-key">claim refs</span>
              <span class="metric-val">{{ c.metrics.claimRefsUsedAvg }}</span>
            </div>
            <div v-if="c.telemetry" class="metric">
              <span class="metric-key">latency ms</span>
              <span class="metric-val">{{ c.telemetry.latencyMsAvg }}</span>
            </div>
            <div v-if="c.telemetry" class="metric">
              <span class="metric-key">tokens</span>
              <span class="metric-val">{{ c.telemetry.tokensTotal }}</span>
            </div>
          </div>
          <div v-if="Object.keys(c.regressionAgainstPrevious ?? {}).length" class="stack stack-1 mt-3">
            <div v-for="(v, k) in c.regressionAgainstPrevious" :key="k" class="ev evidence-item is-minus">
              <span class="ev-mark">−</span><span class="ev-body">{{ k }}: {{ v }}</span>
            </div>
          </div>
        </details>
      </div>
    </section>

    <!-- 发布元信息 -->
    <section v-if="release?.metadata">
      <div class="sec-sub" style="margin-top: 0">
        <h3>发布元信息</h3>
      </div>
      <div class="metrics">
        <div class="metric">
          <span class="metric-key">commit</span>
          <span class="metric-val mono" style="font-size: var(--t-md)">
            {{ (release.metadata.release?.gitCommit || "").slice(0, 12) || "—" }}
          </span>
        </div>
        <div class="metric">
          <span class="metric-key">engine</span>
          <span class="metric-val mono" style="font-size: var(--t-md)">
            {{ release.metadata.engineVersion }}
          </span>
        </div>
        <div class="metric">
          <span class="metric-key">测试</span>
          <span class="metric-val">{{ release.metadata.counts?.tests }}</span>
        </div>
        <div class="metric">
          <span class="metric-key">质量</span>
          <span class="metric-val" style="font-size: var(--t-md)">
            {{ release.qualitySummary?.allPass ? "ALL PASS" : "FAIL" }}
          </span>
        </div>
      </div>
      <details class="mt-3">
        <summary>版本依赖</summary>
        <div class="stack stack-1 mt-2">
          <p v-for="(v, k) in release.metadata.versions" :key="k" class="note mono">
            {{ k }}: {{ v }}
          </p>
        </div>
      </details>
    </section>

    <!-- 复核队列 -->
    <section v-if="review.length">
      <div class="sec-sub" style="margin-top: 0">
        <h3>复核队列</h3>
        <span class="sec-sub-note">
          只读；HUMAN_VERIFIED 只能由真实人工产生，系统不伪造
        </span>
        <span class="sec-sub-aside">
          <StatusBadge :label="String(review.length)" variant="mute" />
        </span>
      </div>
      <div class="rows">
        <article v-for="(it, i) in review" :key="i" class="row-item">
          <div class="row-item-head">
            <StatusBadge
              :label="it.priority"
              :variant="it.priority === 'P1' ? 'neg' : it.priority === 'P2' ? 'warn' : 'mute'"
            />
            <StatusBadge :label="it.section" variant="mute" />
            <span class="mono note">{{ it.id || it.caseId || "" }}</span>
          </div>
          <p v-if="it.text" class="row-item-body">{{ it.text }}</p>
          <p v-else-if="it.title" class="row-item-body">{{ it.title }}</p>
          <p v-if="it.note" class="note mt-2">{{ it.note }}</p>
        </article>
      </div>
    </section>

    <p class="note">
      本页为知识库的只读导航界面：来源、规则、冲突、命例四者的关系由后端声明，
      前端不合并口径、不推断缺失关系。
    </p>
  </div>
</template>

<style scoped>
.rule-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--s-2);
}
</style>
