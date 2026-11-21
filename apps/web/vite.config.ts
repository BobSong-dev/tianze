import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  // 显式 IPv4 双保险：host 绑 127.0.0.1（本机 Node 会把 localhost 只解析到
  // ::1，导致 IPv4 优先的浏览器打不开）；代理目标同样显式 127.0.0.1
  server: { host: "127.0.0.1", proxy: { "/api": process.env.TIANZE_DEV_API_ORIGIN || "http://127.0.0.1:8000" } },
});
