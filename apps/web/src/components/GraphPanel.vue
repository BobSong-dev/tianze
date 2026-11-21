<script setup lang="ts">
/**
 * GraphPanel — 规则 / 冲突 / 救应 / 流派冲突 关系图。
 *
 * 边界：
 *  - 节点、边与统计完全来自后端 /knowledge/graph（conflict-graph.json）；
 *  - 布局是**确定性展示布局**（按 domain 分环、按 id 稳定排序），不含任何推理；
 *  - 不隐藏任何节点；孤立节点（无任何边）照常绘制，只是在视觉上更弱——
 *    稀疏本身就是这份数据的事实，用尺寸与透明度如实表达，而不是靠删点美化。
 *
 * 可读性处理（不删信息）：
 *  - 环改为椭圆，吃满宽幅面板；
 *  - 标签做贪心避让：优先保留选中/悬停/有关系/高序号节点，
 *    被折叠的标签仍可通过悬停、点选或「全部标签」开关看到；
 *  - 工具栏常显「已连接 / 孤立」计数，避免把稀疏误读成密集。
 */
import { computed, ref } from "vue";

const props = defineProps<{
  graph: any;
  selectedId?: string | null;
  /** 由外部（关系引文跳转等）注入的聚焦目标 */
  focusId?: string | null;
}>();

const emit = defineEmits<{
  (e: "select", id: string | null): void;
  (e: "select-edge", edge: any): void;
}>();

const typeFilter = ref<string>("all");
const allLabels = ref(false);
/**
 * 孤立节点（无任何边）默认折叠。
 *
 * 这不是"隐藏证据"：冲突图里 229 个节点只有 18 条边，199 个节点是孤立的。
 * 全部铺成圆环只会得到一圈"珠链"，看不出结构。默认只画有边的部分，
 * 工具栏常显总数与孤立数，并给一个开关一键全部展开；下方另有一行说明。
 */
const showIsolated = ref(false);
const hoverId = ref<string | null>(null);
const view = ref({ x: 0, y: 0, w: 900, h: 566 });
const moved = ref(false);
let drag: { px: number; py: number } | null = null;

const CANVAS = { w: 900, h: 566, cx: 450, cy: 272 };
/** 标签字号（SVG 用户单位）；宽度估算与渲染同源 */
const LABEL_FS = 12;

/** 域名的固定顺序（决定环序）；未列出的域名排在其后 */
const DOMAIN_ORDER = ["predicate", "event", "tenet", "temporal", "tiaohou", "structure", "relation"];

const DOMAIN_COLOR: Record<string, string> = {
  event: "var(--wx-fire)",
  temporal: "var(--wx-water)",
  tiaohou: "var(--wx-wood)",
  tenet: "var(--wx-earth)",
  predicate: "var(--st-experimental)",
  default: "var(--ink-400)",
};

const DOMAIN_CN: Record<string, string> = {
  event: "事件域", temporal: "岁运域", tiaohou: "调候域", tenet: "理论条目",
  predicate: "救应谓词", structure: "结构域", relation: "关系域",
};

const EDGE_TYPE_CN: Record<string, string> = {
  conflict: "冲突", rescues: "救应", "school-conflict": "流派冲突",
};

function domainCn(d?: string | null): string {
  if (!d) return "其它";
  return DOMAIN_CN[d] ?? d;
}
function edgeTypeCn(t?: string | null): string {
  if (!t) return "";
  return EDGE_TYPE_CN[t] ?? t;
}

const edgeTypes = computed<string[]>(() => {
  const g = props.graph;
  if (!g) return [];
  const declared = Object.keys(g.edgeTypes ?? {});
  return declared.length ? declared : ["conflict", "rescues", "school-conflict"];
});

/** 每个节点的度数（用于视觉权重与标签优先级；只统计后端给出的边） */
const degreeOf = computed<Map<string, number>>(() => {
  const m = new Map<string, number>();
  for (const e of props.graph?.edges ?? []) {
    const ids: string[] = e.between ?? [e.from, e.to].filter(Boolean);
    for (const id of ids) m.set(id, (m.get(id) ?? 0) + 1);
  }
  return m;
});

const connectedCount = computed(() => degreeOf.value.size);

