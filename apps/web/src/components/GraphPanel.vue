<script setup lang="ts">
/**
 * GraphPanel — 规则 / 冲突 / 救应 / 流派冲突 关系图。
 *
 * 边界：
 *  - 节点与边完全来自后端 /knowledge/graph（conflict-graph.json）；
 *  - 环形布局是**确定性展示布局**（规则按 domain 分环），不含任何推理；
 *  - 未选中节点时不隐藏任何节点，选中后弱化非邻居（可随时取消）。
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
const view = ref({ x: 0, y: 0, w: 860, h: 620 });
const moved = ref(false);
let drag: { px: number; py: number } | null = null;

const CANVAS = { w: 860, h: 620, cx: 430, cy: 310 };

/** domain → 环半径（确定性；order 固定，保证同一数据总得到同一张图） */
const RING_ORDER = ["predicate", "event", "temporal", "tiaohou"] as const;
const RING_RADIUS: Record<string, number> = { predicate: 84, event: 178, temporal: 268, tiaohou: 348 };

const DOMAIN_COLOR: Record<string, string> = {
  event: "#a8402c",     /* 事件域 · 朱砂系 */
  temporal: "#2c4a5e",  /* 岁运域 · 青黛系 */
  tiaohou: "#2f6448",   /* 调候域 · 木系 */
  predicate: "#7a4a12", /* 救应谓词 · 赭石系 */
  default: "#727a82",
};

const layout = computed(() => {
  const g = props.graph;
  if (!g) return { nodes: [] as any[], width: CANVAS.w, height: CANVAS.h };
  const buckets: Record<string, any[]> = {};
  for (const n of g.nodes ?? []) {
    const ring = n.type === "predicate" ? "predicate" : (n.domain ?? "event");
    (buckets[ring] ??= []).push(n);
  }
  const nodes: any[] = [];
  for (const [ring, list] of Object.entries(buckets)) {
    // 稳定排序：按 id 保证同一输入总得到同一布局
    const sorted = [...list].sort((a, b) => String(a.id).localeCompare(String(b.id)));
    const radius = RING_RADIUS[ring] ?? 268;
    sorted.forEach((n, i) => {
      const angle = (2 * Math.PI * i) / Math.max(1, sorted.length) - Math.PI / 2;
      nodes.push({
        ...n, ring,
        x: CANVAS.cx + radius * Math.cos(angle),
        y: CANVAS.cy + radius * Math.sin(angle),
      });
    });
  }
  return { nodes, width: CANVAS.w, height: CANVAS.h };
});

const nodeById = computed(() => new Map(layout.value.nodes.map(n => [n.id, n])));

const edgeTypes = computed<string[]>(() => {
  const g = props.graph;
  if (!g) return [];
  const declared = Object.keys(g.edgeTypes ?? {});
  return declared.length ? declared : ["conflict", "rescues", "school-conflict"];
});

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
      if (typeFilter.value === "all" || sel) return true;
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

function colorOf(n: any): string {
  if (n.type === "predicate") return DOMAIN_COLOR.predicate;
  return DOMAIN_COLOR[n.domain] ?? DOMAIN_COLOR.default;
}

function shortLabel(n: any): string {
  const raw = n.label ? String(n.label) : String(n.id);
  return raw.length > 11 ? `${raw.slice(0, 11)}…` : raw;
}

function edgeStroke(type: string): string {
  if (type === "conflict") return "#8d2c22";
  if (type === "rescues") return "#2f6448";
  if (type === "school-conflict") return "#7a4a12";
  return "#98a0a7";
}

defineExpose({ reset });
</script>

<template>
  <div class="graph-shell">
    <div class="graph-toolbar">
      <span class="mono">节点 {{ props.graph?.nodeCount ?? layout.nodes.length }}</span>
      <span class="mono">边 {{ props.graph?.edgeCount ?? (props.graph?.edges?.length ?? 0) }}</span>
      <span class="grow" />
      <label class="row row-3" style="gap: var(--s-2)">
        <span class="note">边型</span>
        <select v-model="typeFilter" style="width: auto; min-width: 132px">
          <option value="all">全部</option>
          <option v-for="t in edgeTypes" :key="t" :value="t">{{ t }}</option>
        </select>
      </label>
      <button class="btn-sm" type="button" @click="reset">重置视图</button>
    </div>

    <div class="graph-stage">
      <svg
        :viewBox="viewBox"
        class="graph-svg"
        role="img"
        aria-label="规则冲突与救应关系图"
        @wheel.prevent="onWheel"
        @pointerdown="onDown"
        @pointermove="onMove"
        @pointerup="onUp"
        @pointerleave="onUp"
      >
        <!-- 环：可视化 domain 分层，非装饰 -->
        <circle
          v-for="(r, i) in [84, 178, 268, 348]"
          :key="`ring${i}`"
          :cx="CANVAS.cx" :cy="CANVAS.cy" :r="r"
          fill="none" stroke="#e8e1d1" stroke-width="1"
        />
        <line
          v-for="(e, i) in drawnEdges" :key="`e${i}`"
          :x1="e!.x1" :y1="e!.y1" :x2="e!.x2" :y2="e!.y2"
          :stroke="edgeStroke(e!.edge.type)"
          :stroke-width="e!.edge.type === 'conflict' ? 1.8 : 1.4"
          :stroke-dasharray="e!.edge.type === 'school-conflict' ? '5 4' : e!.edge.type === 'rescues' ? '2 3' : undefined"
          opacity="0.6"
        />
        <g
          v-for="n in visibleNodes" :key="n.id"
          class="graph-node"
          :class="{ 'is-selected': n.selected }"
          :transform="`translate(${n.x},${n.y})`"
          :opacity="n.faded ? 0.28 : 1"
          @click="clickNode(n.id)"
        >
          <circle
            :r="n.type === 'predicate' ? 6 : n.selected ? 11 : 8.5"
            :fill="colorOf(n)"
            :stroke="n.selected ? '#14171a' : '#fdfbf6'"
            :stroke-width="n.selected ? 2.4 : 1.8"
          />
          <text :y="n.type === 'predicate' ? 20 : 22" text-anchor="middle" class="graph-label">
            {{ shortLabel(n) }}
          </text>
        </g>
      </svg>
      <div class="graph-hint">滚轮缩放 · 拖拽平移 · 点击节点聚焦邻居</div>
    </div>

    <div class="graph-legend">
      <span class="graph-legend-item">
        <span class="graph-legend-dot" :style="{ background: DOMAIN_COLOR.event }" />事件域
      </span>
      <span class="graph-legend-item">
        <span class="graph-legend-dot" :style="{ background: DOMAIN_COLOR.temporal }" />岁运域
      </span>
      <span class="graph-legend-item">
        <span class="graph-legend-dot" :style="{ background: DOMAIN_COLOR.tiaohou }" />调候域
      </span>
      <span class="graph-legend-item">
        <span class="graph-legend-dot" :style="{ background: DOMAIN_COLOR.predicate }" />救应谓词
      </span>
      <span class="graph-legend-item">
        <span class="graph-legend-line" :style="{ borderColor: edgeStroke('conflict') }" />conflict
      </span>
      <span class="graph-legend-item">
        <span class="graph-legend-line" :style="{ borderColor: edgeStroke('rescues') }" />rescues
      </span>
      <span class="graph-legend-item">
        <span class="graph-legend-line" :style="{ borderColor: edgeStroke('school-conflict') }" />school-conflict
      </span>
    </div>
  </div>
</template>
