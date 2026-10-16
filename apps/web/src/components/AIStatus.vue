<script setup lang="ts">
/**
 * AIStatus — AI 服务状态条。
 * 契约：受控文案「未配置」/「页面配置」/「环境变量配置」必须原样出现（用户可感）。
 */
import { computed } from "vue";
import type { AiConfigStatus } from "../api/tianze";

const props = defineProps<{
  status: AiConfigStatus | null;
  sourceLabel: string;
  configured: boolean;
  /** 状态条上的操作按钮 */
  showActions?: boolean;
}>();

const emit = defineEmits<{ (e: "configure"): void; (e: "test"): void }>();

const tone = computed(() => {
  if (!props.configured) return "is-off";
  return "is-on";
});

/** 单一文本节点：保证"页面配置 · <model>"与"未配置"都是完整子串 */
const metaText = computed(() => {
  if (!props.configured) return "未配置 · 确定性分析不受影响";
  const st = props.status;
  const parts = [props.sourceLabel];
  if (st?.model) parts.push(st.model);
  if (st?.keyMasked) parts.push(st.keyMasked);
  return parts.join(" · ");
});
</script>

<template>
  <div class="ai-status ai-status-strip" :class="tone">
    <span class="ai-dot" :class="props.configured ? 'is-on' : 'is-off'" aria-hidden="true" />
    <span class="ai-status-label">AI 解读</span>
    <span class="ai-status-meta">{{ metaText }}</span>
    <div v-if="props.showActions !== false" class="ai-status-actions">
      <button
        v-if="props.configured"
        class="btn-sm"
        type="button"
        @click="emit('test')"
      >测试连接</button>
      <button class="btn-sm" type="button" @click="emit('configure')">
        {{ props.configured ? "修改配置" : "配置 AI" }}
      </button>
    </div>
  </div>
</template>
