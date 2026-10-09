/** M41 视觉自审截图：真实浏览器渲染各关键页面 → PNG 供人工复核。 */
import { test } from "@playwright/test";
import fs from "node:fs";

const OUT = "test-results/visual";
fs.mkdirSync(OUT, { recursive: true });

test("screenshot home", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/01-home-1440.png`, fullPage: true });
});

test("screenshot chart + overview", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await page.fill('input[type="date"]', "1984-02-05");
  await page.fill('input[type="time"]', "10:30");
  await page.click("button.submit");
  await page.waitForSelector(".pillar-tile", { timeout: 20000 });
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/02-chart-overview-1440.png`, fullPage: true });
});

test("screenshot strength + temporal", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await page.fill('input[type="date"]', "1984-02-05");
  await page.fill('input[type="time"]', "10:30");
  await page.click("button.submit");
  await page.waitForSelector(".pillar-tile", { timeout: 20000 });
  await page.locator("nav.tabs button", { hasText: "旺衰" }).click();
  await page.screenshot({ path: `${OUT}/03-strength-1440.png` });
  await page.locator("nav.tabs button", { hasText: "时序" }).click();
  await page.locator(".temporal-controls select").first().selectOption({ index: 1 });
  await page.locator(".temporal-controls select").nth(1).selectOption({ index: 1 });
  await page.click('.temporal-controls button:has-text("分析")');
  await page.waitForSelector("text=逐层状态回放", { timeout: 30000 });
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/04-temporal-1440.png`, fullPage: true });
});

test("screenshot ai + settings modal", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await page.fill('input[type="date"]', "1984-02-05");
  await page.fill('input[type="time"]', "10:30");
  await page.click("button.submit");
  await page.waitForSelector(".pillar-tile", { timeout: 20000 });
  await page.locator("nav.tabs button", { hasText: "AI 解读" }).click();
  await page.waitForSelector(".ai-status-strip", { timeout: 15000 });
  await page.screenshot({ path: `${OUT}/05-ai-1440.png` });
  // 未配置时引导；已配置（env）时直接开设置
  const cfgBtn = page.locator("button:has-text('前往配置')");
  if (await cfgBtn.count()) await cfgBtn.click();
  else await page.locator(".ai-status-strip button", { hasText: "配置" }).click();
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/06-ai-settings-1440.png` });
});

test("screenshot mobile 375", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT}/07-home-375.png`, fullPage: true });
  await page.fill('input[type="date"]', "1984-02-05");
  await page.fill('input[type="time"]', "10:30");
  await page.click("button.submit");
  await page.waitForSelector(".pillar-tile", { timeout: 20000 });
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/08-chart-375.png`, fullPage: true });
});
