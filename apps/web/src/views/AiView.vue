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
        AI 只解释引擎已计算的结构与候选，不得自行推算新结论；输出经事实一致性校验，
        未通过的条目会标注警示（不隐藏内容）。AI 文本不构成吉凶或事件预测。
      </span>
    </div>

    <!-- 一致性校验未通过：M51 起不再隐藏内容——照常展示 + 顶部醒目警示
         （真实 Provider 常有少量引用偏差，一票否决会让用户永远看不到结果） -->
    <section v-if="props.aiState === 'GROUNDING_FAILED'" class="ai-state is-warn-state">
      <div class="ai-state-title">⚠ 本次输出有 {{ groundingIssues.length }} 项未通过事实一致性校验</div>
      <p class="ai-state-body">
        以下解读内容照常展示，但模型引用的部分证据 ID 不在引擎事实库中（或含越界表述）。
        带 ! 标记的问题明细见下方；相关表述请以引擎确定性分析为准。可重新生成以获得更干净的输出。
      </p>
      <div class="ai-state-actions">
        <button class="btn-primary" type="button" @click="emit('generate')">重新生成</button>
      </div>

      <details v-if="groundingIssues.length" style="margin-top: var(--s-5); text-align: left">
        <summary>一致性问题明细（{{ groundingIssues.length }}）</summary>
        <div class="stack stack-2 mt-3">
          <div
            v-for="(gi, i) in groundingIssues"
            :key="i"
            class="ev evidence-item is-minus"
          >
            <span class="ev-mark">!</span>
            <span class="ev-body">
              <StatusBadge :code="gi.severity" with-hint />
              <span class="mono">{{ gi.type }}</span>
              <div>{{ gi.detail }}</div>
            </span>
          </div>
        </div>
      </details>
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
    <template v-else-if="(props.aiState === 'SUCCESS' || props.aiState === 'GROUNDING_FAILED') && props.aiResult">
      <section class="verdict">
        <span class="verdict-kicker">AI 辅助解读</span>
        <p class="verdict-text" style="font-size: var(--t-md); line-height: var(--lh-loose)">
          {{ props.aiResult.summary }}
        </p>
        <div class="verdict-meta">
          <StatusBadge label="已通过事实一致性校验" variant="pos" />
          <StatusBadge :label="`段落 ${props.aiResult.sections?.length ?? 0}`" variant="mute" />
          <span class="note">AI 文本仅辅助理解，请以证据链为准</span>
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

          <div v-if="sec.claims?.length" class="mt-3">
            <div class="note-sm" style="margin-bottom: 4px">引用依据</div>
            <div class="row row-1">
              <StatusBadge
                v-for="c in sec.claims"
                :key="String(c.refId)"
                :code="String(c.refId)"
                variant="rule"
                :title="String(c.type ?? '')"
              />
            </div>
          </div>

          <details v-if="sec.sourceIds?.length" class="mt-3">
            <summary>来源（{{ sec.sourceIds.length }}）</summary>
            <div class="stack stack-1 mt-2">
              <p v-for="sid in sec.sourceIds" :key="sid" class="note mono">{{ sid }}</p>
            </div>
          </details>
        </article>
      </section>

      <section v-if="props.aiResult.disagreements?.length">
        <div class="sec-sub" style="margin-top: 0">
          <h3>分析分歧</h3>
          <span class="sec-sub-note">AI 指出的引擎内部或流派分歧点</span>
        </div>
        <div class="stack stack-2">
          <div v-for="d in props.aiResult.disagreements" :key="d" class="ev evidence-item is-warn">
            <span class="ev-mark">⚠</span><span class="ev-body">{{ d }}</span>
          </div>
        </div>
      </section>

      <section v-if="props.aiResult.uncertainties?.length">
        <div class="sec-sub" style="margin-top: 0">
          <h3>不确定项</h3>
          <span class="sec-sub-note">证据不足或存在学派分歧之处，保持未判定</span>
        </div>
        <div class="stack stack-2">
          <div v-for="u in props.aiResult.uncertainties" :key="u" class="ev evidence-item is-quiet">
            <span class="ev-mark">·</span><span class="ev-body">{{ u }}</span>
          </div>
        </div>
      </section>

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
