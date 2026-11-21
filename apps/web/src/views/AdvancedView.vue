<script setup lang="ts">
/**
 * AdvancedView — 高级结构分析。
 * 内容：特殊格局候选（从格 / 专旺 / 外格虚神） · 病药结构 · 通关。
 * 纪律：候选状态原样呈现；病药为结构矛盾与制衡（非医学诊断）；外格虚神非格局。
 */
import { computed } from "vue";
import StatusBadge from "../components/StatusBadge.vue";
import { elementCn } from "../presentation/vocab";
import type { AdvancedAnalysis } from "../types/tianze";

const props = defineProps<{ advanced: AdvancedAnalysis }>();

const special = computed(() => props.advanced.specialPattern);
const bingYao = computed(() => props.advanced.bingYao);
const tongGuan = computed(() => props.advanced.tongGuan);
const elCn = elementCn;

const cong = computed(() => special.value?.cong ?? []);
const zhuanwang = computed(() => special.value?.zhuanwang ?? []);
const xushi = computed(() => special.value?.xushiOuter ?? []);
const transformation = computed(() => special.value?.transformation ?? []);

const patterns = computed(() => [
  ...cong.value.map(c => ({ ...c, family: "从格" })),
  ...zhuanwang.value.map(z => ({ ...z, family: "专旺" })),
]);

/** 结构失衡（病）与制衡（药）—— "病药"是结构概念，不是医学诊断 */
const hasBingYao = computed(() =>
  Boolean(bingYao.value?.problems?.length || bingYao.value?.medicines?.length));
</script>

