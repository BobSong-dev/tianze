<script setup lang="ts">
/**
 * AiView — AI 解读。
 *
 * 定位：AI 只解释引擎已算出的结构与候选，不自行推算；输出经事实一致性校验。
 * 纪律：AI 状态与配置入口在本页显著可见；配置入口同时存在于顶栏与设置弹窗
 *       （共三处：全局导航、本页状态区、未配置引导区），用户无需寻找。
 */
import { computed } from "vue";
import AIStatus from "../components/AIStatus.vue";
import StatusBadge from "../components/StatusBadge.vue";
import { STATUS_MAP } from "../presentation/vocab";

const props = defineProps<{
  aiStatus: any;
  aiSourceLabel: string;
  aiConfigured: boolean;
  aiState: string;
  aiResult: any;
  aiError: string;
  hasResult: boolean;
  temporalLoaded: boolean;
}>();

const emit = defineEmits<{
  (e: "configure"): void;
  (e: "test"): void;
  (e: "generate"): void;
}>();

const groundingIssues = computed(() => props.aiResult?.groundingIssues ?? []);

const sectionTypeCn: Record<string, string> = {
  overview: "总体", personality: "性格", career: "事业求财",
  relationships: "感情人际", recent_trend: "近年走向", honesty: "如实说明",
  strength: "旺衰", pattern: "格局", tiaohou: "调候", relations: "关系",
  temporal: "岁运", structure: "结构", summary: "总述", caveat: "边界",
};
</script>

