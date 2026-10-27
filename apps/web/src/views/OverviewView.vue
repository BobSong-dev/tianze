<script setup lang="ts">
/**
 * OverviewView — 命盘总览（M53 小白优先重写）。
 *
 * 首屏是"三句话读懂你的盘"白话卡；研究性信息（多方法口径、一致性徽章）
 * 降级到白话卡下方的备注区。命盘四柱区（PillarDisplay）在页面更上方，
 * 本页不重复。白话翻译只译"术语指什么"，不产生任何命理断言。
 */
import { computed } from "vue";
import ElementBars from "../components/ElementBars.vue";
import StatusBadge from "../components/StatusBadge.vue";
import { elementCn, yinYangCn, STATUS_MAP } from "../presentation/vocab";
import { STRENGTH_PLAIN } from "../presentation/layman";
import type { AnalyzeResponse } from "../types/tianze";

const props = defineProps<{
  result: AnalyzeResponse;
  order: Array<"year" | "month" | "day" | "hour">;
}>();

const dm = computed(() => props.result.dayMaster);

const agreement = computed(() => {
  const a = props.result.strength?.agreement;
  return a ? (STATUS_MAP[a]?.label ?? a) : null;
});

const patternCandidates = computed(() =>
  (props.result.pattern?.candidates ?? []).slice(0, 3).map(c => c.name));

const tiaohouTargets = computed(() =>
  (props.result.tiaohou?.recommendations ?? []).slice(0, 2)
    .map(r => r.targetStem).filter((x): x is string => !!x));

const relationCount = computed(() => props.result.relations?.length ?? 0);

/** 多方法判定摘要（研究口径，降级展示） */
const strengthSummary = computed(() => {
  const methods = props.result.strength?.methods ?? [];
  const map: Record<string, string> = {
    dimensional_v1: "dimension", "weighted-v1": "weighted", "fuyi-v1": "fuyi",
  };
  return methods
    .filter(m => m.verdict)
    .map(m => `${map[m.analyzerId] ?? m.analyzerId}：${m.verdict}`);
});

/** ---- 白话三句卡数据（纯展示层，从引擎结果拼装） ---- */

// 各方法 verdict 的白话并集（方法间分歧时如实呈现多种说法）
const strengthPlain = computed(() => {
  const methods = props.result.strength?.methods ?? [];
  const plains = [...new Set(
    methods.map(m => m.verdict).filter((v): v is string => !!v)
      .map(v => STRENGTH_PLAIN[v] ?? v))];
  if (!plains.length) return null;
  const unique = plains.length === 1
    ? plains[0]
    : `${plains.slice(0, 2).join("（不同方法说法不一，两种都放这里：")}）`;
  return unique;
});

// 五行最多 / 最少（含藏干口径，展示层计算）
const elementPlain = computed(() => {
  const el = props.result.elementCounts?.elements as
    Record<string, { visible: number; hidden: number }> | undefined;
  if (!el) return null;
  const totals = Object.entries(el)
    .map(([k, v]) => [k, (v.visible ?? 0) + (v.hidden ?? 0)] as const)
    .filter(([, n]) => n > 0);
  if (totals.length < 2) return null;
  totals.sort((a, b) => b[1] - a[1]);
  const [topK, topN] = totals[0];
  const [lowK] = totals[totals.length - 1];
  return { top: elementCn(topK.toUpperCase()), topN, low: elementCn(lowK.toUpperCase()) };
});

const gloss = computed(() => {
  const parts: string[] = [];
  if (patternCandidates.value.length) {
    parts.push(`传统归类上，这个盘比较接近「${patternCandidates.value[0]}」这类结构——`
      + "这只是初步归类（候选），不是定论");
  }
  if (tiaohouTargets.value.length) {
    parts.push(`传统上认为这个盘的"舒适搭配"里 ${tiaohouTargets.value.join("、")} 这类五行比较重要`);
  }
  return parts;
});
</script>

