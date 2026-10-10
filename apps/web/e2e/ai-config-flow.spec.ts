/**
 * M41-hotfix2 · AI 配置→解读 全链路回归（真实 API + 真实浏览器 + Node Mock Provider）。
 *
 * 背景：曾出现两类用户可见故障——
 *  a) "填了 Key 仍提示未配置"（.env 未被加载 / 旧 API 进程）；
 *  b) interpret 已成功但前端误报"未通过事实一致性检查"
 *     （API 返回 snake_case grounding_passed，前端读 camelCase）。
 * 本 spec 锁定用户可见契约：保存 → 状态条"页面配置" → 生成 → Mock 内容可见。
 * Mock 仅验证协议链路，不代表真实云 Provider 成绩（保持 verified:false / BLOCKED 纪律）。
 */
import { test, expect } from "@playwright/test";
import { createServer, type Server } from "node:http";

const MOCK_REPLY = JSON.stringify({
  summary: "MOCK-OK：端到端链路验证成功。",
  sections: [{
    type: "strength", title: "旺衰", content: "MOCK 内容（协议验证）。",
    evidenceIds: [], sourceIds: [],
  }],
  disagreements: [], uncertainties: [], sourceReferences: [],
});

let mockServer: Server | null = null;
let mockPort = 0;

// 两个用例共享 API 进程内存中的配置状态，必须串行
test.describe.configure({ mode: "serial" });

test.beforeAll(async () => {
  mockServer = createServer((req, res) => {
    const body = JSON.stringify({
      id: "mock", object: "chat.completion",
      choices: [{ index: 0, finish_reason: "stop",
                  message: { role: "assistant", content: MOCK_REPLY } }],
      usage: { prompt_tokens: 10, completion_tokens: 6 },
    });
    // 排空请求体（keep-alive 卫生），任何路径都按 chat/completions 应答
    req.on("data", () => {});
    req.on("end", () => {
      res.writeHead(200, { "Content-Type": "application/json",
                           "Content-Length": Buffer.byteLength(body) });
      res.end(body);
    });
  });
  await new Promise<void>(resolve => mockServer!.listen(0, "127.0.0.1", resolve));
  mockPort = (mockServer.address() as { port: number }).port;
});

test.afterAll(async () => {
  // 清理全局 API 状态，避免污染其他 spec（配置存 API 进程内存）
  await fetch("/api/v1/ai-config/clear", { method: "POST" }).catch(() => {});
  await new Promise<void>(resolve => mockServer ? mockServer.close(() => resolve()) : resolve());
});

test("configure via UI → status shows 页面配置 → interpret renders mock content", async ({ page }) => {
  await page.goto("/");
  await page.fill('input[type="date"]', "2003-08-18");
  await page.fill('input[type="time"]', "14:30");
  await page.click("button.submit");
  await expect(page.locator(".pillar-tile")).toHaveCount(4, { timeout: 20000 });

  // 用户路径：右上 ⚙ AI 设置 → 本地模型预设 → 填 Key/端点/模型 → 保存
  await page.click(".ai-entry");
  await page.waitForSelector(".ai-modal");
  await page.locator(".preset-card", { hasText: "本地模型" }).click();
  const inputs = page.locator(".ai-form-row input");
  await inputs.nth(0).fill("e2e-mock-key");
  await inputs.nth(1).fill(`http://127.0.0.1:${mockPort}/v1`);
  await inputs.nth(2).fill("e2e-mock-model");
  await page.click('.ai-modal button:has-text("保存配置")');
  await expect(page.locator(".ai-modal p.note").first())
    .toContainText("已保存", { timeout: 5000 });
  await page.click('.ai-modal button:has-text("关闭")');
  await page.waitForSelector(".ai-modal", { state: "detached" });

  // AI 页状态条必须显示页面配置（否则就是"保存了却不生效"类回归）
  await page.locator("nav.tabs button", { hasText: "AI 解读" }).click();
  await expect(page.locator("section .ai-status-strip").first())
    .toContainText("页面配置 · e2e-mock-model");

  // 生成 → Mock 内容可见；不得出现两种误导状态
  await page.locator("button", { hasText: "生成 AI 解读" }).click();
  await expect(page.locator("text=MOCK-OK")).toBeVisible({ timeout: 15000 });
  const body = await page.evaluate(() => document.body.innerText);
  expect(body).not.toContain("尚未配置");
  expect(body).not.toContain("未通过事实一致性检查");
});

test("unconfigured interpret degrades to guided 503 state", async ({ page }) => {
  // 显式确保未配置（与上一用例并行/乱序时保持独立）
  await fetch("/api/v1/ai-config/clear", { method: "POST" }).catch(() => {});
  await page.goto("/");
  await page.fill('input[type="date"]', "2003-08-18");
  await page.fill('input[type="time"]', "14:30");
  await page.click("button.submit");
  await expect(page.locator(".pillar-tile")).toHaveCount(4, { timeout: 20000 });
  await page.locator("nav.tabs button", { hasText: "AI 解读" }).click();
  await expect(page.locator("section .ai-status-strip").first())
    .toContainText("未配置");
});
