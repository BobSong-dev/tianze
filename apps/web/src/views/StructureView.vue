<script setup lang="ts">
/**
 * StructureView — 结构（月令 / 通根 / 透干 / 神煞位）。
 * 全部内容为引擎给出的结构化事实与说明语句，原样呈现。
 */
import { computed } from "vue";
import StatusBadge from "../components/StatusBadge.vue";
import { elementCn, seasonCn as seasonCnShared } from "../presentation/vocab";
import type { AnalyzeResponse } from "../types/tianze";

const props = defineProps<{ result: AnalyzeResponse }>();

const mc = computed(() => props.result.monthCommand);
const roots = computed(() => props.result.roots ?? []);
const visibility = computed(() => props.result.visibility ?? []);
const points = computed(() => props.result.specialPoints);

const elCn = elementCn;
const seasonCn = seasonCnShared;

const monthRoots = computed(() => roots.value.filter(r => r.isMonthRoot));
</script>

<template>
  <div class="structure-layout">
    <!-- 月令 -->
    <section v-if="mc">
      <div class="sec-sub" style="margin-top: 0">
        <h3>月令</h3>
        <span class="sec-sub-note">日主当令状态的判定依据</span>
      </div>

      <div class="verdict">
        <span class="verdict-kicker">月令结论</span>
        <p class="verdict-text">
          {{ mc.monthBranch }}月 · {{ seasonCn(mc.season) }} · {{ elCn(mc.element) }}
          — 日主{{ mc.relationToDayMaster?.state }}
          <template v-if="mc.relationToDayMaster?.inCommand">（得令）</template>
        </p>
        <div class="verdict-meta">
          <StatusBadge :label="`日主 ${mc.dayMaster}`" variant="mute" />
          <StatusBadge
            v-if="mc.relationToDayMaster?.inCommand"
            label="得令"
            variant="pos"
          />
          <StatusBadge
            v-else
            label="未得令"
            variant="mute"
          />
          <StatusBadge
            v-if="mc.relationToDayMaster?.rule"
            :label="mc.relationToDayMaster.rule"
            variant="rule"
          />
        </div>
      </div>

      <div class="surface mt-4">
        <div class="sec-sub" style="margin-top: 0">
          <h3 style="font-size: var(--t-md)">藏干优先级</h3>
          <span class="sec-sub-note">本气 → 中气 → 余气，标注是否透干</span>
        </div>
        <div class="stack stack-2">
          <div
            v-for="h in mc.hiddenStemPriority ?? []"
            :key="h.stem + h.role"
            class="row row-3"
          >
            <span class="hidden-stem-glyph" style="font-size: var(--t-lg)">{{ h.stem }}</span>
            <StatusBadge :label="h.role" variant="mute" />
            <StatusBadge
              :label="h.transparent ? '已透干' : '未透干'"
              :variant="h.transparent ? 'pos' : 'mute'"
            />
          </div>
          <p v-if="!(mc.hiddenStemPriority ?? []).length" class="note">月支无藏干记录。</p>
        </div>

        <details v-if="mc.evidence?.length" class="mt-4">
          <summary>月令判定依据（{{ mc.evidence.length }} 条）</summary>
          <div class="stack stack-1 mt-3">
            <div v-for="e in mc.evidence" :key="e" class="ev evidence-item is-fact">
              <span class="ev-mark">·</span><span class="ev-body">{{ e }}</span>
            </div>
          </div>
        </details>
      </div>
    </section>

    <!-- 通根 -->
    <section>
      <div class="sec-sub" style="margin-top: 0">
        <h3>通根</h3>
        <span class="sec-sub-note">天干在地支的根系，深度与是否月令根原样标注</span>
        <span class="sec-sub-aside">
          <StatusBadge
            :label="`共 ${roots.length} 条`"
            variant="mute"
          />
        </span>
      </div>
      <div class="stack stack-2">
        <div v-for="(r, i) in roots" :key="`${r.stem}${r.branch}${r.position}${i}`" class="row-item">
          <div class="row-item-head">
            <span class="row-item-title">{{ r.stem }} → {{ r.branch }}</span>
            <StatusBadge :label="r.position" variant="mute" />
            <StatusBadge :label="r.rootType" variant="mute" />
            <StatusBadge :label="r.depth" variant="mute" />
            <StatusBadge v-if="r.isMonthRoot" label="月令" variant="warn" />
            <StatusBadge v-if="r.isDayMaster" label="日主" variant="warn" />
          </div>
          <p class="row-item-body">{{ r.statement }}</p>
        </div>
        <p v-if="!roots.length" class="empty">无通根记录。</p>
      </div>
      <p v-if="monthRoots.length" class="note mt-3">
        其中 {{ monthRoots.length }} 条为月令根——月令根在旺衰判定中权重更高，为通说口径。
      </p>
    </section>

    <!-- 透干 -->
    <section>
      <div class="sec-sub" style="margin-top: 0">
        <h3>透干</h3>
        <span class="sec-sub-note">地支藏干在天干显现的位置与距离</span>
        <span class="sec-sub-aside">
          <StatusBadge :label="`共 ${visibility.length} 条`" variant="mute" />
        </span>
      </div>
      <div class="stack stack-2">
        <div
          v-for="(v, i) in visibility"
          :key="`${v.hiddenStem}${v.position}${i}`"
          class="row-item"
        >
          <div class="row-item-head">
            <span class="row-item-title">{{ v.hiddenStem }} → {{ v.visibleStem }}</span>
            <StatusBadge :label="`源 ${v.sourceBranch}（${v.sourceRole}）`" variant="mute" />
            <StatusBadge :label="`透于 ${v.position}`" variant="mute" />
            <StatusBadge :label="`距离 ${v.distance}`" variant="mute" />
            <StatusBadge v-if="v.monthRelated" label="关联月令" variant="warn" />
            <StatusBadge v-if="v.dayMasterRelated" label="关联日主" variant="warn" />
          </div>
          <p class="row-item-body">{{ v.statement }}</p>
        </div>
        <p v-if="!visibility.length" class="empty">无透干记录。</p>
      </div>
    </section>

    <!-- 神煞位（胎元 / 命宫 / 身宫） -->
    <section v-if="points">
      <div class="sec-sub" style="margin-top: 0">
        <h3>胎元 · 命宫 · 身宫</h3>
        <span class="sec-sub-note">由引擎按传统口径计算的辅助位置</span>
      </div>
      <div class="metrics">
        <div class="metric">
          <span class="metric-key">胎元</span>
          <span class="metric-val">{{ points.taiYuan || "—" }}</span>
        </div>
        <div class="metric">
          <span class="metric-key">命宫</span>
          <span class="metric-val">{{ points.mingGong || "—" }}</span>
        </div>
        <div class="metric">
          <span class="metric-key">身宫</span>
          <span class="metric-val">{{ points.shenGong || "—" }}</span>
        </div>
      </div>
    </section>
  </div>
</template>