<template>
  <div class="stack stack-6">
    <!-- 三句话读懂你的盘（小白首屏） -->
    <section class="verdict">
      <span class="verdict-kicker">三句话读懂你的盘</span>
      <ol class="layman-lines">
        <li>
          代表你本人的字是 <strong>{{ dm.stem }}</strong
          >（{{ elementCn(dm.element) }}·{{ yinYangCn(dm.yinYang) }}，
          即"{{ elementCn(dm.element) }}命"）。
        </li>
        <li v-if="strengthPlain">
          整体强弱：系统用几种方法各算了一遍，结论是——{{ strengthPlain }}。
        </li>
        <li v-if="elementPlain">
          五行里 <strong>{{ elementPlain.top }}</strong> 最多（{{ elementPlain.topN }} 处）、
          {{ elementPlain.low }} 最少——后面各页会反复出现这个特点。
        </li>
        <li v-for="g in gloss" :key="g">{{ g }}</li>
        <li v-if="relationCount">
          八个字之间有 {{ relationCount }} 组相互作用（相合 / 相冲等），在「关系」页可以逐条看。
        </li>
      </ol>

      <!-- 四柱指纹：与上方版框呼应，供快速扫读（E2E 稳定锚点 .summary-pillar） -->
      <div class="pillars-visual" style="margin-top: var(--s-4)">
        <div
          v-for="(k, i) in props.order"
          :key="k"
          class="summary-pillar"
          :class="{ me: k === 'day' }"
        >
          <span class="pillar-label">{{ ["年柱", "月柱", "日柱", "时柱"][i] }}</span>
          <span class="pillar-gz">
            {{ props.result.pillars[k]?.stem }}{{ props.result.pillars[k]?.branch }}
          </span>
        </div>
      </div>

      <!-- 研究口径（愿意深挖的人看） -->
      <details class="mt-4">
        <summary class="note">研究口径：多方法结果与一致性</summary>
        <div class="verdict-meta mt-3">
          <StatusBadge
            v-if="agreement"
            :code="props.result.strength?.agreement"
            :label="`旺衰一致性：${agreement}`"
            with-hint
          />
          <span v-if="strengthSummary.length">{{ strengthSummary.join("；") }}</span>
          <span v-if="patternCandidates.length">
            格局候选 {{ patternCandidates.join("、") }}
          </span>
          <span v-if="tiaohouTargets.length">调候 {{ tiaohouTargets.join("、") }}</span>
          <span>关系 {{ relationCount }} 条</span>
        </div>
      </details>
      <p class="note mt-3">
        以上是结构层面的观察，不是命运结论；标着「候选」「说法不一」的地方尤其如此。
        本站不做吉凶与具体事件预测。
      </p>
    </section>

    <!-- 五行结构 -->
    <section class="sheet">
      <div class="rail">
        <div class="rail-mark">
          <b>一</b>
          显藏对比
        </div>
        <div class="rail-body">
          <div class="sheet-head">
            <h3 class="sheet-title">五行结构</h3>
            <span class="sheet-note">
              显＝直接写在盘面上的 · 藏＝藏在地支里的 · 一共 8 个位置
            </span>
          </div>
          <ElementBars :counts="props.result.elementCounts" />
          <p class="note mt-3">
            白话：木火土金水五种属性在这个盘里的多寡。有的只露在明面（天干），
            有的藏在地支里——两种都算上才是全貌。
          </p>
        </div>
      </div>
    </section>

    <!-- 术语与使用说明 -->
    <section class="sheet">
      <div class="stack stack-3">
        <details>
          <summary><strong>看不懂某个词？</strong>点开查白话对照</summary>
          <dl class="report-dl mt-4">
            <dt>日主</dt>
            <dd>代表你本人的那个字（出生日的天干），全盘都以它为参照。</dd>
            <dt>候选 / 倾向支持 / 两说并存 / 阻断 / 待定</dt>
            <dd>只是初步观察 / 证据偏支持 / 各家说法不一、两种都列 / 明确不成立 / 证据不够，先不定。</dd>
            <dt>十神（比肩、正官、正印……）</dt>
            <dd>给盘里每个字贴的传统"角色标签"——把鼠标停在这些词上会浮出一句白话解释。</dd>
            <dt>真从 / 假从</dt>
            <dd>特殊格局纯粹与不纯粹之分，真假之争是学术分歧，不是吉凶。</dd>
            <dt>虚神 / 填实</dt>
            <dd>盘里"差一点就凑齐"的结构所缺的那一环；岁运补上即"填实"（只是候选级观察）。</dd>
          </dl>
        </details>

        <details>
          <summary><strong>这个网站怎么用？</strong>三步走</summary>
          <ol class="mt-4" style="padding-left: 1.3em">
            <li>本页先看"三句话"和五行图，对你的盘有个整体印象。</li>
            <li>想细看就点上面的标签页：整体强弱、传统归类、字与字的关系、不同年龄段的走向——
                每一页都是"先白话结论、后技术依据"。</li>
            <li>想让 AI 直接用人话给你讲一遍，去「AI 解读」页点生成（需要在设置里配一次 AI 服务）。</li>
          </ol>
          <p class="note mt-3">
            想核对每条结论的古籍出处与规则编号？各页的"查看依据"折叠区都有。完整说明见
            <code>docs/user-guide.md</code>。
          </p>
        </details>
      </div>
    </section>
  </div>
</template>
