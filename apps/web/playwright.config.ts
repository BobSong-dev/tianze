import { defineConfig } from "@playwright/test";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

const localPython = resolve("../../", process.platform === "win32" ? ".venv/Scripts/python.exe" : ".venv/bin/python");
const python = process.env.TIANZE_PYTHON || (existsSync(localPython) ? localPython : "python");
if (process.env.E2E_API_ORIGIN || process.env.E2E_BASE_URL) {
  throw new Error("E2E 需要独立进程。请使用 E2E_WEB_PORT 和 E2E_API_PORT 指定空闲端口。");
}
const webPort = Number(process.env.E2E_WEB_PORT ?? 15173);
const apiPort = Number(process.env.E2E_API_PORT ?? 18000);
if (webPort === apiPort || [webPort, apiPort].some(port => !Number.isInteger(port) || port < 1 || port > 65535)) {
  throw new Error("请为测试前后端指定两个不同的有效端口。");
}
const baseURL = `http://127.0.0.1:${webPort}`;

export default defineConfig({
  testDir: "./e2e",
  outputDir: "./test-results/playwright",
  timeout: 30000,
  retries: 1,
  /**
   * 串行执行。
   * 原因：AI Provider 配置保存在 **API 进程内存**（单用户本地模式的设计），
   * 是跨浏览器共享的全局状态；并行 worker 会互相清除/覆盖配置，
   * 使 ai-config-flow 与其它 spec 出现互相干扰的假失败。
   * 前端其它状态均为 per-page，串行只影响总时长，不影响覆盖率。
   */
  workers: 1,
  fullyParallel: false,
  use: { baseURL },
  webServer: [
    {
      command: `"${python}" -m uvicorn apps.api.main:app --host 127.0.0.1 --port ${apiPort}`,
      cwd: "../../",
      env: { TIANZE_LLM_API_KEY: "", TIANZE_ALLOW_REMOTE_AI_CONFIG: "0" },
      port: apiPort, reuseExistingServer: false, timeout: 15000,
    },
    { command: `node node_modules/vite/bin/vite.js --port ${webPort} --strictPort`,
      env: { TIANZE_DEV_API_ORIGIN: `http://127.0.0.1:${apiPort}` },
      url: baseURL, reuseExistingServer: false, timeout: 15000 },
  ],
});
