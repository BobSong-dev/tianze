<script setup lang="ts">
/**
 * KnowledgeView — 知识与质量工作台。
 *
 * 定位：Source ↔ Rule ↔ Conflict ↔ Case 的只读科研导航。
 * 架构：
 *  - 顶部指标仪表带：快速感知知识库规模与审计门状态
 *  - 标签式科研分区：
 *    1. 规则关系图谱 (GraphPanel & 节点详情)
 *    2. 规则目录检索 (Rule Directory, 分页与领域检索)
 *    3. 知识漏斗与指标 (Funnel & Domain Breakdown)
 *    4. 审计门与覆盖率 (Audit Gates & Case Coverage)
 *    5. AI 评测对比 (Deterministic Evaluation Benchmarks)
 *    6. 复核队列与发布 (Review Queue & Release Info)
 */
import { computed, onMounted, ref, watch } from "vue";
import GraphPanel from "../components/GraphPanel.vue";
import RuleCard from "../components/RuleCard.vue";
import StatusBadge from "../components/StatusBadge.vue";
import { loadKnowledgeBundle, loadKnowledgeGraph } from "../api/tianze";
import { PROVENANCE_MAP } from "../presentation/vocab";

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
const loadError = ref("");
const graphRef = ref<InstanceType<typeof GraphPanel> | null>(null);

type KnowledgeTab = "graph" | "rules" | "funnel" | "gates" | "eval" | "review";
const activeTab = ref<KnowledgeTab>("graph");

const TERM_CN: Record<string, string> = {
  event: "事件", temporal: "时序", tenet: "理论", structure: "结构",
  relation: "关系", pattern: "格局", strength: "旺衰", tiaohou: "调候",
  special_pattern: "特殊格局", stem_branch: "干支", calendar: "历法",
  grounding: "事实接地", banned: "违禁词", "disagreement-missing": "分歧缺失",
  disagreementMissing: "分歧缺失", claimRefs: "引用缺失",
  latencyMs: "延迟 ms", tokens: "tokens", commit: "提交", engine: "引擎",
  "strict-disagreement": "严格分歧",
};
function termCn(k: string): string {
  return TERM_CN[k] ?? k;
}

const rules = computed(() => bundle.value?.rules ?? []);
const stats = computed(() => bundle.value?.stats ?? null);
const funnel = computed(() => bundle.value?.funnel ?? null);
const coverage = computed(() => bundle.value?.coverage ?? null);
const release = computed(() => bundle.value?.release ?? null);
const evalCompare = computed(() => bundle.value?.evaluationCompare ?? null);
const review = computed(() => bundle.value?.review ?? []);
const resourceLabels = { rules: "规则目录", stats: "规则统计", review: "复核队列", funnel: "知识漏斗", coverage: "审计覆盖率", release: "发布信息", evaluationCompare: "AI 评测" };
const resourceErrors = computed(() => bundle.value?.errors ?? {});

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

const PAGE_SIZE = 36;
const visibleCount = ref(PAGE_SIZE);
const pagedRules = computed(() => filtered.value.slice(0, visibleCount.value));
const hasMore = computed(() => filtered.value.length > visibleCount.value);

watch([search, domain], () => { visibleCount.value = PAGE_SIZE; });

async function load(force = false) {
  if (loading.value || (bundle.value && !force)) return;
  loading.value = true;
  loadError.value = "";
  try {
    const [loadedBundle, loadedGraph] = await Promise.all([loadKnowledgeBundle(), loadKnowledgeGraph()]);
    bundle.value = loadedBundle;
    graph.value = loadedGraph;
    const failed = Object.keys(loadedBundle.errors).map(key => resourceLabels[key as keyof typeof resourceLabels]);
    if (!loadedGraph) failed.push("规则图谱");
    if (failed.length) loadError.value = `${failed.join("、")}暂时无法加载，请重新加载。已加载的数据仍可查看。`;
  } catch {
    loadError.value = "知识数据加载失败，请检查本地 API 服务后重试。";
  } finally {
    loading.value = false;
  }
}

onMounted(() => load());