const layout = computed(() => {
  const g = props.graph;
  if (!g) return { nodes: [] as any[], rings: [] as any[], width: CANVAS.w, height: CANVAS.h };

  /**
   * 参与布局的节点集合：折叠孤立节点时，环只按"有边的节点"均分角度，
   * 否则会出现"环上几乎没有点"的空椭圆，既浪费画幅又像装饰。
   */
  const active = (g.nodes ?? []).filter((n: any) =>
    showIsolated.value || (degreeOf.value.get(n.id) ?? 0) > 0);

  const buckets: Record<string, any[]> = {};
  for (const n of active) {
    const ring = n.type === "predicate" ? "predicate" : (n.domain ?? "event");
    (buckets[ring] ??= []).push(n);
  }

  /** 域总量（含孤立节点），仅用于图例；布局用 active 数 */
  const totals: Record<string, number> = {};
  for (const n of g.nodes ?? []) {
    const ring = n.type === "predicate" ? "predicate" : (n.domain ?? "event");
    totals[ring] = (totals[ring] ?? 0) + 1;
  }

  // 环序：固定域序在前，其余按字典序补在后面（保证同一输入总得到同一张图）
  const known = DOMAIN_ORDER.filter(d => buckets[d]);
  const extra = Object.keys(buckets).filter(d => !DOMAIN_ORDER.includes(d)).sort();
  const ringKeys = [...known, ...extra];

  // 椭圆半径按环数均分，确保各环互不重叠且吃满面板
  const rxMin = 92, rxMax = 396, ryMin = 76, ryMax = 248;
  const n = Math.max(1, ringKeys.length);
  const rings = ringKeys.map((key, i) => {
    const t = n === 1 ? 1 : i / (n - 1);
    return {
      key,
      rx: rxMin + (rxMax - rxMin) * t,
      ry: ryMin + (ryMax - ryMin) * t,
      count: buckets[key].length,
      total: totals[key] ?? buckets[key].length,
    };
  });

  const nodes: any[] = [];
  for (const ring of rings) {
    const sorted = [...buckets[ring.key]].sort((a, b) => String(a.id).localeCompare(String(b.id)));
    const total = Math.max(1, sorted.length);
    sorted.forEach((node, i) => {
      // 单节点环放在正上方；多节点环从正上方起顺时针均分
      const angle = total === 1
        ? -Math.PI / 2
        : (2 * Math.PI * i) / total - Math.PI / 2;
      nodes.push({
        ...node,
        ring: ring.key,
        degree: degreeOf.value.get(node.id) ?? 0,
        x: CANVAS.cx + ring.rx * Math.cos(angle),
        y: CANVAS.cy + ring.ry * Math.sin(angle),
      });
    });
  }
  return { nodes, rings, width: CANVAS.w, height: CANVAS.h };
});

const nodeById = computed(() => new Map(layout.value.nodes.map(n => [n.id, n])));

/** 选中节点：只保留邻接边并高亮邻居 */
const selection = computed(() => {
  const sel = props.selectedId ?? null;
  const neighbors = new Set<string>();
  const edges: any[] = [];
  for (const e of props.graph?.edges ?? []) {
    const ids: string[] = e.between ?? [e.from, e.to].filter(Boolean);
    if (sel) {
      if (!ids.includes(sel)) continue;
      ids.forEach(x => { if (x !== sel) neighbors.add(x); });
    } else if (typeFilter.value !== "all" && e.type !== typeFilter.value) {
      continue;
    }
    edges.push(e);
  }
  return { sel, neighbors, edges };
});

const drawnEdges = computed(() =>
  selection.value.edges.map((e: any) => {
    const ids: string[] = e.between ?? [e.from, e.to].filter(Boolean);
    if (ids.length !== 2) return null;
    const a = nodeById.value.get(ids[0]);
    const b = nodeById.value.get(ids[1]);
    if (!a || !b) return null;
    return { edge: e, x1: a.x, y1: a.y, x2: b.x, y2: b.y };
  }).filter(Boolean));

const visibleNodes = computed(() => {
  const { sel, neighbors } = selection.value;
  return layout.value.nodes
    .filter(n => {
      if (typeFilter.value === "all" || sel) {
        // 孤立节点仅在显式要求时参与渲染（选中节点永远保留）
        if (n.degree === 0 && !showIsolated.value && !sel) return false;
        return true;
      }
      if (n.type === "predicate") return typeFilter.value === "rescues";
      return (props.graph?.edges ?? []).some((e: any) =>
        e.type === typeFilter.value && (e.between ?? []).includes(n.id));
    })
    .map(n => ({
      ...n,
      selected: n.id === sel,
      highlighted: sel ? neighbors.has(n.id) : false,
      faded: sel ? !(n.id === sel || neighbors.has(n.id)) : false,
    }));
});

