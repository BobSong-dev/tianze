<script setup lang="ts">
import { computed, ref } from "vue";
import BirthIntake from "./BirthIntake.vue";
import UiIcon from "../components/UiIcon.vue";
import type { BirthForm } from "../composables/useTianze";

const props = defineProps<{
  birth: BirthForm;
  loading: boolean;
  error: string;
  engineVersion?: string;
}>();

const emit = defineEmits<{
  (e: "submit"): void;
  (e: "configure-ai"): void;
}>();

interface SolarTerm {
  name: string;
  kind: "jie" | "qi";
  branch: string;
  season: "春" | "夏" | "秋" | "冬";
  note: string;
}

/** 二十四节气（顺序即历法顺序）；jie=节（月建之界），qi=气（中气） */
const SOLAR_TERMS: SolarTerm[] = [
  { name: "立春", kind: "jie", branch: "寅", season: "春", note: "岁首寅月建始，年柱与月柱交接之界" },
  { name: "雨水", kind: "qi",  branch: "寅", season: "春", note: "寅月中气，东风解冻" },
  { name: "惊蛰", kind: "jie", branch: "卯", season: "春", note: "卯月建始，雷动蛰起" },
  { name: "春分", kind: "qi",  branch: "卯", season: "春", note: "卯月中气，昼夜均平" },
  { name: "清明", kind: "jie", branch: "辰", season: "春", note: "辰月建始，气清景明" },
  { name: "谷雨", kind: "qi",  branch: "辰", season: "春", note: "辰月中气，季春之末" },
  { name: "立夏", kind: "jie", branch: "巳", season: "夏", note: "巳月建始，万物繁茂" },
  { name: "小满", kind: "qi",  branch: "巳", season: "夏", note: "巳月中气，物致于此小得盈满" },
  { name: "芒种", kind: "jie", branch: "午", season: "夏", note: "午月建始，有芒之谷可稼种" },
  { name: "夏至", kind: "qi",  branch: "午", season: "夏", note: "午月中气，阳极阴生之枢" },
  { name: "小暑", kind: "jie", branch: "未", season: "夏", note: "未月建始，季夏之始" },
  { name: "大暑", kind: "qi",  branch: "未", season: "夏", note: "未月中气，炎暑至极" },
  { name: "立秋", kind: "jie", branch: "申", season: "秋", note: "申月建始，凉风至、金气始肃" },
  { name: "处暑", kind: "qi",  branch: "申", season: "秋", note: "申月中气，暑气至此而止" },
  { name: "白露", kind: "jie", branch: "酉", season: "秋", note: "酉月建始，阴气渐重" },
  { name: "秋分", kind: "qi",  branch: "酉", season: "秋", note: "酉月中气，阴阳相半" },
  { name: "寒露", kind: "jie", branch: "戌", season: "秋", note: "戌月建始，露气寒冷" },
  { name: "霜降", kind: "qi",  branch: "戌", season: "秋", note: "戌月中气，气肃而凝" },
  { name: "立冬", kind: "jie", branch: "亥", season: "冬", note: "亥月建始，水始冰、藏伏之始" },
  { name: "小雪", kind: "qi",  branch: "亥", season: "冬", note: "亥月中气，寒未深而雪未大" },
  { name: "大雪", kind: "jie", branch: "子", season: "冬", note: "子月建始，仲冬寒盛" },
  { name: "冬至", kind: "qi",  branch: "子", season: "冬", note: "子月中气，阴极阳生之始" },
  { name: "小寒", kind: "jie", branch: "丑", season: "冬", note: "丑月建始，季冬初寒" },
  { name: "大寒", kind: "qi",  branch: "丑", season: "冬", note: "丑月中气，岁终待春" },
];

const MONTHS_BRANCH = ["寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑"];
/** 先天八卦方位意象（用于内环天象仪轨刻纹） */
const BAGUA = [
  { glyph: "☰", name: "乾" },
  { glyph: "☴", name: "巽" },
  { glyph: "☵", name: "坎" },
  { glyph: "☶", name: "艮" },
  { glyph: "☷", name: "坤" },
  { glyph: "☳", name: "震" },
  { glyph: "☲", name: "离" },
  { glyph: "☱", name: "兑" },
];

