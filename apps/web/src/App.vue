<script setup lang="ts">
import { VIEW_PLAIN } from "./presentation/layman";
/**
 * Tianze · 应用根组件。
 *
 * 职责：研究工作区路由 + 会话级编排。刻意保持为薄壳——
 * 展示层拆分为 components/（构件）与 views/（工作区），
 * 状态与请求集中在 composables/useTianze.ts，不做任何命理推导。
 */
import { computed, onMounted, ref, watch } from "vue";
import AppShell, { type NavGroup } from "./components/AppShell.vue";
import AIProviderDialog from "./components/AIProviderDialog.vue";
import HomeView from "./views/HomeView.vue";
import BirthIntake from "./views/BirthIntake.vue";
import ChartWorkspace from "./views/ChartWorkspace.vue";
import TemporalView from "./views/TemporalView.vue";
import KnowledgeView from "./views/KnowledgeView.vue";
import AiView from "./views/AiView.vue";
import ReportView from "./views/ReportView.vue";
import SectionHeader from "./components/SectionHeader.vue";
import { tianzeStore, workspace, aiDialogOpen, graphFocus, graphSearchSeed, type Workspace } from "./composables/useTianze";
import { aiConfigStore } from "./composables/useAiConfig";
import { POSITION_CN } from "./presentation/vocab";

const t = tianzeStore();
const ai = aiConfigStore();

const sidebarOpen = ref(false);
/** 工作区顶部"排盘参数"展开态（默认收起，参数以单行读数呈现） */
const paramOpen = ref(false);

onMounted(async () => {
  await Promise.all([t.loadMeta(), ai.refresh()]);
});

/* ------------------------------------------------------------ 导航定义 */

const CHART_PAGES: Workspace[] = [
  "overview", "strength", "pattern", "relations", "structure", "tiaohou", "advanced",
];

const navGroups = computed<NavGroup[]>(() => {
  const groups: NavGroup[] = [];
  if (!t.result.value) return groups;

  const plain = (id: string) => VIEW_PLAIN[id] ?? "";
  groups.push({
    title: "命盘 · 原局",
    items: [
      { id: "overview", label: "命盘总览", meta: "01", hint: plain("overview") },
      { id: "strength", label: "旺衰", meta: "02", hint: plain("strength") },
      { id: "pattern", label: "格局", meta: "03", hint: plain("pattern") },
      { id: "relations", label: "关系", meta: "04", hint: plain("relations") },
      { id: "structure", label: "结构", meta: "05", hint: plain("structure") },
      { id: "tiaohou", label: "调候", meta: "06", hint: plain("tiaohou") },
      { id: "advanced", label: "高级结构", meta: "07", hint: "更深的专业观察（合化/虚神），可跳过" },
    ],
  });

  groups.push({
    title: "时序 · 岁运",
    items: [
      { id: "temporal", label: "岁运时序", meta: t.temporal.value ? "✓" : "", hint: plain("temporal") },
    ],
  });

  groups.push({
    title: "知识 · 溯源",
    items: [
      { id: "knowledge", label: "知识图谱", hint: plain("knowledge") },
      { id: "ai", label: "AI 解读", dot: ai.configured.value ? "on" : "warn", hint: plain("ai") },
      { id: "report", label: "研究报告", hint: "把以上内容汇成一份可打印的完整报告" },
    ],
  });

  return groups;
});

const activeNav = computed(() => workspace.value);

/* 侧栏命盘指纹（仅呈现引擎字段） */
const sideChart = computed(() => {
  const r = t.result.value;
  if (!r) return null;
  return {
    pillars: t.pillarOrder.value.map(k => ({
      pos: POSITION_CN[k],
      stem: r.pillars[k]?.stem ?? "",
      branch: r.pillars[k]?.branch ?? "",
      isDm: k === "day",
    })),
    dayMaster: `${r.dayMaster?.stem ?? ""} 日主`,
    meta: [
      r.monthCommand ? `${r.monthCommand.monthBranch} 月令` : "",
      `关系 ${r.relations?.length ?? 0}`,
      r.pattern?.candidates?.length ? `格局候选 ${r.pattern.candidates.length}` : "",
    ].filter(Boolean) as string[],
  };
});

