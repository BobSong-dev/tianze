<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { analyzeBirthInfo, getMeta, type AnalyzePayload } from "./api/tianze";
import type { AnalyzeResponse } from "./types/tianze";

const date = ref("2003-08-18");
const time = ref("14:30");
const timeKnown = ref(true);
const gender = ref("male");
const tzOffset = ref(8.0);
const sect = ref(2);
const longitude = ref<number | null>(null);
const showAdvanced = ref(false);
const loading = ref(false);
const error = ref("");
const result = ref<AnalyzeResponse | null>(null);
const meta = ref<{ analysisSchemaVersion: string; engineVersion: string } | null>(null);

const activeTab = ref("overview");
const tabs = [
  { id: "overview", label: "总览" },
  { id: "relations", label: "关系" },
  { id: "structure", label: "结构" },
  { id: "strength", label: "旺衰" },
  { id: "pattern", label: "格局" },
  { id: "tiaohou", label: "调候" },
  { id: "advanced", label: "高级" },
  { id: "temporal", label: "时序" },
  { id: "knowledge", label: "知识库" },
  { id: "ai", label: "AI 解读" },
];
const expandedEvidence = ref<string | null>(null);
const aiState = ref<"NOT_CONFIGURED" | "READY" | "LOADING" | "SUCCESS" | "GROUNDING_FAILED" | "PROVIDER_ERROR" | "SCHEMA_ERROR">("READY");
const aiResult = ref<any>(null);
const aiError = ref("");

async function generateAI() {
  if (!result.value) return;
  aiState.value = "LOADING";
  aiError.value = "";
  try {
    // M13：若时序工作台已加载岁运上下文，合并进解释输入（AI 只消费引擎结果）
    const payloadAnalysis = temporalData.value
      ? { ...result.value, temporal: temporalData.value }
      : result.value;
    const r = await fetch("/api/v1/interpret", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ analysis: payloadAnalysis }),
    });
    if (r.status === 503) {
      aiState.value = "NOT_CONFIGURED";
      return;
    }
    const body = await r.json();
    if (!r.ok) {
      aiState.value = "PROVIDER_ERROR";
      aiError.value = body?.error?.message || `HTTP ${r.status}`;
      return;
    }
    const interp = body.interpretation;
    if (!interp.groundingPassed) {
      aiState.value = "GROUNDING_FAILED";
      aiResult.value = interp;
      return;
    }
    aiResult.value = interp;
    aiState.value = "SUCCESS";
  } catch (e) {
    aiState.value = "PROVIDER_ERROR";
    aiError.value = e instanceof Error ? e.message : String(e);
  }
}

async function submit() {
  loading.value = true;
  error.value = "";
  result.value = null;
  temporalData.value = null;
  selLuck.value = null;
  selYear.value = null;
  selMonth.value = null;
  selDay.value = "";
  try {
    const payload: AnalyzePayload = {
      birthInfo: {
        date: date.value,
        time: timeKnown.value ? time.value : undefined,
        gender: gender.value,
        timezoneOffset: tzOffset.value,
        sect: sect.value,
        longitude: longitude.value ?? undefined,
      },
      options: {
        includeStrength: true, includePattern: true, includeTiaohou: true,
        includeSpecialPatterns: true, includeRelations: true, includeElementCounts: true,
      },
    };
    result.value = await analyzeBirthInfo(payload);
    activeTab.value = "overview";
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}

const pillarKeys = computed(() => {
  if (!result.value) return [];
  const p = result.value.pillars;
  return (["year", "month", "day", "hour"] as const).filter(k => p[k as keyof typeof p]);
});

function toggleEvidence(id: string) {
  expandedEvidence.value = expandedEvidence.value === id ? null : id;
}

// ---------- M16 知识工作台 ----------
const kbRules = ref<any[]>([]);
const kbStats = ref<any>(null);
const kbReview = ref<any[]>([]);
const kbSearch = ref("");
const kbDomain = ref("all");
const kbLoaded = ref(false);

async function loadKnowledge() {
  if (kbLoaded.value) return;
  const [r, st, rq, fn, cov, rel, cmp] = await Promise.all([
    fetch("/api/v1/knowledge/rules").then(x => x.json()),
    fetch("/api/v1/knowledge/stats").then(x => x.json()),
    fetch("/api/v1/knowledge/review-queue").then(x => x.json()),
    fetch("/api/v1/knowledge/funnel").then(x => x.json()).catch(() => null),
    fetch("/api/v1/knowledge/coverage").then(x => x.json()).catch(() => null),
    fetch("/api/v1/knowledge/release").then(x => x.json()).catch(() => null),
    fetch("/api/v1/knowledge/evaluation-compare").then(x => x.json()).catch(() => null),
  ]);
  kbRules.value = r.rules ?? [];
  kbStats.value = st;
  kbReview.value = (rq.items ?? []).slice(0, 60);
  kbFunnel.value = fn;
  kbCoverage.value = cov;
  kbRelease.value = rel;
  kbEvalCompare.value = cmp;
  kbLoaded.value = true;
}

const kbEvalCompare = ref<any>(null);
const kbGraph = ref<any>(null);
const graphFilter = ref("");
const graphTypeFilter = ref("all");
const selectedNodeId = ref<string | null>(null);

function loadGraphAndRender() {
  void loadGraph();  // graphSvg computed 随 kbGraph 自动重算
}

// 确定性环形布局：规则按 domain 分环，谓词内环——纯展示布局，不含推理
function graphLayout(): { nodes: any[]; width: number; height: number } {
  const g = kbGraph.value;
  if (!g) return { nodes: [], width: 0, height: 0 };
  const nodes: any[] = [];
  const rings: Record<string, any[]> = { event: [], temporal: [], tiaohou: [], predicate: [] };
  for (const n of g.nodes ?? []) {
    const ring = n.type === "predicate" ? "predicate" : (n.domain ?? n.theme ? (n.domain || "event") : "predicate");
    (rings[n.type === "predicate" ? "predicate" : (n.domain ?? "event")] ??= []).push(n);
  }
  const cx = 420, cy = 320;
  const radii: Record<string, number> = { predicate: 90, event: 190, temporal: 280, tiaohou: 360 };
  for (const [ring, ns] of Object.entries(rings)) {
    const radius = radii[ring] ?? 280;
    ns.forEach((n, i) => {
      const angle = (2 * Math.PI * i) / Math.max(1, ns.length) - Math.PI / 2;
      nodes.push({ ...n, ring, x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) });
    });
  }
  return { nodes, width: 840, height: 640 };
}

const graphSvg = computed(() => {
  const g = kbGraph.value;
  if (!g) return null;
  const layout = graphLayout();
  const pos = new Map(layout.nodes.map(n => [n.id, n]));
  const sel = selectedNodeId.value;
  const neighbors = new Set<string>();
  if (sel) {
    for (const e of g.edges ?? []) {
      const ids = e.between ?? [e.from, e.to].filter(Boolean);
      if (ids.includes(sel)) ids.forEach((x: string) => x !== sel && neighbors.add(x));
    }
  }
  const edges = ((g.edges ?? []) as any[]).filter((e: any) => {
    if (graphTypeFilter.value !== "all" && e.type !== graphTypeFilter.value) return false;
    if (!sel) return true;
    const ids = e.between ?? [e.from, e.to].filter(Boolean);
    return ids.includes(sel);
  }).map(e => {
    const ids = e.between ?? [e.from, e.to].filter(Boolean);
    if (ids.length === 2 && pos.has(ids[0]) && pos.has(ids[1])) {
      const a = pos.get(ids[0]); const b = pos.get(ids[1]);
      return { ...e, x1: a.x, y1: a.y, x2: b.x, y2: b.y,
               dim: sel ? !(ids.includes(sel)) : false };
    }
    return null;
  }).filter(Boolean);
  const showNodes = layout.nodes.filter(n => {
    if (graphTypeFilter.value === "all") return true;
    if (n.type === "predicate") return graphTypeFilter.value === "rescues";
    return ((g.edges ?? []) as any[]).some((e: any) => e.type === graphTypeFilter.value &&
      (e.between ?? []).includes(n.id));
  });
  return { ...layout, edges, nodes: showNodes.map(n => ({
    ...n, selected: n.id === sel,
    highlighted: sel ? neighbors.has(n.id) : false,
  })) };
});

function nodeColor(n: any): string {
  if (n.type === "predicate") return "#8e44ad";
  return ({ event: "#e67e22", temporal: "#2980b9", tiaohou: "#27ae60" } as Record<string, string>)[n.domain] ?? "#7f8c8d";
}

function nodeLabel(n: any): string {
  return n.label ? String(n.label).slice(0, 10) : String(n.id).slice(0, 12);
}