const totalNodes = computed(() =>
  props.graph?.nodes?.length ?? layout.value.nodes.length);
const isolatedCount = computed(() => totalNodes.value - connectedCount.value);

/** 标签宽度估算：CJK 按 1em、拉丁与数字按 0.56em（等宽近似的显示宽度） */
function labelWidth(text: string, fontSize = LABEL_FS): number {
  let w = 0;
  for (const ch of text) {
    w += /[\u3400-\u9fff\uf900-\ufaff]/.test(ch) ? fontSize : fontSize * 0.56;
  }
  return w;
}

function shortLabel(n: any): string {
  const raw = n.label ? String(n.label) : String(n.id);
  return raw.length > 13 ? `${raw.slice(0, 13)}…` : raw;
}

/** 让标签不出画布：靠近左右边缘时向内平移 */
function labelDx(n: any, text: string): number {
  const half = labelWidth(text, LABEL_FS) / 2 + 6;
  const clamped = Math.min(Math.max(n.x, half), CANVAS.w - half);
  return clamped - n.x;
}

/**
 * 贪心避让：按优先级依次尝试放置标签，与已放置的标签重叠则跳过。
 * 优先级：选中 > 悬停 > 有关系 > 其余。跳过不等于丢失——
 * 悬停/点选/「全部标签」都会重新显示。
 */
const shownLabels = computed<Set<string>>(() => {
  const list = visibleNodes.value;
  if (allLabels.value) return new Set(list.map(n => n.id));

  /**
   * 节点很多时，孤立的「珠链」节点不参与标注——它们没有边，
   * 标签只会把图糊掉；悬停仍会给出完整提示，勾选「全部标签」可强制显示。
   */
  const crowded = list.length > 60;
  const eligible = crowded
    ? list.filter(n => n.degree > 0 || n.selected || n.id === hoverId.value)
    : list;

  const fs = LABEL_FS;
  const priority = [...eligible].sort((a, b) => {
    if (a.selected !== b.selected) return a.selected ? -1 : 1;
    if ((a.id === hoverId.value) !== (b.id === hoverId.value)) return a.id === hoverId.value ? -1 : 1;
    if ((a.degree > 0) !== (b.degree > 0)) return a.degree > 0 ? -1 : 1;
    if (a.degree !== b.degree) return b.degree - a.degree;
    return String(a.id).localeCompare(String(b.id));
  });

  const kept: { x1: number; y1: number; x2: number; y2: number }[] = [];
  const shown = new Set<string>();
  for (const n of priority) {
    const text = shortLabel(n);
    const w = labelWidth(text, fs);
    const y = n.y + (n.type === "predicate" ? 15 : 18);
    const box = { x1: n.x - w / 2 - 2.5, y1: y - fs, x2: n.x + w / 2 + 2.5, y2: y + 3 };
    const hit = kept.some(k =>
      !(box.x2 < k.x1 || box.x1 > k.x2 || box.y2 < k.y1 || box.y1 > k.y2));
    if (hit) continue;
    kept.push(box);
    shown.add(n.id);
  }
  return shown;
});

/** 悬停节点完整标签（12px 以内不截断时直接复用） */
const hoveredNode = computed(() =>
  hoverId.value ? nodeById.value.get(hoverId.value) ?? null : null);

const viewBox = computed(() =>
  `${view.value.x} ${view.value.y} ${view.value.w} ${view.value.h}`);

function onWheel(e: WheelEvent) {
  const v = view.value;
  const k = e.deltaY > 0 ? 1.12 : 1 / 1.12;
  const nw = Math.min(2600, Math.max(200, v.w * k));
  const ratio = nw / v.w;
  const rect = (e.currentTarget as SVGElement).getBoundingClientRect();
  const mx = v.x + ((e.clientX - rect.left) / rect.width) * v.w;
  const my = v.y + ((e.clientY - rect.top) / rect.height) * v.h;
  view.value = { x: mx - (mx - v.x) * ratio, y: my - (my - v.y) * ratio, w: nw, h: v.h * ratio };
}

