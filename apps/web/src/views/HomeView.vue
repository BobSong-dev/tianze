<script setup lang="ts">
/**
 * HomeView — 研究入口。
 *
 * 构图：整幅暗色题头（品牌 + 定位 + 二十四节气版刻索引）
 *   → 纸白区「四部」版刻索引 → 排盘入口 → 研究定位与方法边界 → 状态词表
 *
 * 题头右侧的二十四节气不是装饰：月建以「节」为界，这正是引擎定月柱与流月的依据。
 * 十二「节」提亮、十二「气」压暗，并用一行脚注说明这一关系。
 */
import BirthIntake from "./BirthIntake.vue";
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

/** 二十四节气（顺序即历法顺序）；jie=节（月建之界），qi=气（中气） */
const SOLAR_TERMS: { name: string; kind: "jie" | "qi" }[] = [
  { name: "立春", kind: "jie" }, { name: "雨水", kind: "qi" },
  { name: "惊蛰", kind: "jie" }, { name: "春分", kind: "qi" },
  { name: "清明", kind: "jie" }, { name: "谷雨", kind: "qi" },
  { name: "立夏", kind: "jie" }, { name: "小满", kind: "qi" },
  { name: "芒种", kind: "jie" }, { name: "夏至", kind: "qi" },
  { name: "小暑", kind: "jie" }, { name: "大暑", kind: "qi" },
  { name: "立秋", kind: "jie" }, { name: "处暑", kind: "qi" },
  { name: "白露", kind: "jie" }, { name: "秋分", kind: "qi" },
  { name: "寒露", kind: "jie" }, { name: "霜降", kind: "qi" },
  { name: "立冬", kind: "jie" }, { name: "小雪", kind: "qi" },
  { name: "大雪", kind: "jie" }, { name: "冬至", kind: "qi" },
  { name: "小寒", kind: "jie" }, { name: "大寒", kind: "qi" },
];

interface Capability {
  idx: string;
  name: string;
  desc: string;
  keys: string[];
}

