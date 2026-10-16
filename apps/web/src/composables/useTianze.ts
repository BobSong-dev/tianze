/**
 * Tianze · 前端共享状态（单一事实源）
 *
 * 纪律：
 *  - 本文件只做**编排与请求**，绝不重新推导任何命理结论；
 *  - 所有分析结果原样来自 /api/v1/analyze（SDK SimplifiedResult）；
 *  - 所有状态码（CANDIDATE/DISPUTED/BLOCKED/…）原样透传，不升级为确定性结论。
 */
import { computed, reactive, readonly, ref, toRefs } from "vue";
import type {
  AnalyzeResponse, LuckData, DaYunEntryData, TemporalAnalysisData,
} from "../types/tianze";
import {
  analyzeBirthInfo, getMeta, interpretAnalysis,
  type AnalyzeOptionsPayload, type BirthInfoPayload, type Interpretation,
} from "../api/tianze";

/* ------------------------------------------------------------------ 排盘输入 */

export interface BirthForm {
  date: string;
  time: string;
  timeKnown: boolean;
  gender: string;
  timezoneOffset: number;
  sect: number;
  longitude: number | null;
  place: string;
}

export function createBirthForm(): BirthForm {
  return {
    date: "2003-08-18",
    time: "14:30",
    timeKnown: true,
    gender: "male",
    timezoneOffset: 8.0,
    sect: 2,
    longitude: null,
    place: "",
  };
}

/** 岁运控制 */
export interface TemporalSelection {
  luckIndex: number | null;
  year: number | null;
  month: number | null;
  day: string;
  withReplay: boolean;
}

interface State {
  birth: BirthForm;
  result: AnalyzeResponse | null;
  loading: boolean;
  error: string;
  meta: { engineVersion: string; analysisSchemaVersion: string } | null;

  temporal: TemporalAnalysisData | null;
  temporalSelection: TemporalSelection;
  temporalLoading: boolean;
  temporalError: string;

  aiState: "IDLE" | "LOADING" | "SUCCESS" | "GROUNDING_FAILED" | "PROVIDER_ERROR" | "NOT_CONFIGURED";
  aiResult: Interpretation | null;
  aiError: string;
}

