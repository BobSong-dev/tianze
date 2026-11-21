<script setup lang="ts">
/**
 * ReportView — 研究报告预览。
 *
 * 定位（重要）：本页是**引擎结果的呈现层汇编**，供研究者在浏览器中通读与打印。
 * 它不新增推理、不改写任何结论。权威的 Markdown / HTML 导出由 CLI 完成：
 *   tianze export …（见 tianze/export.py、tianze/export_html.py）
 * 页面底部明确标注这一分工，避免误认为本页是新的结论来源。
 *
 * 版式：研究报告（封面 → 目录 → 章节），并用打印样式支持导出 PDF。
 */
import { computed } from "vue";
import PillarDisplay from "../components/PillarDisplay.vue";
import ElementBars from "../components/ElementBars.vue";
import StatusBadge from "../components/StatusBadge.vue";
import Citation from "../components/Citation.vue";
import { elementCn, seasonCn as seasonCnShared, STATUS_MAP, analyzerCn, positionShortCn } from "../presentation/vocab";
import type { AnalyzeResponse } from "../types/tianze";

const props = defineProps<{
  result: AnalyzeResponse;
  order: Array<"year" | "month" | "day" | "hour">;
  birth: { date: string; time: string; timeKnown: boolean; gender: string; timezoneOffset: number; sect: number; longitude: number | null };
  temporal: any;
  aiResult: any;
  aiConfigured: boolean;
  engineVersion?: string;
}>();

const dm = computed(() => props.result.dayMaster);
const elCn = elementCn;
const seasonCn = seasonCnShared;

const SECTIONS = [
  { id: "basic", n: "01", title: "基本信息" },
  { id: "chart", n: "02", title: "命盘" },
  { id: "structure", n: "03", title: "结构分析" },
  { id: "strength", n: "04", title: "旺衰" },
  { id: "pattern", n: "05", title: "格局" },
  { id: "relations", n: "06", title: "关系" },
  { id: "temporal", n: "07", title: "岁运" },
  { id: "evidence", n: "08", title: "证据链" },
  { id: "ai", n: "09", title: "AI 辅助解读" },
  { id: "boundary", n: "10", title: "边界与限制" },
];

const strengthVerdicts = computed(() =>
  (props.result.strength?.methods ?? [])
    .filter(m => m.verdict)
    .map(m => ({ id: m.analyzerId, verdict: m.verdict })));

const citations = computed(() => {
  const out: any[] = [];
  for (const rec of props.result.tiaohou?.recommendations ?? []) {
    if (rec.quote) out.push({ quote: rec.quote, book: rec.source?.book, title: rec.source?.chapter, pages: rec.source?.pages, ruleIds: rec.ruleIds });
  }
  for (const e of (props.result as any).relationExplanations ?? []) {
    for (const c of e.citations ?? []) {
      out.push({ quote: c.quote, book: c.book, title: c.title, candidateId: c.candidateId, sourceKind: c.sourceKind, ocrRisk: c.ocrRisk, label: e.label });
    }
  }
  return out;
});

function jump(id: string) {
  document.getElementById(`sec-${id}`)?.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth", block: "start" });
}
</script>

