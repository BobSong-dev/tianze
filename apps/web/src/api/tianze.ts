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

export interface AnalyzePayload {
  birthInfo: {
    date: string; time?: string; gender?: string;
    timezoneOffset?: number; longitude?: number;
    sect?: number; place?: string;
  };
  options?: {
    includeStrength?: boolean; includePattern?: boolean; includeTiaohou?: boolean;
    includeSpecialPatterns?: boolean; includeRelations?: boolean; includeElementCounts?: boolean;
    strengthMethods?: string[];
    includeTemporal?: boolean;
    targetLuckIndex?: number | null; targetYear?: number | null;
    targetMonth?: number | null; targetDay?: string | null;
    includeTemporalDelta?: boolean;
  };
}

export async function analyzeBirthInfo(payload: AnalyzePayload): Promise<AnalyzeResponse> {
  const r = await fetch(`${BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await r.json();
  if (!r.ok) {
    const err = body?.error;
    throw new Error(err?.message || `Analysis failed: ${r.status}`);
  }
  return body as AnalyzeResponse;
}
