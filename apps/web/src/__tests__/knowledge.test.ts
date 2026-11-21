import { afterEach, expect, it, vi } from "vitest";
import { loadKnowledgeBundle } from "../api/tianze";

afterEach(() => vi.unstubAllGlobals());
it.each(["rules", "stats", "review-queue", "funnel", "coverage", "release", "evaluation-compare"])("tracks a partial %s failure independently", async endpoint => {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => url.endsWith(`/${endpoint}`)
    ? Response.json({ error: "unavailable" }, { status: 500 })
    : Response.json({ rules: [{ id: "test" }], items: [], executableTotal: 1 })));
  const bundle = await loadKnowledgeBundle();
  expect(Object.keys(bundle.errors)).toHaveLength(1);
  if (endpoint !== "rules") expect(bundle.rules).toHaveLength(1);
});
