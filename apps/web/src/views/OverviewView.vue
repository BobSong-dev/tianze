<script setup lang="ts">
/**
 * OverviewView — 命盘总览。
 *
 * 编辑原则：**不重复命盘区已经给出的信息**。
 * 四柱版块已含日主（反白列 + 日主印记）与干支五行，此处不再设一张"日主大卡片"，
 * 只保留：结论摘要 → 五行结构（表格式） → 术语与使用说明。
 */
import { computed } from "vue";
import ElementBars from "../components/ElementBars.vue";
import StatusBadge from "../components/StatusBadge.vue";
import { elementCn, yinYangCn, STATUS_MAP } from "../presentation/vocab";
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
  (props.result.tiaohou?.recommendations ?? []).slice(0, 2).map(r => r.targetStem));

const relationCount = computed(() => props.result.relations?.length ?? 0);

/** 多方法判定摘要（只读，服从后端 agreement 语义） */
const strengthSummary = computed(() => {
  const methods = props.result.strength?.methods ?? [];
  const map: Record<string, string> = {
    dimensional_v1: "dimension", "weighted-v1": "weighted", "fuyi-v1": "fuyi",
  };
  return methods
    .filter(m => m.verdict)
    .map(m => `${map[m.analyzerId] ?? m.analyzerId}：${m.verdict}`);
});
</script>

<template>
  <div class="stack stack-6">
    <!-- 结论摘要 -->
    <section class="verdict">
      <span class="verdict-kicker">分析摘要</span>
      <p class="verdict-text">
        日主 {{ dm.stem }}（{{ elementCn(dm.element) }}·{{ yinYangCn(dm.yinYang) }}）
        <template v-if="strengthSummary.length">，多方法判定为 {{ strengthSummary.join("；") }}</template>
      </p>

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

      <div class="verdict-meta">
        <StatusBadge
          v-if="agreement"
          :code="props.result.strength?.agreement"
          :label="`旺衰一致性：${agreement}`"
          with-hint
        />
        <span v-if="patternCandidates.length">
          格局候选 {{ patternCandidates.join("、") }}（候选，需复核）
        </span>
        <span v-if="tiaohouTargets.length">调候 {{ tiaohouTargets.join("、") }}</span>
        <span>关系 {{ relationCount }} 条</span>
      </div>
      <p class="note mt-3">
        以上为结构观察摘要。候选状态（CANDIDATE）与多方法分歧（DISPUTED）均不构成结论。
      </p>
    </section>

    <!-- 五行结构：批注栏 + 表格式图 -->
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
              显＝天干与地支本气 · 藏＝地支藏干 · 刻度 8 格（八字八位）
            </span>
          </div>
          <ElementBars :counts="props.result.elementCounts" />
        </div>
      </div>
    </section>

    <!-- 术语与使用说明 -->
    <section class="sheet">
      <div class="stack stack-3">
        <details>
          <summary><strong>术语与状态说明</strong>（候选状态词汇表）</summary>
          <dl class="report-dl mt-4">
            <dt>日主</dt>
            <dd>日柱天干，是十神与旺衰判定的参照点；其五行与阴阳由引擎给出。</dd>
            <dt>候选（CANDIDATE）</dt>
            <dd>满足部分结构条件，需进一步复核，不是结论。</dd>
            <dt>倾向支持（LIKELY）/ 两说并存（DISPUTED）</dt>
            <dd>支持证据占优 / 方法或流派存在分歧，两说并列。</dd>
            <dt>阻断（BLOCKED）/ 待定（UNRESOLVED）</dt>
            <dd>存在明确阻断 / 证据不足。</dd>
            <dt>实验性（EXPERIMENTAL）</dt>
            <dd>岁运参与该计算存在流派分歧，仅作参考。</dd>
            <dt>真从 / 假从</dt>
            <dd>从格纯粹与不纯粹之分；假从岁运敏感。</dd>
            <dt>争合 / 合去 / 合绊</dt>
            <dd>多干争一合 / 合而使原十神失效（两说）/ 合而不化仍有意。</dd>
            <dt>虚神 / 填实</dt>
            <dd>拱夹所缺之支；岁运补上即为填实（候选级观察）。</dd>
          </dl>
        </details>

        <details>
          <summary><strong>首次使用？</strong>查看研究路径</summary>
          <ol class="mt-4" style="padding-left: 1.3em">
            <li>在此页确认四柱与五行结构，核对排盘口径是否符合你的研究约定。</li>
            <li>依次查看旺衰、格局、关系、结构、调候——每个结论都可展开到依据。</li>
            <li>在「岁运时序」选择大运与流年，逐层查看状态变化与其触发规则。</li>
            <li>在「知识图谱」按规则或命例反向检索；在「报告」汇整为可打印文稿。</li>
          </ol>
          <p class="note mt-3">
            完整说明见仓库 <code>docs/user-guide.md</code>。
          </p>
        </details>
      </div>
    </section>
  </div>
</template>
