<script setup lang="ts">
/**
 * PillarDisplay — 四柱命盘。视觉核心，三层信息层级：
 *   第一层 干支（大字，五行着色）
 *   第二层 十神（次级，日主列强调）
 *   第三层 藏干 / 纳音 / 长生（密集小字）
 *
 * 仅展示引擎已给出的字段（PillarData），不推导任何命理内容。
 * 保留 .pillar-card / .pillar-tile / .gz-stem 等既有标记作为稳定测试锚点。
 */
import { POSITION_CN, elementCn, yinYangCn } from "../presentation/vocab";
import { TERM_PLAIN, TENGOD_PLAIN } from "../presentation/layman";
import type { PillarData } from "../types/tianze";

const props = defineProps<{
  pillars: Partial<Record<"year" | "month" | "day" | "hour", PillarData>>;
  order: Array<"year" | "month" | "day" | "hour">;
}>();

const WX: Record<string, string> = {
  WOOD: "wx-wood", FIRE: "wx-fire", EARTH: "wx-earth", METAL: "wx-metal", WATER: "wx-water",
};
const wx = (el?: string) => WX[(el ?? "").toUpperCase()] ?? "";
const elCn = elementCn;
const yyCn = yinYangCn;
// 白话悬停（M53 小白优先）：术语标签与十神值挂 :title，不新增视觉噪音
const tgPlain = (tg?: string | null) => TENGOD_PLAIN[tg ?? ""] ?? "";
const termPlain = (k: string) => TERM_PLAIN[k] ?? "";
</script>

<template>
  <div class="pillar-board" role="table" aria-label="四柱命盘">
    <article
      v-for="key in props.order"
      :key="key"
      class="pillar-card pillar-tile"
      :class="{ 'is-dm': key === 'day', dm: key === 'day' }"
      role="row"
    >
      <span v-if="key === 'day'" class="dm-seal">日主</span>

      <!-- 第一层：柱位 + 干支 -->
      <div class="pillar-top">
        <div class="pillar-pos">{{ POSITION_CN[key] }}</div>
        <div class="pillar-glyphs">
          <span class="pillar-glyph gz-stem" :class="wx(props.pillars[key]?.stemElement)">
            {{ props.pillars[key]?.stem }}
          </span>
          <span class="pillar-glyph-sep" aria-hidden="true" />
          <span class="pillar-glyph gz-branch" :class="wx(props.pillars[key]?.branchElement)">
            {{ props.pillars[key]?.branch }}
          </span>
        </div>
        <div class="note-sm">
          {{ elCn(props.pillars[key]?.stemElement) }}·{{ yyCn(props.pillars[key]?.stemYinYang) }}
          ／ {{ elCn(props.pillars[key]?.branchElement) }}·{{ yyCn(props.pillars[key]?.branchYinYang) }}
        </div>
      </div>

      <!-- 第二层：十神 -->
      <div class="pillar-tengod">
        <span class="pillar-tengod-label" :title="termPlain('十神') + '：给盘里每个字贴的传统角色标签'">十神</span>
        <div class="pillar-tengod-value" :title="tgPlain(props.pillars[key]?.tenGod)">
          {{ props.pillars[key]?.tenGod ?? (key === "day" ? "日主本人" : "—") }}
        </div>
      </div>

      <!-- 第三层：藏干 / 纳音 / 长生 / 旬空 -->
      <div class="pillar-meta">
        <div v-if="props.pillars[key]?.hiddenStems?.length" class="pillar-meta-row">
          <span class="pillar-meta-key" :title="termPlain('藏干')">藏干</span>
          <span class="pillar-meta-val">
            <span
              v-for="h in props.pillars[key]?.hiddenStems"
              :key="h.stem"
              class="hidden-stem"
            >
              <span class="hidden-stem-glyph" :class="wx(h.element)">{{ h.stem }}</span>
              <span class="hidden-stem-role">{{ h.role }}</span>
              <span class="hidden-stem-tg">{{ h.tenGod }}</span>
            </span>
          </span>
        </div>
        <div v-if="props.pillars[key]?.naYin" class="pillar-meta-row">
          <span class="pillar-meta-key" :title="termPlain('纳音')">纳音</span>
          <span class="pillar-meta-val">{{ props.pillars[key]?.naYin }}</span>
        </div>
        <div v-if="props.pillars[key]?.changSheng" class="pillar-meta-row">
          <span class="pillar-meta-key" :title="termPlain('长生')">长生</span>
          <span class="pillar-meta-val">{{ props.pillars[key]?.changSheng }}</span>
        </div>
        <div v-if="props.pillars[key]?.xunKong" class="pillar-meta-row">
          <span class="pillar-meta-key">旬空</span>
          <span class="pillar-meta-val">{{ props.pillars[key]?.xunKong }}</span>
        </div>
      </div>
    </article>
  </div>
</template>
