import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30000,
  retries: 1,
  use: { baseURL: "http://localhost:5173" },
  webServer: [
    {
      command: "cd ../../ && .venv\\Scripts\\python.exe -m uvicorn apps.api.main:app --port 8000",
      port: 8000, reuseExistingServer: true, timeout: 15000,
    },
    { command: "npm run dev", port: 5173, reuseExistingServer: true, timeout: 15000 },
  ],
});