const SEASON_ANCHORS = [
  { label: "春 · 立春", name: "立春" },
  { label: "夏 · 立夏", name: "立夏" },
  { label: "秋 · 立秋", name: "立秋" },
  { label: "冬 · 立冬", name: "立冬" },
];

const activeTermName = ref<string>("立春");
const activeIndex = computed(() =>
  Math.max(0, SOLAR_TERMS.findIndex(t => t.name === activeTermName.value)));
const activeTerm = computed(() => SOLAR_TERMS[activeIndex.value] ?? SOLAR_TERMS[0]);
const pointerDeg = computed(() => activeIndex.value * 15);

/** 72 道周天精细刻度（5° 一刻，对应古代七十二候意象） */
const degreeTicks = computed(() =>
  Array.from({ length: 72 }, (_, i) => {
    const a = (i * 5 - 90) * (Math.PI / 180);
    const major = i % 3 === 0;
    const r1 = major ? 190 : 194;
    const r2 = 200;
    return {
      major,
      x1: 210 + r1 * Math.cos(a),
      y1: 210 + r1 * Math.sin(a),
      x2: 210 + r2 * Math.cos(a),
      y2: 210 + r2 * Math.sin(a),
    };
  }));

/** 浑天罗盘 SVG 坐标计算（中心 210, 210） */
const astrolabeTerms = computed(() =>
  SOLAR_TERMS.map((t, i) => {
    const angle = (i * 15 - 90) * (Math.PI / 180);
    const rInner = 142;
    const rDot = 148;
    const rText = 171;
    const rOuter = 190;
    return {
      ...t,
      index: i,
      x1: 210 + rInner * Math.cos(angle),
      y1: 210 + rInner * Math.sin(angle),
      x2: 210 + rOuter * Math.cos(angle),
      y2: 210 + rOuter * Math.sin(angle),
      dx: 210 + rDot * Math.cos(angle),
      dy: 210 + rDot * Math.sin(angle),
      tx: 210 + rText * Math.cos(angle),
      ty: 210 + rText * Math.sin(angle),
    };
  }));

const astrolabeBranches = computed(() =>
  MONTHS_BRANCH.map((b, i) => {
    const angle = (i * 30 + 7.5 - 90) * (Math.PI / 180);
    const r = 120;
    return {
      branch: b,
      x: 210 + r * Math.cos(angle),
      y: 210 + r * Math.sin(angle),
    };
  }));

const astrolabeBagua = computed(() =>
  BAGUA.map((g, i) => {
    const angle = (i * 45 - 90) * (Math.PI / 180);
    const r = 82;
    return {
      ...g,
      x: 210 + r * Math.cos(angle),
      y: 210 + r * Math.sin(angle),
    };
  }));

/** 八卦外框八边形顶点 */
const octagonPoints = computed(() =>
  Array.from({ length: 8 }, (_, i) => {
    const a = (i * 45 + 22.5 - 90) * (Math.PI / 180);
    return `${(210 + 98 * Math.cos(a)).toFixed(1)},${(210 + 98 * Math.sin(a)).toFixed(1)}`;
  }).join(" "));

interface Capability {
  idx: string;
  seal: string;
  name: string;
  desc: string;
  keys: string[];
}

