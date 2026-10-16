import type { AnalyzeResponse, MetaResponse } from "../types/tianze";

const BASE = "/api/v1";

export async function healthCheck(): Promise<{ status: string }> {
  const r = await fetch(`${BASE}/health`);
  if (!r.ok) throw new Error(`Health check failed: ${r.status}`);
  return r.json();
}

export async function getMeta(): Promise<MetaResponse> {
  const r = await fetch(`${BASE}/meta`);
  if (!r.ok) throw new Error(`Meta failed: ${r.status}`);
  return r.json();
}

export interface BirthInfoPayload {
  date: string; time?: string; gender?: string;
  timezoneOffset?: number; longitude?: number;
  sect?: number; place?: string;
}

export interface AnalyzeOptionsPayload {
  includeStrength?: boolean; includePattern?: boolean; includeTiaohou?: boolean;
  includeSpecialPatterns?: boolean; includeRelations?: boolean; includeElementCounts?: boolean;
  strengthMethods?: string[];
  includeTemporal?: boolean;
  targetLuckIndex?: number | null; targetYear?: number | null;
  targetMonth?: number | null; targetDay?: string | null;
  includeTemporalDelta?: boolean;
  includeEventThemes?: boolean;
  includeExplanations?: boolean;
  includeTemporalReplay?: boolean;
}

export interface AnalyzePayload {
  birthInfo: BirthInfoPayload;
  options?: AnalyzeOptionsPayload;
}

/** 把后端的 error envelope 归一成 Error（保留 code 供上层区分处理）。 */
export class TianzeApiError extends Error {
  code: string;
  constructor(message: string, code = "UNKNOWN") {
    super(message);
    this.name = "TianzeApiError";
    this.code = code;
  }
}

function messageOf(err: unknown, fallback: string): string {
  if (typeof err === "string" && err) return err;
  if (err && typeof err === "object") {
    const e = err as { message?: string; code?: string };
    if (e.message) return e.message;
    if (e.code) return e.code;
  }
  return fallback;
}