const crumbs = computed(() => {
  if (workspace.value === "home") return [];
  const map: Record<string, string> = {
    overview: "命盘总览", strength: "旺衰", pattern: "格局", relations: "关系",
    structure: "结构", tiaohou: "调候", advanced: "高级结构",
    temporal: "岁运时序", knowledge: "知识图谱", ai: "AI 解读", report: "研究报告",
  };
  return ["命例", map[workspace.value] ?? workspace.value];
});

/* 顶栏 AI 状态点 */
const aiDot = computed<"on" | "warn" | null>(() => (ai.configured.value ? "on" : "warn"));

/* -------------------------------------------------- 工作区状态切换行为 */

/** 未排盘时：允许停留在首页；其它工作区自动回首页 */
watch(() => t.result.value, (r) => {
  if (!r && workspace.value !== "home" && workspace.value !== "intake") {
    workspace.value = "home";
  }
});

/**
 * 切换工作区时回到页首。
 * 首页的"开始排盘"按钮在页面下方，若保留滚动位置，进入工作台会落在半截处——必须归位。
 */
watch(workspace, () => {
  window.scrollTo({ top: 0, behavior: "instant" as ScrollBehavior });
});

async function onNavigate(id: string) {
  workspace.value = id as Workspace;
}

function goHome() {
  workspace.value = "home";
}

async function onSubmit() {
  await t.submit();
  if (t.result.value) workspace.value = "overview";
}

function openGraph(id: string) {
  graphFocus.value = id;
  graphSearchSeed.value = id;
  workspace.value = "knowledge";
}

/* -------------------------------------------------------- AI 配置入口 */

function openAi() { aiDialogOpen.value = true; }
function testAi() { openAi(); void ai.test(); }

/* ---------------------------------------------------------- 岁运控制 */

const temporalSelection = computed(() => t.state.temporalSelection);

function printReport() { window.print(); }
</script>