function selectNode(id: string | null) {
  if (graphMoved.value) return;  // 拖拽平移结束不当作点击
  selectedNodeId.value = id === selectedNodeId.value ? null : id;
}

const selectedNodeDetail = computed(() => {
  if (!selectedNodeId.value || !kbRules.value.length) return null;
  return kbRules.value.find(r => r.id === selectedNodeId.value) ?? null;
});

// M23 · Graph pan/zoom：viewBox 平移缩放（纯展示交互，不影响图数据）
const graphView = ref({ x: 0, y: 0, w: 840, h: 640 });
const graphViewBox = computed(() =>
  `${graphView.value.x} ${graphView.value.y} ${graphView.value.w} ${graphView.value.h}`);
const graphMoved = ref(false);
let graphDrag: { px: number; py: number } | null = null;

function onGraphWheel(e: WheelEvent) {
  const v = graphView.value;
  const scale = e.deltaY > 0 ? 1.12 : 1 / 1.12;
  const nw = Math.min(2400, Math.max(180, v.w * scale));
  const k = nw / v.w;
  const svg = e.currentTarget as SVGElement;
  const rect = svg.getBoundingClientRect();
  const mx = v.x + ((e.clientX - rect.left) / rect.width) * v.w;
  const my = v.y + ((e.clientY - rect.top) / rect.height) * v.h;
  graphView.value = { x: mx - (mx - v.x) * k, y: my - (my - v.y) * k, w: nw, h: v.h * k };
}

function onGraphDown(e: PointerEvent) {
  graphDrag = { px: e.clientX, py: e.clientY };
  graphMoved.value = false;
  (e.currentTarget as Element).setPointerCapture?.(e.pointerId);
}

function onGraphMove(e: PointerEvent) {
  if (!graphDrag) return;
  const svg = e.currentTarget as SVGElement;
  const rect = svg.getBoundingClientRect();
  const dx = ((e.clientX - graphDrag.px) / rect.width) * graphView.value.w;
  const dy = ((e.clientY - graphDrag.py) / rect.height) * graphView.value.h;
  if (Math.abs(e.clientX - graphDrag.px) + Math.abs(e.clientY - graphDrag.py) > 3)
    graphMoved.value = true;
  graphView.value = { ...graphView.value, x: graphView.value.x - dx, y: graphView.value.y - dy };
  graphDrag = { px: e.clientX, py: e.clientY };
}

function onGraphUp() { graphDrag = null; }

function resetGraphView() { graphView.value = { x: 0, y: 0, w: 840, h: 640 }; graphMoved.value = false; }

// M23 · 规则 → ExplanationChain 跳转：当前分析的哪个主题链引用了选中规则
const chainJumpThemes = computed<string[]>(() => {
  const id = selectedNodeId.value;
  const ex = (temporalData.value?.eventThemes?.explanations ?? {}) as Record<string, any>;
  if (!id) return [];
  return Object.keys(ex).filter(theme => {
    const r = ex[theme]?.reasoning ?? {};
    return [...(r.supportingChain ?? []), ...(r.opposingChain ?? [])]
      .some((h: any) => h?.ruleId === id);
  });
});

function jumpToChain() { activeTab.value = "temporal"; }

// M26：关系引文 → 知识图谱跳转（切 tab + 搜索 + 聚焦节点）
function jumpToGraph(candidateId: string) {
  activeTab.value = "knowledge";
  kbSearch.value = candidateId;
  void loadGraph();
  selectedNodeId.value = candidateId;
}

// M23 · 遥测趋势 sparkline：确定性指标（pass 率/grounding）+ 遥测 latency 的历史折线
const evalFilterProvider = ref("");
const evalOnlyRegression = ref(false);
const evalComparisonsFiltered = computed(() => {
  const cs: any[] = kbEvalCompare.value?.comparisons ?? [];
  const q = evalFilterProvider.value.trim();
  return cs.filter(c =>
    (!q || `${c.metrics?.provider ?? ""}/${c.metrics?.model ?? ""}`.includes(q)) &&
    (!evalOnlyRegression.value || Object.keys(c.regressionAgainstPrevious ?? {}).length > 0));
});

const evalTrend = computed(() => {
  const cs: any[] = evalComparisonsFiltered.value;
  const tail = cs.slice(-40);
  if (tail.length < 2) return null;
  const n = tail.length;
  const px = (i: number) => 34 + (i * 556) / Math.max(1, n - 1);
  const line = (vals: number[], lo: number, hi: number) => {
    const span = hi - lo || 1;
    return vals.map((v, i) => `${px(i).toFixed(1)},${(86 - ((v - lo) / span) * 72).toFixed(1)}`).join(" ");
  };
  const rates = tail.map(c => (c.metrics?.verdictTotal ? c.metrics.verdictPass / c.metrics.verdictTotal : 0));
  const grounds = tail.map(c => c.metrics?.groundingIssueTotal ?? 0);
  const latencies = tail.map(c => c.telemetry?.latencyMsAvg).filter((x: any) => typeof x === "number") as number[];
  return {
    n,
    rateLine: line(rates, Math.min(...rates), Math.max(...rates, 1)),
    groundLine: line(grounds, 0, Math.max(...grounds, 1)),
    latencyLine: latencies.length >= 2 ? line(latencies, Math.min(...latencies), Math.max(...latencies)) : null,
    latencyMax: latencies.length ? Math.max(...latencies) : null,
    groundMax: Math.max(...grounds),
  };
});

async function loadGraph() {
  if (kbGraph.value) return;
  kbGraph.value = await fetch("/api/v1/knowledge/graph").then(x => x.json()).catch(() => null);
}

const graphEdges = computed(() => {
  const g = kbGraph.value;
  if (!g) return [];
  const f = graphFilter.value.trim();
  return ((g.edges ?? []) as any[]).filter((e: any) =>
    !f || e.type.includes(f) || (e.between ?? []).some((x: string) => x.includes(f))
      || (e.from ?? "").includes(f) || (e.to ?? "").includes(f));
});

const kbFunnel = ref<any>(null);
const kbCoverage = ref<any>(null);
const kbRelease = ref<any>(null);

const kbFiltered = computed(() => {
  const q = kbSearch.value.trim();
  return kbRules.value.filter(r =>
    (kbDomain.value === "all" || r.domain === kbDomain.value) &&
    (!q || r.id.includes(q) || (r.label || "").includes(q) ||
     (r.theme || "").includes(q) || (r.category || "").includes(q)));
});

watch(activeTab, (t) => { if (t === "knowledge") loadKnowledge(); });

// ---------- M13 时序工作台 ----------

const selLuck = ref<number | null>(null);
const selYear = ref<number | null>(null);
const selMonth = ref<number | null>(null);
const selDay = ref<string>("");
const temporalLoading = ref(false);
const temporalError = ref("");
const temporalData = ref<any>(null);

const luckOptions = computed(() => {
  const luck = (result.value as any)?.luck;
  if (!luck?.daYun?.length) return [];
  return luck.daYun.filter((d: any) => d.ganZhi);
});

const yearOptions = computed(() => {
  const luck = luckOptions.value.find((d: any) => d.index === selLuck.value);
  if (!luck) return [];
  const years: number[] = [];
  for (let y = luck.startYear; y <= luck.endYear; y++) years.push(y);
  return years;
});

const monthOptions = computed(() => [
  { n: 1, label: "寅月（立春起）" }, { n: 2, label: "卯月（惊蛰起）" },
  { n: 3, label: "辰月（清明起）" }, { n: 4, label: "巳月（立夏起）" },
  { n: 5, label: "午月（芒种起）" }, { n: 6, label: "未月（小暑起）" },
  { n: 7, label: "申月（立秋起）" }, { n: 8, label: "酉月（白露起）" },
  { n: 9, label: "戌月（寒露起）" }, { n: 10, label: "亥月（立冬起）" },
  { n: 11, label: "子月（大雪起）" }, { n: 12, label: "丑月（小寒起）" },
]);

const matchedRules = computed(() =>
  (temporalData.value?.ruleTriggers ?? []).filter((t: any) => t.matched));

const deltaByAnalysis = computed(() => {
  const items: any[] = temporalData.value?.delta?.items ?? [];
  const groups: Record<string, any[]> = {};
  for (const it of items) {
    (groups[it.analysis] ??= []).push(it);
  }
  return groups;
});

function relationExplanation(label: string): any {
  // M25：按关系 label 查解释链（解释链与关系同 label 生成）
  const exs: any[] = result.value?.relationExplanations ?? [];
  return exs.find((e: any) => e.label === label && e.status !== "BLOCKED") ?? null;
}

function explanationForBlocked(label: string): any {
  const exs: any[] = result.value?.relationExplanations ?? [];
  return exs.find((e: any) => e.label === label && e.status === "BLOCKED") ?? null;
}

function explanationFor(theme: string): any {
  return (temporalData.value?.eventThemes?.explanations ?? {})[theme] ?? null;
}