const CAPABILITIES: Capability[] = [
  {
    idx: "壹",
    seal: "历",
    name: "历法校度",
    desc: "可核对出生地时区、节气交界和晚子时流派对排盘的影响。",
    keys: ["节气", "时区", "晚子时"],
  },
  {
    idx: "贰",
    seal: "局",
    name: "四柱结构",
    desc: "旺衰三法并列、月令与通根透干、格局与调候、刑冲合害破与合化状态。分歧如实保留。",
    keys: ["旺衰", "格局", "调候", "关系"],
  },
  {
    idx: "叁",
    seal: "运",
    name: "岁运星轨",
    desc: "大运、流年、流月、流日逐层展开，并以状态回放呈现每一层引入或移除了什么。",
    keys: ["大运", "流年", "差值", "回放"],
  },
  {
    idx: "肆",
    seal: "典",
    name: "典籍溯源",
    desc: "每条判断可展开到规则、古籍出处与原文页码；规则图与命例索引可反向检索。",
    keys: ["规则", "引文", "命例", "溯源"],
  },
];

const STATUS_LEGEND = [
  { code: "candidate", term: "候选", raw: "CANDIDATE", desc: "满足部分结构条件，需进一步复核——不是结论。" },
  { code: "likely", term: "倾向支持", raw: "LIKELY", desc: "支持证据占优，仍非确定性判断。" },
  { code: "disputed", term: "两说并存", raw: "DISPUTED", desc: "方法或流派存在分歧，两说并列，工具不代为裁决。" },
  { code: "blocked", term: "阻断", raw: "BLOCKED", desc: "存在明确阻断条件，该结构不成立——并给出「为什么不成立」。" },
  { code: "unresolved", term: "待定", raw: "UNRESOLVED", desc: "证据不足，保持未判定状态而非猜测。" },
  { code: "experimental", term: "实验性", raw: "EXPERIMENTAL", desc: "岁运参与该计算存在流派分歧，仅作参考。" },
];

function toIntake() {
  document.getElementById("intake")?.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth", block: "start" });
  document.querySelector<HTMLInputElement>('#intake input[type="date"]')?.focus({ preventScroll: true });
}
</script>