function onDown(e: PointerEvent) {
  drag = { px: e.clientX, py: e.clientY };
  moved.value = false;
  (e.currentTarget as Element).setPointerCapture?.(e.pointerId);
}
function onMove(e: PointerEvent) {
  if (!drag) return;
  const rect = (e.currentTarget as SVGElement).getBoundingClientRect();
  const dx = ((e.clientX - drag.px) / rect.width) * view.value.w;
  const dy = ((e.clientY - drag.py) / rect.height) * view.value.h;
  if (Math.abs(e.clientX - drag.px) + Math.abs(e.clientY - drag.py) > 3) moved.value = true;
  view.value = { ...view.value, x: view.value.x - dx, y: view.value.y - dy };
  drag = { px: e.clientX, py: e.clientY };
}
function onUp() { drag = null; }

function clickNode(id: string) {
  if (moved.value) return;
  emit("select", id === props.selectedId ? null : id);
}

function reset() {
  view.value = { x: 0, y: 0, w: CANVAS.w, h: CANVAS.h };
  moved.value = false;
}

function zoom(factor: number) {
  const current = view.value;
  const width = Math.min(2600, Math.max(200, current.w * factor));
  const height = current.h * width / current.w;
  view.value = { x: current.x + (current.w - width) / 2, y: current.y + (current.h - height) / 2, w: width, h: height };
}

function pan(horizontal: number, vertical: number) {
  view.value = { ...view.value, x: view.value.x + horizontal * view.value.w * .12, y: view.value.y + vertical * view.value.h * .12 };
}

function selectWithKeyboard(id: string) {
  moved.value = false;
  clickNode(id);
}

function colorOf(n: any): string {
  if (n.type === "predicate") return DOMAIN_COLOR.predicate;
  return DOMAIN_COLOR[n.domain] ?? DOMAIN_COLOR.default;
}

function edgeStroke(type: string): string {
  if (type === "conflict") return "var(--wx-fire)";
  if (type === "rescues") return "var(--wx-wood)";
  if (type === "school-conflict") return "var(--wx-earth)";
  return "var(--ink-400)";
}

defineExpose({ reset });
</script>