<template>
  <div class="report">
    <!-- 封面 -->
    <header class="report-cover">
      <div class="report-title">天泽命理结构分析报告</div>
      <p class="report-sub">
        {{ props.birth.date }}
        <template v-if="props.birth.timeKnown"> {{ props.birth.time }}</template>
        <template v-else> （时辰未知）</template>
        · {{ props.birth.gender === "male" ? "男" : "女" }}
        · UTC{{ props.birth.timezoneOffset >= 0 ? "+" : "" }}{{ props.birth.timezoneOffset }}
        · 晚子时流派 {{ props.birth.sect }}
      </p>

      <nav class="report-toc" aria-label="报告目录">
        <button
          v-for="s in SECTIONS"
          :key="s.id"
          type="button"
          class="report-toc-item"
          @click="jump(s.id)"
        >
          <span class="report-toc-idx">{{ s.n }}</span>
          <span>{{ s.title }}</span>
        </button>
      </nav>
    </header>

    <!-- 01 基本信息 -->
    <section class="report-sec" id="sec-basic">
      <div class="report-sec-head">
        <span class="report-sec-idx">01</span>
        <h2 class="report-sec-title">基本信息</h2>
      </div>
      <dl class="report-dl">
        <dt>出生日期</dt><dd>{{ props.birth.date }}</dd>
        <dt>出生时间</dt><dd>{{ props.birth.timeKnown ? props.birth.time : "未知（三柱分析）" }}</dd>
        <dt>性别</dt><dd>{{ props.birth.gender === "male" ? "男" : "女" }}</dd>
        <dt>时区偏移</dt><dd>UTC{{ props.birth.timezoneOffset >= 0 ? "+" : "" }}{{ props.birth.timezoneOffset }}</dd>
        <dt>晚子时流派</dt><dd>流派 {{ props.birth.sect }}</dd>
        <dt v-if="props.birth.longitude != null">经度</dt>
        <dd v-if="props.birth.longitude != null">{{ props.birth.longitude }}°（仅记录）</dd>
        <dt>日时柱计时</dt><dd>出生地钟表时，适用时扣除中国夏令时</dd>
        <dt>日主</dt><dd>{{ dm.stem }}（{{ elCn(dm.element) }}）</dd>
        <dt v-if="props.result.monthCommand">月令</dt>
        <dd v-if="props.result.monthCommand">
          {{ props.result.monthCommand.monthBranch }}月 ·
          {{ seasonCn(props.result.monthCommand.season) }} ·
          {{ elCn(props.result.monthCommand.element) }}
        </dd>
      </dl>
    </section>

    <!-- 02 命盘 -->
    <section class="report-sec" id="sec-chart">
      <div class="report-sec-head">
        <span class="report-sec-idx">02</span>
        <h2 class="report-sec-title">命盘</h2>
      </div>
      <PillarDisplay :pillars="props.result.pillars" :order="props.order" />

      <div style="margin-top: var(--s-6)">
        <h3 style="font-size: var(--t-md); margin-bottom: var(--s-3)">五行结构</h3>
        <ElementBars :counts="props.result.elementCounts" />
      </div>

      <div v-if="props.result.specialPoints" style="margin-top: var(--s-6)">
        <dl class="report-dl">
          <dt>胎元</dt><dd>{{ props.result.specialPoints.taiYuan || "—" }}</dd>
          <dt>命宫</dt><dd>{{ props.result.specialPoints.mingGong || "—" }}</dd>
          <dt>身宫</dt><dd>{{ props.result.specialPoints.shenGong || "—" }}</dd>
        </dl>
      </div>
    </section>

    <!-- 03 结构分析 -->
    <section class="report-sec" id="sec-structure">
      <div class="report-sec-head">
        <span class="report-sec-idx">03</span>
        <h2 class="report-sec-title">结构分析</h2>
      </div>

      <div v-if="props.result.monthCommand" style="margin-bottom: var(--s-5)">
        <h3 style="font-size: var(--t-md); margin-bottom: var(--s-2)">月令</h3>
        <p class="report-sec-body">
          {{ props.result.monthCommand.monthBranch }}月 ·
          日主{{ props.result.monthCommand.relationToDayMaster?.state }}
          <template v-if="props.result.monthCommand.relationToDayMaster?.inCommand">（得令）</template>
        </p>
        <ul class="report-sec-body" style="padding-left: 1.2em">
          <li v-for="(e, i) in props.result.monthCommand.evidence" :key="i">{{ e }}</li>
        </ul>
      </div>

      <div v-if="props.result.roots?.length" style="margin-bottom: var(--s-5)">
        <h3 style="font-size: var(--t-md); margin-bottom: var(--s-2)">通根（{{ props.result.roots.length }}）</h3>
        <ul class="report-sec-body" style="padding-left: 1.2em">
          <li v-for="(r, i) in props.result.roots" :key="i">
            {{ r.statement }}
            <span class="note-sm">［{{ r.depth }}{{ r.isMonthRoot ? "·月令根" : "" }}］</span>
          </li>
        </ul>
      </div>

      <div v-if="props.result.visibility?.length">
        <h3 style="font-size: var(--t-md); margin-bottom: var(--s-2)">透干（{{ props.result.visibility.length }}）</h3>
        <ul class="report-sec-body" style="padding-left: 1.2em">
          <li v-for="(v, i) in props.result.visibility" :key="i">{{ v.statement }}</li>
        </ul>
      </div>
    </section>

    <!-- 04 旺衰 -->
    <section class="report-sec" id="sec-strength">
      <div class="report-sec-head">
        <span class="report-sec-idx">04</span>
        <h2 class="report-sec-title">旺衰</h2>
      </div>
      <p class="report-sec-body">
        多方法并列呈现，不裁决。
        <template v-if="props.result.strength?.agreement">
          一致性：
          <strong>{{ STATUS_MAP[props.result.strength.agreement]?.label ?? props.result.strength.agreement }}</strong>
        </template>
      </p>
      <div class="table-scroll" tabindex="0" role="region" aria-label="旺衰方法比较表">
      <table style="margin-top: var(--s-4)">
        <thead>
          <tr><th>方法</th><th>判定</th><th>置信</th><th>计分</th></tr>
        </thead>
        <tbody>
          <tr v-for="m in props.result.strength?.methods ?? []" :key="m.analyzerId">
            <td>{{ analyzerCn(m.analyzerId) }}<span class="note-sm mono" style="display:block">{{ m.analyzerId }}</span></td>
            <td>{{ m.verdict ?? "—" }}</td>
            <td>{{ m.confidence ?? "—" }}</td>
            <td class="mono">{{ m.score ?? "—" }}</td>
          </tr>
        </tbody>
      </table>
      </div>
      <p v-if="props.result.strength?.note" class="note" style="margin-top: var(--s-3)">
        {{ props.result.strength.note }}
      </p>
      <p v-if="strengthVerdicts.length" class="report-sec-body" style="margin-top: var(--s-3)">
        {{ strengthVerdicts.map(v => `${v.id}：${v.verdict}`).join("　·　") }}
      </p>
    </section>

    <!-- 05 格局 -->
    <section class="report-sec" id="sec-pattern">
      <div class="report-sec-head">
        <span class="report-sec-idx">05</span>
        <h2 class="report-sec-title">格局</h2>
      </div>
      <template v-if="props.result.pattern">
        <ul class="report-sec-body" style="padding-left: 1.2em">
          <li v-for="(c, i) in props.result.pattern.candidates" :key="i">
            <strong>{{ c.name }}</strong>（{{ c.via }}）
            <span class="note-sm">［候选，需复核］</span>
            <div class="note-sm">{{ c.evidence.join("；") }}</div>
          </li>
        </ul>
        <div v-if="props.result.pattern.evaluation" style="margin-top: var(--s-4)">
          <p class="report-sec-body">
            综合评估：<strong>{{ props.result.pattern.evaluation.status }}</strong>
          </p>
          <ul class="report-sec-body" style="padding-left: 1.2em">
            <li v-for="f in props.result.pattern.evaluation.supports" :key="f.ruleId">
              支持 · {{ f.name }}：{{ f.detail }}
            </li>
            <li v-for="f in props.result.pattern.evaluation.damages" :key="f.ruleId">
              破坏 · {{ f.name }}：{{ f.detail }}
            </li>
            <li v-for="f in props.result.pattern.evaluation.rescues" :key="f.ruleId">
              救应 · {{ f.name }}：{{ f.detail }}
            </li>
            <li v-for="f in props.result.pattern.evaluation.conflicts ?? []" :key="f.ruleId">
              冲突 · {{ f.name }}：{{ f.detail }}
            </li>
          </ul>
        </div>
        <p v-if="props.result.pattern.note" class="note" style="margin-top: var(--s-3)">
          {{ props.result.pattern.note }}
        </p>
      </template>
      <p v-else class="report-sec-body">本次分析未产生格局结果。</p>
    </section>

    <!-- 06 关系 -->
    <section class="report-sec" id="sec-relations">
      <div class="report-sec-head">
        <span class="report-sec-idx">06</span>
        <h2 class="report-sec-title">关系</h2>
      </div>
      <p class="report-sec-body">
        已成立 {{ props.result.relations?.length ?? 0 }} 条<template
          v-if="props.result.blockedRelations?.length"
        >，未成立候选 {{ props.result.blockedRelations.length }} 条</template>。
      </p>
      <ul class="report-sec-body" style="padding-left: 1.2em">
        <li v-for="(r, i) in props.result.relations" :key="i">
          <strong>{{ r.label }}</strong>
          <span class="note-sm">
            ［{{ r.positions.map(positionShortCn).join(" · ") }}<template v-if="r.adjacency"> · {{ r.adjacency === "ADJACENT" ? "贴邻" : "隔位" }}</template><template v-if="r.monthInvolved"> · 月令</template>］
          </span>
          <div v-if="r.note" class="note-sm">{{ r.note }}</div>
        </li>
      </ul>
      <template v-if="props.result.blockedRelations?.length">
        <h3 style="font-size: var(--t-md); margin: var(--s-4) 0 var(--s-2)">未成立的候选</h3>
        <ul class="report-sec-body" style="padding-left: 1.2em">
          <li v-for="(r, i) in props.result.blockedRelations" :key="i">
            {{ r.label }}［{{ r.positions.map(positionShortCn).join(" · ") }}］
            <span v-if="r.note" class="note-sm">{{ r.note }}</span>
          </li>
        </ul>
      </template>
    </section>

    <!-- 07 岁运 -->
    <section class="report-sec" id="sec-temporal">
      <div class="report-sec-head">
        <span class="report-sec-idx">07</span>
        <h2 class="report-sec-title">岁运</h2>
      </div>
      <template v-if="props.temporal">
        <dl class="report-dl">
          <dt>原局</dt>
          <dd class="mono">
            {{ (props.temporal.context?.natalStems ?? []).map((s: string, i: number) => `${s ?? ""}${(props.temporal.context?.natalBranches ?? [])[i] ?? ""}`).filter(Boolean).join(" ") }}
          </dd>
          <template v-if="props.temporal.context?.luckStem">
            <dt>大运</dt><dd class="mono">{{ props.temporal.context.luckStem }}{{ props.temporal.context.luckBranch }}</dd>
          </template>
          <template v-if="props.temporal.context?.annualStem">
            <dt>流年</dt><dd class="mono">{{ props.temporal.context.annualStem }}{{ props.temporal.context.annualBranch }}（{{ props.temporal.context.annualYear }}）</dd>
          </template>
          <template v-if="props.temporal.context?.monthlyStem">
            <dt>流月</dt><dd class="mono">{{ props.temporal.context.monthlyStem }}{{ props.temporal.context.monthlyBranch }}</dd>
          </template>
          <template v-if="props.temporal.context?.dailyStem">
            <dt>流日</dt><dd class="mono">{{ props.temporal.context.dailyStem }}{{ props.temporal.context.dailyBranch }}</dd>
          </template>
        </dl>

        <div v-if="props.temporal.ruleTriggers?.length" style="margin-top: var(--s-5)">
          <h3 style="font-size: var(--t-md); margin-bottom: var(--s-2)">
            规则触发（命中 {{ props.temporal.ruleTriggers.filter((t: any) => t.matched).length }} / {{ props.temporal.ruleTriggers.length }}）
          </h3>
          <ul class="report-sec-body" style="padding-left: 1.2em">
            <li v-for="t in props.temporal.ruleTriggers.filter((x: any) => x.matched)" :key="t.ruleId">
              <span class="mono">{{ t.ruleId }}</span> {{ t.label }}
              <div v-for="(o, i) in t.observations" :key="i" class="note-sm">{{ o }}</div>
            </li>
          </ul>
        </div>

        <div v-if="props.temporal.delta" style="margin-top: var(--s-5)">
          <h3 style="font-size: var(--t-md); margin-bottom: var(--s-2)">状态差异（Temporal Delta）</h3>
          <ul class="report-sec-body" style="padding-left: 1.2em">
            <li v-for="(it, i) in props.temporal.delta.items ?? []" :key="i">
              <span class="mono">{{ it.analysis }}</span> · {{ it.kind }} · {{ it.subject }}
              <template v-if="it.natalValue !== null || it.temporalValue !== null">
                ：{{ JSON.stringify(it.natalValue) }} → {{ JSON.stringify(it.temporalValue) }}
              </template>
              <span v-if="it.supportLevel === 'EXPERIMENTAL'" class="note-sm">［EXPERIMENTAL］</span>
            </li>
          </ul>
        </div>

        <div v-if="props.temporal.replay?.steps?.length" style="margin-top: var(--s-5)">
          <h3 style="font-size: var(--t-md); margin-bottom: var(--s-2)">逐层状态回放</h3>
          <ul class="report-sec-body" style="padding-left: 1.2em">
            <li v-for="(st, i) in props.temporal.replay.steps" :key="i">
              <span class="mono">{{ st.layer }}{{ st.ganzhi ? " " + st.ganzhi : "" }}</span>：{{ st.note }}
            </li>
          </ul>
        </div>
      </template>
      <p v-else class="report-sec-body">
        本次未加载岁运分析。可在「岁运时序」中选择大运与流年后重新生成。
      </p>
    </section>

    <!-- 08 证据链 -->
    <section class="report-sec" id="sec-evidence">
      <div class="report-sec-head">
        <span class="report-sec-idx">08</span>
        <h2 class="report-sec-title">证据链</h2>
      </div>

      <h3 style="font-size: var(--t-md); margin-bottom: var(--s-3)">古籍引文（{{ citations.length }}）</h3>
      <div v-if="citations.length" class="stack stack-4">
        <div v-for="(c, i) in citations" :key="i">
          <div class="note-sm" style="margin-bottom: 4px">
            <StatusBadge :label="c.label ?? '调候'" variant="mute" />
            <StatusBadge v-for="rid in c.ruleIds ?? []" :key="rid" :code="rid" variant="rule" />
          </div>
          <Citation
            :quote="c.quote"
            :book="c.book"
            :title="c.title"
            :candidate-id="c.candidateId"
            :source-kind="c.sourceKind"
            :ocr-risk="c.ocrRisk"
          />
          <p v-if="c.pages?.length" class="note-sm" style="margin-top: 4px">
            出处页码：PDF 第 {{ c.pages.join("-") }} 页
          </p>
        </div>
      </div>
      <p v-else class="report-sec-body">本次分析未附带古籍引文。</p>

      <h3 style="font-size: var(--t-md); margin: var(--s-5) 0 var(--s-3)">
        引擎与 schema 版本
      </h3>
      <dl class="report-dl">
        <dt>引擎</dt><dd class="mono">{{ props.result.meta?.engineVersion ?? props.engineVersion ?? "—" }}</dd>
        <dt>分析 schema</dt><dd class="mono">{{ props.result.meta?.analysisSchemaVersion }}</dd>
        <dt>知识 schema</dt><dd class="mono">{{ props.result.meta?.knowledgeSchemaVersion }}</dd>
        <dt>命例 schema</dt><dd class="mono">{{ props.result.meta?.caseSchemaVersion }}</dd>
      </dl>
    </section>

    <!-- 09 AI 辅助解读 -->
    <section class="report-sec" id="sec-ai">
      <div class="report-sec-head">
        <span class="report-sec-idx">09</span>
        <h2 class="report-sec-title">AI 辅助解读</h2>
      </div>
      <template v-if="props.aiResult?.summary">
        <p class="report-sec-body" style="font-family: var(--font-display); font-size: var(--t-lg)">
          {{ props.aiResult.summary }}
        </p>
        <div class="stack stack-4" style="margin-top: var(--s-4)">
          <div v-for="sec in props.aiResult.sections ?? []" :key="sec.type + sec.title">
            <h3 style="font-size: var(--t-md); margin-bottom: var(--s-2)">{{ sec.title }}</h3>
            <p class="report-sec-body" style="white-space: pre-line">{{ sec.content }}</p>
          </div>
        </div>
        <div v-if="props.aiResult.disagreements?.length" style="margin-top: var(--s-4)">
          <h3 style="font-size: var(--t-md); margin-bottom: var(--s-2)">分歧</h3>
          <ul class="report-sec-body" style="padding-left: 1.2em">
            <li v-for="d in props.aiResult.disagreements" :key="d">{{ d }}</li>
          </ul>
        </div>
        <div v-if="props.aiResult.uncertainties?.length" style="margin-top: var(--s-4)">
          <h3 style="font-size: var(--t-md); margin-bottom: var(--s-2)">不确定项</h3>
          <ul class="report-sec-body" style="padding-left: 1.2em">
            <li v-for="u in props.aiResult.uncertainties" :key="u">{{ u }}</li>
          </ul>
        </div>
        <p class="note" style="margin-top: var(--s-3)">
          <template v-if="props.aiResult.groundingPassed === true">以上 AI 文本已通过事实一致性校验；它仅解释引擎已给出的结构，不构成结论。</template>
          <template v-else-if="props.aiResult.groundingPassed === false">以上 AI 文本未通过事实一致性校验，请以引擎证据为准，不应作为已核实结论。</template>
          <template v-else>以上 AI 文本的事实一致性校验状态未知，请核对引擎证据。</template>
        </p>
        <ul v-if="props.aiResult.groundingIssues?.length" class="report-sec-body">
          <li v-for="(issue, index) in props.aiResult.groundingIssues" :key="index">{{ issue.detail }}</li>
        </ul>
      </template>
      <p v-else-if="!props.aiConfigured" class="report-sec-body">
        未配置 AI 服务，本次报告不含 AI 辅助解读。确定性命理分析不受影响。
      </p>
      <p v-else class="report-sec-body">
        已配置 AI 服务但本次尚未生成解读。可在「AI 解读」页生成后再回到本页查看。
      </p>
    </section>

    <!-- 10 边界与限制 -->
    <section class="report-sec" id="sec-boundary">
      <div class="report-sec-head">
        <span class="report-sec-idx">10</span>
        <h2 class="report-sec-title">边界与限制</h2>
      </div>

      <ol class="report-sec-body" style="padding-left: 1.3em">
        <li>本报告为<strong>结构分析</strong>，不构成任何吉凶、成败、健康、婚姻等现实事件的预测或建议。</li>
        <li>候选状态（CANDIDATE / LIKELY / DISPUTED / UNRESOLVED / EXPERIMENTAL）均<strong>不是确定性结论</strong>。</li>
        <li>多方法与多流派分歧处一律并列呈现，工具不代为裁决。</li>
        <li>「事件主题」为结构层面的关注候选，置信度为工程启发式加权，<strong>不是概率</strong>，也无 CONFIRMED 状态。</li>
        <li>AI 解读仅辅助解释引擎结果；存在一致性校验偏差时显示警示，不能替代引擎证据。</li>
      </ol>

      <div v-if="props.result.warnings?.length" style="margin-top: var(--s-5)">
        <h3 style="font-size: var(--t-md); margin-bottom: var(--s-2)">引擎注意事项</h3>
        <ul class="report-sec-body" style="padding-left: 1.2em">
          <li v-for="w in props.result.warnings" :key="w">{{ w }}</li>
        </ul>
      </div>

      <div v-if="props.result.fallbacks?.length" style="margin-top: var(--s-4)">
        <h3 style="font-size: var(--t-md); margin-bottom: var(--s-2)">降级说明</h3>
        <ul class="report-sec-body" style="padding-left: 1.2em">
          <li v-for="f in props.result.fallbacks" :key="f">{{ f }}</li>
        </ul>
      </div>

      <div v-if="props.result.missingCapabilities?.length" style="margin-top: var(--s-4)">
        <h3 style="font-size: var(--t-md); margin-bottom: var(--s-2)">缺席能力</h3>
        <ul class="report-sec-body" style="padding-left: 1.2em">
          <li v-for="m in props.result.missingCapabilities" :key="m">{{ m }}</li>
        </ul>
      </div>

      <div class="notice is-boundary" style="margin-top: var(--s-5)">
        <span class="notice-key">导出分工</span>
        <span>
          本页是引擎结果的呈现层汇编，供浏览器内通读与打印为 PDF。
          权威的 Markdown / HTML 报告导出由命令行完成：
          <code>tianze export</code>（实现见 <code>tianze/export.py</code> 与
          <code>tianze/export_html.py</code>）。两者内容同源，本页不新增任何结论。
        </span>
      </div>
    </section>
  </div>
</template>
