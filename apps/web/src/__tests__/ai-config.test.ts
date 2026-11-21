import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { useAiConfig } from "../composables/useAiConfig";

const configured = { configured: true, source: "ui", model: "fixture", baseUrl: "https://example.invalid/v1" };
let action: (url: string) => Response | Promise<Response>;
beforeEach(() => {
  action = () => Response.json({ ok: true });
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (url.endsWith("/status")) return Response.json(configured);
    if (url.endsWith("/presets")) return Response.json({ presets: [] });
    return action(url);
  }));
});
afterEach(() => vi.unstubAllGlobals());

it.each(["offline", "html", "403", "500", "negative"])("save recovers from %s and retains credentials for retry", async failure => {
  const store = useAiConfig();
  store.form.value.apiKey = "fixture-not-a-secret";
  action = () => {
    if (failure === "offline") throw new Error("offline");
    if (failure === "html") return new Response("<html>Error</html>");
    return Response.json({ ok: false, error: "rejected" }, { status: failure === "negative" ? 200 : Number(failure) });
  };
  await store.save();
  expect(store.saving.value).toBe(false);
  expect(store.messageTone.value).toBe("err");
  expect(store.form.value.apiKey).toBe("fixture-not-a-secret");
  action = () => Response.json({ ok: true });
  await store.save();
  expect(store.messageTone.value).toBe("ok");
  expect(store.form.value.apiKey).toBe("");
});

it.each([403, 500, 200, 0])("never confirms an unsuccessful clear (%s)", async status => {
  const store = useAiConfig();
  await store.refresh();
  action = () => {
    if (!status) throw new Error("offline");
    return Response.json({ ok: false, error: "rejected" }, { status });
  };
  await store.clear();
  expect(store.clearing.value).toBe(false);
  expect(store.messageTone.value).toBe("err");
  expect(store.configured.value).toBe(true);
  expect(store.message.value).not.toContain("UI 配置已清除");
});

it("does not overwrite an edited form on refresh or pretend a failed status is unconfigured", async () => {
  const store = useAiConfig();
  await store.refresh();
  store.form.value.model = "unsaved-edit";
  await store.refresh();
  expect(store.form.value.model).toBe("unsaved-edit");
  vi.mocked(fetch).mockRejectedValue(new Error("offline"));
  await store.refresh();
  expect(store.configured.value).toBe(true);
  expect(store.loadError.value).toContain("无法刷新");
});