<template>
  <div class="graph-shell">
    <div class="graph-toolbar">
      <span class="mono" title="冲突图节点总数（含无关联条目）">节点 {{ totalNodes }}</span>
      <span class="mono">边 {{ props.graph?.edgeCount ?? (props.graph?.edges?.length ?? 0) }}</span>
      <span class="mono" title="有边的节点数 / 无任何边的孤立节点数">
        已连接 {{ connectedCount }} · 孤立 {{ isolatedCount }}
      </span>
      <span class="grow" />
      <label class="row" style="gap: var(--s-2)">
        <span class="note">边型</span>
        <select v-model="typeFilter" style="width: auto; min-width: 128px">
          <option value="all">全部</option>
          <option v-for="t in edgeTypes" :key="t" :value="t">{{ edgeTypeCn(t) }}</option>
        </select>
      </label>
      <label class="row" style="gap: 5px" :title="`无任何边的 ${isolatedCount} 条规则`">
        <input v-model="showIsolated" type="checkbox" />
        <span class="note">含孤立节点</span>
      </label>
      <label class="row" style="gap: 5px">
        <input v-model="allLabels" type="checkbox" />
        <span class="note">全部标签</span>
      </label>
      <button class="btn-sm" type="button" @click="reset">重置视图</button>
    </div>

    <div class="graph-controls" role="group" aria-label="图谱视图控制">
      <button class="btn-sm" type="button" @click="zoom(1 / 1.3)">放大</button>
      <button class="btn-sm" type="button" @click="zoom(1.3)">缩小</button>
      <span class="note-sm">平移</span>
      <button class="btn-sm" type="button" aria-label="向左平移" @click="pan(-1, 0)">左</button>
      <button class="btn-sm" type="button" aria-label="向右平移" @click="pan(1, 0)">右</button>
      <button class="btn-sm" type="button" aria-label="向上平移" @click="pan(0, -1)">上</button>
      <button class="btn-sm" type="button" aria-label="向下平移" @click="pan(0, 1)">下</button>
    </div>
    <div class="graph-stage">
      <svg
        :viewBox="viewBox"
        class="graph-svg"
        role="group"
        aria-label="规则冲突与救应关系图"
        @wheel.prevent="onWheel"
        @pointerdown="onDown"
        @pointermove="onMove"
        @pointerup="onUp"
        @pointerleave="onUp"
      >
        <!-- 环：domain 分层的可视化，非装饰 -->
        <ellipse
          v-for="(r, i) in layout.rings" :key="`ring${i}`"
          :cx="CANVAS.cx" :cy="CANVAS.cy" :rx="r.rx" :ry="r.ry"
          fill="none" stroke="var(--bronze-300)" stroke-width="1"
        />
        <line
          v-for="(e, i) in drawnEdges" :key="`e${i}`"
          :x1="e!.x1" :y1="e!.y1" :x2="e!.x2" :y2="e!.y2"
          :stroke="edgeStroke(e!.edge.type)"
          :stroke-width="e!.edge.type === 'conflict' ? 2 : 1.5"
          :stroke-dasharray="e!.edge.type === 'school-conflict' ? '5 4' : e!.edge.type === 'rescues' ? '2 3' : undefined"
          opacity="0.72"
        />
        <g
          v-for="n in visibleNodes" :key="n.id"
          class="graph-node"
          role="button"
          tabindex="0"
          :aria-label="`${n.id} ${n.label ?? ''}`"
          :aria-pressed="n.selected"
          :class="{ 'is-selected': n.selected, 'is-isolated': n.degree === 0 }"
          :transform="`translate(${n.x},${n.y})`"
          :opacity="n.faded ? 0.24 : n.degree === 0 ? 0.72 : 1"
          @click="clickNode(n.id)"
          @keydown.enter.prevent="selectWithKeyboard(n.id)"
          @keydown.space.prevent="selectWithKeyboard(n.id)"
          @focus="hoverId = n.id"
          @blur="hoverId = null"
          @pointerenter="hoverId = n.id"
          @pointerleave="hoverId = null"
        >
          <circle
            :r="n.type === 'predicate' ? 5 : n.selected ? 11 : n.degree > 0 ? 8 : 6"
            :fill="colorOf(n)"
            :stroke="n.selected ? 'var(--ink-900)' : 'var(--ink-surface)'"
            :stroke-width="n.selected ? 2.5 : 1.6"
          />
          <text
            v-if="shownLabels.has(n.id) || n.selected"
            :x="labelDx(n, shortLabel(n))"
            :y="n.type === 'predicate' ? 15 : 18"
            text-anchor="middle"
            class="graph-label"
          >{{ shortLabel(n) }}</text>
        </g>
      </svg>

      <div class="graph-hint">滚轮缩放 · 拖拽平移 · 悬停看标签 · 点击节点聚焦邻居</div>

      <!-- 悬停提示：被避让掉的标签在这里完整显示 -->
      <div v-if="hoveredNode" class="graph-tip">
        <span class="graph-tip-id mono">{{ hoveredNode.id }}</span>
        <span class="graph-tip-label">{{ hoveredNode.label ?? hoveredNode.id }}</span>
        <span class="graph-tip-meta">
          {{ domainCn(hoveredNode.type === "predicate" ? "predicate" : hoveredNode.domain) }}
          · 度数 {{ hoveredNode.degree }}
        </span>
      </div>
    </div>

    <!-- 折叠说明：数字常显，避免把"稀疏"误读成"密集" -->
    <p v-if="!showIsolated && isolatedCount > 0" class="graph-fold-line">
      另有 <b>{{ isolatedCount }}</b> 条在冲突图中无任何边（占 {{ totalNodes }} 条中的
      {{ Math.round((isolatedCount / Math.max(1, totalNodes)) * 100) }}%），
      默认折叠以免把稀疏读成密集；勾选「含孤立节点」可全部展开，不剔除任何数据。
    </p>

    <div class="graph-legend">
      <span
        v-for="r in layout.rings" :key="r.key"
        class="graph-legend-item"
      >
        <span class="graph-legend-dot" :style="{ background: DOMAIN_COLOR[r.key] ?? DOMAIN_COLOR.default }" />
        {{ domainCn(r.key) }} <span class="mono">{{ r.total }}</span>
      </span>
      <span class="grow" />
      <span class="graph-legend-item">
        <span class="graph-legend-line" :style="{ borderColor: edgeStroke('conflict') }" />{{ edgeTypeCn("conflict") }}
      </span>
      <span class="graph-legend-item">
        <span class="graph-legend-line" :style="{ borderColor: edgeStroke('rescues') }" />{{ edgeTypeCn("rescues") }}
      </span>
      <span class="graph-legend-item">
        <span class="graph-legend-line" :style="{ borderColor: edgeStroke('school-conflict') }" />{{ edgeTypeCn("school-conflict") }}
      </span>
    </div>
  </div>
</template>
