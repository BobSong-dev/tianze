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
import { onMounted, watch } from "vue";
import { aiConfigStore } from "../composables/useAiConfig";

const props = defineProps<{ open: boolean }>();
const emit = defineEmits<{ (e: "close"): void }>();

const ai = aiConfigStore();

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
    <div class="modal ai-modal">
      <div class="modal-head">
        <div class="modal-head-text">
          <div class="modal-title">AI 服务设置</div>
          <p class="modal-sub">
            用于生成基于当前证据链的辅助解释。不配置时，全部确定性分析仍在本地完成。
          </p>
        </div>
        <button class="modal-close" type="button" aria-label="关闭" @click="emit('close')">×</button>
      </div>

      <div class="modal-body">
        <!-- 当前状态 -->
        <div class="ai-status ai-status-strip" :class="ai.configured.value ? 'is-on' : 'is-off'">
          <span class="ai-dot" :class="ai.configured.value ? 'is-on' : 'is-off'" aria-hidden="true" />
          <span class="ai-status-label">当前</span>
          <span class="ai-status-meta">
            {{ ai.sourceLabel.value }}
            <template v-if="ai.configured.value && ai.status.value?.model">
              · {{ ai.status.value.model }}
            </template>
            <template v-if="ai.status.value?.keyMasked"> · {{ ai.status.value.keyMasked }}</template>
          </span>
        </div>

        <p v-if="ai.source.value === 'env'" class="notice is-boundary mt-3">
          <span class="notice-key">环境变量优先</span>
          <span>
            检测到 TIANZE_LLM_API_KEY 环境变量，实际调用使用环境变量配置；
            下方页面配置会被覆盖，可保留以备后用。
          </span>
        </p>

        <!-- Provider 选择 -->
        <div class="sec-sub" style="margin-top: var(--s-5)">
          <h3>服务商</h3>
          <span class="sec-sub-note">OpenAI 兼容端点 · 预设仅为便利填充，未逐一实测者不标记已验证</span>
        </div>
        <div class="preset-grid prov-grid">
          <button
            v-for="p in ai.presets.value"
            :key="p.id"
            type="button"
            class="preset-card prov-card"
            :class="{ selected: ai.form.value.preset === p.id, 'is-selected': ai.form.value.preset === p.id }"
            @click="ai.pickPreset(p)"
          >
            <span class="prov-name">{{ p.name }} <span class="prov-proto">{{ p.protocol === "anthropic" ? "/v1/messages" : "chat/completions" }}</span></span>
            <span class="prov-url" :title="p.baseUrl || '自定义端点'">{{ p.baseUrl || "— 自定义端点 —" }}</span>
            <span v-if="p.note" class="prov-note">{{ p.note }}</span>
            <span class="prov-flag">
              {{ p.verified ? "已验证" : "预设（未逐一实测）" }}
              <template v-if="p.allowLocal"> · 本机地址</template>
            </span>
          </button>
        </div>

        <!-- 凭据 -->
        <div class="sec-sub">
          <h3>连接参数</h3>
          <span class="sec-sub-note">Base URL 需为 OpenAI 兼容端点（…/v1）</span>
        </div>
        <div class="ai-form-row field">
          <span class="field-label">
            API Key
            <span class="mono">仅存服务端内存</span>
          </span>
          <input
            v-model="ai.form.value.apiKey"
            type="password"
            placeholder="sk-…"
            autocomplete="off"
            spellcheck="false"
          />
          <span class="field-hint">
            密钥不回显、不落盘、不写入浏览器存储；服务重启后需重新填写。
          </span>
        </div>
        <div class="ai-form-row field">
          <span class="field-label">Base URL <span class="mono">OpenAI 兼容端点</span></span>
          <input
            v-model="ai.form.value.baseUrl"
            placeholder="https://api.deepseek.com/v1"
            autocomplete="off"
            spellcheck="false"
          />
        </div>
        <div class="ai-form-row field">
          <span class="field-label">模型名称 <span class="mono">model</span></span>
          <input
            v-model="ai.form.value.model"
            :placeholder="ai.activePreset.value?.model || 'gpt-4o-mini'"
            autocomplete="off"
            spellcheck="false"
          />
        </div>

        <!-- 结果消息：必须是 modal 内第一个 p.note -->
        <p v-if="ai.message.value" class="note" :class="`msg-${ai.messageTone.value}`" style="margin-top: var(--s-4)">
          {{ ai.message.value }}
        </p>

        <div v-if="ai.testResult.value" class="test-result mt-3"
             :class="ai.testResult.value.ok ? 'is-ok' : 'is-fail'">
          <span class="mono">{{ ai.testResult.value.ok ? "OK" : "FAIL" }}</span>
          <span>
            {{ ai.testResult.value.ok
              ? `连接成功 · ${ai.testResult.value.provider ?? ""}`
              : (ai.testResult.value.error || "测试失败") }}
          </span>
        </div>
      </div>

      <div class="modal-foot">
        <button class="btn-primary" type="button" :disabled="ai.saving.value" @click="ai.save()">
          {{ ai.saving.value ? "保存中…" : "保存配置" }}
        </button>
        <button type="button" :disabled="ai.testing.value" @click="ai.test()">
          {{ ai.testing.value ? "测试中…" : "测试连接" }}
        </button>
        <button v-if="ai.source.value === 'ui'" type="button" @click="ai.clear()">清除配置</button>
        <button class="btn-link" type="button" style="margin-left: auto" @click="emit('close')">
          关闭
        </button>
      </div>

      <div class="modal-foot" style="border-top: none; padding-top: 0; display: block">
        <p class="note">
          <strong>数据边界</strong>：启用 AI 解读后，当前命盘分析结果（含由出生信息派生的四柱、
          结构与证据摘要）将发送至你配置的第三方模型服务。API Key 仅保存在当前 Tianze
          进程内存中，服务重启后清除。配置操作仅限本机访问（单用户本地模式）；
          公网部署须由运维在反向代理层加鉴权，详见 <code>docs/known-limitations.md</code>。
        </p>
      </div>
    </div>
  </div>
</template>