<template>
  <div class="advanced-layout">
    <!-- 特殊格局候选 -->
    <section>
      <div class="sec-sub" style="margin-top: 0">
        <h3>特殊格局候选</h3>
        <span class="sec-sub-note">
          从格与专旺为结构候选；分歧（真从 / 假从等）如实并列，不裁决
        </span>
      </div>

      <div class="stack stack-3">
        <article v-for="p in patterns" :key="p.family + p.type" class="row-item">
          <div class="row-item-head">
            <span class="row-item-title">{{ p.type }}</span>
            <StatusBadge :label="p.family" variant="mute" />
            <StatusBadge :code="p.status" with-hint />
            <StatusBadge v-if="p.school" :label="p.school" variant="mute" />
          </div>

          <details class="mt-3">
            <summary>成立前提 · 支持 / 阻断 / 例外 / 冲突 / 流派差异</summary>

            <div v-if="p.prerequisites?.length" class="mt-3">
              <div class="note-sm" style="margin-bottom: 4px">成立前提（结构条件）</div>
              <ol class="prereq-list">
                <li v-for="(pr, i) in p.prerequisites" :key="i">{{ pr }}</li>
              </ol>
            </div>

            <div v-if="p.supports?.length" class="mt-4">
              <div class="note-sm" style="margin-bottom: 4px">支持（{{ p.supports.length }}）</div>
              <div class="stack stack-1">
                <div v-for="(s, i) in p.supports" :key="i" class="ev evidence-item is-plus">
                  <span class="ev-mark">+</span>
                  <span class="ev-body">
                    <StatusBadge :code="s.ruleId" variant="rule" />
                    {{ s.text }}
                  </span>
                </div>
              </div>
            </div>

            <div v-if="p.blockers?.length" class="mt-4">
              <div class="note-sm" style="margin-bottom: 4px">阻断（{{ p.blockers.length }}）</div>
              <div class="stack stack-1">
                <div v-for="(b, i) in p.blockers" :key="i" class="ev evidence-item is-minus">
                  <span class="ev-mark">−</span>
                  <span class="ev-body">
                    <StatusBadge :code="b.ruleId" variant="rule" />
                    {{ b.text }}
                  </span>
                </div>
              </div>
            </div>

            <div v-if="p.exceptions?.length" class="mt-4">
              <div class="note-sm" style="margin-bottom: 4px">例外与两说（{{ p.exceptions.length }}）</div>
              <div class="stack stack-1">
                <div v-for="(e, i) in p.exceptions" :key="i" class="ev evidence-item is-warn">
                  <span class="ev-mark">◎</span>
                  <span class="ev-body">
                    <StatusBadge :code="e.ruleId" variant="rule" />
                    {{ e.text }}
                  </span>
                </div>
              </div>
            </div>

            <div v-if="p.conflicts?.length" class="mt-4">
              <div class="note-sm" style="margin-bottom: 4px">冲突（{{ p.conflicts.length }}）</div>
              <div class="stack stack-1">
                <div v-for="(c, i) in p.conflicts" :key="i" class="ev evidence-item is-warn">
                  <span class="ev-mark">⚠</span>
                  <span class="ev-body">
                    <StatusBadge :code="c.ruleId" variant="rule" />
                    {{ c.text }}
                  </span>
                </div>
              </div>
            </div>

            <div v-if="Object.keys(p.schoolVariants ?? {}).length" class="mt-4">
              <div class="note-sm" style="margin-bottom: 4px">流派差异</div>
              <div class="stack stack-1">
                <div v-for="(v, k) in p.schoolVariants" :key="k" class="ev evidence-item is-quiet">
                  <span class="ev-mark">·</span>
                  <span class="ev-body"><strong>{{ k }}</strong>：{{ v }}</span>
                </div>
              </div>
            </div>

            <div v-if="p.provenance?.length" class="mt-4">
              <div class="note-sm" style="margin-bottom: 4px">溯源层级</div>
              <div class="stack stack-1">
                <div v-for="(pv, i) in p.provenance" :key="i" class="ev evidence-item is-quiet">
                  <span class="ev-mark">·</span>
                  <span class="ev-body">
                    <StatusBadge :label="pv.level" variant="mute" />
                    {{ pv.concept }}
                    <span v-if="pv.project" class="note-sm">（{{ pv.project }}）</span>
                  </span>
                </div>
              </div>
            </div>
          </details>
        </article>

        <p v-if="!patterns.length" class="empty">无特殊格局候选。</p>
      </div>
    </section>

    <!-- 外格虚神候选 -->
    <section v-if="xushi.length">
      <div class="sec-sub" style="margin-top: 0">
        <h3>外格虚神候选</h3>
        <span class="sec-sub-note">
          飞天禄马 / 井栏叉 / 刑合 / 子邀巳 —— 候选仅供参考，非格局（DTZ-26/36）
        </span>
      </div>
      <div class="stack stack-2">
        <article v-for="x in xushi" :key="x.type" class="row-item">
          <div class="row-item-head">
            <span class="row-item-title">{{ x.type }}</span>
            <StatusBadge :code="x.status" with-hint />
          </div>
          <div v-if="Object.keys(x.schoolVariants ?? {}).length" class="stack stack-1 mt-3">
            <p v-for="(sv, k) in x.schoolVariants" :key="k" class="note">
              <strong>{{ k }}</strong>：{{ sv }}
            </p>
          </div>
          <div v-if="x.blockers?.length" class="stack stack-1 mt-3">
            <div v-for="(b, i) in (x.blockers ?? [])" :key="i" class="ev evidence-item is-minus">
              <span class="ev-mark">−</span><span class="ev-body">阻断：{{ b.text }}</span>
            </div>
          </div>
        </article>
      </div>
    </section>

    <!-- 天干合化候选 -->
    <section v-if="transformation.length">
      <div class="sec-sub" style="margin-top: 0">
        <h3>天干合化候选</h3>
        <span class="sec-sub-note">合化状态按传统口径判定，非化成断言</span>
      </div>
      <div class="stack stack-2">
        <article v-for="(t, i) in transformation" :key="i" class="row-item">
          <div class="row-item-head">
            <span class="row-item-title">{{ t.stemPair?.join(" + ") }}</span>
            <span class="row-item-pos">→ {{ elCn(t.targetElement) }}</span>
            <StatusBadge :code="t.status" with-hint />
            <StatusBadge
              v-if="t.seasonSupport !== null"
              :label="t.seasonSupport ? '得月令之助' : '不得月令之助'"
              :variant="t.seasonSupport ? 'pos' : 'mute'"
            />
          </div>
          <div v-if="t.obstructions?.length" class="stack stack-1 mt-3">
            <div v-for="(o, oi) in t.obstructions" :key="oi" class="ev evidence-item is-minus">
              <span class="ev-mark">−</span><span class="ev-body">阻化：{{ o }}</span>
            </div>
          </div>
        </article>
      </div>
    </section>

    <!-- 病药结构 -->
    <section>
      <div class="sec-sub" style="margin-top: 0">
        <h3>病药结构</h3>
        <span class="sec-sub-note">
          「病药」指命局结构中的失衡与制衡关系，不是医学诊断
        </span>
      </div>

      <template v-if="hasBingYao">
        <div class="stack stack-4">
          <div v-if="bingYao?.problems?.length">
            <div class="note-sm" style="margin-bottom: var(--s-2)">结构问题（病）</div>
            <div class="stack stack-2">
              <article v-for="p in bingYao.problems" :key="p.target" class="row-item">
                <div class="row-item-head">
                  <span class="row-item-title">{{ p.target }}</span>
                  <StatusBadge :label="p.type" variant="mute" />
                </div>
                <div class="stack stack-1 mt-2">
                  <p v-for="(e, i) in p.evidence" :key="i" class="note">{{ e }}</p>
                </div>
              </article>
            </div>
          </div>

          <div v-if="bingYao?.medicines?.length">
            <div class="note-sm" style="margin-bottom: var(--s-2)">制衡（药）</div>
            <div class="stack stack-2">
              <article v-for="m in bingYao.medicines" :key="m.problem + m.kind" class="row-item">
                <div class="row-item-head">
                  <span class="row-item-title">{{ m.target }}</span>
                  <StatusBadge :label="m.kind" variant="mute" />
                  <span class="row-item-pos">解 {{ m.problem }}</span>
                </div>
                <div class="stack stack-1 mt-2">
                  <p v-for="(e, i) in m.evidence" :key="i" class="note">{{ e }}</p>
                </div>
              </article>
            </div>
          </div>
        </div>
      </template>
      <p v-else class="empty">本命局未检出显著的结构失衡（病）与制衡（药）。</p>

      <div v-if="bingYao?.provenance?.length" class="note mt-3 stack stack-1">
        <p v-for="(pv, i) in bingYao.provenance" :key="i">
          口径 · <span class="mono">{{ pv.level }}</span> {{ pv.concept }}
        </p>
      </div>
    </section>

    <!-- 通关 -->
    <section>
      <div class="sec-sub" style="margin-top: 0">
        <h3>通关</h3>
        <span class="sec-sub-note">两行对峙与中间桥的检索结果</span>
      </div>

      <div v-if="tongGuan?.conflictPairs?.length || tongGuan?.bridges?.length" class="stack stack-4">
        <div v-if="tongGuan?.conflictPairs?.length">
          <div class="note-sm" style="margin-bottom: var(--s-2)">五行对峙（冲突对）</div>
          <div class="stack stack-2">
            <article v-for="(c, i) in tongGuan.conflictPairs" :key="i" class="row-item">
              <div class="rel-link" style="max-width: 300px">
                <span class="rel-glyph" style="font-size: var(--t-lg)">{{ elCn(c.conflict.from) }}</span>
                <span class="rel-edge is-clash">
                  <span class="rel-edge-label">对峙</span>
                </span>
                <span class="rel-glyph" style="font-size: var(--t-lg)">{{ elCn(c.conflict.to) }}</span>
              </div>
              <div class="stack stack-1 mt-2">
                <p v-for="(e, ei) in c.evidence" :key="ei" class="note">{{ e }}</p>
              </div>
            </article>
          </div>
        </div>

        <div v-if="tongGuan?.bridges?.length">
          <div class="note-sm" style="margin-bottom: var(--s-2)">通关桥</div>
          <div class="stack stack-2">
            <article v-for="(b, i) in tongGuan.bridges" :key="i" class="row-item">
              <div class="rel-link" style="max-width: 400px">
                <span class="rel-glyph" style="font-size: var(--t-lg)">{{ elCn(b.conflict.from) }}</span>
                <span class="rel-edge is-harmony">
                  <span class="rel-edge-label">{{ elCn(b.bridge) }}</span>
                </span>
                <span class="rel-glyph" style="font-size: var(--t-lg)">{{ elCn(b.conflict.to) }}</span>
              </div>
              <div class="rel-facts mt-2">
                <StatusBadge
                  :label="b.present ? '桥已存在' : '桥未现'"
                  :variant="b.present ? 'pos' : 'mute'"
                />
                <StatusBadge
                  v-if="b.positions?.length"
                  :label="`位置 ${b.positions.join(' · ')}`"
                  variant="mute"
                />
              </div>
              <div class="stack stack-1 mt-2">
                <p v-for="(e, ei) in b.evidence" :key="ei" class="note">{{ e }}</p>
              </div>
            </article>
          </div>
        </div>
      </div>
      <p v-else class="empty">未检出行间对峙结构。</p>
    </section>
  </div>
</template>

<style scoped>
.prereq-list {
  margin: 0;
  padding-left: 1.2em;
  font-size: var(--t-sm);
  color: var(--ink-500);
  line-height: var(--lh-snug);
}
</style>
