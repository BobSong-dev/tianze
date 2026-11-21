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

const EMPTY_FORM: AiConfigForm = { apiKey: "", baseUrl: "", model: "", preset: "openai" };

export function useAiConfig() {
  const status = ref<AiConfigStatus | null>(null);
  const presets = ref<AiPreset[]>([]);
  const form = ref<AiConfigForm>({ ...EMPTY_FORM });
  const message = ref("");
  const messageTone = ref<"ok" | "warn" | "err" | "">("");
  const testing = ref(false);
  const testResult = ref<AiTestResult | null>(null);
  const saving = ref(false);
  const clearing = ref(false);
  const loadError = ref("");
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
    loadError.value = "";
    try {
      const [currentStatus, currentPresets] = await Promise.all([getAiStatus(), getAiPresets()]);
      status.value = currentStatus;
      presets.value = currentPresets;
      if (!loaded.value && !form.value.apiKey && !form.value.baseUrl && currentStatus.source === "ui") {
        form.value = {
          apiKey: "", baseUrl: currentStatus.baseUrl ?? "",
          model: currentStatus.model ?? "", preset: currentStatus.preset ?? EMPTY_FORM.preset,
        };
      }
      loaded.value = true;
    } catch (error) {
      loadError.value = `配置状态暂时无法刷新：${errorText(error)}。显示的状态可能已过期。`;
    }
  }

  function errorText(error: unknown): string {
    if (error instanceof Error) return error.message;
    if (error && typeof error === "object" && "message" in error) return String(error.message);
    return String(error ?? "未知错误");
  }

  function pickPreset(p: AiPreset) {
    form.value.preset = p.id;
    if (p.baseUrl) form.value.baseUrl = p.baseUrl;
    if (p.model) form.value.model = p.model;
    message.value = "";
    messageTone.value = "";
  }

  async function save() {
    if (saving.value || clearing.value) return;
    saving.value = true;
    message.value = "";
    messageTone.value = "";
    try {
      const result = await setAiConfig({ ...form.value });
      if (result.ok !== true) throw new Error(errorText(result.error));
      message.value = String(result.note ?? "已保存（存于服务端内存；重启后需重新配置）");
      messageTone.value = result.warning ? "warn" : "ok";
      if (result.warning) message.value += `　⚠ ${result.warning}`;
      form.value.apiKey = "";
      await refresh();
    } catch (error) {
      message.value = `保存失败：${errorText(error)}。请重试。`;
      messageTone.value = "err";
    } finally {
      saving.value = false;
    }
  }

  async function test() {
    if (testing.value) return;
    testing.value = true;
    testResult.value = null;
    try {
      testResult.value = await testAiConfig();
    } catch (error) {
      testResult.value = { ok: false, error: errorText(error) };
    } finally {
      testing.value = false;
    }
  }

  async function clear() {
    if (saving.value || clearing.value) return;
    clearing.value = true;
    message.value = "";
    messageTone.value = "";
    try {
      const result = await clearAiConfig();
      if (result.ok !== true) throw new Error(errorText(result.error));
      form.value = { ...EMPTY_FORM };
      testResult.value = null;
      message.value = "UI 配置已清除。环境变量配置不受影响。";
      messageTone.value = "ok";
      await refresh();
    } catch (error) {
      message.value = `清除失败：${errorText(error)}。原配置未确认清除，请重试。`;
      messageTone.value = "err";
    } finally {
      clearing.value = false;
    }
  }

  return {
    status, presets, form, message, messageTone, testing, testResult, saving, clearing, loaded, loadError,
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