function moveTab(event: KeyboardEvent) {
  const tabs: KnowledgeTab[] = ["graph", "rules", "funnel", "gates", "eval", "review"];
  const index = tabs.indexOf(activeTab.value);
  let target = index;
  if (event.key === "ArrowRight") target = (index + 1) % tabs.length;
  else if (event.key === "ArrowLeft") target = (index + tabs.length - 1) % tabs.length;
  else if (event.key === "Home") target = 0;
  else if (event.key === "End") target = tabs.length - 1;
  else return;
  event.preventDefault();
  activeTab.value = tabs[target];
  (event.currentTarget as HTMLElement).querySelectorAll<HTMLButtonElement>('[role="tab"]')[target]?.focus();
}

watch(() => props.focusId, (v) => {
  if (v) {
    selectedId.value = v;
    search.value = v;
    activeTab.value = "graph";
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

function switchToRules(id?: string) {
  if (id) {
    selectedId.value = id;
    search.value = id;
  }
  activeTab.value = "rules";
}
</script>

<template>
  <div class="stack stack-5 knowledge-workspace" :aria-busy="loading">
    <p v-if="loading" class="loading-status" role="status"><span class="loading-indicator" aria-hidden="true" />正在读取规则、来源与审计信息…</p>
    <div v-if="loadError" class="error" role="alert"><span>{{ loadError }}</span><button type="button" :disabled="loading" @click="load(true)">重新加载</button></div>
    <!-- 顶层科研指标带 -->
    <section v-if="stats" class="surface surface-tint">
      <div class="metrics">
        <div class="metric">
          <span class="metric-key">可执行规则</span>
          <span class="metric-val mono">{{ stats.executableTotal }}</span>
          <span class="metric-sub">ExecutableRule</span>
        </div>
        <div v-if="stats.candidateTotal != null" class="metric">
          <span class="metric-key">候选规则</span>
          <span class="metric-val mono">{{ stats.candidateTotal }}</span>
          <span class="metric-sub">候选 ≠ 可执行</span>
        </div>
        <div v-if="funnel?.funnel" class="metric">
          <span class="metric-key">来源古籍</span>
          <span class="metric-val mono">{{ funnel.funnel.sources }}</span>
          <span class="metric-sub">Sources</span>
        </div>
        <div v-if="coverage" class="metric">
          <span class="metric-key">质量审计门</span>
          <span class="metric-val" :style="{ color: coverage.allPass ? 'var(--st-likely)' : 'var(--st-blocked)' }">
            {{ coverage.allPass ? 'ALL PASS' : 'FAIL' }}
          </span>
          <span class="metric-sub">10 项自动化质检门</span>
        </div>
        <div v-if="review.length" class="metric">
          <span class="metric-key">复核队列</span>
          <span class="metric-val mono">{{ review.length }}</span>
          <span class="metric-sub">需人工核实条目</span>
        </div>
      </div>
    </section>

    <!-- 工作台导航切换标签 -->
    <div class="kw-tab-bar" role="tablist" aria-label="知识研究分区" @keydown="moveTab">
      <button
        type="button"
        class="kw-tab-btn"
        :class="{ 'is-active': activeTab === 'graph' }"
        role="tab"
        :aria-selected="activeTab === 'graph'"
        :tabindex="activeTab === 'graph' ? 0 : -1"
        id="tab-graph"
        aria-controls="panel-graph"
        @click="activeTab = 'graph'"
      >
        <span class="kw-tab-idx">01</span>
        <span>规则关系图谱</span>
      </button>

      <button
        type="button"
        class="kw-tab-btn"
        :class="{ 'is-active': activeTab === 'rules' }"
        role="tab"
        :aria-selected="activeTab === 'rules'"
        :tabindex="activeTab === 'rules' ? 0 : -1"
        id="tab-rules"
        aria-controls="panel-rules"
        @click="activeTab = 'rules'"
      >
        <span class="kw-tab-idx">02</span>
        <span>规则目录检索</span>
        <span class="kw-tab-badge mono">{{ loading || resourceErrors.rules ? "—" : filtered.length }}</span>
      </button>

      <button
        type="button"
        class="kw-tab-btn"
        :class="{ 'is-active': activeTab === 'funnel' }"
        role="tab"
        :aria-selected="activeTab === 'funnel'"
        :tabindex="activeTab === 'funnel' ? 0 : -1"
        id="tab-funnel"
        aria-controls="panel-funnel"
        @click="activeTab = 'funnel'"
      >
        <span class="kw-tab-idx">03</span>
        <span>知识规模与漏斗</span>
      </button>

      <button
        type="button"
        class="kw-tab-btn"
        :class="{ 'is-active': activeTab === 'gates' }"
        role="tab"
        :aria-selected="activeTab === 'gates'"
        :tabindex="activeTab === 'gates' ? 0 : -1"
        id="tab-gates"
        aria-controls="panel-gates"
        @click="activeTab = 'gates'"
      >
        <span class="kw-tab-idx">04</span>
        <span>审计门与覆盖率</span>
      </button>

      <button
        type="button"
        class="kw-tab-btn"
        :class="{ 'is-active': activeTab === 'eval' }"
        role="tab"
        :aria-selected="activeTab === 'eval'"
        :tabindex="activeTab === 'eval' ? 0 : -1"
        id="tab-eval"
        aria-controls="panel-eval"
        @click="activeTab = 'eval'"
      >
        <span class="kw-tab-idx">05</span>
        <span>AI 评测对比</span>
      </button>

      <button
        type="button"
        class="kw-tab-btn"
        :class="{ 'is-active': activeTab === 'review' }"
        role="tab"
        :aria-selected="activeTab === 'review'"
        :tabindex="activeTab === 'review' ? 0 : -1"
        id="tab-review"
        aria-controls="panel-review"
        @click="activeTab = 'review'"
      >
        <span class="kw-tab-idx">06</span>
        <span>复核队列与发布</span>
      </button>
    </div>

    <!-- 01 规则关系图谱 (主视图) -->
    <section v-show="activeTab === 'graph'" id="panel-graph" role="tabpanel" aria-labelledby="tab-graph">
      <div class="sec-sub" style="margin-top: 0">
        <h3>规则关系图 (Rule Graph)</h3>
        <span class="sec-sub-note">
          节点按 domain 分层椭圆布局；边为后端 conflict / rescues / school-conflict 声明
        </span>
      </div>

      <div v-if="graph" class="graph-split">
        <GraphPanel
          ref="graphRef"
          :graph="graph"
          :selected-id="selectedId"
          @select="onSelect"
        />

        <!-- 节点研究详情面板 -->
        <aside class="graph-detail">
          <template v-if="selectedRule">
            <div class="row row-2">
              <StatusBadge :code="selectedRule.id" variant="rule" />
              <StatusBadge :label="selectedRule.domain" variant="mute" />
            </div>
            <p class="rule-card-label" style="font-size: var(--t-md); color: var(--ink-900); margin-top: 6px">
              {{ selectedRule.label }}
            </p>

            <dl class="report-dl mt-3">
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
              <div class="row row-1" style="flex-wrap: wrap">
                <StatusBadge
                  v-for="lv in selectedRule.provenanceLevels"
                  :key="lv"
                  :label="PROVENANCE_MAP[lv] ?? lv"
                  :variant="lv === 'ENGINEERING_HEURISTIC' ? 'warn' : 'mute'"
                  :title="lv"
                />
              </div>
            </div>

            <div v-if="selectedRule.normalizationNotes" class="notice mt-3">
              <span class="notice-key">归一化</span>
              <span>{{ selectedRule.normalizationNotes }}</span>
            </div>

            <div v-if="selectedRule.conflictNeighbors?.length" class="mt-3">
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

            <details v-if="selectedRule.conditions?.length" class="mt-3">
              <summary>成立条件（{{ selectedRule.conditions.length }} 项）</summary>
              <div class="stack stack-1 mt-2">
                <p v-for="(cd, i) in selectedRule.conditions" :key="i" class="note mono">
                  {{ cd.field }} {{ cd.operator }}
                  {{ Array.isArray(cd.value) ? cd.value.join("/") : cd.value }}
                </p>
              </div>
            </details>

            <details v-if="selectedRule.replaySamples?.length" class="mt-3">
              <summary>重放命例（Rule → Case，共 {{ selectedRule.replaySamples.length }} 例）</summary>
              <div class="stack stack-2 mt-2">
                <div v-for="(rc, i) in selectedRule.replaySamples" :key="i" class="ev evidence-item is-quiet">
                  <span class="ev-mark">·</span>
                  <span class="ev-body">
                    <span class="mono">{{ rc.caseId }}</span>
                    <span class="note-sm">（{{ rc.book }}·{{ rc.luck || "原局" }}{{ rc.annual ? "→" + rc.annual : "" }}）</span>
                    <div class="mt-1 row row-1">
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

            <div class="mt-3 row between">
              <span v-if="selectedRule.randomTriggerRate != null" class="note mono">
                随机盘触发 {{ (selectedRule.randomTriggerRate * 100).toFixed(1) }}%
              </span>
              <button class="btn-link" type="button" @click="switchToRules(selectedRule.id)">
                在目录中定位 →
              </button>
            </div>
          </template>

          <div v-else class="stack stack-2" style="padding: var(--s-4) var(--s-2); text-align: center">
            <p class="note" style="color: var(--ink-700); font-weight: 600">
              点击图中节点或下方规则卡
            </p>
            <p class="note-sm">
              在此查看规则身份、溯源层级、成立条件、冲突邻接与历史重放命例。
            </p>
            <div class="note-sm" style="margin-top: var(--s-2)">
              节点颜色对应领域，连线样式区分冲突、救应与流派分歧。
            </div>
          </div>
        </aside>
      </div>
      <p v-else-if="!loading" class="empty">规则图谱暂不可用，请使用上方“重新加载”。</p>
    </section>

    <!-- 02 规则目录检索 -->
    <section v-show="activeTab === 'rules'" id="panel-rules" role="tabpanel" aria-labelledby="tab-rules">
      <div class="sec-sub" style="margin-top: 0">
        <h3>规则名录检索</h3>
        <span class="sec-sub-note">按规则 ID / 标签 / 领域 / 主题关键字即时检索</span>
        <span class="sec-sub-aside">
          <StatusBadge :label="resourceErrors.rules ? '暂不可用' : `${filtered.length} / ${rules.length}`" variant="mute" />
        </span>
      </div>

      <div class="toolbar" style="margin-bottom: var(--s-4)">
        <label class="field grow">
          <span class="field-label">关键字检索</span>
          <input v-model="search" type="search" placeholder="例如 EV-CAR-01 / 官星 / career / 伏吟" />
        </label>
        <label class="field" style="min-width: 140px">
          <span class="field-label">所属领域</span>
          <select v-model="domain">
            <option value="all">全部领域</option>
            <option v-for="d in domains" :key="d" :value="d">{{ termCn(d) }} ({{ d }})</option>
          </select>
        </label>
        <button v-if="search || domain !== 'all'" class="btn-sm" type="button" @click="search = ''; domain = 'all'">
          清除筛选
        </button>
      </div>

      <p v-if="loading" class="empty">正在载入规则库…</p>
      <p v-else-if="resourceErrors.rules" class="empty">规则目录加载失败，请使用上方“重新加载”。</p>
      <div v-else class="rule-list">
        <RuleCard
          v-for="r in pagedRules"
          :key="r.id"
          :rule="r"
          :selected="selectedId === r.id"
          @select="onSelect"
        />
      </div>
      <p v-if="!loading && !resourceErrors.rules && !filtered.length" class="empty">无匹配规则。</p>
      <div v-if="hasMore" class="row row-3 mt-4">
        <button
          class="btn-sm btn-primary"
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

    <!-- 03 知识规模与漏斗 -->
    <section v-show="activeTab === 'funnel'" id="panel-funnel" role="tabpanel" aria-labelledby="tab-funnel">
      <div class="sec-sub" style="margin-top: 0">
        <h3>知识库规模与领域分布</h3>
      </div>
      <div v-if="stats" class="metrics">
        <div
          v-for="(v, k) in stats.executableByDomain"
          :key="k"
          class="metric"
        >
          <span class="metric-key">{{ termCn(String(k)) }}</span>
          <span class="metric-val mono">{{ v }}</span>
          <span class="metric-sub">{{ k }} domain</span>
        </div>
      </div>

      <div class="sec-sub" style="margin-top: var(--s-6)">
        <h3>知识工程漏斗 (Knowledge Funnel)</h3>
        <span class="sec-sub-note">古籍出处 → 候选规则 → 引擎可执行规则的转化链路</span>
      </div>
      <div v-if="funnel?.funnel" class="funnel">
        <div class="funnel-stage">
          <div class="funnel-key">Sources</div>
          <div class="funnel-val mono">{{ funnel.funnel.sources }}</div>
          <div class="funnel-sub">古籍来源</div>
        </div>
        <div class="funnel-stage">
          <div class="funnel-key">Candidates</div>
          <div class="funnel-val mono">{{ funnel.funnel.candidates }}</div>
          <div class="funnel-sub">候选规则</div>
        </div>
        <div class="funnel-stage">
          <div class="funnel-key">Executable</div>
          <div class="funnel-val mono">{{ funnel.funnel.executable }}</div>
          <div class="funnel-sub">引擎可执行规则</div>
        </div>
        <div class="funnel-stage">
          <div class="funnel-key">Unused Candidates</div>
          <div class="funnel-val mono">{{ funnel.candidatesUnused }}</div>
          <div class="funnel-sub">尚未进入引擎</div>
        </div>
        <div class="funnel-stage">
          <div class="funnel-key">Never Triggered</div>
          <div class="funnel-val mono">{{ funnel.neverTriggered }}</div>
          <div class="funnel-sub">全命例未触发数</div>
        </div>
        <div class="funnel-stage">
          <div class="funnel-key">Conflict Density</div>
          <div class="funnel-val mono">{{ funnel.conflictDensity }}</div>
          <div class="funnel-sub">冲突密度指数</div>
        </div>
      </div>
    </section>

    <!-- 04 审计门与覆盖率 -->
    <section v-show="activeTab === 'gates'" id="panel-gates" role="tabpanel" aria-labelledby="tab-gates">
      <div class="sec-sub" style="margin-top: 0">
        <h3>质量审计门 (Quality Assurance Gates)</h3>
        <span class="sec-sub-note">规则完整性、古籍出处与事实推演自动化质量门</span>
      </div>

      <div v-if="coverage?.gates" class="surface">
        <div class="row between" style="margin-bottom: var(--s-3)">
          <h4 style="font-size: var(--t-md)">自动化质量门状态</h4>
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
        <h4 style="margin-bottom: var(--s-3); font-size: var(--t-md)">Rule → Case 命例覆盖</h4>
        <div class="stack stack-2">
          <p class="note">
            {{ Object.entries(coverage.coverage.ruleCaseCoverage ?? {})
                .map(([k, v]) => `${k}:${v}`).join("、") || "无" }}
          </p>
          <p class="note">
            重放未触发（never-in-replay）：
            {{ (coverage.coverage.eventRulesNeverInReplay ?? []).join("、") || "无" }}
          </p>
        </div>
      </div>
    </section>

    <!-- 05 AI 评测对比 -->
    <section v-show="activeTab === 'eval'" id="panel-eval" role="tabpanel" aria-labelledby="tab-eval">
      <div class="sec-sub" style="margin-top: 0">
        <h3>AI 解释确定性评测对比</h3>
        <span class="sec-sub-note">
          确定性指标回归对比（无 LLM-as-judge）· 呈现近期评测历史
        </span>
        <span class="sec-sub-aside">
          <StatusBadge v-if="evalCompare?.comparisons" :label="`共 ${evalCompare.comparisons.length} 次运行`" variant="mute" />
        </span>
      </div>

      <div v-if="evalCompare?.comparisons?.length" class="stack stack-2">
        <details
          v-for="(c, i) in evalCompare.comparisons.slice(-12).reverse()"
          :key="i"
          class="surface"
        >
          <summary>
            <span class="mono" style="font-weight: 700">{{ c.metrics.provider }}/{{ c.metrics.model }}</span>
            <span class="note-sm" style="margin: 0 8px">（prompt {{ c.metrics.promptVersion }}）</span>
            — pass {{ c.metrics.verdictPass }}/{{ c.metrics.verdictTotal }}
            <StatusBadge
              v-if="Object.keys(c.regressionAgainstPrevious ?? {}).length"
              label="回归告警"
              variant="neg"
            />
          </summary>
          <div class="metrics mt-3">
            <div class="metric">
              <span class="metric-key">事实接地</span>
              <span class="metric-val mono">{{ c.metrics.groundingIssueTotal }}</span>
            </div>
            <div class="metric">
              <span class="metric-key">违禁词</span>
              <span class="metric-val mono">{{ c.metrics.bannedTotal }}</span>
            </div>
            <div class="metric">
              <span class="metric-key">分歧缺失</span>
              <span class="metric-val mono">{{ c.metrics.disagreementMissingCount }}</span>
            </div>
            <div class="metric">
              <span class="metric-key">引用缺失</span>
              <span class="metric-val mono">{{ c.metrics.claimRefsUsedAvg }}</span>
            </div>
            <div v-if="c.telemetry" class="metric">
              <span class="metric-key">平均延迟</span>
              <span class="metric-val mono">{{ c.telemetry.latencyMsAvg }} ms</span>
            </div>
            <div v-if="c.telemetry" class="metric">
              <span class="metric-key">消耗 tokens</span>
              <span class="metric-val mono">{{ c.telemetry.tokensTotal }}</span>
            </div>
          </div>
          <div v-if="Object.keys(c.regressionAgainstPrevious ?? {}).length" class="stack stack-1 mt-3">
            <div v-for="(v, k) in c.regressionAgainstPrevious" :key="k" class="ev evidence-item is-minus">
              <span class="ev-mark">−</span><span class="ev-body">{{ k }}: {{ v }}</span>
            </div>
          </div>
        </details>
      </div>
      <p v-else-if="!loading" class="empty">{{ resourceErrors.evaluationCompare ? "评测数据加载失败，请使用上方“重新加载”。" : "暂无评测比对数据。" }}</p>
    </section>

    <!-- 06 复核队列与发布 -->
    <section v-show="activeTab === 'review'" id="panel-review" role="tabpanel" aria-labelledby="tab-review">
      <div v-if="review.length">
        <div class="sec-sub" style="margin-top: 0">
          <h3>人工复核队列</h3>
          <span class="sec-sub-note">
            HUMAN_VERIFIED 仅由真实人工产出，系统不伪造
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
      </div>

      <!-- 发布元信息 -->
      <div v-if="release?.metadata" style="margin-top: var(--s-6)">
        <div class="sec-sub" style="margin-top: 0">
          <h3>发布与环境元信息</h3>
        </div>
        <div class="metrics">
          <div class="metric">
            <span class="metric-key">提交 Commit</span>
            <span class="metric-val mono" style="font-size: var(--t-md)">
              {{ (release.metadata.release?.gitCommit || "").slice(0, 12) || "—" }}
            </span>
          </div>
          <div class="metric">
            <span class="metric-key">引擎版本</span>
            <span class="metric-val mono" style="font-size: var(--t-md)">
              {{ release.metadata.engineVersion }}
            </span>
          </div>
          <div class="metric">
            <span class="metric-key">回归测试数</span>
            <span class="metric-val mono">{{ release.metadata.counts?.tests }}</span>
          </div>
          <div class="metric">
            <span class="metric-key">质量评估结论</span>
            <span class="metric-val" style="font-size: var(--t-md); color: var(--st-likely)">
              {{ release.qualitySummary?.allPass ? "ALL PASS" : "FAIL" }}
            </span>
          </div>
        </div>
        <details class="mt-3">
          <summary>版本依赖树</summary>
          <div class="stack stack-1 mt-2">
            <p v-for="(v, k) in release.metadata.versions" :key="k" class="note mono">
              {{ k }}: {{ v }}
            </p>
          </div>
        </details>
      </div>
    </section>

    <p class="note" style="border-top: 1px solid var(--line-200); padding-top: var(--s-3)">
      本页为知识工作台只读导航：来源、规则、冲突、命例四者关系由后端声明，前端不合并口径、不推测缺失关系。
    </p>
  </div>
</template>
