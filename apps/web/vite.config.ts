import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  // 127.0.0.1 显式 IPv4：避免 Node ≥17 把 localhost 解析为 ::1 而
  // uvicorn 绑定 127.0.0.1 时代理连接被拒（全站 /api 502）
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
});
