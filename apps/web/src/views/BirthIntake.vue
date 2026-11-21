<script setup lang="ts">
/**
 * BirthIntake — 排盘入口。
 *
 * 两种呈现，**共用同一份字段与状态**（不复制任何输入语义或默认值）：
 *  - 默认：三节式卷首版式（一、出生信息 / 二、历法校正 / 三、排盘方式），用于首页；
 *  - compact：单行密集排版，用于命盘工作区（研究者需要反复改流派 / 时区核对，
 *    但输入区不应占据主要内容空间）。
 *
 * 字段集合与默认值完全沿用既有契约，未新增任何输入语义。
 */
import { computed, ref } from "vue";
import type { BirthForm } from "../composables/useTianze";

const props = withDefaults(defineProps<{
  birth: BirthForm;
  loading: boolean;
  error: string;
  /** 工作区内的单行密集版式 */
  compact?: boolean;
}>(), { compact: false });

const emit = defineEmits<{ (e: "submit"): void }>();

const showAdvanced = ref(false);

const GENDER = [
  { v: "male", label: "男" },
  { v: "female", label: "女" },
];

const SECT = [
  { v: 2, label: "流派 2（默认）", hint: "晚子时归次日" },
  { v: 1, label: "流派 1", hint: "晚子时不换日" },
];

const TZ_PRESETS = [
  { v: 8, label: "东八区 UTC+8（中国）" },
  { v: 9, label: "UTC+9（日本 / 韩国）" },
  { v: 7, label: "UTC+7（东南亚）" },
  { v: 0, label: "UTC+0（格林尼治）" },
  { v: -4, label: "UTC−4（纽约夏令时）" },
  { v: -5, label: "UTC−5（纽约标准时）" },
  { v: -8, label: "UTC−8（洛杉矶）" },
  { v: 1, label: "UTC+1（中欧）" },
];

const tzIsPreset = computed(() =>
  TZ_PRESETS.some(p => p.v === props.birth.timezoneOffset));
</script>

