/**
 * useAiConfig — AI Provider 配置的前端状态（薄封装，不含任何推理）。
 *
 * 安全纪律（与后端一致，UI 必须如实告知）：
 *  - API Key 只存于**后端进程内存**，前端不持久化、不写入 localStorage；
 *  - 状态接口只回显掩码尾 4 位；
 *  - 配置操作仅限本机（后端强制），公网部署须自行加鉴权。
 */
import { computed, ref } from "vue";
import {
  clearAiConfig, getAiPresets, getAiStatus, setAiConfig, testAiConfig,
  type AiConfigForm, type AiConfigStatus, type AiPreset, type AiTestResult,
} from "../api/tianze";

const EMPTY_FORM: AiConfigForm = { apiKey: "", baseUrl: "", model: "", preset: "custom" };

export function useAiConfig() {
  const status = ref<AiConfigStatus | null>(null);
  const presets = ref<AiPreset[]>([]);
  const form = ref<AiConfigForm>({ ...EMPTY_FORM });
  const message = ref("");
  const messageTone = ref<"ok" | "warn" | "err" | "">("");
  const testing = ref(false);
  const testResult = ref<AiTestResult | null>(null);
  const saving = ref(false);
  const loaded = ref(false);

  const configured = computed(() => Boolean(status.value?.configured));
  const source = computed(() => status.value?.source ?? "none");
  /** 已配置来源的中文（E2E 依赖「页面配置」字样） */
  const sourceLabel = computed(() => {
    if (source.value === "env") return "环境变量配置";
    if (source.value === "ui") return "页面配置";
    return "未配置";
  });
  const activePreset = computed(() =>
    presets.value.find(p => p.id === form.value.preset) ?? null);

  async function refresh() {
    const [st, ps] = await Promise.all([getAiStatus(), getAiPresets()]);
    status.value = st;
    presets.value = ps;
    if (st?.source === "ui") {
      form.value = {
        apiKey: "",
        baseUrl: st.baseUrl ?? "",
        model: st.model ?? "",
        preset: st.preset ?? "custom",
      };
    }
    loaded.value = true;
  }

  function pickPreset(p: AiPreset) {
    form.value.preset = p.id;
    if (p.baseUrl) form.value.baseUrl = p.baseUrl;
    if (p.model) form.value.model = p.model;
    message.value = "";
    messageTone.value = "";
  }

  async function save() {
    saving.value = true;
    message.value = "";
    messageTone.value = "";
    const r = await setAiConfig({ ...form.value });
    const errText = typeof r.error === "object" && r.error
      ? String((r.error as any).message ?? (r.error as any).code ?? "")
      : (r.error as string | undefined);
    if (r.ok) {
      message.value = String(r.note ?? "已保存（存于服务端内存；重启后需重新配置）");
      messageTone.value = r.warning ? "warn" : "ok";
      if (r.warning) message.value += `　⚠ ${r.warning}`;
      form.value.apiKey = "";
      await refresh();
    } else {
      message.value = `保存失败：${errText ?? "未知错误"}`;
      messageTone.value = "err";
    }
    saving.value = false;
  }

  async function test() {
    testing.value = true;
    testResult.value = null;
    testResult.value = await testAiConfig();
    testing.value = false;
  }

  async function clear() {
    await clearAiConfig();
    form.value = { ...EMPTY_FORM };
    testResult.value = null;
    message.value = "UI 配置已清除。环境变量配置不受影响。";
    messageTone.value = "ok";
    await refresh();
  }

  return {
    status, presets, form, message, messageTone, testing, testResult, saving, loaded,
    configured, source, sourceLabel, activePreset,
    refresh, pickPreset, save, test, clear,
  };
}

export type AiConfigStore = ReturnType<typeof useAiConfig>;

let singleton: AiConfigStore | null = null;
export function aiConfigStore(): AiConfigStore {
  if (!singleton) singleton = useAiConfig();
  return singleton;
}