export function useTianze() {
  const state = reactive<State>({
    birth: createBirthForm(),
    result: null,
    loading: false,
    error: "",
    meta: null,

    temporal: null,
    temporalSelection: { luckIndex: null, year: null, month: null, day: "", withReplay: true },
    temporalLoading: false,
    temporalError: "",

    aiState: "IDLE",
    aiResult: null,
    aiError: "",
  });

  /* ------------------------------------------------ 派生：命盘 / 岁运选项 */

  const pillars = computed(() => state.result?.pillars ?? null);

  const pillarOrder = computed<Array<"year" | "month" | "day" | "hour">>(() => {
    const p = state.result?.pillars;
    if (!p) return [];
    return (["year", "month", "day", "hour"] as const).filter(k => Boolean(p[k]));
  });

  const dayMasterStem = computed(() => state.result?.dayMaster?.stem ?? "");

  const luck = computed<LuckData | null>(() => state.result?.luck ?? null);

  const luckOptions = computed<DaYunEntryData[]>(() =>
    (luck.value?.daYun ?? []).filter(d => Boolean(d.ganZhi)));

  /** 流年候选完全由后端 startYear/endYear 给出，前端不推算年表 */
  const yearOptions = computed<number[]>(() => {
    const d = luckOptions.value.find(x => x.index === state.temporalSelection.luckIndex);
    if (!d) return [];
    const out: number[] = [];
    for (let y = d.startYear; y <= d.endYear; y++) out.push(y);
    return out;
  });

  /** 流月：节气月序（1=寅月）。标签描述节气起讫，属历法常识展示，非推理。 */
  const monthOptions = [
    { n: 1, label: "寅月", jie: "立春起" }, { n: 2, label: "卯月", jie: "惊蛰起" },
    { n: 3, label: "辰月", jie: "清明起" }, { n: 4, label: "巳月", jie: "立夏起" },
    { n: 5, label: "午月", jie: "芒种起" }, { n: 6, label: "未月", jie: "小暑起" },
    { n: 7, label: "申月", jie: "立秋起" }, { n: 8, label: "酉月", jie: "白露起" },
    { n: 9, label: "戌月", jie: "寒露起" }, { n: 10, label: "亥月", jie: "立冬起" },
    { n: 11, label: "子月", jie: "大雪起" }, { n: 12, label: "丑月", jie: "小寒起" },
  ];

  /** 当前选中的岁运上下文链（供时间轨道展示；取后端回显的干支） */
  const timeStops = computed(() => {
    const c = state.temporal?.context;
    const sel = state.temporalSelection;
    const luckEntry = luckOptions.value.find(x => x.index === sel.luckIndex);
    return [
      {
        key: "natal", layer: "natal", label: "原局",
        ganzhi: (state.result?.pillars
          ? (["year", "month", "day", "hour"] as const)
              .map(k => state.result?.pillars[k])
              .filter(Boolean)
              .map(p => `${p!.stem}${p!.branch}`)
              .join(" ")
          : ""),
        sub: state.result?.dayMaster ? `日主 ${state.result.dayMaster.stem}` : "",
        enabled: true,
      },
      {
        key: "luck", layer: "luck", label: "大运",
        ganzhi: c?.luckStem ? `${c.luckStem}${c.luckBranch}` : (luckEntry?.ganZhi ?? ""),
        sub: luckEntry ? `${luckEntry.startYear}–${luckEntry.endYear} · ${luckEntry.startAge} 岁起` : "未选择",
        enabled: Boolean(luckEntry),
      },
      {
        key: "annual", layer: "annual", label: "流年",
        ganzhi: c?.annualStem ? `${c.annualStem}${c.annualBranch}` : "",
        sub: c?.annualYear ? `${c.annualYear}` : (sel.year ? `${sel.year}` : "未选择"),
        enabled: Boolean(c?.annualStem || sel.year),
      },
      {
        key: "monthly", layer: "monthly", label: "流月",
        ganzhi: c?.monthlyStem ? `${c.monthlyStem}${c.monthlyBranch}` : "",
        sub: state.temporal?.monthWindow
          ? `${state.temporal.monthWindow.jieName}起`
          : (sel.month ? monthOptions.find(m => m.n === sel.month)?.label ?? "" : "未选择"),
        enabled: Boolean(c?.monthlyStem),
      },
      {
        key: "daily", layer: "daily", label: "流日",
        ganzhi: c?.dailyStem ? `${c.dailyStem}${c.dailyBranch}` : "",
        sub: sel.day || "未选择",
        enabled: Boolean(c?.dailyStem),
      },
    ];
  });

  const matchedRules = computed(() =>
    (state.temporal?.ruleTriggers ?? []).filter(t => t.matched));

  const deltaGroups = computed<Record<string, any[]>>(() => {
    const groups: Record<string, any[]> = {};
    for (const it of (state.temporal?.delta?.items ?? []) as any[]) {
      (groups[it.analysis] ??= []).push(it);
    }
    return groups;
  });

  /** 关系解释链按 label 索引（后端 relationExplanations 与 relations 同 label 生成） */
  const relationChains = computed(() => {
    const exs: any[] = (state.result as any)?.relationExplanations ?? [];
    const byLabel = new Map<string, any>();
    for (const e of exs) if (!byLabel.has(e.label)) byLabel.set(e.label, e);
    return byLabel;
  });

  const combinationStates = computed(() =>
    ((state.result as any)?.relationExplanations ?? [])
      .filter((e: any) => e.kind === "combination_state"));

  const eventThemeExplanations = computed<Record<string, any>>(
    () => (state.temporal?.eventThemes as any)?.explanations ?? {});

  /* --------------------------------------------------------------- 动作 */

  async function loadMeta() {
    if (state.meta) return;
    try {
      const m = await getMeta();
      state.meta = { engineVersion: m.engineVersion, analysisSchemaVersion: m.analysisSchemaVersion };
    } catch { /* 版本信息非关键路径 */ }
  }

  function baseBirth(): BirthInfoPayload {
    return {
      date: state.birth.date,
      time: state.birth.timeKnown ? state.birth.time : undefined,
      gender: state.birth.gender,
      timezoneOffset: state.birth.timezoneOffset,
      sect: state.birth.sect,
      longitude: state.birth.longitude ?? undefined,
    };
  }

  const FULL_OPTIONS: AnalyzeOptionsPayload = {
    includeStrength: true, includePattern: true, includeTiaohou: true,
    includeSpecialPatterns: true, includeRelations: true, includeElementCounts: true,
  };

  async function submit() {
    state.loading = true;
    state.error = "";
    state.result = null;
    resetTemporal();
    resetAi();
    try {
      state.result = await analyzeBirthInfo({
        birthInfo: baseBirth(),
        options: { ...FULL_OPTIONS },
      });
    } catch (e) {
      state.error = e instanceof Error ? e.message : String(e);
    } finally {
      state.loading = false;
    }
    void loadMeta();
  }

  function resetTemporal() {
    state.temporal = null;
    state.temporalError = "";
    state.temporalLoading = false;
    state.temporalSelection = { luckIndex: null, year: null, month: null, day: "", withReplay: true };
  }

  function resetAi() {
    state.aiState = "IDLE";
    state.aiResult = null;
    state.aiError = "";
  }

  /** 岁运分析：复用同一 analyze 端点，仅追加 temporal 相关 options（契约不变） */
  async function runTemporal() {
    if (!state.result) return;
    if (state.temporalSelection.luckIndex === null && state.temporalSelection.year === null) {
      state.temporalError = "请先选择大运或流年";
      return;
    }
    state.temporalLoading = true;
    state.temporalError = "";
    try {
      const resp = await analyzeBirthInfo({
        birthInfo: baseBirth(),
        options: {
          ...FULL_OPTIONS,
          includeTemporal: true,
          targetLuckIndex: state.temporalSelection.luckIndex,
          targetYear: state.temporalSelection.year,
          targetMonth: state.temporalSelection.month,
          targetDay: state.temporalSelection.day || undefined,
          includeTemporalDelta: true,
          includeEventThemes: true,
          includeTemporalReplay: state.temporalSelection.withReplay,
        },
      });
      state.temporal = resp.temporal ?? null;
      if (!state.temporal) {
        state.temporalError = "该命例无法进行岁运分析（大运缺席：性别或时辰未知）";
      }
    } catch (e) {
      state.temporalError = e instanceof Error ? e.message : String(e);
    } finally {
      state.temporalLoading = false;
    }
  }

  function setLuck(v: number | null) {
    state.temporalSelection.luckIndex = v;
    state.temporalSelection.year = null;
    state.temporalSelection.month = null;
    state.temporalSelection.day = "";
    state.temporal = null;
  }
  function setYear(v: number | null) {
    state.temporalSelection.year = v;
    state.temporalSelection.month = null;
    state.temporalSelection.day = "";
    state.temporal = null;
  }
  function setMonth(v: number | null) {
    state.temporalSelection.month = v;
    state.temporalSelection.day = "";
    state.temporal = null;
  }
  function setDay(v: string) {
    state.temporalSelection.day = v;
    state.temporal = null;
  }

  async function generateAi() {
    if (!state.result) return;
    state.aiState = "LOADING";
    state.aiError = "";
    // 若时序工作台已加载岁运上下文，合并进解释输入（AI 只消费引擎结果）
    const payload = state.temporal
      ? { ...state.result, temporal: state.temporal }
      : state.result;

    const out = await interpretAnalysis(payload);
    if (out.kind === "not_configured") {
      state.aiState = "NOT_CONFIGURED";
      return;
    }
    if (out.kind === "error") {
      state.aiState = "PROVIDER_ERROR";
      state.aiError = out.message;
      return;
    }
    if (!out.interpretation.groundingPassed) {
      state.aiResult = out.interpretation;
      state.aiState = "GROUNDING_FAILED";
      return;
    }
    state.aiResult = out.interpretation;
    state.aiState = "SUCCESS";
  }

  return {
    state,
    // 供只读消费
    ...toRefs(state),
    pillars, pillarOrder, dayMasterStem,
    luck, luckOptions, yearOptions, monthOptions,
    timeStops, matchedRules, deltaGroups,
    relationChains, combinationStates, eventThemeExplanations,
    // 动作
    loadMeta, submit, runTemporal, resetTemporal, resetAi, generateAi,
    setLuck, setYear, setMonth, setDay,
  };
}

export type TianzeStore = ReturnType<typeof useTianze>;

/** 全局唯一 store（研究报告工具：单命例、单会话，无需多实例） */
let singleton: TianzeStore | null = null;
export function tianzeStore(): TianzeStore {
  if (!singleton) singleton = useTianze();
  return singleton;
}

/* ---------------------------------------------------------- 会话级 UI 状态 */

/** 当前研究工作区路由（侧栏导航目标） */
export type Workspace =
  | "home" | "intake"
  | "overview" | "strength" | "pattern" | "relations" | "structure" | "tiaohou" | "advanced"
  | "temporal" | "knowledge" | "ai" | "report";

export const workspace = ref<Workspace>("home");
export const aiDialogOpen = ref(false);
/** 知识图谱的聚焦目标（关系引文 → 图谱联动） */
export const graphFocus = ref<string | null>(null);
/** 知识图谱搜索框初值（由跳转注入） */
export const graphSearchSeed = ref("");

export const ui = readonly({
  openWorkspace(w: Workspace) { workspace.value = w; },
  openAiDialog() { aiDialogOpen.value = true; },
});

export function openWorkspace(w: Workspace) { workspace.value = w; }