<template>
  <form class="intake" :class="{ 'is-compact': props.compact }" :aria-busy="props.loading" novalidate @submit.prevent="emit('submit')">
    <!-- ============ 单行密集版式（工作区） ============ -->
    <div v-if="props.compact" class="birth-compact">
      <label class="field">
        <span class="field-label">出生日期</span>
        <input v-model="props.birth.date" type="date" required />
      </label>

      <label v-if="props.birth.timeKnown" class="field">
        <span class="field-label">出生时间</span>
        <input v-model="props.birth.time" type="time" />
      </label>

      <div class="field">
        <span class="field-label">性别</span>
        <div class="row" style="gap: 3px">
          <button
            v-for="g in GENDER"
            :key="g.v"
            type="button"
            class="btn-sm"
            :class="props.birth.gender === g.v ? 'btn-ink' : ''"
            :aria-pressed="props.birth.gender === g.v"
            @click="props.birth.gender = g.v"
          >{{ g.label }}</button>
        </div>
      </div>

      <label class="field">
        <span class="field-label">时区偏移 <span class="mono">hour</span></span>
        <select v-model.number="props.birth.timezoneOffset">
          <option v-for="p in TZ_PRESETS" :key="p.v" :value="p.v">{{ p.label }}</option>
          <option v-if="!tzIsPreset" :value="props.birth.timezoneOffset">
            当前值 UTC{{ props.birth.timezoneOffset >= 0 ? "+" : "" }}{{ props.birth.timezoneOffset }}
          </option>
        </select>
      </label>

      <label class="field">
        <span class="field-label">晚子时流派 <span class="mono">sect</span></span>
        <select v-model="props.birth.sect">
          <option v-for="s in SECT" :key="s.v" :value="s.v">{{ s.label }}</option>
        </select>
      </label>

      <label class="field">
        <span class="field-label">经度 <span class="mono">仅记录</span></span>
        <input
          v-model.number="props.birth.longitude"
          type="number"
          step="0.1"
          placeholder="可留空"
        />
      </label>

      <label class="check-row checkbox" style="padding-bottom: 6px">
        <input v-model="props.birth.timeKnown" type="checkbox" />
        知道出生时间
      </label>

      <button class="btn-primary submit" type="submit" :disabled="props.loading">
        {{ props.loading ? "排盘中…" : "重新排盘" }}
      </button>
    </div>

    <!-- ============ 三节式版式（首页） ============ -->
    <template v-else>
      <div class="intake-steps">
        <!-- 一、出生信息 -->
        <section class="intake-step">
          <div class="intake-step-no">
            <b>一</b><span>出生信息</span>
          </div>
          <div class="intake-step-body">
            <div class="field-grid">
              <label class="field">
                <span class="field-label">出生日期 <span class="mono">YYYY-MM-DD</span></span>
                <input v-model="props.birth.date" type="date" required />
              </label>

              <label v-if="props.birth.timeKnown" class="field">
                <span class="field-label">出生时间 <span class="mono">HH:MM</span></span>
                <input v-model="props.birth.time" type="time" />
              </label>

              <div class="field">
                <span class="field-label">性别 <span class="mono">排大运顺逆</span></span>
                <div class="row" style="gap: 4px">
                  <button
                    v-for="g in GENDER"
                    :key="g.v"
                    type="button"
                    :class="props.birth.gender === g.v ? 'btn-ink' : ''"
                    :aria-pressed="props.birth.gender === g.v"
                    @click="props.birth.gender = g.v"
                  >{{ g.label }}</button>
                </div>
              </div>
            </div>

            <label class="check-row checkbox mt-4">
              <input v-model="props.birth.timeKnown" type="checkbox" />
              知道出生时间
            </label>
            <p v-if="!props.birth.timeKnown" class="field-hint mt-2">
              时辰未知时，时柱与大运将缺席，分析降级为三柱结构（引擎行为，非前端取舍）。
            </p>
          </div>
        </section>

        <!-- 二、历法校正 -->
        <section class="intake-step">
          <div class="intake-step-no">
            <b>二</b><span>历法校正</span>
          </div>
          <div class="intake-step-body">
            <div class="field-grid">
              <label class="field">
                <span class="field-label">时区偏移 <span class="mono">hour</span></span>
                <select v-model.number="props.birth.timezoneOffset">
                  <option v-for="p in TZ_PRESETS" :key="p.v" :value="p.v">{{ p.label }}</option>
                  <option v-if="!tzIsPreset" :value="props.birth.timezoneOffset">
                    当前值 UTC{{ props.birth.timezoneOffset >= 0 ? "+" : "" }}{{ props.birth.timezoneOffset }}
                  </option>
                </select>
              </label>

              <label class="field">
                <span class="field-label">精细偏移 <span class="mono">0.5 步进</span></span>
                <input v-model.number="props.birth.timezoneOffset" type="number" step="0.5" />
              </label>
            </div>
            <p class="field-hint mt-3">
              请选择出生地的标准时区。日柱与时柱按当地钟表时计算，适用时扣除中国夏令时。
            </p>
          </div>
        </section>

        <!-- 三、排盘方式 -->
        <section class="intake-step">
          <div class="intake-step-no">
            <b>三</b><span>排盘方式</span>
          </div>
          <div class="intake-step-body">
            <label class="field">
              <span class="field-label">晚子时流派 <span class="mono">sect</span></span>
              <select v-model="props.birth.sect">
                <option v-for="s in SECT" :key="s.v" :value="s.v">{{ s.label }}</option>
              </select>
              <span class="field-hint">
                23:00 之后出生适用。两流派结论可能不同，本工具并列保留，不代替你裁决。
              </span>
            </label>

            <div class="mt-4">
              <button class="btn-link" type="button" :aria-expanded="showAdvanced" @click="showAdvanced = !showAdvanced">
                {{ showAdvanced ? "收起高级选项" : "高级选项（出生地经度）" }}
              </button>
            </div>

            <label v-if="showAdvanced" class="field mt-3">
              <span class="field-label">经度 <span class="mono">longitude, 东经为正</span></span>
              <input
                v-model.number="props.birth.longitude"
                type="number"
                step="0.1"
                placeholder="例如 116.4（北京）"
              />
              <span class="field-hint">
                经度仅作为出生地资料记录，当前排盘使用钟表时。
              </span>
            </label>
          </div>
        </section>
      </div>

      <!-- 视觉终点：开始排盘 -->
      <div class="intake-actions">
        <button class="btn-primary btn-lg submit" type="submit" :disabled="props.loading">
          {{ props.loading ? "正在排盘…" : "开始排盘" }}
        </button>
        <span class="spacer" />
        <span class="note">确定性分析由当前后端引擎完成；不调用第三方 AI。</span>
      </div>
    </template>

    <p v-if="props.error" class="error" role="alert">
      <span class="mono" aria-hidden="true">ERR</span>
      <span>{{ props.error }}</span>
    </p>
    <p v-if="props.loading" class="loading-status" role="status"><span class="loading-indicator" aria-hidden="true" />正在核对历法与结构，请稍候…</p>
  </form>
</template>