<template>
  <div class="stack stack-5">
    <!-- AI 状态：本页第一屏必须可见 -->
    <section>
      <AIStatus
        :status="props.aiStatus"
        :source-label="props.aiSourceLabel"
        :configured="props.aiConfigured"
        @configure="emit('configure')"
        @test="emit('test')"
      />
    </section>

    <!-- 数据边界：不隐藏 -->
    <div class="notice is-privacy">
      <span class="notice-key">数据边界</span>
      <span>
        启用后，当前命盘分析结果（含由出生信息派生的四柱、结构与证据摘要）将发送至
        你配置的第三方模型服务。不配置时，全部确定性分析仍在本机完成，不产生任何外发请求。
      </span>
    </div>

    <div class="notice">
      <span class="notice-key">方法边界</span>
      <span>
        AI 用大白话帮你理解排盘结果；它不做预测（不算吉凶、不算婚期财运），
        说法与系统对不上的地方会如实标出来。
      </span>
    </div>

    <!-- 一致性校验未通过：M51 起不再隐藏内容——照常展示 + 顶部醒目警示
         （真实 Provider 常有少量引用偏差，一票否决会让用户永远看不到结果） -->
    <section v-if="props.aiState === 'GROUNDING_FAILED' || props.aiState === 'GROUNDING_UNKNOWN'" class="ai-state is-warn-state" role="alert">
      <div v-if="props.aiState === 'GROUNDING_UNKNOWN'" class="ai-state-title">这次解读的事实一致性校验状态未知</div>
      <div v-else class="ai-state-title">⚠ 这次解读未通过事实一致性校验（{{ groundingIssues.length }} 处问题）</div>
      <p class="ai-state-body">
        内容照常展示；请在下方「查看依据与技术细节」中核对校验问题。
        拿不准的说法以页面上的确定性分析为准；也可以点「重新生成」试试更干净的结果。
      </p>
      <div class="ai-state-actions">
        <button class="btn-primary" type="button" @click="emit('generate')">重新生成</button>
      </div>

    </section>

    <!-- 未配置：引导 -->
    <section v-if="!props.aiConfigured || props.aiState === 'NOT_CONFIGURED'" class="ai-state">
      <div class="ai-state-title">尚未配置 AI 服务</div>
      <p class="ai-state-body">
        确定性命理分析不受影响。配置一个 OpenAI 兼容服务后，即可生成基于当前证据链的辅助解释。
      </p>
      <div class="ai-state-actions">
        <button class="btn-primary" type="button" @click="emit('configure')">配置 AI 服务</button>
      </div>
    </section>

    <!-- 已配置：空闲 -->
    <section v-else-if="props.aiState === 'IDLE'" class="ai-state">
      <div class="ai-state-title">可以生成 AI 解读</div>
      <p class="ai-state-body">
        <template v-if="props.temporalLoaded">
          当前会连同已加载的岁运上下文一并作为解释输入。
        </template>
        <template v-else>
          当前仅包含原局分析结果。若已加载岁运时序，将一并作为解释输入。
        </template>
      </p>
      <div class="ai-state-actions">
        <button class="btn-primary btn-lg" type="button" @click="emit('generate')">
          生成 AI 解读
        </button>
      </div>
    </section>

    <!-- 生成中 -->
    <section v-else-if="props.aiState === 'LOADING'" class="ai-state">
      <div class="ai-state-title">正在生成解释</div>
      <p class="ai-state-body">
        请求已发送至你配置的服务，正在基于 Tianze 的结构与证据生成解释，请稍候。
      </p>
      <div class="ai-state-actions">
        <span class="badge is-mute">处理中…</span>
      </div>
    </section>


    <!-- Provider 错误 -->
    <section v-else-if="props.aiState === 'PROVIDER_ERROR'" class="ai-state">
      <div class="ai-state-title">AI 服务调用失败</div>
      <p class="ai-state-body">{{ props.aiError }}</p>
      <div class="ai-state-actions">
        <button class="btn-primary" type="button" @click="emit('generate')">重试</button>
        <button type="button" @click="emit('configure')">检查配置</button>
        <button type="button" @click="emit('test')">测试连接</button>
      </div>
    </section>

    <!-- 成功 -->
    <template v-else-if="['SUCCESS', 'GROUNDING_FAILED', 'GROUNDING_UNKNOWN'].includes(props.aiState) && props.aiResult">
      <section class="verdict">
        <span class="verdict-kicker">AI 辅助解读</span>
        <p class="verdict-text" style="font-size: var(--t-md); line-height: var(--lh-loose)">
          {{ props.aiResult.summary }}
        </p>
        <div class="verdict-meta">
          <span class="note">AI 解读仅帮助你理解，不预测具体事件；依据可在下方「查看依据」中核对</span>
        </div>
      </section>

      <section class="stack stack-3">
        <article
          v-for="sec in props.aiResult.sections || []"
          :key="sec.type + sec.title"
          class="ai-section"
        >
          <div class="ai-section-head">
            <span class="ai-section-title">{{ sec.title }}</span>
            <StatusBadge
              :label="sectionTypeCn[sec.type] ?? sec.type"
              variant="mute"
              :title="sec.type"
            />
          </div>
          <p class="ai-section-body">{{ sec.content }}</p>
        </article>
      </section>

      <!-- 查看依据：技术细节统一折叠（小白默认不看；愿意深挖的用户展开） -->
      <details class="ai-evidence-fold mt-2">
        <summary>查看依据与技术细节（引用编号 / 分歧 / 校验结果）</summary>
        <div class="stack stack-3 mt-3">
          <section v-for="sec in props.aiResult.sections || []" :key="'ev-' + sec.type + sec.title">
            <div class="note-sm" style="margin-bottom: 4px">{{ sec.title }}</div>
            <div v-if="sec.claims?.length || sec.sourceIds?.length" class="row row-1">
              <StatusBadge
                v-for="c in sec.claims || []"
                :key="String(c.refId)"
                :code="String(c.refId)"
                variant="rule"
                :title="String(c.type ?? '')"
              />
              <StatusBadge
                v-for="sid in sec.sourceIds || []"
                :key="sid"
                :code="String(sid)"
                variant="mute"
              />
            </div>
            <p v-if="!sec.claims?.length && !sec.sourceIds?.length" class="note">（本段未附引用编号）</p>
          </section>

          <section v-if="props.aiResult.disagreements?.length">
            <div class="note-sm" style="margin-bottom: 4px">分析分歧（各流派说法不一之处）</div>
            <div class="stack stack-2">
              <div v-for="d in props.aiResult.disagreements" :key="d" class="ev evidence-item is-warn">
                <span class="ev-mark">⚠</span><span class="ev-body">{{ d }}</span>
              </div>
            </div>
          </section>

          <section v-if="props.aiResult.uncertainties?.length">
            <div class="note-sm" style="margin-bottom: 4px">不确定项（证据不足，如实保留疑问）</div>
            <div class="stack stack-2">
              <div v-for="u in props.aiResult.uncertainties" :key="u" class="ev evidence-item is-quiet">
                <span class="ev-mark">·</span><span class="ev-body">{{ u }}</span>
              </div>
            </div>
          </section>

          <section v-if="groundingIssues.length">
            <div class="note-sm" style="margin-bottom: 4px">一致性校验问题（模型说法与引擎对不上的地方）</div>
            <div class="stack stack-2">
              <div v-for="(gi, i) in groundingIssues" :key="'g' + i" class="ev evidence-item is-minus">
                <span class="ev-mark">!</span><span class="ev-body">{{ gi.detail }}</span>
              </div>
            </div>
          </section>
        </div>
      </details>

      <div class="row row-3 mt-4">
        <button class="btn-primary" type="button" @click="emit('generate')">重新生成</button>
        <button type="button" @click="emit('configure')">修改配置</button>
      </div>
    </template>

    <p v-if="!props.hasResult" class="empty">
      请先完成一次排盘，再使用 AI 解读。
    </p>
  </div>
</template>
