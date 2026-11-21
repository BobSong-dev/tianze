<script setup lang="ts">
/**
 * AIProviderDialog — AI 服务配置。
 *
 * 后端能力（OpenAI / DeepSeek / 通义千问 / 智谱 GLM / Ollama 等本地端点 / 自定义）
 * 全部保留；本组件只重做呈现与信息层级，不改任何接口行为。
 *
 * 必须明确告知用户（不可隐藏）：
 *  1) API Key 仅保存在当前 Tianze 进程内存中，服务重启后清除；
 *  2) AI 解读会将当前命盘相关信息发送至所配置的第三方模型服务；
 *  3) 配置操作仅限本机访问（后端强制），公网部署须自行加鉴权。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { aiConfigStore } from "../composables/useAiConfig";
import { useFocusTrap } from "../composables/useFocusTrap";
import UiIcon from "./UiIcon.vue";

const props = defineProps<{ open: boolean }>();
const emit = defineEmits<{ (e: "close"): void }>();

const ai = aiConfigStore();
const modal = ref<HTMLElement | null>(null);
useFocusTrap(computed(() => props.open), modal, () => emit("close"));
watch(() => props.open, open => document.body.classList.toggle("is-modal-open", open));
onBeforeUnmount(() => document.body.classList.remove("is-modal-open"));

onMounted(() => { void ai.refresh(); });
watch(() => props.open, (v) => { if (v) void ai.refresh(); });
</script>

<template>
  <div
    v-if="props.open"
    class="modal-mask"
    role="dialog"
    aria-modal="true"
    aria-label="AI 服务设置"
    @click.self="emit('close')"
  >
    <div ref="modal" class="modal ai-modal">
      <div class="modal-head">
        <span class="connection-symbol"><UiIcon name="settings" :size="24" /></span>
        <div class="modal-head-text">
          <h2 class="modal-title">AI 服务设置</h2>
          <p class="modal-sub">为命盘解读连接模型服务。</p>
        </div>
        <button class="modal-close" type="button" aria-label="关闭" @click="emit('close')"><UiIcon name="close" /></button>
      </div>

      <div class="modal-body">
        <div v-if="ai.loadError.value" class="error" role="alert">
          <span>{{ ai.loadError.value }}</span><button type="button" @click="ai.refresh()">重新加载状态</button>
        </div>
        <p v-if="ai.source.value === 'env'" class="notice is-boundary mt-3">
          <span class="notice-key">环境变量优先</span>
          <span>
            检测到 TIANZE_LLM_API_KEY 环境变量，实际调用使用环境变量配置；
            下方页面配置会被覆盖，可保留以备后用。
          </span>
        </p>

        <div class="connection-layout">
        <section class="connection-presets" aria-labelledby="provider-heading">
        <h3 id="provider-heading">选择服务商</h3>
        <div class="preset-grid prov-grid">
          <button
            v-for="p in ai.presets.value"
            :key="p.id"
            type="button"
            class="preset-card prov-card"
            :class="{ selected: ai.form.value.preset === p.id, 'is-selected': ai.form.value.preset === p.id }"
            :aria-pressed="ai.form.value.preset === p.id"
            @click="ai.pickPreset(p)"
          >
            <span class="prov-name">{{ p.name }}</span>
            <span class="prov-indicator" aria-hidden="true" />
          </button>
        </div>
        <p v-if="ai.activePreset.value" class="preset-caption">
          {{ ai.activePreset.value.protocol === 'anthropic' ? '/v1/messages' : 'chat/completions' }}
          · {{ ai.activePreset.value.verified ? '已验证' : '预设待验证' }}<template v-if="ai.activePreset.value.allowLocal"> · 支持本机地址</template>
          <span v-if="ai.activePreset.value.note">{{ ai.activePreset.value.note }}</span>
        </p>
        <p v-else class="preset-caption">手动填写时默认使用 OpenAI 兼容协议。</p>
        </section>

        <section class="connection-fields" aria-labelledby="connection-heading">
        <div class="connection-heading">
          <h3 id="connection-heading">连接参数</h3>
          <span class="ai-status-meta connection-status">
            <span class="ai-dot" :class="ai.configured.value ? 'is-on' : 'is-off'" aria-hidden="true" />
            {{ ai.loadError.value ? '状态待确认' : ai.sourceLabel.value }}
            <template v-if="ai.configured.value && ai.status.value?.model"> · {{ ai.status.value.model }}</template>
            <template v-if="ai.status.value?.keyMasked"> · {{ ai.status.value.keyMasked }}</template>
          </span>
        </div>
        <div class="ai-form-row field">
          <label for="provider-key" class="field-label">API Key</label>
          <input
            id="provider-key"
            aria-describedby="provider-key-hint"
            v-model="ai.form.value.apiKey"
            type="password"
            placeholder="粘贴服务商提供的密钥"
            autocomplete="off"
            spellcheck="false"
          />
          <span id="provider-key-hint" class="field-hint">密钥仅存于本机服务内存，重启后需重新填写。</span>
        </div>
        <div class="ai-form-row field">
          <label for="provider-url" class="field-label">服务地址 <span class="mono">Base URL</span></label>
          <input
            id="provider-url"
            aria-label="Base URL"
            v-model="ai.form.value.baseUrl"
            placeholder="https://api.deepseek.com/v1"
            autocomplete="off"
            spellcheck="false"
          />
        </div>
        <div class="ai-form-row field">
          <label for="provider-model" class="field-label">模型名称</label>
          <input
            id="provider-model"
            aria-label="模型名称"
            v-model="ai.form.value.model"
            :placeholder="ai.activePreset.value?.model || 'gpt-4o-mini'"
            autocomplete="off"
            spellcheck="false"
          />
        </div>
        </section>
        </div>

        <p class="connection-privacy"><strong>数据使用</strong>生成 AI 解读时，四柱、结构和证据摘要会发送给所选服务商。排盘分析在本地完成。配置仅限本机访问，公网部署需另设鉴权。</p>
      </div>

      <div class="connection-actions">
        <p v-if="ai.message.value" class="note action-feedback" :role="ai.messageTone.value === 'err' ? 'alert' : 'status'" :class="`msg-${ai.messageTone.value}`">
          {{ ai.message.value }}
        </p>

        <div v-if="ai.testResult.value" class="test-result action-feedback" role="status"
             :class="ai.testResult.value.ok ? 'is-ok' : 'is-fail'">
          <span>
            {{ ai.testResult.value.ok
              ? `连接成功 · ${ai.testResult.value.provider ?? ""}`
              : (ai.testResult.value.error || "测试失败") }}
          </span>
        </div>
      <div class="modal-foot">
        <button class="test-connection" title="测试当前已保存的连接" type="button" :disabled="ai.testing.value" @click="ai.test()">
          {{ ai.testing.value ? "测试中…" : "测试连接" }}
        </button>
        <button v-if="ai.source.value === 'ui'" class="clear-connection" type="button" :disabled="ai.saving.value || ai.clearing.value" @click="ai.clear()">{{ ai.clearing.value ? "清除中…" : "清除配置" }}</button>
        <button class="cancel-connection" type="button" @click="emit('close')">关闭</button>
        <button class="btn-primary" type="button" :disabled="ai.saving.value || ai.clearing.value" @click="ai.save()">
          {{ ai.saving.value ? "保存中…" : "保存配置" }}
        </button>
      </div>
      </div>
    </div>
  </div>
</template>