function statusBadgeClass(status: string): string {
  return { LIKELY: "rescue", DISPUTED: "conflict", BLOCKED: "damage",
           UNRESOLVED: "", CANDIDATE: "" }[status] ?? "";
}

const KIND_CN: Record<string, string> = {
  added: "新出现", removed: "消失", strengthened: "增强", weakened: "减弱",
  status_changed: "状态改变", blocked: "被阻断", unblocked: "解除/到位",
  disagreement_changed: "一致性变化",
};

function onLuckChange() {
  selYear.value = null;
  selMonth.value = null;
  selDay.value = "";
  temporalData.value = null;
}

function onYearChange() {
  selMonth.value = null;
  selDay.value = "";
  temporalData.value = null;
}

function onMonthChange() {
  selDay.value = "";
  temporalData.value = null;
}

async function loadTemporal() {
  if (!result.value) return;
  if (selLuck.value === null && selYear.value === null) {
    temporalError.value = "请先选择大运或年份";
    return;
  }
  temporalLoading.value = true;
  temporalError.value = "";
  try {
    const resp = await analyzeBirthInfo({
      birthInfo: {
        date: date.value,
        time: timeKnown.value ? time.value : undefined,
        gender: gender.value,
        timezoneOffset: tzOffset.value,
        sect: sect.value,
        longitude: longitude.value ?? undefined,
      },
      options: {
        includeStrength: true, includePattern: true, includeTiaohou: true,
        includeSpecialPatterns: true, includeRelations: true, includeElementCounts: true,
        includeTemporal: true,
        targetLuckIndex: selLuck.value,
        targetYear: selYear.value,
        targetMonth: selMonth.value,
        targetDay: selDay.value || undefined,
        includeTemporalDelta: true,
        includeEventThemes: true,
      },
    });
    temporalData.value = resp.temporal;
    if (!temporalData.value) {
      temporalError.value = "该命例无法进行岁运分析（缺少大运：性别或时辰未知）";
    }
  } catch (e) {
    temporalError.value = e instanceof Error ? e.message : String(e);
  } finally {
    temporalLoading.value = false;
  }
}
</script>

