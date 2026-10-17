<script setup lang="ts">
/**
 * ChartWorkspace — 命盘工作区。
 * 顶部常驻四柱命盘（研究者的参照锚点），下方按研究路径渲染小节。
 * 每个小节自带独立标题层级与边界说明。
 */
import { computed } from "vue";
import PillarDisplay from "../components/PillarDisplay.vue";
import SectionHeader from "../components/SectionHeader.vue";
import OverviewView from "./OverviewView.vue";
import StrengthView from "./StrengthView.vue";
import PatternView from "./PatternView.vue";
import RelationsView from "./RelationsView.vue";
import StructureView from "./StructureView.vue";
import TiaoHouView from "./TiaoHouView.vue";
import AdvancedView from "./AdvancedView.vue";
import StatusBadge from "../components/StatusBadge.vue";
import type { AnalyzeResponse } from "../types/tianze";

const props = defineProps<{
  page: string;
  result: AnalyzeResponse;
  order: Array<"year" | "month" | "day" | "hour">;
  relationChains: Map<string, any>;
  combinationStates: any[];
}>();

const emit = defineEmits<{ (e: "open-graph", id: string): void }>();

interface PageMeta {
  index: string;
  title: string;
  lede: string;
  note?: string;
}

const META: Record<string, PageMeta> = {
  overview: {
    index: "01",
    title: "命盘总览",
    lede: "四柱、日主与五行结构的整体核对。所有候选状态在此明确标注，不做确定性表述。",
    note: "研究起点：先确认排盘口径与结构事实，再进入各专项分析。",
  },
  strength: {
    index: "02",
    title: "旺衰",
    lede: "得令、得地、得势三项维度与多方法判定并列呈现，分歧如实保留。",
    note: "多方法并列，工具不裁决；EXPERIMENTAL 标记表示岁运参与该计算存在流派分歧。",
  },
  pattern: {
    index: "03",
    title: "格局",
    lede: "月令取格路径、候选格局与支持 / 破坏 / 救应 / 冲突因素的结构化评估。",
    note: "格局候选为结构观察，需结合研究者判断复核。",
  },
  relations: {
    index: "04",
    title: "关系",
    lede: "刑冲合害破、三合三会与天干五合的成立条件、流派注记与合化状态。",
    note: "合化状态为三要素候选（邻位 / 月令化神 / 阻化），工具永不判定化成。",
  },
  structure: {
    index: "05",
    title: "结构",
    lede: "月令、通根、透干与胎元命宫身宫等结构性事实，逐条附依据。",
  },
  tiaohou: {
    index: "06",
    title: "调候",
    lede: "按穷通宝鉴逐月调候规则给出的目标干候选，附古籍原文与页码出处。",
    note: "调候取向可能与旺衰 / 格局取向冲突，冲突处如实并列。",
  },
  advanced: {
    index: "07",
    title: "高级结构",
    lede: "从格与专旺候选、外格虚神、天干合化、病药结构与通关。",
    note: "外格虚神为候选参考，非格局；病药指结构失衡与制衡，不是医学诊断。",
  },
};

const meta = computed<PageMeta>(() => META[props.page] ?? META.overview);
const warnings = computed(() => props.result.warnings ?? []);
const fallbacks = computed(() => props.result.fallbacks ?? []);
</script>

<template>
  <div class="stack stack-6 panel">
    <!-- 命盘：总览页给完整版框；其它页只给一行速览，
         把首屏让给该页真正的分析内容（同一参照信息，两种密度） -->
    <section v-if="props.page === 'overview'">
      <div class="sec-sub" style="margin-top: 0">
        <h3>四柱命盘</h3>
        <span class="sec-sub-note">当前命例的参照锚点 · 各页面共用</span>
        <span class="sec-sub-aside">
          <StatusBadge :label="`${props.result.dayMaster?.stem ?? ''} 日主`" variant="mute" />
          <StatusBadge
            v-if="props.result.monthCommand"
            :label="`${props.result.monthCommand.monthBranch} 月令`"
            variant="mute"
          />
        </span>
      </div>
      <PillarDisplay :pillars="props.result.pillars" :order="props.order" />
    </section>

    <div v-else class="pillar-line" :aria-label="`四柱速览：日主 ${props.result.dayMaster?.stem ?? ''}`">
      <span class="pillar-line-label">四柱</span>
      <div
        v-for="k in props.order"
        :key="k"
        class="pillar-line-item"
        :class="{ 'is-dm': k === 'day' }"
      >
        <span class="pillar-line-pos">{{ ["年", "月", "日", "时"][props.order.indexOf(k)] }}</span>
        <span class="pillar-line-gz">{{ props.result.pillars[k]?.stem }}{{ props.result.pillars[k]?.branch }}</span>
        <span class="pillar-line-tg">{{ props.result.pillars[k]?.tenGod ?? "日主" }}</span>
      </div>
      <span class="grow" />
      <span class="pillar-line-meta">
        {{ props.result.monthCommand?.monthBranch ?? "" }} 月令
        · 关系 {{ props.result.relations?.length ?? 0 }}
      </span>
    </div>

    <!-- 注意事项（引擎警告与降级） -->
    <section
      v-if="warnings.length || fallbacks.length"
      class="surface surface-tint"
    >
      <div class="sec-sub" style="margin-top: 0; border-bottom: none; padding-bottom: 0">
        <h3 style="font-size: var(--t-md)">注意事项</h3>
        <span class="sec-sub-note">引擎如实标注的降级与警告</span>
      </div>
      <div class="stack stack-1 mt-3">
        <div v-for="w in warnings" :key="w" class="ev is-warn">
          <span class="ev-mark">⚠</span><span class="ev-body warning">{{ w }}</span>
        </div>
        <div v-for="f in fallbacks" :key="f" class="ev is-quiet">
          <span class="ev-mark">ℹ</span><span class="ev-body fallback">{{ f }}</span>
        </div>
      </div>
    </section>

    <!-- 小节内容 -->
    <section>
      <SectionHeader
        :index="meta.index"
        :title="meta.title"
        :lede="meta.lede"
        :note="meta.note"
        :level="2"
      />

      <OverviewView
        v-if="props.page === 'overview'"
        :result="props.result"
        :order="props.order"
      />
      <StrengthView
        v-else-if="props.page === 'strength' && props.result.strength"
        :strength="props.result.strength"
      />
      <PatternView
        v-else-if="props.page === 'pattern' && props.result.pattern"
        :pattern="props.result.pattern"
      />
      <RelationsView
        v-else-if="props.page === 'relations'"
        :result="props.result"
        :relation-chains="props.relationChains"
        :combination-states="props.combinationStates"
        @open-graph="emit('open-graph', $event)"
      />
      <StructureView
        v-else-if="props.page === 'structure'"
        :result="props.result"
      />
      <TiaoHouView
        v-else-if="props.page === 'tiaohou' && props.result.tiaohou"
        :tiaohou="props.result.tiaohou"
      />
      <AdvancedView
        v-else-if="props.page === 'advanced' && props.result.advancedAnalysis"
        :advanced="props.result.advancedAnalysis"
      />

      <p
        v-else
        class="empty"
      >
        该模块未包含在本次分析结果中（可能未请求或该命例不适用）。
      </p>
    </section>
  </div>
</template>
