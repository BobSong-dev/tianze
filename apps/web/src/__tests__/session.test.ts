import { beforeEach, describe, expect, it, vi } from "vitest";
import { useTianze } from "../composables/useTianze";
import { analyzeBirthInfo, getMeta, interpretAnalysis } from "../api/tianze";
import type { AnalyzeResponse } from "../types/tianze";

vi.mock("../api/tianze", () => ({ analyzeBirthInfo: vi.fn(), getMeta: vi.fn(), interpretAnalysis: vi.fn() }));
const result = { pillars: {}, dayMaster: { stem: "甲" } } as AnalyzeResponse;
function deferred<Value>() {
  let resolve!: (value: Value) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<Value>((accept, fail) => { resolve = accept; reject = fail; });
  return { promise, resolve, reject };
}
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(analyzeBirthInfo).mockResolvedValue(result);
  vi.mocked(getMeta).mockResolvedValue({ engineVersion: "test", analysisSchemaVersion: "1" } as Awaited<ReturnType<typeof getMeta>>);
});

describe("analysis snapshots and request ownership", () => {
  it("retains the entire successful snapshot when a replacement fails", async () => {
    const store = useTianze();
    await store.submit();
    store.setLuck(1);
    vi.mocked(analyzeBirthInfo).mockResolvedValueOnce({ ...result, temporal: { context: { annualYear: 1994 } } } as AnalyzeResponse);
    await store.runTemporal();
    vi.mocked(interpretAnalysis).mockResolvedValueOnce({ kind: "ok", interpretation: { summary: "上次解读", groundingPassed: true } });
    await store.generateAi();
    store.state.birth.date = "1990-07-12";
    vi.mocked(analyzeBirthInfo).mockRejectedValueOnce(new Error("offline"));
    expect(await store.submit()).toBe(false);
    expect(store.analysisBirth.value.date).toBe("2003-08-18");
    expect(store.state.temporal?.context.annualYear).toBe(1994);
    expect(store.state.aiResult?.summary).toBe("上次解读");
    expect(await store.submit()).toBe(true);
    expect(store.analysisBirth.value.date).toBe("1990-07-12");
    expect(store.state.temporal).toBeNull();
    expect(store.state.aiResult).toBeNull();
  });
  it("keeps report and temporal inputs on the submitted birth", async () => {
    const store = useTianze();
    await store.submit();
    store.state.birth.date = "1990-07-12";
    expect(store.hasDraftChanges.value).toBe(true);
    expect(store.analysisBirth.value.date).toBe("2003-08-18");
    store.setLuck(1);
    await store.runTemporal();
    expect(vi.mocked(analyzeBirthInfo).mock.lastCall?.[0].birthInfo.date).toBe("2003-08-18");
  });

  it("only accepts the latest natal request including its input snapshot", async () => {
    const store = useTianze();
    const older = deferred<AnalyzeResponse>();
    vi.mocked(analyzeBirthInfo).mockReturnValueOnce(older.promise);
    const pending = store.submit();
    store.state.birth.date = "1990-07-12";
    await store.submit();
    older.resolve({ ...result, dayMaster: { stem: "旧" } } as AnalyzeResponse);
    await pending;
    expect(store.state.result?.dayMaster.stem).toBe("甲");
    expect(store.analysisBirth.value.date).toBe("1990-07-12");
  });

  it.each(["success", "failure"])("discards stale temporal %s and preserves a newer loading state", async outcome => {
    const store = useTianze();
    await store.submit();
    store.setLuck(1);
    const older = deferred<AnalyzeResponse>();
    const newer = deferred<AnalyzeResponse>();
    vi.mocked(analyzeBirthInfo).mockReturnValueOnce(older.promise).mockReturnValueOnce(newer.promise);
    const pendingOld = store.runTemporal();
    store.setYear(1994);
    const pendingNew = store.runTemporal();
    if (outcome === "success") older.resolve({ ...result, temporal: { context: { annualYear: 1993 } } } as AnalyzeResponse);
    else older.reject(new Error("obsolete error"));
    await pendingOld;
    expect(store.state.temporal).toBeNull();
    expect(store.state.temporalError).toBe("");
    expect(store.state.temporalLoading).toBe(true);
    newer.resolve({ ...result, temporal: { context: { annualYear: 1994 } } } as AnalyzeResponse);
    await pendingNew;
    expect(store.state.temporal?.context.annualYear).toBe(1994);
  });

  it.each(["rechart", "year", "replay", "rerun"])("invalidates AI on %s", async action => {
    const store = useTianze();
    await store.submit();
    store.setLuck(1);
    const older = deferred<Awaited<ReturnType<typeof interpretAnalysis>>>();
    vi.mocked(interpretAnalysis).mockReturnValueOnce(older.promise);
    const pending = store.generateAi();
    if (action === "rechart") await store.submit();
    if (action === "year") store.setYear(1994);
    if (action === "replay") store.state.temporalSelection.withReplay = false;
    if (action === "rerun") await store.runTemporal();
    older.resolve({ kind: "ok", interpretation: { summary: "old", groundingPassed: true } });
    await pending;
    expect(store.state.aiResult).toBeNull();
    expect(store.state.aiState).toBe("IDLE");
  });

  it("keeps only the latest AI retry", async () => {
    const store = useTianze();
    await store.submit();
    const older = deferred<Awaited<ReturnType<typeof interpretAnalysis>>>();
    vi.mocked(interpretAnalysis).mockReturnValueOnce(older.promise).mockResolvedValueOnce({ kind: "ok", interpretation: { summary: "new", groundingPassed: true } });
    const pending = store.generateAi();
    await store.generateAi();
    older.resolve({ kind: "error", message: "old error", status: 500 });
    await pending;
    expect(store.state.aiResult?.summary).toBe("new");
    expect(store.state.aiState).toBe("SUCCESS");
  });

  it.each([[true, "SUCCESS"], [false, "GROUNDING_FAILED"], [undefined, "GROUNDING_UNKNOWN"]] as const)("preserves grounding state %s", async (groundingPassed, expected) => {
    const store = useTianze();
    await store.submit();
    vi.mocked(interpretAnalysis).mockResolvedValue({ kind: "ok", interpretation: { summary: "fixture", groundingPassed } });
    await store.generateAi();
    expect(store.state.aiState).toBe(expected);
  });
});