<template>
  <div class="home">
    <header class="home-top">
      <a class="brand-block" href="#top" style="border: none; padding: 0; width: auto">
        <span class="brand-seal" aria-hidden="true">泽</span>
        <span class="brand-text">
          <span class="brand-name">天泽</span>
          <span class="brand-latin">TIANZE · 观象研究室</span>
        </span>
      </a>
      <nav class="home-nav" aria-label="首页导航"><a href="#intake">排盘研究</a><a href="#research">研究路径</a><a href="#principles">方法与边界</a></nav>
      <div class="topbar-actions">
        <button class="btn-ghost" type="button" @click="emit('configure-ai')">AI 设置</button>
        <button class="btn-primary btn-sm" type="button" @click="toIntake">开始排盘</button>
      </div>
    </header>

    <!-- 题头：玄夜天幕 · 观象台 -->
    <main id="main" tabindex="-1">
    <section class="home-hero" id="top">
      <div class="home-hero-inner">
        <div class="home-hero-copy">
          <div class="home-eyebrow">
            <span class="eyebrow-line" aria-hidden="true" />
            <span>东方历法 · 四柱结构 · 典籍溯源</span>
          </div>

          <h1 class="home-title">
            观天时，<br /><span>明结构。</span>
          </h1>
          <p class="home-title-latin">A FIELD GUIDE TO TIME & PATTERN</p>

          <p class="home-lede">
            从一组出生时空，读懂四柱之间的联系。<br />
            让每一条结构判断，都有可以追溯的依据。
          </p>

          <div class="home-actions">
            <button class="btn-primary btn-lg" type="button" @click="toIntake">
              <UiIcon name="compass" />开始一次分析
            </button>
            <a class="home-secondary" href="#research">了解研究方法</a>
          </div>

          <dl class="home-facts">
            <div>
              <dt class="home-fact-key">排盘口径</dt>
              <dd class="home-fact-val">节气 · 时区 · 晚子时</dd>
            </div>
            <div>
              <dt class="home-fact-key">结构口径</dt>
              <dd class="home-fact-val">多方法并列，分歧不裁决</dd>
            </div>
            <div>
              <dt class="home-fact-key">输出性质</dt>
              <dd class="home-fact-val">结构分析，非吉凶或事件预测</dd>
            </div>
            <div v-if="props.engineVersion">
              <dt class="home-fact-key">推演引擎</dt>
              <dd class="home-fact-val mono">{{ props.engineVersion }}</dd>
            </div>
          </dl>
        </div>

        <!-- 钦天监太极八卦 × 二十四节气浑天罗盘 -->
        <aside class="calendar-panel" aria-label="二十四节气浑天罗盘">
          <div class="calendar-head">
            <span>二十四节气 · 月建图</span>
            <span class="calendar-head-tag">历法示意 / 非实时天象</span>
          </div>

          <!-- SVG 交互式太极八卦浑天罗盘 -->
          <div class="astrolabe-wrap">
            <svg viewBox="0 0 420 420" class="astrolabe-svg" aria-hidden="true">
              <defs>
                <radialGradient id="astroGlow" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stop-color="rgba(212, 175, 55, 0.16)" />
                  <stop offset="55%" stop-color="rgba(212, 175, 55, 0.04)" />
                  <stop offset="100%" stop-color="transparent" />
                </radialGradient>
                <linearGradient id="needleGold" x1="0%" y1="100%" x2="0%" y2="0%">
                  <stop offset="0%" stop-color="rgba(212, 175, 55, 0)" />
                  <stop offset="50%" stop-color="rgba(212, 175, 55, 0.45)" />
                  <stop offset="100%" stop-color="#fde68a" />
                </linearGradient>
              </defs>
              <circle cx="210" cy="210" r="204" fill="url(#astroGlow)" />

              <g class="astrolabe-orbit">
                <circle cx="210" cy="210" r="202" fill="none" stroke="rgba(212, 175, 55, 0.30)" stroke-width="0.9" stroke-dasharray="2 5" />
                <line
                  v-for="(tk, i) in degreeTicks"
                  :key="i"
                  :x1="tk.x1" :y1="tk.y1" :x2="tk.x2" :y2="tk.y2"
                  :stroke="tk.major ? 'rgba(212, 175, 55, 0.42)' : 'rgba(212, 175, 55, 0.16)'"
                  :stroke-width="tk.major ? 1.1 : 0.6"
                />
              </g>

              <!-- 司南金针：随选中节气平滑旋转 -->
              <g class="astrolabe-needle" :style="{ transform: `rotate(${pointerDeg}deg)` }">
                <line x1="210" y1="210" x2="210" y2="62" stroke="url(#needleGold)" stroke-width="1.8" />
                <polygon points="210,56 206,66 214,66" fill="#fde68a" />
              </g>

              <!-- 同心仪轨圈与八卦八边形 -->
              <circle cx="210" cy="210" r="190" fill="none" stroke="rgba(212, 175, 55, 0.28)" stroke-width="0.9" />
              <circle cx="210" cy="210" r="142" fill="none" stroke="rgba(212, 175, 55, 0.36)" stroke-width="1.1" />
              <circle cx="210" cy="210" r="102" fill="none" stroke="rgba(212, 175, 55, 0.25)" stroke-width="0.9" />
              <polygon :points="octagonPoints" fill="none" stroke="rgba(212, 175, 55, 0.24)" stroke-width="0.8" />

              <!-- 24 节气星标与文字 -->
              <g
                v-for="t in astrolabeTerms"
                :key="t.name"
                class="astrolabe-spoke"
                :class="{ 'is-jie': t.kind === 'jie', 'is-active': activeTermName === t.name }"
                @click="activeTermName = t.name"
              >
                <line
                  :x1="t.x1" :y1="t.y1" :x2="t.x2" :y2="t.y2"
                  :stroke="activeTermName === t.name ? '#fde68a' : t.kind === 'jie' ? 'rgba(212, 175, 55, 0.42)' : 'rgba(168, 160, 144, 0.14)'"
                  :stroke-width="activeTermName === t.name ? 1.5 : t.kind === 'jie' ? 0.9 : 0.5"
                />
                <circle
                  v-if="t.kind === 'jie' || activeTermName === t.name"
                  :cx="t.dx" :cy="t.dy"
                  :r="activeTermName === t.name ? 3.5 : 2.3"
                  :fill="activeTermName === t.name ? '#fde68a' : '#dc4c3a'"
                />
                <text
                  :x="t.tx" :y="t.ty + 3.6"
                  text-anchor="middle"
                  class="astrolabe-term-text"
                  :fill="activeTermName === t.name ? '#fde68a' : t.kind === 'jie' ? '#e5c973' : '#857d70'"
                  :font-weight="t.kind === 'jie' || activeTermName === t.name ? '700' : '400'"
                >{{ t.name }}</text>
              </g>

              <!-- 十二地支月建 -->
              <g v-for="b in astrolabeBranches" :key="b.branch">
                <text
                  :x="b.x" :y="b.y + 4.5"
                  text-anchor="middle"
                  class="astrolabe-branch-text"
                  :fill="activeTerm.branch === b.branch ? '#f87171' : '#c59b5f'"
                  :font-weight="activeTerm.branch === b.branch ? '700' : '500'"
                >{{ b.branch }}</text>
              </g>

              <!-- 先天八卦爻符 -->
              <g v-for="g in astrolabeBagua" :key="g.name">
                <text :x="g.x" :y="g.y + 4" text-anchor="middle" class="astrolabe-bagua-text">{{ g.glyph }}</text>
              </g>

              <!-- 盘心太极暗纹与实时节气铭牌 -->
              <circle cx="210" cy="210" r="54" fill="rgba(12, 15, 22, 0.92)" stroke="rgba(212, 175, 55, 0.58)" stroke-width="1.3" />
              <circle cx="210" cy="210" r="48" fill="none" stroke="rgba(212, 175, 55, 0.22)" stroke-width="0.7" />
              <path
                d="M210,162 A24,24 0 0,1 210,210 A24,24 0 0,0 210,258 A48,48 0 0,1 210,162 Z"
                fill="rgba(212, 175, 55, 0.06)"
              />
              <text x="210" y="203" text-anchor="middle" class="astrolabe-center-title">{{ activeTerm.name }}</text>
              <text x="210" y="224" text-anchor="middle" class="astrolabe-center-sub">
                {{ activeTerm.branch }}月 · {{ activeTerm.kind === 'jie' ? '节界' : '中气' }}
              </text>
            </svg>

            <!-- 四季锚点快切 -->
            <div class="astrolabe-seasons">
              <button
                v-for="s in SEASON_ANCHORS"
                :key="s.name"
                type="button"
                class="season-pill"
                :class="{ 'is-active': activeTermName === s.name }"
                :aria-pressed="activeTermName === s.name"
                @click="activeTermName = s.name"
              >{{ s.label }}</button>
            </div>

            <label class="calendar-select"><span>选择节气</span><select v-model="activeTermName" aria-label="选择节气"><option v-for="term in SOLAR_TERMS" :key="term.name" :value="term.name">{{ term.name }} · {{ term.branch }}月</option></select></label>
            <div class="astrolabe-readout" aria-live="polite">
              <span class="badge" :class="activeTerm.kind === 'jie' ? 'is-neg' : 'is-mute'">
                {{ activeTerm.kind === 'jie' ? '十二节 · 定月建' : '十二气 · 候流转' }}
              </span>
              <span class="astrolabe-readout-note">{{ activeTerm.note }}</span>
            </div>
          </div>

          <p class="calendar-foot">
            十二节分定月建。点选星盘、四季或节气菜单查看；排盘以精准交节时刻换月，不依公历初一。
          </p>
        </aside>
      </div>
    </section>

    <section class="home-method home-intake" id="intake">
      <div class="home-method-inner">
        <div class="intake-heading"><div><span class="eyebrow-text">开始研究 · BIRTH INFORMATION</span><h2>把时空，落在盘上。</h2></div><p>输入出生信息，建立你的研究起点。<br />历法口径可调整，分析依据可核对。</p></div>
        <BirthIntake :birth="props.birth" :loading="props.loading" :error="props.error" @submit="emit('submit')" />
      </div>
    </section>

    <section class="home-index" id="research">
      <div class="home-index-inner">
        <div class="sec-head">
          <div class="sec-head-top">
            <span class="sec-head-idx">研究路径</span>
            <h2>由时入局，循证而行。</h2>
          </div>
          <p class="sec-head-lede">
            历法、结构、岁运、典籍——四维互相印证，缺一则命理推演失其所据。
          </p>
        </div>

        <div class="cap-colonnade">
          <article v-for="c in CAPABILITIES" :key="c.idx" class="cap-stele">
            <div class="cap-top">
              <span class="cap-idx">{{ c.idx }}</span>
              <span class="cap-seal" aria-hidden="true">{{ c.seal }}</span>
            </div>
            <h3 class="cap-name">{{ c.name }}</h3>
            <p class="cap-desc">{{ c.desc }}</p>
            <div class="cap-keys">
              <span v-for="k in c.keys" :key="k">{{ k }}</span>
            </div>
          </article>
        </div>
      </div>
    </section>

    <!-- 研究定位与方法边界 -->
    <section class="home-method" id="principles">
      <div class="home-method-inner">
        <div class="sec-head">
          <div class="sec-head-top">
            <span class="sec-head-idx">律则</span>
            <h2>研究定位与方法边界</h2>
          </div>
          <p class="sec-head-lede">
            天泽既重中华传统命理学之深邃渊源，亦恪守可审计、可追溯之科学准则。以下边界全站共守。
          </p>
        </div>

        <div class="method-grid">
          <div class="method-item ornate-frame">
            <h4>不进行确定性人生预测</h4>
            <p>
              输出为干支结构、关系与候选状态的结构化描述，不给出吉凶、成败、疾病、
              婚姻等现实事件的断言。任何"必然发生"的表述都不是本工具的输出。
            </p>
          </div>
          <div class="method-item ornate-frame">
            <h4>分歧并列，不代为裁决</h4>
            <p>
              旺衰三法、流派注记、合化状态等存在学术分歧之处，工具并列呈现并标注
              来源层级，由研究者自行判断，而不是选一个"正确"答案。
            </p>
          </div>
          <div class="method-item ornate-frame">
            <h4>每条判断可回溯到依据</h4>
            <p>
              结论 → 规则编号 → 成立条件 → 古籍引文与页码。缺少依据的部分显式标注
              UNRESOLVED，而不是用文学化措辞掩盖。
            </p>
          </div>
          <div class="method-item ornate-frame">
            <h4>AI 只解释，不推导</h4>
            <p>
              AI 解读消费的是引擎已经算出的结构与证据，输出还需经事实一致性校验；
              引用偏差会明确警示，不替代引擎结果。不配置 AI 时，全部确定性分析仍在本机完成。
            </p>
          </div>
        </div>

        <div class="sec-sub" style="margin-top: var(--s-8)">
          <h3>状态词表</h3>
          <span class="sec-sub-note">全站受控词汇 · 悬停可见原码</span>
        </div>
        <div class="legend-ledger">
          <div v-for="s in STATUS_LEGEND" :key="s.raw" class="legend-row">
            <div class="legend-term">
              <span class="badge" :class="`st-${s.code}`" :title="s.raw">{{ s.term }}</span>
              <span class="mono note-sm">{{ s.raw }}</span>
            </div>
            <p class="legend-desc">{{ s.desc }}</p>
          </div>
        </div>

        <p class="note" style="margin-top: var(--s-6); max-width: 72ch">
          说明：以上为产品的输出性质声明，不构成任何现实决策建议。完整方法边界见仓库
          <code>docs/known-limitations.md</code> 与 <code>docs/user-guide.md</code>。
        </p>
      </div>
    </section>
    </main>
    <footer class="home-footer"><span class="brand-name">天泽 <small>TIANZE</small></span><span>以历法为基 · 以结构为据 · 以典籍为证</span><span>仅供传统文化研究</span></footer>
  </div>
</template>
