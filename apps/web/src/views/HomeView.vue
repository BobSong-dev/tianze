<script setup lang="ts">
/**
 * HomeView — 研究入口。
 *
 * 结构：品牌标识 → 定位 → 四项核心能力 → 研究入口（排盘）→ 研究定位 /
 *       方法边界 / 状态词表。
 * 刻意避免「表单即首页」：首屏是产品与研究定位，排盘是明确的下一步。
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
    desc: "节气交界、时区偏移、真太阳时与晚子时流派逐项可核，排盘口径不做黑箱处理。",
    keys: ["节气", "时区", "真太阳时", "晚子时"],
  },
  {
    idx: "02",
    name: "结构",
    desc: "旺衰三法并列、月令与通根透干、格局与调候、刑冲合害破与合化状态，分歧如实保留。",
    keys: ["旺衰", "格局", "调候", "关系"],
  },
  {
    idx: "03",
    name: "时序",
    desc: "大运 → 流年 → 流月 → 流日逐层展开，并以状态回放呈现每一层引入或移除了什么。",
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
  { code: "CANDIDATE", term: "候选", desc: "满足部分结构条件，需进一步复核——不是结论。" },
  { code: "LIKELY", term: "倾向支持", desc: "支持证据占优，仍非确定性判断。" },
  { code: "DISPUTED", term: "两说并存", desc: "方法或流派存在分歧，两说并列，工具不代为裁决。" },
  { code: "BLOCKED", term: "阻断", desc: "存在明确阻断条件，该结构不成立——并给出「为什么不成立」。" },
  { code: "UNRESOLVED", term: "待定", desc: "证据不足，保持未判定状态而非猜测。" },
  { code: "EXPERIMENTAL", term: "实验性", desc: "岁运参与该计算存在流派分歧，仅作参考。" },
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
          <span class="brand-latin">TIANZE</span>
        </span>
      </a>
      <div class="topbar-actions">
        <button class="btn-ghost" type="button" @click="emit('configure-ai')">AI 设置</button>
        <button class="btn-sm" type="button" @click="toIntake">开始一次分析</button>
      </div>
    </header>

    <!-- 首屏 -->
    <section class="home-hero" id="top">
      <div class="home-hero-grid">
        <div>
          <div class="home-eyebrow">东方历法结构研究工具 · 可追溯推理</div>
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

        <!-- 四项核心能力：编号索引，不是卡片墙 -->
        <div class="home-index">
          <div class="home-index-head">
            <span>核心能力</span>
            <span>四部</span>
          </div>
          <article v-for="c in CAPABILITIES" :key="c.idx" class="home-cap">
            <span class="home-cap-idx">{{ c.idx }}</span>
            <div>
              <h2 class="home-cap-name">{{ c.name }}</h2>
              <p class="home-cap-desc">{{ c.desc }}</p>
              <div class="home-cap-keys">
                <span v-for="k in c.keys" :key="k" class="badge is-mute">{{ k }}</span>
              </div>
            </div>
          </article>
        </div>
      </div>
    </section>

    <!-- 研究入口 -->
    <section class="home-method" id="intake" style="background: var(--paper-050)">
      <div class="home-method-inner">
        <div class="sec-head" style="border-bottom-color: var(--line-200)">
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
        <div class="sec-head" style="border-bottom-color: var(--line-200)">
          <div class="sec-head-top">
            <span class="sec-head-idx">—</span>
            <h2>研究定位与方法边界</h2>
          </div>
          <p class="sec-head-lede">
            天泽是一个知识整理与结构推演工具，不是预测机器。以下边界在产品的每一页都成立。
          </p>
        </div>

        <div class="home-method-grid">
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
          <div v-for="s in STATUS_LEGEND" :key="s.code" class="legend-row">
            <div class="legend-term">
              <span class="badge" :class="`st-${s.code.toLowerCase()}`" :title="s.code">{{ s.term }}</span>
              <span class="mono note-sm">{{ s.code }}</span>
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
