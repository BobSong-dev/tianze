<script setup lang="ts">
import { computed, ref } from "vue";
import { analyzeBirthInfo, getMeta, type AnalyzePayload } from "./api/tianze";
import type { AnalyzeResponse } from "./types/tianze";

const date = ref("2003-08-18");
const time = ref("14:30");
const timeKnown = ref(true);
const gender = ref("male");
const tzOffset = ref(8.0);
const sect = ref(2);
const longitude = ref<number | null>(null);
const showAdvanced = ref(false);
const loading = ref(false);
const error = ref("");
const result = ref<AnalyzeResponse | null>(null);
const meta = ref<{ analysisSchemaVersion: string; engineVersion: string } | null>(null);

const activeTab = ref("overview");
const tabs = [
  { id: "overview", label: "总览" },
  { id: "relations", label: "关系" },
  { id: "structure", label: "结构" },
  { id: "strength", label: "旺衰" },
  { id: "pattern", label: "格局" },
  { id: "tiaohou", label: "调候" },
  { id: "advanced", label: "高级" },
];
const expandedEvidence = ref<string | null>(null);

async function submit() {
  loading.value = true;
  error.value = "";
  result.value = null;
  try {
    const payload: AnalyzePayload = {
      birthInfo: {
        date: date.value,
        time: timeKnown.value ? time.value : undefined,
        gender: gender.value,
        timezoneOffset: tzOffset.value,
        sect: sect.value,
        longitude: longitude.value ?? undefined,
      },
      options: {
        includeStrength: true, includePattern: true, includeTiaohou: true,
        includeSpecialPatterns: true, includeRelations: true, includeElementCounts: true,
      },
    };
    result.value = await analyzeBirthInfo(payload);
    activeTab.value = "overview";
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}

const pillarKeys = computed(() => {
  if (!result.value) return [];
  const p = result.value.pillars;
  return (["year", "month", "day", "hour"] as const).filter(k => p[k as keyof typeof p]);
});

function toggleEvidence(id: string) {
  expandedEvidence.value = expandedEvidence.value === id ? null : id;
}
</script>

<template>
  <div class="tianze-app">
    <header class="header">
      <h1>Tianze 天泽</h1>
      <span class="subtitle">可解释八字结构分析引擎</span>
      <span v-if="meta" class="version">v{{ meta.engineVersion }}</span>
    </header>

    <!-- Birth Input -->
    <section class="panel input-panel">
      <h2>出生信息</h2>
      <div class="form-grid">
        <label>出生日期 <input v-model="date" type="date" required /></label>
        <template v-if="timeKnown">
          <label>出生时间 <input v-model="time" type="time" /></label>
        </template>
        <label class="checkbox">
          <input v-model="timeKnown" type="checkbox" /> 知道出生时间
        </label>
        <label>性别
          <select v-model="gender">
            <option value="male">男</option>
            <option value="female">女</option>
          </select>
        </label>
        <label>时区偏移 <input v-model.number="tzOffset" type="number" step="0.5" /></label>
        <label>晚子时流派
          <select v-model="sect">
            <option :value="2">流派 2（默认）</option>
            <option :value="1">流派 1</option>
          </select>
        </label>
        <template v-if="showAdvanced">
          <label>经度 <input v-model.number="longitude" type="number" step="0.1" /></label>
        </template>
        <button class="link" @click="showAdvanced = !showAdvanced">
          {{ showAdvanced ? "隐藏" : "高级选项" }}
        </button>
      </div>
      <button class="submit" :disabled="loading" @click="submit">
        {{ loading ? "正在分析命局结构…" : "开始分析" }}
      </button>
      <div v-if="error" class="error">{{ error }}</div>
    </section>

    <!-- Results -->
    <template v-if="result">
      <section class="panel chart-panel">
        <h2>四柱</h2>
        <div class="pillars">
          <div v-for="key in pillarKeys" :key="key" class="pillar-card">
            <div class="pillar-label">{{ ({ year: "年柱", month: "月柱", day: "日柱", hour: "时柱" } as Record<string, string>)[key as string] }}</div>
            <div class="pillar-ganzhi">
              <span class="stem">{{ (result.pillars as any)[key]?.stem }}</span>
              <span class="branch">{{ (result.pillars as any)[key]?.branch }}</span>
            </div>
            <div class="pillar-tengod">{{ (result.pillars as any)[key]?.tenGod ?? "日主" }}</div>
            <div class="pillar-details">
              <span>{{ (result.pillars as any)[key]?.naYin }}</span>
              <span v-if="(result.pillars as any)[key]?.changSheng">{{ (result.pillars as any)[key]?.changSheng }}</span>
            </div>
            <details><summary>藏干</summary>
              <div v-for="h in (result.pillars as any)[key]?.hiddenStems" :key="h.stem" class="hidden-stem">
                {{ h.stem }}（{{ h.role }}）→ {{ h.tenGod }}
              </div>
            </details>
          </div>
        </div>
      </section>

      <!-- Tabs -->
      <nav class="tabs">
        <button v-for="t in tabs" :key="t.id" :class="{ active: activeTab === t.id }" @click="activeTab = t.id">
          {{ t.label }}
        </button>
      </nav>

      <!-- Overview -->
      <section v-if="activeTab === 'overview'" class="panel">
        <h2>日主</h2>
        <p>{{ result.dayMaster.stem }}（{{ result.dayMaster.element }}·{{ result.dayMaster.yinYang }}）</p>
        <h2>五行分布</h2>
        <div v-if="result.elementCounts" class="elements">
          <div v-for="(v, k) in result.elementCounts.elements" :key="k" class="element-row">
            <span class="elem-label">{{ k }}</span>
            <div class="bar"><div class="fill" :style="{ width: (v.visible / 8 * 100) + '%' }"></div></div>
            <span>显 {{ v.visible }} / 藏 {{ v.hidden }}</span>
          </div>
        </div>
      </section>

      <!-- Relations -->
      <section v-if="activeTab === 'relations' && result.relations.length" class="panel">
        <h2>干支关系</h2>
        <div v-for="r in result.relations" :key="r.label + r.positions.join()" class="relation-item">
          <strong>{{ r.label }}</strong>
          <span class="pos">{{ r.positions.join(" · ") }}</span>
          <span v-if="r.adjacency" class="badge">{{ r.adjacency === "ADJACENT" ? "贴邻" : "隔柱" }}</span>
          <span v-if="r.monthInvolved" class="badge">月令</span>
          <span v-if="r.transformCandidate" class="badge">化 {{ r.transformCandidate }}（候选）</span>
          <span v-if="r.note" class="note">{{ r.note }}</span>
        </div>
      </section>

      <!-- Structure (roots/visibility/month) -->
      <section v-if="activeTab === 'structure'" class="panel">
        <h2>月令</h2>
        <div v-if="result.monthCommand">
          <p>{{ result.monthCommand.monthBranch }}月 · {{ result.monthCommand.season }} · {{ result.monthCommand.element }}</p>
          <p>日主状态：{{ result.monthCommand.relationToDayMaster.state }}
            <template v-if="result.monthCommand.relationToDayMaster.inCommand">（得令）</template>
          </p>
          <details open><summary>证据</summary>
            <div v-for="e in result.monthCommand.evidence" :key="e" class="evidence-item">{{ e }}</div>
          </details>
        </div>
        <h2>通根</h2>
        <div v-for="r in result.roots" :key="r.stem + r.branch + r.position" class="evidence-item">
          {{ r.statement }}
          <span class="badge">{{ r.depth }}</span>
          <span v-if="r.isMonthRoot" class="badge">月令</span>
        </div>
        <h2>透干</h2>
        <div v-for="v in result.visibility" :key="v.hiddenStem + v.position" class="evidence-item">
          {{ v.statement }}
        </div>
      </section>

      <!-- Strength -->
      <section v-if="activeTab === 'strength' && result.strength" class="panel">
        <h2>旺衰分析（多方法并列）</h2>
        <p class="agreement" v-if="result.strength.agreement">
          Agreement: {{ result.strength.agreement }}
        </p>
        <div v-for="m in result.strength.methods" :key="m.analyzerId" class="method-block">
          <h3>{{ m.name }} <span class="badge" v-if="m.verdict">{{ m.verdict }}</span>
            <span class="badge" v-if="m.confidence">{{ m.confidence }}</span>
          </h3>
          <!-- Dimension -->
          <template v-if="m.strengthEvidence">
            <div class="dim-row">
              <span>得令 {{ m.strengthEvidence.deLing.result ? "✓" : "✗" }}</span>
              <span>得地 {{ m.strengthEvidence.deDi.result ? "✓" : "✗" }}</span>
              <span>得势 {{ m.strengthEvidence.deShi.result ? "✓" : "✗" }}</span>
            </div>
            <details><summary>为什么？</summary>
              <div v-for="r in m.strengthEvidence.deLing.reason" :key="r" class="evidence-item">{{ r }}</div>
              <div v-for="r in m.strengthEvidence.deDi.reason" :key="r" class="evidence-item">{{ r }}</div>
              <div v-for="r in m.strengthEvidence.deShi.reason" :key="r" class="evidence-item">{{ r }}</div>
            </details>
          </template>
          <!-- Weighted -->
          <template v-if="m.score !== null && m.score !== undefined">
            <p>score: {{ m.score }}</p>
            <details><summary>Contributions</summary>
              <div v-for="c in m.contributions || []" :key="c.factor" class="evidence-item">
                {{ c.effect === "support" ? "+" : "−" }} {{ c.reason }} ({{ c.value }})
              </div>
            </details>
            <details><summary>Parameters</summary>
              <pre>{{ JSON.stringify(m.params, null, 2) }}</pre>
            </details>
          </template>
          <!-- Fuyi -->
          <template v-if="m.supportEvidence">
            <div class="evidence-item" v-for="e in m.supportEvidence" :key="e">+ {{ e }}</div>
            <div class="evidence-item" v-for="e in m.drainEvidence || []" :key="e">− {{ e }}</div>
          </template>
          <details><summary>General Evidence</summary>
            <div v-for="e in m.evidence" :key="e" class="evidence-item">{{ e }}</div>
          </details>
          <p class="note" v-if="m.note">{{ m.note }}</p>
        </div>
      </section>

      <!-- Pattern -->
      <section v-if="activeTab === 'pattern' && result.pattern" class="panel">
        <h2>格局</h2>
        <div v-for="c in result.pattern.candidates" :key="c.name + c.via" class="candidate-block">
          <h3>{{ c.name }} <span class="badge">{{ c.via }}</span></h3>
          <div v-for="e in c.evidence" :key="e" class="evidence-item">{{ e }}</div>
        </div>
        <template v-if="result.pattern.evaluation">
          <p class="status">Status: <strong>{{ result.pattern.evaluation.status }}</strong></p>
          <h3>支持因素</h3>
          <div v-for="f in result.pattern.evaluation.supports" :key="f.ruleId" class="evidence-item">
            {{ f.name }}: {{ f.detail }}
          </div>
          <h3>破坏因素</h3>
          <div v-for="f in result.pattern.evaluation.damages" :key="f.ruleId" class="evidence-item damage">
            {{ f.name }}: {{ f.detail }}
          </div>
          <h3>救应</h3>
          <div v-for="f in result.pattern.evaluation.rescues" :key="f.ruleId" class="evidence-item rescue">
            {{ f.name }}: {{ f.detail }}
          </div>
          <div v-if="result.pattern.evaluation.conflicts?.length">
            <h3>冲突</h3>
            <div v-for="f in result.pattern.evaluation.conflicts" :key="f.ruleId" class="evidence-item conflict">
              {{ f.name }}: {{ f.detail }}
            </div>
          </div>
        </template>
      </section>

      <!-- TiaoHou -->
      <section v-if="activeTab === 'tiaohou' && result.tiaohou" class="panel">
        <h2>调候</h2>
        <p v-if="!result.tiaohou.resolved" class="note">资料不足（UNRESOLVED）</p>
        <div v-for="rec in result.tiaohou.recommendations" :key="rec.targetStem + rec.priority" class="tiaohou-item">
          <strong>{{ rec.targetStem }}</strong>（{{ rec.element }} · {{ rec.priority }}）
          <span class="badge">{{ rec.present ? "命局已有" : "命局未见" }}</span>
          <span v-if="rec.positions.length" class="pos">{{ rec.positions.join(" · ") }}</span>
          <details><summary>查看依据</summary>
            <div v-for="rid in rec.ruleIds" :key="rid" class="evidence-item">规则：{{ rid }}</div>
            <div v-if="rec.quote" class="evidence-item quote">「{{ rec.quote }}」</div>
            <div v-if="rec.source" class="evidence-item">
              出处：{{ rec.source.book }} · {{ rec.source.chapter }} · PDF第{{ rec.source.pages?.join("-") }}页
            </div>
            <div v-for="p in rec.provenance" :key="p.level + p.concept" class="evidence-item">
              <span class="badge">{{ p.level }}</span> {{ p.concept }}
            </div>
          </details>
        </div>
        <div v-if="result.tiaohou.conflicts?.length" class="conflict">
          <div v-for="c in result.tiaohou.conflicts" :key="c" class="evidence-item conflict">⚠ {{ c }}</div>
        </div>
      </section>

      <!-- Advanced (M8) -->
      <section v-if="activeTab === 'advanced' && result.advancedAnalysis" class="panel">
        <h2>高级结构分析</h2>
        <!-- Special Patterns -->
        <h3>特殊格局候选</h3>
        <div v-for="c in result.advancedAnalysis.specialPattern?.cong || []" :key="c.type" class="candidate-block">
          <strong>{{ c.type }}</strong>
          <span class="badge" :class="c.status.toLowerCase()">{{ c.status }}</span>
          <details><summary>Supports / Blockers</summary>
            <div v-for="s in c.supports" :key="s.ruleId" class="evidence-item">+ {{ s.text }}</div>
            <div v-for="b in c.blockers" :key="b.ruleId" class="evidence-item damage">− {{ b.text }}</div>
          </details>
          <details v-if="c.schoolVariants"><summary>流派差异</summary>
            <div v-for="(v, k) in c.schoolVariants" :key="k" class="evidence-item">{{ k }}: {{ v }}</div>
          </details>
        </div>
        <div v-for="z in result.advancedAnalysis.specialPattern?.zhuanwang || []" :key="z.type" class="candidate-block">
          <strong>{{ z.type }}</strong> <span class="badge">{{ z.status }}</span>
        </div>
        <!-- BingYao -->
        <h3>病药结构 <span class="note">（"病药"指命局结构中的失衡与制衡关系，不是医学诊断）</span></h3>
        <div v-for="p in result.advancedAnalysis.bingYao?.problems || []" :key="p.target" class="evidence-item damage">
          结构问题：{{ p.target }}（{{ p.evidence.join("；") }}）
        </div>
        <div v-for="m in result.advancedAnalysis.bingYao?.medicines || []" :key="m.problem + m.kind" class="evidence-item rescue">
          制衡：{{ m.target }} {{ m.kind }} → 解决 {{ m.problem }} 问题
        </div>
        <!-- TongGuan -->
        <h3>通关</h3>
        <div v-for="(b, i) in result.advancedAnalysis.tongGuan?.bridges || []" :key="i" class="evidence-item">
          {{ b.conflict.from }} → {{ b.bridge }} → {{ b.conflict.to }}
          <span class="badge">{{ b.present ? "桥已存在" : "桥未现" }}</span>
        </div>
      </section>

      <!-- Warnings / Fallbacks -->
      <section v-if="result.warnings.length || result.fallbacks.length" class="panel warnings-panel">
        <h3>注意事项</h3>
        <div v-for="w in result.warnings" :key="w" class="evidence-item warning">⚠ {{ w }}</div>
        <div v-for="f in result.fallbacks" :key="f" class="evidence-item fallback">ℹ {{ f }}</div>
      </section>
    </template>
  </div>
</template>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: "Noto Sans SC", system-ui, sans-serif; background: #f5f6fa; color: #2c3e50; }
.tianze-app { max-width: 960px; margin: 0 auto; padding: 1rem; }
.header { padding: 1rem 0; border-bottom: 2px solid #3498db; margin-bottom: 1rem; }
.header h1 { display: inline; font-size: 1.5rem; color: #2c3e50; }
.header .subtitle { margin-left: 0.5rem; color: #7f8c8d; font-size: 0.9rem; }
.header .version { float: right; color: #95a5a6; font-size: 0.8rem; }
.panel { background: white; border: 1px solid #e0e0e0; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
.panel h2 { font-size: 1.1rem; color: #2c3e50; margin-bottom: 0.5rem; border-left: 3px solid #3498db; padding-left: 0.5rem; }
.panel h3 { font-size: 0.95rem; color: #34495e; margin: 0.5rem 0 0.3rem; }
.form-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 0.5rem; margin: 0.5rem 0; }
.form-grid label { display: flex; flex-direction: column; gap: 0.2rem; font-size: 0.85rem; }
.form-grid input, .form-grid select { padding: 0.4rem; border: 1px solid #bdc3c7; border-radius: 4px; }
.checkbox { flex-direction: row !important; align-items: center; }
.submit { background: #3498db; color: white; border: none; padding: 0.6rem 1.5rem; border-radius: 6px; cursor: pointer; font-size: 1rem; margin-top: 0.5rem; }
.submit:hover { background: #2980b9; }
.submit:disabled { background: #95a5a6; }
.error { color: #e74c3c; margin-top: 0.5rem; padding: 0.5rem; background: #fdf0ef; border-radius: 4px; }
.pillars { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 0.5rem; }
.pillar-card { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 6px; padding: 0.8rem; text-align: center; }
.pillar-label { font-size: 0.8rem; color: #7f8c8d; }
.pillar-ganzhi { font-size: 1.8rem; font-weight: bold; margin: 0.3rem 0; }
.pillar-ganzhi .stem { color: #2c3e50; margin-right: 0.3rem; }
.pillar-ganzhi .branch { color: #3498db; }
.pillar-tengod { font-size: 0.85rem; color: #e67e22; }
.pillar-details { font-size: 0.75rem; color: #95a5a6; display: flex; flex-direction: column; gap: 0.1rem; }
.pillar-details details { margin-top: 0.3rem; }
.tabs { display: flex; gap: 0.2rem; margin-bottom: 0.5rem; flex-wrap: wrap; }
.tabs button { padding: 0.4rem 0.8rem; border: 1px solid #bdc3c7; background: white; cursor: pointer; border-radius: 4px 4px 0 0; }
.tabs button.active { background: #3498db; color: white; border-color: #3498db; }
.relation-item, .evidence-item, .tiaohou-item, .candidate-block { padding: 0.4rem 0; border-bottom: 1px solid #f0f0f0; font-size: 0.9rem; }
.badge { display: inline-block; padding: 0.1rem 0.4rem; border-radius: 3px; font-size: 0.75rem; background: #eaf2f8; color: #2980b9; margin: 0 0.2rem; }
.badge.likely { background: #e8f8f5; color: #27ae60; }
.badge.blocked { background: #fdedec; color: #e74c3c; }
.damage { color: #c0392b; }
.rescue { color: #27ae60; }
.conflict { color: #e67e22; }
.note { color: #95a5a6; font-size: 0.8rem; }
.pos { color: #7f8c8d; font-size: 0.8rem; }
.quote { font-style: italic; color: #555; }
.agreement { padding: 0.5rem; background: #fef9e7; border-radius: 4px; font-size: 0.9rem; }
.method-block { border-left: 3px solid #3498db; padding-left: 0.8rem; margin: 0.8rem 0; }
.dim-row { display: flex; gap: 1rem; font-size: 0.95rem; }
.elements { display: flex; flex-direction: column; gap: 0.3rem; }
.element-row { display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; }
.elem-label { width: 3em; text-align: right; }
.bar { flex: 1; height: 1rem; background: #ecf0f1; border-radius: 3px; overflow: hidden; }
.fill { height: 100%; background: #3498db; border-radius: 3px; }
.status { font-size: 1rem; }
.candidate-block { border-left: 3px solid #e67e22; padding-left: 0.8rem; margin: 0.5rem 0; }
.warnings-panel { border-left: 3px solid #f39c12; }
.warning { color: #e67e22; }
.fallback { color: #7f8c8d; }
details { margin: 0.3rem 0; }
summary { cursor: pointer; color: #3498db; font-size: 0.85rem; }
.link { background: none; border: none; color: #3498db; cursor: pointer; text-decoration: underline; font-size: 0.85rem; }
@media (max-width: 600px) { .pillars { grid-template-columns: repeat(2, 1fr); } .form-grid { grid-template-columns: 1fr; } }
</style>
