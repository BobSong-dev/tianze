import { createApp } from "vue";
import App from "./App.vue";

// 设计体系：令牌 → 基础 → 组件
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/components.css";

createApp(App).mount("#app");
