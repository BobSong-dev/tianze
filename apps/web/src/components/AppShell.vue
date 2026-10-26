<script setup lang="ts">
/**
 * AppShell — 应用外壳。
 *
 * 桌面端：左侧「研究路径」常驻（品牌 → 命盘指纹 → 分组导航 → 元信息），
 *         右侧为分析内容区；顶部条承担面包屑与全局动作（含 AI 入口）。
 * 移动端：侧栏变为抽屉，顶栏保留菜单按钮与 AI 入口。
 *
 * 纪律：导航项由上层传入，外壳不含任何命理语义。
 */
import { watch } from "vue";
import ParticleField from "./ParticleField.vue";

export interface NavItem {
  id: string;
  label: string;
  /** 等宽右侧小标（数量/规则数等） */
  meta?: string;
  /** 状态点：'on' | 'warn' | undefined */
  dot?: "on" | "warn";
}
export interface NavGroup {
  title: string;
  items: NavItem[];
}

const props = defineProps<{
  groups: NavGroup[];
  active: string;
  /** 侧栏命盘指纹（可选） */
  chart?: {
    pillars: { pos: string; stem: string; branch: string; isDm: boolean }[];
    dayMaster: string;
    meta?: string[];
  } | null;
  /** 面包屑 */
  crumbs?: string[];
  engineVersion?: string;
  analysisSchema?: string;
  /** 未选择命例时隐藏研究路径导航 */
  showNav?: boolean;
  /** 顶栏 AI 状态点 */
  aiDot?: "on" | "warn" | null;
}>();

const emit = defineEmits<{
  (e: "navigate", id: string): void;
  (e: "home"): void;
  (e: "configure-ai"): void;
}>();

/** 移动端抽屉开关（双向绑定，供外壳自己在导航后关闭） */
const sidebarOpen = defineModel<boolean>("sidebarOpen", { default: false });

watch(() => props.active, () => { sidebarOpen.value = false; });

/**
 * 抽屉打开时锁定页面滚动。
 * 抽屉是 fixed 定位，若底层页面仍可滚动，就会出现"抽屉在视口外"与
 * "背景内容跟着滚"的两类问题（桌面不受影响）。
 */
watch(sidebarOpen, (open) => {
  if (typeof document === "undefined") return;
  document.body.classList.toggle("is-drawer-open", open);
});

function go(id: string) {
  emit("navigate", id);
  sidebarOpen.value = false;
}
</script>

<template>
  <div class="app-shell">
    <!-- 移动端遮罩 -->
    <div v-if="sidebarOpen" class="sidebar-scrim" @click="sidebarOpen = false" />

    <aside class="app-sidebar" :class="{ 'is-open': sidebarOpen }">
      <button class="brand-block" type="button" @click="emit('home')">
        <span class="brand-seal" aria-hidden="true">泽</span>
        <span class="brand-text">
          <span class="brand-name">天泽</span>
          <span class="brand-latin">TIANZE</span>
        </span>
      </button>

      <!-- 命盘指纹：四柱 + 日主 -->
      <div v-if="props.chart" class="side-chart">
        <div class="side-chart-head">
          <span class="side-chart-label">命盘</span>
          <span class="side-chart-dm">{{ props.chart.dayMaster }}</span>
        </div>
        <div class="side-chart-gz">
          <div
            v-for="(p, i) in props.chart.pillars"
            :key="i"
            class="side-chart-cell"
            :class="{ 'is-dm': p.isDm }"
          >
            <span class="side-chart-pos">{{ p.pos }}</span>
            <span class="side-chart-glyph">{{ p.stem }}</span>
            <span class="side-chart-glyph">{{ p.branch }}</span>
          </div>
        </div>
        <div v-if="props.chart.meta?.length" class="side-chart-meta">
          <span v-for="m in props.chart.meta" :key="m">{{ m }}</span>
        </div>
      </div>

      <!-- 研究路径 -->
      <nav v-if="props.groups && props.groups.length" class="side-nav" aria-label="研究路径">
        <div v-for="grp in props.groups" :key="grp.title" class="side-nav-group">
          <div class="side-nav-title">{{ grp.title }}</div>
          <button
            v-for="(it, i) in grp.items"
            :key="it.id"
            type="button"
            class="side-nav-item"
            :class="{ 'is-active': props.active === it.id }"
            :aria-current="props.active === it.id ? 'page' : undefined"
            @click="go(it.id)"
          >
            <span class="side-nav-idx">{{ String(i + 1).padStart(2, "0") }}</span>
            <span class="side-nav-label">{{ it.label }}</span>
            <span v-if="it.meta" class="side-nav-count">{{ it.meta }}</span>
            <span v-if="it.dot" class="side-nav-dot" :class="`is-${it.dot}`" />
          </button>
        </div>
      </nav>

      <div class="side-foot">
        <div class="side-foot-row">
          <span>引擎</span>
          <span class="mono">{{ props.engineVersion ?? "—" }}</span>
        </div>
        <div class="side-foot-row">
          <span>分析 schema</span>
          <span class="mono">{{ props.analysisSchema ?? "—" }}</span>
        </div>
        <div class="side-foot-row" style="margin-top: var(--s-2)">
          <button class="btn-link" type="button" @click="emit('configure-ai')">AI 设置</button>
          <span>研究用途</span>
        </div>
      </div>
    </aside>

    <div class="app-main">
      <ParticleField variant="dust" fit="viewport" class="app-dust" />
      <header class="app-topbar">
        <button
          class="btn-ghost sidebar-toggle"
          type="button"
          aria-label="打开研究路径"
          @click="sidebarOpen = !sidebarOpen"
        >
          <span aria-hidden="true">☰</span>
        </button>

        <nav class="crumb" aria-label="位置">
          <button class="crumb-root" type="button" @click="emit('home')">天泽</button>
          <template v-for="(c, i) in props.crumbs ?? []" :key="c">
            <span class="crumb-sep" aria-hidden="true">/</span>
            <span :class="i === (props.crumbs?.length ?? 0) - 1 ? 'crumb-current' : ''">{{ c }}</span>
          </template>
        </nav>

        <div class="app-topbar-spacer" />
        <div class="topbar-actions">
          <slot name="actions" />
          <button class="btn-ghost ai-entry" type="button" @click="emit('configure-ai')">
            <span class="side-nav-dot" :class="props.aiDot ? `is-${props.aiDot}` : ''" style="margin-right: 6px" />
            <span>AI 设置</span>
          </button>
        </div>
      </header>

      <main class="app-content" id="main">
        <div class="content-inner" :class="{ 'is-wide': $slots.default && props.showNav === false }">
          <slot />
        </div>
      </main>
    </div>
  </div>
</template>
