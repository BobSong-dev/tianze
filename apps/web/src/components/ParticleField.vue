<script setup lang="ts">
/**
 * ParticleField · 微粒场（大气古朴的动态质感层）
 *
 * 两种形态（克制原则：低密度、慢速度、低透明，服务气质而非炫技）：
 * - variant="ember"：深底上的「烛尘/星屑」——暖白与古铜微粒缓慢上浮，
 *   带呼吸式明暗（像烛光下的香灰微光），用于首页题头；
 * - variant="dust"：宣纸底上的「纸尘」——极淡墨色微粒缓慢漂移下沉，
 *   alpha ≤ 0.05，几乎只被余光察觉，用于工作台背景。
 *
 * 工程约束：
 * - Canvas 2D（无 WebGL 依赖）；devicePixelRatio 适配；
 * - 页面不可见 / 元素滚出视口时自动暂停（IntersectionObserver + visibilitychange）；
 * - prefers-reduced-motion 时完全不渲染动画（画一帧静态或直接隐藏）；
 * - pointer-events: none，不参与交互与命中测试。
 */
import { onBeforeUnmount, onMounted, ref } from "vue";

const props = withDefaults(
  defineProps<{ variant?: "ember" | "dust"; density?: number; fit?: "parent" | "viewport" }>(),
  { variant: "dust", density: 1, fit: "parent" },
);

const canvasRef = ref<HTMLCanvasElement | null>(null);
let raf = 0;
let running = false;
let visible = true;
let pageVisible = !document.hidden;
let cleanups: Array<() => void> = [];

interface P {
  x: number; y: number;            // 位置（CSS px）
  vx: number; vy: number;          // 速度（px/s，极慢）
  r: number;                       // 半径
  a: number;                       // 基础 alpha
  tw: number;                      // 闪烁相位
  tws: number;                     // 闪烁速度
  hue: 0 | 1;                      // 色系索引
}

function seed(w: number, h: number): P[] {
  const ember = props.variant === "ember";
  const n = Math.round((ember ? 42 : 26) * props.density
    * Math.min(1.6, Math.max(0.5, (w * h) / (1440 * 900))));
  const ps: P[] = [];
  for (let i = 0; i < n; i++) {
    ps.push({
      x: Math.random() * w,
      y: Math.random() * h,
      vx: (Math.random() - 0.5) * (ember ? 3.5 : 2.2),
      vy: ember ? -(2.5 + Math.random() * 5.5)           // 烛尘：缓慢升腾
                : (1.2 + Math.random() * 2.4),           // 纸尘：缓慢沉降
      r: ember ? (Math.random() < 0.12 ? 1.9 : 0.7 + Math.random() * 0.9)
               : (0.8 + Math.random() * 1.1),
      a: ember ? (0.22 + Math.random() * 0.5)            // 星屑可被直视
               : (0.02 + Math.random() * 0.035),         // 纸尘仅余光可察
      tw: Math.random() * Math.PI * 2,
      tws: 0.3 + Math.random() * 0.7,
      hue: Math.random() < (ember ? 0.72 : 0.5) ? 0 : 1,
    });
  }
  return ps;
}

onMounted(() => {
  const canvas = canvasRef.value;
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let w = 0, h = 0, dpr = 1;
  let particles: P[] = [];

  // ember 色系：暖纸白 与 古铜金；dust 色系：淡墨 与 淡褐
  const colors = props.variant === "ember"
    ? ["244, 240, 229", "201, 188, 158"]
    : ["58, 53, 44", "122, 104, 71"];

  const viewportFit = () => props.fit === "viewport";
  const size = () => {
    let rw: number, rh: number;
    if (viewportFit()) { rw = window.innerWidth; rh = window.innerHeight; }
    else { const rect = canvas.parentElement!.getBoundingClientRect(); rw = rect.width; rh = rect.height; }
    w = Math.max(1, rw); h = Math.max(1, rh);
    dpr = Math.min(2, window.devicePixelRatio || 1);
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    canvas.style.width = w + "px";
    canvas.style.height = h + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    particles = seed(w, h);
  };

  const draw = (t: number) => {
    ctx.clearRect(0, 0, w, h);
    for (const p of particles) {
      const twinkle = 0.6 + 0.4 * Math.sin(p.tw + t * 0.001 * p.tws);
      ctx.beginPath();
      ctx.fillStyle = `rgba(${colors[p.hue]}, ${(p.a * twinkle).toFixed(3)})`;
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fill();
    }
  };

  let last = 0;
  const frame = (t: number) => {
    if (!running) return;
    const dt = Math.min(0.05, (t - last) / 1000 || 0.016);
    last = t;
    for (const p of particles) {
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      if (props.variant === "ember") {
        p.x += Math.sin(t * 0.0004 + p.tw) * 0.12;       // 烛尘的横向摇曳
        if (p.y < -6) { p.y = h + 6; p.x = Math.random() * w; }
      } else if (p.y > h + 6) {
        p.y = -6; p.x = Math.random() * w;
      }
      if (p.x < -6) p.x = w + 6; else if (p.x > w + 6) p.x = -6;
    }
    draw(t);
    raf = requestAnimationFrame(frame);
  };

  const start = () => { if (!running && visible && pageVisible) { running = true; last = performance.now(); raf = requestAnimationFrame(frame); } };
  const stop = () => { running = false; cancelAnimationFrame(raf); };

  size();
  if (reduced) {
    draw(0);                       // 静态一帧：有质感无动效
  } else {
    start();
  }

  let ro: ResizeObserver | null = null;
  if (viewportFit()) {
    const onWinResize = () => { size(); if (reduced) draw(0); };
    window.addEventListener("resize", onWinResize);
    cleanups.push(() => window.removeEventListener("resize", onWinResize));
  } else {
    ro = new ResizeObserver(() => { size(); if (reduced) draw(0); });
    ro.observe(canvas.parentElement!);
  }
  const io = new IntersectionObserver(([e]) => { visible = !!e.isIntersecting; visible && !reduced ? start() : stop(); });
  io.observe(canvas);
  const onVis = () => { pageVisible = !document.hidden; pageVisible && !reduced ? start() : stop(); };
  document.addEventListener("visibilitychange", onVis);

  cleanups.push(() => {
    ro?.disconnect();
    io.disconnect();
    document.removeEventListener("visibilitychange", onVis);
    stop();
  });
});

onBeforeUnmount(() => { cleanups.forEach(fn => fn()); });
</script>

<template>
  <canvas ref="canvasRef" class="particle-field" :data-variant="variant" aria-hidden="true" />
</template>

<style scoped>
/* :where() 不计特异性：使用方（如 .app-dust 的 fixed 定位）可整体覆盖 */
:where(.particle-field) {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}
</style>