const CAPABILITIES: Capability[] = [
  {
    idx: "01",
    name: "历法",
    desc: "节气交界、时区偏移、真太阳时与晚子时流派逐项可核。排盘口径不做黑箱处理。",
    keys: ["节气", "时区", "真太阳时", "晚子时"],
  },
  {
    idx: "02",
    name: "结构",
    desc: "旺衰三法并列、月令与通根透干、格局与调候、刑冲合害破与合化状态。分歧如实保留。",
    keys: ["旺衰", "格局", "调候", "关系"],
  },
  {
    idx: "03",
    name: "时序",
    desc: "大运、流年、流月、流日逐层展开，并以状态回放呈现每一层引入或移除了什么。",
    keys: ["大运", "流年", "Delta", "Replay"],
  },
  {
    idx: "04",
    name: "证据",
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
  document.getElementById("intake")?.scrollIntoView({ behavior: "smooth", block: "start" });
}
</script>

<template>
  <div class="home">
    <header class="home-top">
      <a class="brand-block" href="#top" style="border: none; padding: 0; width: auto" @click.prevent="toIntake">
        <span class="brand-seal" aria-hidden="true">泽</span>
        <span class="brand-text">
          <span class="brand-name">天泽</span>
          <span class="brand-latin">Tianze</span>
        </span>
      </a>
      <div class="topbar-actions">
        <button class="btn-ghost" type="button" @click="emit('configure-ai')">AI 设置</button>
        <button class="btn-sm" type="button" @click="toIntake">开始一次分析</button>
      </div>
    </header>

    <!-- 题头：整幅暗部 -->
    <section class="home-hero" id="top">
      <div class="home-hero-inner">
        <div>
          <div class="home-eyebrow">东方历法结构研究 · 可追溯推理</div>
          <h1 class="home-title">
            天泽
            <span class="home-title-latin">Tianze</span>
          </h1>
          <p class="home-lede">
            以<em>历法</em>为基，以<em>结构</em>为据，<br />
            构建可追溯的命理分析。
          </p>
          <div class="home-actions">
            <button class="btn-primary btn-lg" type="button" @click="toIntake">
              开始一次分析
            </button>
            <button class="btn-lg" type="button" @click="emit('configure-ai')">
              配置 AI 解读
            </button>
          </div>

          <dl class="home-facts">
            <div>
              <dt class="home-fact-key">排盘口径</dt>
              <dd class="home-fact-val">节气 · 时区 · 晚子时与真太阳时</dd>
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
              <dt class="home-fact-key">引擎</dt>
              <dd class="home-fact-val mono">{{ props.engineVersion }}</dd>
            </div>
          </dl>
        </div>

        <!-- 二十四节气：月建以节为界 -->
        <aside class="calendar-panel" aria-label="二十四节气">
          <div class="calendar-head">
            <span>二十四节气</span>
            <span>月建以节为界</span>
          </div>
          <div class="calendar-grid">
            <span
              v-for="t in SOLAR_TERMS"
              :key="t.name"
              class="calendar-cell"
              :class="{ 'is-node': t.kind === 'jie' }"
              :title="t.kind === 'jie' ? `${t.name}（节）` : `${t.name}（气）`"
            >{{ t.name }}</span>
          </div>
          <p class="calendar-foot">
            亮者为「节」，十二节分定十二月的月柱与流月；暗者为「气」。
            天泽按节气交接时刻换月，而非按日期换月。
          </p>
        </aside>
      </div>
    </section>

    <!-- 四部能力：版刻索引 -->
    <section class="home-index">
      <div class="home-index-inner">
        <div class="sec-head" style="border-bottom-color: var(--ink-900)">
          <div class="sec-head-top">
            <span class="sec-head-idx">四部</span>
            <h2>核心能力</h2>
          </div>
          <p class="sec-head-lede">
            历法、结构、时序、证据——四者互为支撑，缺一层则结论不可追溯。
          </p>
        </div>

        <div class="cap-grid">
          <article v-for="c in CAPABILITIES" :key="c.idx" class="cap">
            <span class="cap-idx">{{ c.idx }}</span>
            <h3 class="cap-name">{{ c.name }}</h3>
            <p class="cap-desc">{{ c.desc }}</p>
            <div class="cap-keys">
              <span v-for="k in c.keys" :key="k">{{ k }}</span>
            </div>
          </article>
        </div>
      </div>
    </section>

    <!-- 排盘入口 -->
    <section class="home-method" id="intake" style="background: var(--paper-050)">
      <div class="home-method-inner">
        <div class="sec-head">
          <div class="sec-head-top">
            <span class="sec-head-idx">00</span>
            <h2>排盘入口</h2>
          </div>
          <p class="sec-head-lede">
            三节输入：出生信息、历法校正、排盘方式。填写完毕后由本地引擎完成全部确定性推导。
          </p>
        </div>
        <BirthIntake
          :birth="props.birth"
          :loading="props.loading"
          :error="props.error"
          @submit="emit('submit')"
        />
      </div>
    </section>

    <!-- 研究定位与方法边界 -->
    <section class="home-method">
      <div class="home-method-inner">
        <div class="sec-head">
          <div class="sec-head-top">
            <span class="sec-head-idx">—</span>
            <h2>研究定位与方法边界</h2>
          </div>
          <p class="sec-head-lede">
            天泽是一个知识整理与结构推演工具，不是预测机器。以下边界在产品的每一页都成立。
          </p>
        </div>

        <div class="method-grid">
          <div class="method-item">
            <h4>不进行确定性人生预测</h4>
            <p>
              输出为干支结构、关系与候选状态的结构化描述，不给出吉凶、成败、疾病、
              婚姻等现实事件的断言。任何"必然发生"的表述都不是本工具的输出。
            </p>
          </div>
          <div class="method-item">
            <h4>分歧并列，不代为裁决</h4>
            <p>
              旺衰三法、流派注记、合化状态等存在学术分歧之处，工具并列呈现并标注
              来源层级，由研究者自行判断，而不是选一个"正确"答案。
            </p>
          </div>
          <div class="method-item">
            <h4>每条判断可回溯到依据</h4>
            <p>
              结论 → 规则编号 → 成立条件 → 古籍引文与页码。缺少依据的部分显式标注
              UNRESOLVED，而不是用文学化措辞掩盖。
            </p>
          </div>
          <div class="method-item">
            <h4>AI 只解释，不推导</h4>
            <p>
              AI 解读消费的是引擎已经算出的结构与证据，输出还需经事实一致性校验；
              未通过校验的内容不会被展示。不配置 AI 时，全部确定性分析仍在本机完成。
            </p>
          </div>
        </div>

        <div class="sec-sub" style="margin-top: var(--s-8)">
          <h3>状态词表</h3>
          <span class="sec-sub-note">全站受控词汇 · 悬停可见原码</span>
        </div>
        <div class="legend-table">
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
  </div>
</template>
