import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
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
  use: { baseURL: "http://localhost:5173" },
  webServer: [
    {
      command: "cd ../../ && .venv\\Scripts\\python.exe -m uvicorn apps.api.main:app --port 8000",
      port: 8000, reuseExistingServer: true, timeout: 15000,
    },
    { command: "npm run dev", port: 5173, reuseExistingServer: true, timeout: 15000 },
  ],
});
