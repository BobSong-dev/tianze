<script setup lang="ts">
/**
 * Citation — 古籍引文（论文级版式）。
 * 消费后端 citations（candidateId/book/title/quote/sourceKind/ocrRisk）。
 * OCR 风险如实标注，不隐藏、不美化。
 */
import StatusBadge from "./StatusBadge.vue";
import { VIEW_MAP } from "../presentation/vocab";

defineProps<{
  candidateId?: string;
  book?: string;
  title?: string;
  quote?: string;
  sourceKind?: string;
  ocrRisk?: boolean;
  quality?: string;
  /** 由上层决定是否提供"在图谱中查看"跳转 */
  linkable?: boolean;
}>();

const emit = defineEmits<{ (e: "open-graph", id: string): void }>();
</script>

<template>
  <figure class="cite">
    <blockquote style="margin: 0">{{ quote }}</blockquote>
    <figcaption class="cite-src">
      <span v-if="book">《{{ book }}》</span>
      <span v-if="title"> · {{ title }}</span>
      <span v-if="sourceKind" class="mono"> · {{ VIEW_MAP[sourceKind] ?? sourceKind }}</span>
      <span v-if="candidateId" class="mono"> · {{ candidateId }}</span>
      <span v-if="ocrRisk" style="margin-left: 6px">
        <StatusBadge code="OCR 风险" variant="warn" />
      </span>
      <button
        v-if="linkable && candidateId"
        class="btn-link"
        style="margin-left: 8px"
        type="button"
        @click="emit('open-graph', candidateId)"
      >在知识图谱中查看</button>
    </figcaption>
  </figure>
</template>