export async function analyzeBirthInfo(payload: AnalyzePayload): Promise<AnalyzeResponse> {
  const r = await fetch(`${BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await r.json().catch(() => null);
  if (!r.ok) {
    const err = body?.error;
    throw new TianzeApiError(
      messageOf(err, `分析失败：HTTP ${r.status}`),
      err?.code ?? `HTTP_${r.status}`,
    );
  }
  return body as AnalyzeResponse;
}

// ---------------- AI Provider 配置（后端会话内存；前端不持久化密钥） ----------------

export interface AiConfigStatus {
  configured: boolean;
  source: "env" | "ui" | "none" | string;
  baseUrl?: string;
  model?: string;
  keyMasked?: string;
  preset?: string;
  storage?: string;
  publicDeployWarning?: string;
}

export interface AiPreset {
  id: string;
  name: string;
  baseUrl: string;
  model: string;
  verified: boolean;
  allowLocal?: boolean;
}

export interface AiConfigForm {
  apiKey: string;
  baseUrl: string;
  model: string;
  preset: string;
}

export interface AiTestResult {
  ok: boolean;
  httpStatus?: number;
  provider?: string;
  error?: string;
}

async function jsonOr<T>(url: string, init?: RequestInit, fallback?: T): Promise<T> {
  try {
    const r = await fetch(url, init);
    return (await r.json()) as T;
  } catch {
    if (fallback !== undefined) return fallback;
    throw new Error("网络错误");
  }
}

export function getAiStatus(): Promise<AiConfigStatus> {
  return jsonOr<AiConfigStatus>(`${BASE}/ai-config/status`, undefined,
    { configured: false, source: "none" } as AiConfigStatus);
}

export function getAiPresets(): Promise<AiPreset[]> {
  return jsonOr<{ presets: AiPreset[] }>(`${BASE}/ai-config/presets`, undefined, { presets: [] })
    .then(d => d.presets ?? []);
}

export function setAiConfig(form: AiConfigForm): Promise<Record<string, unknown>> {
  return jsonOr<Record<string, unknown>>(`${BASE}/ai-config/set`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(form),
  });
}

export function testAiConfig(): Promise<AiTestResult> {
  return jsonOr<AiTestResult>(`${BASE}/ai-config/test`, { method: "POST" }, { ok: false, error: "网络错误" });
}

export function clearAiConfig(): Promise<Record<string, unknown>> {
  return jsonOr<Record<string, unknown>>(`${BASE}/ai-config/clear`, { method: "POST" }, {});
}

// ---------------- AI 解读 ----------------

export interface InterpretationSection {
  type: string;
  title: string;
  content: string;
  claims?: { refId?: string | null; ref_id?: string | null; type?: string }[];
  evidenceIds?: string[];
  evidence_ids?: string[];
  sourceIds?: string[];
  source_ids?: string[];
}

export interface Interpretation {
  summary: string;
  sections?: InterpretationSection[];
  disagreements?: string[];
  uncertainties?: string[];
  groundingPassed?: boolean;
  grounding_passed?: boolean;
  groundingIssues?: { severity: string; type: string; detail: string }[];
  grounding_issues?: { severity: string; type: string; detail: string }[];
  sourceReferences?: unknown[];
  source_references?: unknown[];
  [k: string]: unknown;
}

export type InterpretOutcome =
  | { kind: "ok"; interpretation: Interpretation }
  | { kind: "not_configured"; status: number }
  | { kind: "error"; message: string; status: number };

/**
 * 调用 /interpret。仅做 snake_case → camelCase 的**读取别名**归一
 * （API 契约未变，后端返回何种键即读何种键），不做任何语义加工。
 */
export async function interpretAnalysis(analysis: unknown): Promise<InterpretOutcome> {
  let r: Response;
  try {
    r = await fetch(`${BASE}/interpret`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ analysis }),
    });
  } catch (e) {
    return { kind: "error", message: e instanceof Error ? e.message : String(e), status: 0 };
  }

  if (r.status === 503) return { kind: "not_configured", status: 503 };

  const body = await r.json().catch(() => null);
  if (!r.ok) {
    return { kind: "error", message: messageOf(body?.error, `HTTP ${r.status}`), status: r.status };
  }

  const interp = (body?.interpretation ?? {}) as Interpretation;
  interp.groundingPassed = interp.groundingPassed ?? interp.grounding_passed;
  interp.groundingIssues = interp.groundingIssues ?? interp.grounding_issues ?? [];
  interp.sourceReferences = interp.sourceReferences ?? interp.source_references ?? [];
  for (const sec of interp.sections ?? []) {
    sec.sourceIds = sec.sourceIds ?? sec.source_ids ?? [];
    sec.evidenceIds = sec.evidenceIds ?? sec.evidence_ids ?? [];
    for (const c of sec.claims ?? []) c.refId = c.refId ?? c.ref_id ?? null;
  }
  return { kind: "ok", interpretation: interp };
}

// ---------------- 知识工作台（只读导航） ----------------

export interface KnowledgeBundle {
  rules: any[];
  stats: any;
  review: any[];
  funnel: any;
  coverage: any;
  release: any;
  evaluationCompare: any;
}

export async function loadKnowledgeBundle(): Promise<KnowledgeBundle> {
  const safe = (u: string) => fetch(u).then(x => x.json()).catch(() => null);
  const [rules, stats, review, funnel, coverage, release, evaluationCompare] = await Promise.all([
    safe(`${BASE}/knowledge/rules`),
    safe(`${BASE}/knowledge/stats`),
    safe(`${BASE}/knowledge/review-queue`),
    safe(`${BASE}/knowledge/funnel`),
    safe(`${BASE}/knowledge/coverage`),
    safe(`${BASE}/knowledge/release`),
    safe(`${BASE}/knowledge/evaluation-compare`),
  ]);
  return {
    rules: rules?.rules ?? [],
    stats,
    review: (review?.items ?? []).slice(0, 60),
    funnel, coverage, release, evaluationCompare,
  };
}

export function loadKnowledgeGraph(): Promise<any> {
  return fetch(`${BASE}/knowledge/graph`).then(x => x.json()).catch(() => null);
}