<template>
  <div class="tianze-app">
    <header class="header">
      <h1>Tianze 天泽</h1>
      <span class="subtitle">可解释八字结构分析引擎</span>
      <span v-if="meta" class="version">v{{ meta.engineVersion }}</span>
    </header>

    <!-- Birth Input -->
    <section class="panel input-panel">
      <h2>出生信息</h2>
      <div class="form-grid">
        <label>出生日期 <input v-model="date" type="date" required /></label>
        <template v-if="timeKnown">
          <label>出生时间 <input v-model="time" type="time" /></label>
        </template>
        <label class="checkbox">
          <input v-model="timeKnown" type="checkbox" /> 知道出生时间
        </label>
        <label>性别
          <select v-model="gender">
            <option value="male">男</option>
            <option value="female">女</option>
          </select>
        </label>
        <label>时区偏移 <input v-model.number="tzOffset" type="number" step="0.5" /></label>
        <label>晚子时流派
          <select v-model="sect">
            <option :value="2">流派 2（默认）</option>
            <option :value="1">流派 1</option>
          </select>
        </label>
        <template v-if="showAdvanced">
          <label>经度 <input v-model.number="longitude" type="number" step="0.1" /></label>
        </template>
        <button class="link" @click="showAdvanced = !showAdvanced">
          {{ showAdvanced ? "隐藏" : "高级选项" }}
        </button>
      </div>
      <button class="submit" :disabled="loading" @click="submit">
        {{ loading ? "正在分析命局结构…" : "开始分析" }}
      </button>
      <div v-if="error" class="error">{{ error }}</div>
    </section>

    <!-- Results -->
    <template v-if="result">
      <section class="panel chart-panel">
        <h2>四柱</h2>
        <div class="pillars">
          <div v-for="key in pillarKeys" :key="key" class="pillar-card">
            <div class="pillar-label">{{ ({ year: "年柱", month: "月柱", day: "日柱", hour: "时柱" } as Record<string, string>)[key as string] }}</div>
            <div class="pillar-ganzhi">
              <span class="stem">{{ (result.pillars as any)[key]?.stem }}</span>
              <span class="branch">{{ (result.pillars as any)[key]?.branch }}</span>
            </div>
            <div class="pillar-tengod">{{ (result.pillars as any)[key]?.tenGod ?? "日主" }}</div>
            <div class="pillar-details">
              <span>{{ (result.pillars as any)[key]?.naYin }}</span>
              <span v-if="(result.pillars as any)[key]?.changSheng">{{ (result.pillars as any)[key]?.changSheng }}</span>
            </div>
            <details><summary>藏干</summary>
              <div v-for="h in (result.pillars as any)[key]?.hiddenStems" :key="h.stem" class="hidden-stem">
                {{ h.stem }}（{{ h.role }}）→ {{ h.tenGod }}
              </div>
            </details>
          </div>
        </div>
      </section>

      <!-- Tabs -->
      <nav class="tabs">
        <button v-for="t in tabs" :key="t.id" :class="{ active: activeTab === t.id }" @click="activeTab = t.id">
          {{ t.label }}
        </button>
      </nav>

      <!-- Overview -->
      <section v-if="activeTab === 'overview'" class="panel">
        <h2>日主</h2>
        <p>{{ result.dayMaster.stem }}（{{ result.dayMaster.element }}·{{ result.dayMaster.yinYang }}）</p>
        <h2>五行分布</h2>
        <div v-if="result.elementCounts" class="elements">
          <div v-for="(v, k) in result.elementCounts.elements" :key="k" class="element-row">
            <span class="elem-label">{{ k }}</span>
            <div class="bar"><div class="fill" :style="{ width: (v.visible / 8 * 100) + '%' }"></div></div>
            <span>显 {{ v.visible }} / 藏 {{ v.hidden }}</span>
          </div>
        </div>
      </section>

      <!-- Relations -->
      <section v-if="activeTab === 'relations' && result.relations.length" class="panel">
        <h2>干支关系 <span class="note">点开任意关系查看成立条件、流派注记与古籍引文（M25 解释链）</span></h2>
        <div v-for="r in result.relations" :key="r.label + r.positions.join()" class="relation-item">
          <strong>{{ r.label }}</strong>
          <span class="pos">{{ r.positions.join(" · ") }}</span>
          <span v-if="r.adjacency" class="badge">{{ r.adjacency === "ADJACENT" ? "贴邻" : "隔柱" }}</span>
          <span v-if="r.monthInvolved" class="badge">月令</span>
          <span v-if="r.subType" class="badge">{{ r.subType }}</span>
          <span v-if="r.transformCandidate" class="badge">化 {{ r.transformCandidate }}（候选）</span>
          <span v-if="r.note" class="note">{{ r.note }}</span>
          <details v-if="relationExplanation(r.label)">
            <summary>解释链（{{ relationExplanation(r.label).status === 'ESTABLISHED' ? '结构事实' : '候选关系' }}）</summary>
            <div class="note">{{ relationExplanation(r.label).boundary }}</div>
            <div v-for="(c, ci) in relationExplanation(r.label).conditions" :key="ci" class="evidence-item"
                 :class="c.satisfied ? 'rescue' : 'damage'">
              {{ c.satisfied ? '✓' : '✗' }} {{ c.text }}
            </div>
            <div v-for="(sn, si) in relationExplanation(r.label).schoolNotes" :key="'s' + si" class="note">流派：{{ sn }}</div>
            <div v-for="(c2, ki) in relationExplanation(r.label).citations" :key="'c' + ki" class="evidence-item">
              <span class="badge">{{ c2.candidateId }}</span> {{ c2.book }}《{{ c2.title }}》——{{ c2.quote }}
              <span v-if="c2.ocrRisk" class="badge damage">OCR 风险</span>
              <button v-if="c2.sourceKind === 'CLASSICAL_EXPLICIT'" class="link"
                      @click="jumpToGraph(c2.candidateId)">在知识图谱查看</button>
            </div>
          </details>
        </div>
        <template v-if="result.blockedRelations && result.blockedRelations.length">
          <h3>未成立的关系候选 <span class="note">「为什么不成立」——仅解释，不参与推理</span></h3>
          <div v-for="r in result.blockedRelations" :key="'b' + r.label + r.positions.join()" class="relation-item">
            <strong>{{ r.label }}</strong>
            <span class="pos">{{ r.positions.join(" · ") }}</span>
            <span class="badge">{{ r.subType }}</span>
            <span class="note">{{ r.note }}</span>
            <details v-if="explanationForBlocked(r.label)">
              <summary>为什么未成立</summary>
              <div class="note">{{ explanationForBlocked(r.label).boundary }}</div>
              <div v-for="(c, ci) in explanationForBlocked(r.label).conditions" :key="ci" class="evidence-item"
                   :class="c.satisfied ? 'rescue' : 'damage'">{{ c.satisfied ? '✓' : '✗' }} {{ c.text }}</div>
              <div v-for="(c2, ki) in explanationForBlocked(r.label).citations" :key="'c' + ki" class="evidence-item">
                <span class="badge">{{ c2.candidateId }}</span> {{ c2.book }}——{{ c2.quote }}
              </div>
            </details>
          </div>
        </template>
      </section>

      <!-- Structure (roots/visibility/month) -->
      <section v-if="activeTab === 'structure'" class="panel">
        <h2>月令</h2>
        <div v-if="result.monthCommand">
          <p>{{ result.monthCommand.monthBranch }}月 · {{ result.monthCommand.season }} · {{ result.monthCommand.element }}</p>
          <p>日主状态：{{ result.monthCommand.relationToDayMaster.state }}
            <template v-if="result.monthCommand.relationToDayMaster.inCommand">（得令）</template>
          </p>
          <details open><summary>证据</summary>
            <div v-for="e in result.monthCommand.evidence" :key="e" class="evidence-item">{{ e }}</div>
          </details>
        </div>
        <h2>通根</h2>
        <div v-for="r in result.roots" :key="r.stem + r.branch + r.position" class="evidence-item">
          {{ r.statement }}
          <span class="badge">{{ r.depth }}</span>
          <span v-if="r.isMonthRoot" class="badge">月令</span>
        </div>
        <h2>透干</h2>
        <div v-for="v in result.visibility" :key="v.hiddenStem + v.position" class="evidence-item">
          {{ v.statement }}
        </div>
      </section>

      <!-- Strength -->
      <section v-if="activeTab === 'strength' && result.strength" class="panel">
        <h2>旺衰分析（多方法并列）</h2>
        <p class="agreement" v-if="result.strength.agreement">
          Agreement: {{ result.strength.agreement }}
        </p>
        <div v-for="m in result.strength.methods" :key="m.analyzerId" class="method-block">
          <h3>{{ m.name }} <span class="badge" v-if="m.verdict">{{ m.verdict }}</span>
            <span class="badge" v-if="m.confidence">{{ m.confidence }}</span>
          </h3>
          <!-- Dimension -->
          <template v-if="m.strengthEvidence">
            <div class="dim-row">
              <span>得令 {{ m.strengthEvidence.deLing.result ? "✓" : "✗" }}</span>
              <span>得地 {{ m.strengthEvidence.deDi.result ? "✓" : "✗" }}</span>
              <span>得势 {{ m.strengthEvidence.deShi.result ? "✓" : "✗" }}</span>
            </div>
            <details><summary>为什么？</summary>
              <div v-for="r in m.strengthEvidence.deLing.reason" :key="r" class="evidence-item">{{ r }}</div>
              <div v-for="r in m.strengthEvidence.deDi.reason" :key="r" class="evidence-item">{{ r }}</div>
              <div v-for="r in m.strengthEvidence.deShi.reason" :key="r" class="evidence-item">{{ r }}</div>
            </details>
          </template>
          <!-- Weighted -->
          <template v-if="m.score !== null && m.score !== undefined">
            <p>score: {{ m.score }}</p>
            <details><summary>Contributions</summary>
              <div v-for="c in m.contributions || []" :key="c.factor" class="evidence-item">
                {{ c.effect === "support" ? "+" : "−" }} {{ c.reason }} ({{ c.value }})
              </div>
            </details>
            <details><summary>Parameters</summary>
              <pre>{{ JSON.stringify(m.params, null, 2) }}</pre>
            </details>
          </template>
          <!-- Fuyi -->
          <template v-if="m.supportEvidence">
            <div class="evidence-item" v-for="e in m.supportEvidence" :key="e">+ {{ e }}</div>
            <div class="evidence-item" v-for="e in m.drainEvidence || []" :key="e">− {{ e }}</div>
          </template>
          <details><summary>General Evidence</summary>
            <div v-for="e in m.evidence" :key="e" class="evidence-item">{{ e }}</div>
          </details>
          <p class="note" v-if="m.note">{{ m.note }}</p>
        </div>
      </section>

      <!-- Pattern -->
      <section v-if="activeTab === 'pattern' && result.pattern" class="panel">
        <h2>格局</h2>
        <div v-for="c in result.pattern.candidates" :key="c.name + c.via" class="candidate-block">
          <h3>{{ c.name }} <span class="badge">{{ c.via }}</span></h3>
          <div v-for="e in c.evidence" :key="e" class="evidence-item">{{ e }}</div>
        </div>
        <template v-if="result.pattern.evaluation">
          <p class="status">Status: <strong>{{ result.pattern.evaluation.status }}</strong></p>
          <h3>支持因素</h3>
          <div v-for="f in result.pattern.evaluation.supports" :key="f.ruleId" class="evidence-item">
            {{ f.name }}: {{ f.detail }}
          </div>
          <h3>破坏因素</h3>
          <div v-for="f in result.pattern.evaluation.damages" :key="f.ruleId" class="evidence-item damage">
            {{ f.name }}: {{ f.detail }}
          </div>
          <h3>救应</h3>
          <div v-for="f in result.pattern.evaluation.rescues" :key="f.ruleId" class="evidence-item rescue">
            {{ f.name }}: {{ f.detail }}
          </div>
          <div v-if="result.pattern.evaluation.conflicts?.length">
            <h3>冲突</h3>
            <div v-for="f in result.pattern.evaluation.conflicts" :key="f.ruleId" class="evidence-item conflict">
              {{ f.name }}: {{ f.detail }}
            </div>
          </div>
        </template>
      </section>

      <!-- TiaoHou -->
      <section v-if="activeTab === 'tiaohou' && result.tiaohou" class="panel">
        <h2>调候</h2>
        <p v-if="!result.tiaohou.resolved" class="note">资料不足（UNRESOLVED）</p>
        <div v-for="rec in result.tiaohou.recommendations" :key="rec.targetStem + rec.priority" class="tiaohou-item">
          <strong>{{ rec.targetStem }}</strong>（{{ rec.element }} · {{ rec.priority }}）
          <span class="badge">{{ rec.present ? "命局已有" : "命局未见" }}</span>
          <span v-if="rec.positions.length" class="pos">{{ rec.positions.join(" · ") }}</span>
          <details><summary>查看依据</summary>
            <div v-for="rid in rec.ruleIds" :key="rid" class="evidence-item">规则：{{ rid }}</div>
            <div v-if="rec.quote" class="evidence-item quote">「{{ rec.quote }}」</div>
            <div v-if="rec.source" class="evidence-item">
              出处：{{ rec.source.book }} · {{ rec.source.chapter }} · PDF第{{ rec.source.pages?.join("-") }}页
            </div>
            <div v-for="p in rec.provenance" :key="p.level + p.concept" class="evidence-item">
              <span class="badge">{{ p.level }}</span> {{ p.concept }}
            </div>
          </details>
        </div>
        <div v-if="result.tiaohou.conflicts?.length" class="conflict">
          <div v-for="c in result.tiaohou.conflicts" :key="c" class="evidence-item conflict">⚠ {{ c }}</div>
        </div>
      </section>

      <!-- Advanced (M8) -->
      <section v-if="activeTab === 'advanced' && result.advancedAnalysis" class="panel">
        <h2>高级结构分析</h2>
        <!-- Special Patterns -->
        <h3>特殊格局候选</h3>
        <div v-for="c in result.advancedAnalysis.specialPattern?.cong || []" :key="c.type" class="candidate-block">
          <strong>{{ c.type }}</strong>
          <span class="badge" :class="c.status.toLowerCase()">{{ c.status }}</span>
          <details><summary>Supports / Blockers / 例外与两说</summary>
            <div v-for="s in c.supports" :key="s.ruleId" class="evidence-item">+ {{ s.text }}</div>
            <div v-for="b in c.blockers" :key="b.ruleId" class="evidence-item damage">− {{ b.text }}</div>
            <div v-for="e in c.exceptions || []" :key="'e' + e.ruleId" class="evidence-item">◎ {{ e.text }}</div>
            <div v-for="cf in c.conflicts || []" :key="'cf' + cf.ruleId" class="evidence-item conflict">⚠ {{ cf.text }}</div>
          </details>
          <details v-if="c.schoolVariants"><summary>流派差异</summary>
            <div v-for="(v, k) in c.schoolVariants" :key="k" class="evidence-item">{{ k }}: {{ v }}</div>
          </details>
        </div>
        <div v-for="z in result.advancedAnalysis.specialPattern?.zhuanwang || []" :key="z.type" class="candidate-block">
          <strong>{{ z.type }}</strong> <span class="badge">{{ z.status }}</span>
        </div>
        <!-- M25 外格虚神候选 -->
        <template v-if="result.advancedAnalysis.specialPattern?.xushiOuter?.length">
          <h3>外格虚神候选 <span class="note">飞天禄马/井栏叉/刑合/子邀巳——候选仅供参考，非格局（DTZ-26/36）</span></h3>
          <div v-for="x in result.advancedAnalysis.specialPattern.xushiOuter" :key="x.type" class="candidate-block">
            <strong>{{ x.type }}</strong> <span class="badge">{{ x.status }}</span>
            <div v-for="(sv, k) in x.schoolVariants" :key="k" class="note">{{ k }}：{{ sv }}</div>
            <div v-for="(b, i) in (x.blockers || [])" :key="'b' + i" class="evidence-item damage">阻断：{{ b.text }}</div>
          </div>
        </template>
        <!-- BingYao -->
        <h3>病药结构 <span class="note">（"病药"指命局结构中的失衡与制衡关系，不是医学诊断）</span></h3>
        <div v-for="p in result.advancedAnalysis.bingYao?.problems || []" :key="p.target" class="evidence-item damage">
          结构问题：{{ p.target }}（{{ p.evidence.join("；") }}）
        </div>
        <div v-for="m in result.advancedAnalysis.bingYao?.medicines || []" :key="m.problem + m.kind" class="evidence-item rescue">
          制衡：{{ m.target }} {{ m.kind }} → 解决 {{ m.problem }} 问题
        </div>
        <!-- TongGuan -->
        <h3>通关</h3>
        <div v-for="(b, i) in result.advancedAnalysis.tongGuan?.bridges || []" :key="i" class="evidence-item">
          {{ b.conflict.from }} → {{ b.bridge }} → {{ b.conflict.to }}
          <span class="badge">{{ b.present ? "桥已存在" : "桥未现" }}</span>
        </div>
      </section>

      <!-- M13 Temporal Workspace -->
      <section v-if="activeTab === 'temporal' && result" class="panel">
        <h2>时序工作台 <span class="note">大运 → 流年 → 流月 → 流日；岁运不替换原局月令</span></h2>

        <div class="temporal-controls">
          <label>大运
            <select v-model.number="selLuck" @change="onLuckChange" :disabled="!luckOptions.length">
              <option :value="null" disabled>选择大运</option>
              <option v-for="d in luckOptions" :key="d.index" :value="d.index">
                {{ d.ganZhi }}（{{ d.startYear }}–{{ d.endYear }}，{{ d.startAge }} 岁起）
              </option>
            </select>
          </label>
          <label>流年
            <select v-model.number="selYear" @change="onYearChange" :disabled="!yearOptions.length">
              <option :value="null" disabled>选择年份</option>
              <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}</option>
            </select>
          </label>
          <label>流月
            <select v-model.number="selMonth" @change="onMonthChange" :disabled="selYear === null">
              <option :value="null">（不选）</option>
              <option v-for="m in monthOptions" :key="m.n" :value="m.n">{{ m.label }}</option>
            </select>
          </label>
          <label>流日（可选）
            <input type="date" v-model="selDay" :disabled="selMonth === null" />
          </label>
          <button class="submit" @click="loadTemporal" :disabled="temporalLoading">
            {{ temporalLoading ? "分析中…" : "分析" }}
          </button>
        </div>
        <p v-if="!luckOptions.length" class="note">
          该命例无大运数据（性别或时辰未知时大运缺席，R7/R11）。
        </p>
        <p v-if="temporalError" class="error-text">{{ temporalError }}</p>

        <template v-if="temporalData">
          <!-- 岁运上下文 -->
          <div class="temporal-context">
            <span class="ctx-chip natal">原局 {{ temporalData.context.natalStems.filter(Boolean).map((s: string, i: number) => s + temporalData.context.natalBranches.filter(Boolean)[i]).join(" ") }}</span>
            <template v-if="temporalData.context.luckStem"><span class="arrow">→</span><span class="ctx-chip luck">大运 {{ temporalData.context.luckStem }}{{ temporalData.context.luckBranch }}</span></template>
            <template v-if="temporalData.context.annualStem"><span class="arrow">→</span><span class="ctx-chip annual">流年 {{ temporalData.context.annualStem }}{{ temporalData.context.annualBranch }}</span></template>
            <template v-if="temporalData.context.monthlyStem"><span class="arrow">→</span><span class="ctx-chip monthly">流月 {{ temporalData.context.monthlyStem }}{{ temporalData.context.monthlyBranch }}<span v-if="temporalData.monthWindow">（{{ temporalData.monthWindow.jieName }}起）</span></span></template>
            <template v-if="temporalData.context.dailyStem"><span class="arrow">→</span><span class="ctx-chip daily">流日 {{ temporalData.context.dailyStem }}{{ temporalData.context.dailyBranch }}</span></template>
          </div>

          <!-- 规则触发 -->
          <h3>岁运规则触发 <span class="note">ExecutableRule(domain=temporal) → 结构观察，不含吉凶</span></h3>
          <div v-for="t in matchedRules" :key="t.ruleId" class="candidate-block">
            <strong>{{ t.label }}</strong>
            <span class="badge">{{ t.ruleId }}</span>
            <div v-for="(o, i) in t.observations" :key="i" class="evidence-item">{{ o }}</div>
          </div>
          <p v-if="!matchedRules.length" class="note">无规则触发（全部 {{ temporalData.ruleTriggers?.length ?? 0 }} 条规则已参与判定，matched=false 保留可审计）。</p>

          <!-- 关系与结构 -->
          <h3>新增关系 <span class="note">原局不存在、由岁运引入</span></h3>
          <div v-for="(r, i) in temporalData.relations" :key="i" class="evidence-item">
            {{ r.label }}
            <span class="badge">{{ r.sources.join("+") }}</span>
            <span v-if="r.completesHarmony" class="badge rescue">补齐三合</span>
            <span v-if="r.transformCandidate" class="badge">化{{ r.transformCandidate }}候选</span>
            <span class="note">{{ r.positions.join(" ↔ ") }}</span>
          </div>
          <p v-if="!temporalData.relations.length" class="note">无新增关系。</p>
          <h3>结构现象</h3>
          <div v-for="(s, i) in temporalData.structures" :key="i" class="evidence-item damage">
            {{ s.label }}：{{ s.description }}
          </div>
          <p v-if="!temporalData.structures.length" class="note">无结构现象（伏吟/反吟/岁运并临/天克地冲等）。</p>

          <!-- Delta -->
          <template v-if="temporalData.delta">
            <h3>完整 Temporal Delta <span class="note">相对原局的状态差异；EXPERIMENTAL = 岁运参与该计算存在流派分歧</span></h3>
            <div v-for="(items, analysis) in deltaByAnalysis" :key="analysis" class="candidate-block">
              <strong>{{ analysis }}</strong>
              <div v-for="it in items" :key="it.refId + it.kind" class="evidence-item">
                <span class="badge">{{ KIND_CN[it.kind] || it.kind }}</span>
                <span v-if="it.supportLevel === 'EXPERIMENTAL'" class="badge damage">EXPERIMENTAL</span>
                <strong>{{ it.subject }}</strong>
                <span v-if="it.natalValue !== null || it.temporalValue !== null" class="note">
                  {{ JSON.stringify(it.natalValue) }} → {{ JSON.stringify(it.temporalValue) }}
                </span>
                <div v-for="(e, i) in it.evidence" :key="i" class="evidence-item">{{ e }}</div>
              </div>
            </div>
            <div v-for="(n, i) in temporalData.delta.unsupportedNotes || []" :key="'u' + i" class="evidence-item note">
              UNSUPPORTED：{{ n }}
            </div>

            <!-- StructuralTheme 结构主题层 -->
            <h3>结构主题 <span class="note">十神主题/冲突关系/结构波动——中间描述层，不是事件预测</span></h3>
            <div v-for="(t, i) in temporalData.delta.themes || []" :key="'t' + i" class="evidence-item">
              <span class="badge rescue">{{ t.label }}</span>
              <span v-if="t.supportLevel === 'EXPERIMENTAL'" class="badge damage">EXPERIMENTAL</span>
              <span class="note">{{ t.note }}</span>
              <details><summary>依据</summary>
                <div v-for="(b, j) in t.basis" :key="j" class="evidence-item">{{ b }}</div>
              </details>
            </div>
            <p v-if="!(temporalData.delta.themes || []).length" class="note">无结构主题。</p>
          </template>

          <!-- M14 Event Themes -->
          <template v-if="temporalData.eventThemes">
            <h3>事件主题 <span class="note">结构层面的「值得关注」候选——不是预测事件；无 CONFIRMED 状态</span></h3>
            <div v-for="t in temporalData.eventThemes.themes" :key="t.theme" class="candidate-block">
              <strong>{{ t.themeCn || t.theme }}</strong>
              <span class="badge" :class="statusBadgeClass(t.status)">{{ t.status }}</span>
              <span v-if="t.agreement === 'CONFLICT'" class="badge damage">多体系冲突</span>
              <span v-else-if="t.agreement === 'HIGH'" class="badge rescue">多体系一致</span>
              <span class="badge">confidence {{ t.confidence }}</span>
              <span class="note">（ENGINEERING_HEURISTIC 加权，非概率）</span>
              <div v-for="(v, k) in t.schoolViews" :key="k" class="evidence-item note">
                视角 {{ k }}：{{ v }}
              </div>
              <details open><summary>支持证据</summary>
                <div v-for="(e, i) in t.supportingEvidence" :key="'s' + i" class="evidence-item rescue">+ {{ e }}</div>
                <p v-if="!t.supportingEvidence.length" class="note">无</p>
              </details>
              <details v-if="t.opposingEvidence.length"><summary>反对证据</summary>
                <div v-for="(e, i) in t.opposingEvidence" :key="'o' + i" class="evidence-item damage">− {{ e }}</div>
              </details>
              <details v-if="t.conflictExplanations && t.conflictExplanations.length">
                <summary>冲突解释（上下文相关，无全局优先级）</summary>
                <div v-for="(c, i) in t.conflictExplanations" :key="'c' + i" class="evidence-item">
                  <span class="badge">{{ c.kind }}</span> {{ c.explanation }}
                </div>
              </details>
              <details v-if="explanationFor(t.theme)"
                       class="chain-details">
                <summary>解释链（Event Theme → Rule → 救应 → Evidence → Quote → Source）</summary>
                <div class="chain-verdict">{{ explanationFor(t.theme).reasoning.verdictStatement }}</div>
                <h4>支持链</h4>
                <div v-for="h in explanationFor(t.theme).reasoning.supportingChain" :key="h.ruleId" class="evidence-item rescue">
                  <strong>{{ h.ruleId }}</strong>（{{ h.view }}）
                  <span v-if="h.rescueApplied" class="badge rescue">救应：{{ h.rescueApplied.id }}</span>
                  <div v-for="(e, i) in h.evidence" :key="'e' + i" class="note">{{ e }}</div>
                  <div v-if="h.quote" class="quote">原文：{{ h.quote }}（{{ h.source?.book }}）</div>
                  <div v-if="h.rescueApplied" class="note">{{ h.rescueApplied.note }}</div>
                </div>
                <h4>反对链</h4>
                <div v-for="h in explanationFor(t.theme).reasoning.opposingChain" :key="'o' + h.ruleId" class="evidence-item damage">
                  <strong>{{ h.ruleId }}</strong>（{{ h.view }}）
                  <span v-if="h.rescueApplied" class="badge rescue">被救应削弱：{{ h.rescueApplied.id }}</span>
                  <div v-for="(e, i) in h.evidence" :key="'oe' + i" class="note">{{ e }}</div>
                  <div v-if="h.quote" class="quote">原文：{{ h.quote }}（{{ h.source?.book }}）</div>
                </div>
              </details>
            </div>
            <p v-if="!temporalData.eventThemes.themes.length" class="note">当前岁运上下文无事件主题候选。</p>
          </template>

          <div class="note" style="margin-top: 0.6rem;">
            ⚠️ 所有内容为结构变化描述，不构成任何吉凶或事件预测。
          </div>
        </template>
      </section>

      <!-- M16 Knowledge Explorer -->
      <section v-if="activeTab === 'knowledge'" class="panel">
        <h2>知识工作台 <span class="note">Source ↔ Rule ↔ Conflict ↔ Case 只读导航；不复制推理逻辑</span></h2>
        <div class="kb-stats" v-if="kbStats">
          <span class="badge">executable {{ kbStats.executableTotal }}</span>
          <span class="badge" v-for="(v, k) in kbStats.executableByDomain" :key="k">{{ k }}: {{ v }}</span>
          <span class="note">candidates（556）与 executable（{{ kbStats.executableTotal }}）是不同口径</span>
        </div>
        <div class="temporal-controls">
          <input v-model="kbSearch" placeholder="搜索 id/label/theme…" />
          <select v-model="kbDomain">
            <option value="all">全部 domain</option>
            <option value="tiaohou">tiaohou</option>
            <option value="temporal">temporal</option>
            <option value="event">event</option>
          </select>
        </div>
        <div v-for="r in kbFiltered" :key="r.id" class="candidate-block">
          <strong>{{ r.id }}</strong>
          <span class="badge">{{ r.domain }}</span>
          <span v-if="r.view" class="badge">{{ r.view }}</span>
          <span class="badge" v-for="lv in r.provenanceLevels" :key="lv"
                :class="{ damage: lv === 'ENGINEERING_HEURISTIC' }">{{ lv }}</span>
          <span class="badge">Q{{ r.quality }}</span>
          <span class="badge">{{ r.verification?.status }}</span>
          <div>{{ r.label }}</div>
          <div v-if="r.conflictNeighbors.length" class="note">
            冲突/救应邻接：{{ r.conflictNeighbors.map((c: any) => c.edgeType + (c.related ? '→' + c.related.join(',') : '')).join("；") }}
          </div>
          <div v-if="r.conflictNote" class="note">⚠ {{ r.conflictNote }}</div>
          <details v-if="r.replaySamples?.length">
            <summary>典型案例回放（{{ r.replaySamples.length }}）</summary>
            <div v-for="(rp, i) in r.replaySamples" :key="i" class="evidence-item note">
              {{ rp.caseId }}（{{ rp.book }}）{{ rp.luck ? '· 运 ' + rp.luck : '' }}{{ rp.annual ? '· 年 ' + rp.annual : '' }}
              — {{ rp.theme }}/{{ rp.status }}
              <span v-if="rp.relation" :class="{ rescue: rp.relation === 'SOURCE_SUPPORTS', damage: rp.relation === 'SOURCE_DIFFERS' }">
                [{{ rp.relation }}]</span>
            </div>
            <div v-if="Object.keys(r.relationDistribution || {}).length" class="note">
              分布：{{ Object.entries(r.relationDistribution).map(([k, v]) => k + ':' + v).join('、') }}
            </div>
          </details>
        </div>
        <p v-if="!kbFiltered.length" class="note">无匹配规则。</p>

        <h3>Rule / Conflict / Rescue Graph
          <span class="note">点击边查看声明出处；反查用规则搜索框</span>
        </h3>
        <div class="temporal-controls">
          <input v-model="graphFilter" placeholder="过滤 type/规则 id…" @focus="loadGraph" />
          <button class="link" @click="loadGraphAndRender">加载图</button>
        </div>
        <div v-if="kbGraph" class="note">
          节点 {{ kbGraph.nodeCount }} · 边 {{ kbGraph.edgeCount }}（{{ kbGraph.edgeTypes }}）
        </div>
        <div class="temporal-controls">
          <select v-model="graphTypeFilter">
            <option value="all">全部边型</option>
            <option value="conflict">conflict（冲突声明）</option>
            <option value="rescues">rescues（救应）</option>
            <option value="school-conflict">school-conflict（流派）</option>
          </select>
          <button class="link" @click="resetGraphView">重置视图</button>
          <span class="note">滚轮缩放 · 拖拽平移 · 点击节点聚焦邻居（再点取消）。颜色：橙=event 蓝=temporal 绿=tiaohou 紫=救应谓词</span>
        </div>
        <svg v-if="graphSvg" :viewBox="graphViewBox"
             class="graph-svg" role="img" aria-label="Rule Conflict/Rescue Graph"
             @wheel.prevent="onGraphWheel" @pointerdown="onGraphDown"
             @pointermove="onGraphMove" @pointerup="onGraphUp" @pointerleave="onGraphUp">
          <line v-for="(e, i) in graphSvg.edges" :key="'e' + i"
                :x1="e.x1" :y1="e.y1" :x2="e.x2" :y2="e.y2"
                :stroke="e.type === 'conflict' ? '#c0392b' : e.type === 'rescues' ? '#8e44ad' : '#95a5a6'"
                :stroke-width="e.dim ? 0.5 : 1.6"
                :stroke-dasharray="e.type === 'school-conflict' ? '6 4' : e.type === 'rescues' ? '2 3' : undefined"
                :opacity="e.dim ? 0.15 : 0.75" />
          <g v-for="n in graphSvg.nodes" :key="n.id"
             :transform="`translate(${n.x},${n.y})`"
             class="graph-node" @click="selectNode(n.id)"
             :opacity="selectedNodeId && !n.selected && !n.highlighted ? 0.35 : 1">
            <circle :r="n.type === 'predicate' ? 7 : n.selected ? 11 : 9"
                    :fill="nodeColor(n)"
                    :stroke="n.selected ? '#1a1a1a' : '#fff'" stroke-width="2" />
            <text :y="n.type === 'predicate' ? 22 : 24" text-anchor="middle" class="graph-label">
              {{ nodeLabel(n) }}</text>
          </g>
        </svg>
        <div v-if="selectedNodeDetail" class="candidate-block">
          <strong>{{ selectedNodeDetail.id }}</strong>
          <span class="badge">{{ selectedNodeDetail.domain }}</span>
          <span v-if="selectedNodeDetail.view" class="badge">{{ selectedNodeDetail.view }}</span>
          <div>{{ selectedNodeDetail.label }}</div>
          <div class="note">
            来源：{{ selectedNodeDetail.source?.book || '—' }}
            · provenance {{ (selectedNodeDetail.provenanceLevels || []).join('/') }}
          </div>
          <div v-if="selectedNodeDetail.conflictNote" class="note">⚠ {{ selectedNodeDetail.conflictNote }}</div>
          <details v-if="(selectedNodeDetail.replaySamples || []).length">
            <summary>重放命例（Rule→Case，最多 3 条）</summary>
            <div v-for="(rc, ri) in selectedNodeDetail.replaySamples" :key="ri" class="evidence-item">
              {{ rc.caseId }}（{{ rc.book }}·{{ rc.luck || '原局' }}{{ rc.annual ? '→' + rc.annual : '' }}）
              <span class="badge">{{ rc.theme }}</span>
              <span class="badge">{{ rc.relation }}</span>
            </div>
          </details>
          <div v-if="selectedNodeDetail.randomTriggerRate != null" class="note">
            随机盘触发率 {{ (selectedNodeDetail.randomTriggerRate * 100).toFixed(1) }}%
          </div>
          <div v-if="chainJumpThemes.length" class="note">
            当前分析的解释链引用了该规则（{{ chainJumpThemes.join('、') }} 主题）：
            <button class="link" @click="jumpToChain">跳转解释链</button>
          </div>
        </div>
        <div v-for="(e, i) in graphEdges" :key="i" class="evidence-item">
          <span class="badge" :class="{ damage: e.type === 'conflict' }">{{ e.type }}</span>
          {{ (e.between ?? [e.from, e.to]).join(' ↔ ') }}
          <span v-if="e.resolution" class="badge">{{ e.resolution }}</span>
          <span v-if="e.specificCondition" class="badge rescue">condition: {{ e.specificCondition }}</span>
          <div class="note">{{ e.note }}</div>
        </div>

        <!-- M19 Quality/Coverage Dashboard -->
        <h3>Quality / Coverage Dashboard</h3>
        <div v-if="kbFunnel" class="kb-stats">
          <span class="badge">Source {{ kbFunnel.funnel?.sources }} → Candidate {{ kbFunnel.funnel?.candidates }} → Executable {{ kbFunnel.funnel?.executable }}</span>
          <span class="badge">未用候选 {{ kbFunnel.candidatesUnused }}</span>
          <span class="badge">未触发 {{ kbFunnel.neverTriggered }}</span>
          <span class="badge">冲突密度 {{ kbFunnel.conflictDensity }}</span>
        </div>
        <div v-if="kbCoverage?.gates" class="candidate-block">
          <strong>Audit Gates</strong>
          <span class="badge" :class="kbCoverage.allPass ? 'rescue' : 'damage'">
            {{ kbCoverage.allPass ? 'ALL PASS' : 'FAIL' }}</span>
          <div v-for="(g, k) in kbCoverage.gates" :key="k" class="evidence-item note">
            {{ k }}：{{ g.pass ? 'PASS' : 'FAIL' }}
          </div>
        </div>
        <div v-if="kbCoverage?.coverage" class="candidate-block">
          <strong>Rule→Case 覆盖</strong>
          <div class="note">
            {{ Object.entries(kbCoverage.coverage.ruleCaseCoverage || {}).map(([k, v]) => k + ':' + v).join('、') || '无' }}
          </div>
          <div class="note">未触发（never-in-replay）：{{ (kbCoverage.coverage.eventRulesNeverInReplay || []).join('、') || '无' }}</div>
        </div>
        <div v-if="kbEvalCompare?.comparisons?.length" class="candidate-block">
          <strong>AI Evaluation Compare <span class="note">确定性指标回归对比（无 LLM-as-judge）</span></strong>
          <div class="temporal-controls">
            <input v-model="evalFilterProvider" placeholder="过滤 provider/model…" />
            <label class="checkbox"><input type="checkbox" v-model="evalOnlyRegression" /> 仅显示有回归信号的运行</label>
          </div>
          <div v-if="evalTrend" class="trend-box">
            <div class="note">趋势（最近 {{ evalTrend.n }} 次运行）：pass 率（蓝）· grounding 问题数（红）
              <span v-if="evalTrend.latencyLine">· latency ms（绿，max {{ evalTrend.latencyMax }}）</span></div>
            <svg viewBox="0 0 600 96" class="trend-svg" role="img" aria-label="evaluation trend">
              <polyline :points="evalTrend.rateLine" fill="none" stroke="#2980b9" stroke-width="2" />
              <polyline :points="evalTrend.groundLine" fill="none" stroke="#c0392b" stroke-width="1.5"
                        :opacity="evalTrend.groundMax ? 1 : 0.15" />
              <polyline v-if="evalTrend.latencyLine" :points="evalTrend.latencyLine" fill="none"
                        stroke="#27ae60" stroke-width="1.5" stroke-dasharray="4 3" />
            </svg>
          </div>
          <details v-for="(c, i) in evalComparisonsFiltered" :key="i">
            <summary>
              {{ c.metrics.provider }}/{{ c.metrics.model }}（prompt {{ c.metrics.promptVersion }}）
              — pass {{ c.metrics.verdictPass }}/{{ c.metrics.verdictTotal }}
              <span v-if="Object.keys(c.regressionAgainstPrevious).length" class="badge damage">回归</span>
            </summary>
            <div class="note">
              grounding {{ c.metrics.groundingIssueTotal }} · banned {{ c.metrics.bannedTotal }} ·
              disagreementMissing {{ c.metrics.disagreementMissingCount }} ·
              claimRefs {{ c.metrics.claimRefsUsedAvg }}
            </div>
            <div v-if="c.telemetry" class="note">
              遥测：latency {{ c.telemetry.latencyMsAvg }}ms · tokens {{ c.telemetry.tokensTotal }} ·
              retries {{ c.telemetry.retriesTotal }} · errors {{ (c.telemetry.errorCategories || []).join(',') || '无' }}
            </div>
            <div v-for="(v, k) in c.regressionAgainstPrevious" :key="k" class="evidence-item damage">
              {{ k }}: {{ v }}
            </div>
          </details>
        </div>

        <div v-if="kbRelease?.metadata" class="candidate-block">
          <strong>Release Metadata</strong>
          <div class="note">
            commit {{ (kbRelease.metadata.release?.gitCommit || '').slice(0, 12) }} ·
            engine {{ kbRelease.metadata.engineVersion }} ·
            测试 {{ kbRelease.metadata.counts?.tests }} ·
            质量 {{ kbRelease.qualitySummary?.allPass ? 'ALL PASS' : 'FAIL' }}
          </div>
          <details><summary>版本依赖</summary>
            <div v-for="(v, k) in kbRelease.metadata.versions" :key="k" class="evidence-item note">{{ k }}: {{ v }}</div>
          </details>
        </div>

        <h3>Review Queue <span class="note">只读；HUMAN_VERIFIED 只能由真实人工产生</span></h3>
        <div v-for="(it, i) in kbReview" :key="i" class="evidence-item">
          <span class="badge" :class="{ damage: it.priority === 'P1' }">{{ it.priority }}</span>
          <span class="badge">{{ it.section }}</span>
          {{ it.id || it.caseId || it.text || '' }}
          <span class="note">{{ (it.note || it.title || '').slice(0, 80) }}</span>
        </div>
      </section>

      <!-- AI Interpretation -->
    <section v-if="activeTab === 'ai' && result" class="panel">
      <h2>AI 解读</h2>
      <div v-if="aiState === 'READY'" class="ai-ready">
        <p>点击下方按钮生成基于确定性分析结果的 AI 解释。</p>
        <button class="submit" @click="generateAI">生成 AI 解读</button>
      </div>
      <div v-if="aiState === 'LOADING'" class="ai-loading">
        <p>正在生成基于 Tianze 分析结果的解释…</p>
      </div>
      <div v-if="aiState === 'NOT_CONFIGURED'" class="ai-not-configured">
        <p>当前未配置 AI 解读服务，确定性命理分析仍可正常使用。</p>
      </div>
      <div v-if="aiState === 'GROUNDING_FAILED'" class="ai-grounding-failed">
        <p>本次 AI 输出未通过事实一致性检查，因此未展示。</p>
        <details v-if="aiResult?.groundingIssues?.length"><summary>Grounding Issues</summary>
          <div v-for="(gi, i) in aiResult.groundingIssues" :key="i" class="evidence-item conflict">
            [{{ gi.severity }}] {{ gi.type }}: {{ gi.detail }}
          </div>
        </details>
        <button class="submit" @click="generateAI">重新生成</button>
      </div>
      <div v-if="aiState === 'PROVIDER_ERROR'" class="error">
        <p>{{ aiError }}</p>
        <button class="submit" @click="generateAI">重试</button>
      </div>
      <template v-if="aiState === 'SUCCESS' && aiResult">
        <p class="ai-summary">{{ aiResult.summary }}</p>
        <div v-for="sec in aiResult.sections || []" :key="sec.type + sec.title" class="ai-section">
          <h3>{{ sec.title }}</h3>
          <p>{{ sec.content }}</p>
          <details v-if="sec.claims?.length"><summary>引用依据</summary>
            <div v-for="c in sec.claims" :key="c.refId" class="evidence-item">
              <span class="badge">{{ c.type }}</span> {{ c.refId }}
            </div>
          </details>
          <details v-if="sec.sourceIds?.length"><summary>来源</summary>
            <div v-for="sid in sec.sourceIds" :key="sid" class="evidence-item">{{ sid }}</div>
          </details>
        </div>
        <div v-if="aiResult.disagreements?.length">
          <h3>分析分歧</h3>
          <div v-for="d in aiResult.disagreements" :key="d" class="evidence-item conflict">{{ d }}</div>
        </div>
        <div v-if="aiResult.uncertainties?.length">
          <h3>不确定项</h3>
          <div v-for="u in aiResult.uncertainties" :key="u" class="evidence-item fallback">{{ u }}</div>
        </div>
      </template>
    </section>

    <!-- Warnings / Fallbacks -->
      <section v-if="result.warnings.length || result.fallbacks.length" class="panel warnings-panel">
        <h3>注意事项</h3>
        <div v-for="w in result.warnings" :key="w" class="evidence-item warning">⚠ {{ w }}</div>
        <div v-for="f in result.fallbacks" :key="f" class="evidence-item fallback">ℹ {{ f }}</div>
      </section>
    </template>
  </div>