<template>
  <!-- M54 · 全局纸感肌理层（噪点 + 暗角；纯装饰，不参与交互） -->
  <div class="paper-grain" aria-hidden="true" />
  <div class="paper-vignette" aria-hidden="true" />

  <!-- 首页：独立版式（产品官网 + 研究入口） -->
  <HomeView
    v-if="workspace === 'home'"
    :birth="t.state.birth"
    :loading="t.state.loading"
    :error="t.state.error"
    :engine-version="t.state.meta?.engineVersion"
    @submit="onSubmit"
    @configure-ai="openAi"
  />

  <!-- 研究工作台：左栏研究路径 + 右栏分析内容 -->
  <AppShell
    v-else
    v-model:sidebar-open="sidebarOpen"
    :groups="navGroups"
    :active="activeNav"
    :chart="sideChart"
    :crumbs="crumbs"
    :engine-version="t.state.meta?.engineVersion"
    :analysis-schema="t.state.meta?.analysisSchemaVersion"
    :ai-dot="aiDot"
    @navigate="onNavigate"
    @home="goHome"
    @configure-ai="openAi"
  >
    <template #actions>
      <button class="btn-ghost" type="button" @click="onSubmit" :disabled="t.state.loading">
        {{ t.state.loading ? "排盘中…" : "重新排盘" }}
      </button>
    </template>

    <!-- 排盘参数：一行"仪表读数"，需要改时再展开。
         研究者常要反复改流派 / 时区核对，但参数区不该占据内容重心。 -->
    <div class="param-strip no-print">
      <span class="param-strip-key">排盘参数</span>
      <span class="param-strip-val">{{ t.state.birth.date }}</span>
      <span v-if="t.state.birth.timeKnown" class="param-strip-val">{{ t.state.birth.time }}</span>
      <span v-else class="param-strip-val">时辰未知</span>
      <span class="param-strip-val">{{ t.state.birth.gender === "male" ? "男" : "女" }}</span>
      <span class="param-strip-val">
        UTC{{ t.state.birth.timezoneOffset >= 0 ? "+" : "" }}{{ t.state.birth.timezoneOffset }}
      </span>
      <span class="param-strip-val">晚子时流派 {{ t.state.birth.sect }}</span>
      <span v-if="t.state.birth.longitude != null" class="param-strip-val">
        经度 {{ t.state.birth.longitude }}
      </span>
      <span class="grow" />
      <button class="btn-link" type="button" @click="paramOpen = !paramOpen">
        {{ paramOpen ? "收起" : "调整参数" }}
      </button>
    </div>

    <div v-if="paramOpen" class="no-print" style="margin-bottom: var(--s-5)">
      <BirthIntake
        :birth="t.state.birth"
        :loading="t.state.loading"
        :error="t.state.error"
        compact
        @submit="onSubmit"
      />
    </div>

    <!-- 岁运时序 -->
    <template v-if="workspace === 'temporal'">
      <SectionHeader
        index="08"
        title="时序工作台"
        lede="大运 → 流年 → 流月 → 流日逐层展开；岁运不替换原局月令，每层变化均附触发规则与证据。"
        note="全部内容为结构变化描述，不构成吉凶或事件预测。"
        :level="2"
      />
      <TemporalView
        :temporal="t.temporal.value"
        :luck-options="t.luckOptions.value"
        :year-options="t.yearOptions.value"
        :month-options="t.monthOptions"
        :time-stops="t.timeStops.value"
        :matched-rules="t.matchedRules.value"
        :delta-groups="t.deltaGroups.value"
        :selection="temporalSelection"
        :loading="t.state.temporalLoading"
        :error="t.state.temporalError"
        @run="t.runTemporal"
        @luck="t.setLuck"
        @year="t.setYear"
        @month="t.setMonth"
        @day="t.setDay"
        @toggle-replay="t.state.temporalSelection.withReplay = $event"
        @open-rule="openGraph"
      />
    </template>

    <!-- 知识图谱 -->
    <template v-else-if="workspace === 'knowledge'">
      <SectionHeader
        index="09"
        title="知识图谱"
        lede="来源 ↔ 规则 ↔ 冲突 ↔ 命例的只读导航。规则节点按领域分层铺设，点击即见身份、溯源与重放命例。"
        note="本页不复制推理逻辑；冲突密度、覆盖率与审计门指标原样呈现。"
        :level="2"
      />
      <KnowledgeView
        :focus-id="graphFocus"
        :search-seed="graphSearchSeed"
      />
    </template>

    <!-- AI 解读 -->
    <template v-else-if="workspace === 'ai'">
      <SectionHeader
        index="10"
        title="AI 解读"
        lede="基于当前证据链生成辅助解释。AI 只解释引擎已算出的结构与候选，不自行推算。"
        note="输出需通过事实一致性校验；未通过的内容不予展示。"
        :level="2"
      />
      <AiView
        :ai-status="ai.status.value"
        :ai-source-label="ai.sourceLabel.value"
        :ai-configured="ai.configured.value"
        :ai-state="t.state.aiState"
        :ai-result="t.state.aiResult"
        :ai-error="t.state.aiError"
        :has-result="Boolean(t.result.value)"
        :temporal-loaded="Boolean(t.temporal.value)"
        @configure="openAi"
        @test="testAi"
        @generate="t.generateAi"
      />
    </template>

    <!-- 研究报告 -->
    <template v-else-if="workspace === 'report'">
      <SectionHeader
        index="11"
        title="研究报告"
        lede="引擎结果的呈现层汇编，供通读与打印为 PDF。章节顺序与研究路径一致。"
        note="权威 Markdown / HTML 导出由 CLI 完成：tianze export。两者内容同源，本页不新增结论。"
        :level="2"
      >
        <template #aside>
          <button class="btn-sm no-print" type="button" @click="printReport">
            打印 / 导出 PDF
          </button>
        </template>
      </SectionHeader>
      <ReportView
        v-if="t.result.value"
        :result="t.result.value"
        :order="t.pillarOrder.value"
        :birth="t.state.birth"
        :temporal="t.temporal.value"
        :ai-result="t.state.aiResult"
        :ai-configured="ai.configured.value"
        :engine-version="t.state.meta?.engineVersion"
      />
    </template>

    <!-- 命盘工作区 -->
    <template v-else>
      <ChartWorkspace
        v-if="t.result.value"
        :page="workspace"
        :result="t.result.value"
        :order="t.pillarOrder.value"
        :relation-chains="t.relationChains.value"
        :combination-states="t.combinationStates.value"
        @open-graph="openGraph"
      />
    </template>
  </AppShell>

  <!-- AI 服务设置（全局，唯一实例） -->
  <AIProviderDialog :open="aiDialogOpen" @close="aiDialogOpen = false" />
</template>