</template>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: "Noto Sans SC", system-ui, sans-serif; background: #f5f6fa; color: #2c3e50; }
.tianze-app { max-width: 960px; margin: 0 auto; padding: 1rem; }
.header { padding: 1rem 0; border-bottom: 2px solid #3498db; margin-bottom: 1rem; }
.header h1 { display: inline; font-size: 1.5rem; color: #2c3e50; }
.header .subtitle { margin-left: 0.5rem; color: #7f8c8d; font-size: 0.9rem; }
.header .version { float: right; color: #95a5a6; font-size: 0.8rem; }
.panel { background: white; border: 1px solid #e0e0e0; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
.panel h2 { font-size: 1.1rem; color: #2c3e50; margin-bottom: 0.5rem; border-left: 3px solid #3498db; padding-left: 0.5rem; }
.panel h3 { font-size: 0.95rem; color: #34495e; margin: 0.5rem 0 0.3rem; }
.form-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 0.5rem; margin: 0.5rem 0; }
.form-grid label { display: flex; flex-direction: column; gap: 0.2rem; font-size: 0.85rem; }
.form-grid input, .form-grid select { padding: 0.4rem; border: 1px solid #bdc3c7; border-radius: 4px; }
.checkbox { flex-direction: row !important; align-items: center; }
.submit { background: #3498db; color: white; border: none; padding: 0.6rem 1.5rem; border-radius: 6px; cursor: pointer; font-size: 1rem; margin-top: 0.5rem; }
.submit:hover { background: #2980b9; }
.submit:disabled { background: #95a5a6; }
.error { color: #e74c3c; margin-top: 0.5rem; padding: 0.5rem; background: #fdf0ef; border-radius: 4px; }
.pillars { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 0.5rem; }
.pillar-card { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 6px; padding: 0.8rem; text-align: center; }
.pillar-label { font-size: 0.8rem; color: #7f8c8d; }
.pillar-ganzhi { font-size: 1.8rem; font-weight: bold; margin: 0.3rem 0; }
.pillar-ganzhi .stem { color: #2c3e50; margin-right: 0.3rem; }
.pillar-ganzhi .branch { color: #3498db; }
.pillar-tengod { font-size: 0.85rem; color: #e67e22; }
.pillar-details { font-size: 0.75rem; color: #95a5a6; display: flex; flex-direction: column; gap: 0.1rem; }
.pillar-details details { margin-top: 0.3rem; }
.tabs { display: flex; gap: 0.2rem; margin-bottom: 0.5rem; flex-wrap: wrap; }
.tabs button { padding: 0.4rem 0.8rem; border: 1px solid #bdc3c7; background: white; cursor: pointer; border-radius: 4px 4px 0 0; }
.tabs button.active { background: #3498db; color: white; border-color: #3498db; }
.relation-item, .evidence-item, .tiaohou-item, .candidate-block { padding: 0.4rem 0; border-bottom: 1px solid #f0f0f0; font-size: 0.9rem; }
.badge { display: inline-block; padding: 0.1rem 0.4rem; border-radius: 3px; font-size: 0.75rem; background: #eaf2f8; color: #2980b9; margin: 0 0.2rem; }
.badge.likely { background: #e8f8f5; color: #27ae60; }
.badge.blocked { background: #fdedec; color: #e74c3c; }
.damage { color: #c0392b; }
.rescue { color: #27ae60; }
.conflict { color: #e67e22; }
.note { color: #95a5a6; font-size: 0.8rem; }
.pos { color: #7f8c8d; font-size: 0.8rem; }
.quote { font-style: italic; color: #555; }
.agreement { padding: 0.5rem; background: #fef9e7; border-radius: 4px; font-size: 0.9rem; }
.method-block { border-left: 3px solid #3498db; padding-left: 0.8rem; margin: 0.8rem 0; }
.dim-row { display: flex; gap: 1rem; font-size: 0.95rem; }
.elements { display: flex; flex-direction: column; gap: 0.3rem; }
.element-row { display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; }
.elem-label { width: 3em; text-align: right; }
.bar { flex: 1; height: 1rem; background: #ecf0f1; border-radius: 3px; overflow: hidden; }
.fill { height: 100%; background: #3498db; border-radius: 3px; }
.status { font-size: 1rem; }
.candidate-block { border-left: 3px solid #e67e22; padding-left: 0.8rem; margin: 0.5rem 0; }
.warnings-panel { border-left: 3px solid #f39c12; }
.warning { color: #e67e22; }
.fallback { color: #7f8c8d; }
details { margin: 0.3rem 0; }
summary { cursor: pointer; color: #3498db; font-size: 0.85rem; }
.link { background: none; border: none; color: #3498db; cursor: pointer; text-decoration: underline; font-size: 0.85rem; }
.temporal-controls { display: flex; gap: 0.8rem; flex-wrap: wrap; align-items: end; margin-bottom: 0.8rem; }
.temporal-controls label { display: flex; flex-direction: column; gap: 0.2rem; font-size: 0.85rem; }
.temporal-controls select, .temporal-controls input { padding: 0.3rem; border: 1px solid #bdc3c7; border-radius: 4px; }
.temporal-context { display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; margin: 0.6rem 0 1rem; }
.ctx-chip { padding: 0.3rem 0.7rem; border-radius: 4px; font-size: 0.9rem; font-weight: 600; }
.ctx-chip.natal { background: #eaf2f8; color: #2471a3; }
.ctx-chip.luck { background: #fef9e7; color: #b7950b; }
.ctx-chip.annual { background: #e8f8f5; color: #148f77; }
.ctx-chip.monthly { background: #f4ecf7; color: #7d3c98; }
.ctx-chip.daily { background: #fdedec; color: #b03a2e; }
.arrow { color: #95a5a6; font-weight: 700; }
.error-text { color: #e74c3c; font-size: 0.9rem; }
.graph-svg { width: 100%; height: auto; background: #fafafa; border: 1px solid #eee; border-radius: 6px; margin: 0.5rem 0; }
.graph-node { cursor: pointer; }
.graph-node:hover circle { stroke: #3498db; }
.graph-svg { touch-action: none; user-select: none; }
.trend-box { margin: 0.4rem 0; }
.trend-svg { width: 100%; max-width: 640px; height: auto; background: #fafafa; border: 1px solid #eee; border-radius: 6px; }
.graph-label { font-size: 9px; fill: #555; pointer-events: none; }
@media (max-width: 600px) { .pillars { grid-template-columns: repeat(2, 1fr); } .form-grid { grid-template-columns: 1fr; } }
</style>
