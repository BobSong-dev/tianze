/**
 * M42 视觉自审截图：真实浏览器渲染各关键页面 → PNG 供人工复核。
 *
 * 覆盖三档视口（1440 / 768 / 375）与全部主要工作区，
 * 使"视觉自审"成为可重复运行的验收步骤，而不是一次性人工操作。
 */
import { test, type Page } from "@playwright/test";
import fs from "node:fs";
import { navigateTo, openDrawer } from "./helpers";

const OUT = "test-results/visual";
fs.mkdirSync(OUT, { recursive: true });

async function analyze(page: Page, date = "1984-02-05", time = "10:30") {
  await page.goto("/");
  await page.fill('input[type="date"]', date);
  await page.fill('input[type="time"]', time);
  await page.click("button.submit");
  await page.waitForSelector(".pillar-tile", { timeout: 20000 });
  await page.waitForTimeout(300);
}

/** 导航到工作区（.side-nav 是唯一导航入口；容器内含编号与计数文本，按标签匹配） */
function nav(page: Page, label: string) {
  return navigateTo(page, label);
}

/* ------------------------------- 1440 ------------------------------- */

test("1440 home", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/01-home-1440.png`, fullPage: true });
});

test("1440 chart + overview", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await analyze(page);
  await page.screenshot({ path: `${OUT}/02-chart-overview-1440.png`, fullPage: true });
});

test("1440 strength + pattern + relations", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await analyze(page);
  await nav(page, "旺衰");
  await page.waitForTimeout(250);
  await page.screenshot({ path: `${OUT}/03-strength-1440.png`, fullPage: true });
  await nav(page, "格局");
  await page.waitForTimeout(250);
  await page.screenshot({ path: `${OUT}/04-pattern-1440.png`, fullPage: true });
  await nav(page, "关系");
  await page.waitForTimeout(250);
  await page.screenshot({ path: `${OUT}/05-relations-1440.png`, fullPage: true });
});

test("1440 temporal", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await analyze(page, "2003-08-18", "14:30");
  await nav(page, "时序");
  await page.locator(".temporal-controls select").first().selectOption({ index: 1 });
  await page.locator(".temporal-controls select").nth(1).selectOption({ index: 1 });
  await page.click('.temporal-controls button:has-text("分析")');
  await page.waitForSelector("text=逐层状态回放", { timeout: 30000 });
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/06-temporal-1440.png`, fullPage: true });
});

test("1440 knowledge graph", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await analyze(page);
  await nav(page, "知识图谱");
  await page.waitForSelector(".graph-svg", { timeout: 25000 });
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT}/07-knowledge-1440.png`, fullPage: true });
});

test("1440 ai + settings modal", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await analyze(page);
  await nav(page, "AI 解读");
  await page.waitForSelector(".ai-status-strip", { timeout: 15000 });
  await page.waitForTimeout(200);
  await page.screenshot({ path: `${OUT}/08-ai-1440.png`, fullPage: true });

  // 全局 AI 设置入口（顶栏），不依赖当前是否已配置
  await page.locator(".topbar-actions button", { hasText: "AI 设置" }).click();
  await page.waitForSelector(".ai-modal", { timeout: 10000 });
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT}/09-ai-settings-1440.png` });
  await page.locator(".modal-close").click();
  await page.waitForSelector(".ai-modal", { state: "detached" });
});

test("1440 report", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await analyze(page);
  await nav(page, "研究报告");
  await page.waitForSelector(".report", { timeout: 15000 });
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${OUT}/10-report-1440.png`, fullPage: true });
});

/* -------------------------------- 768 ------------------------------- */

test("768 chart + relations", async ({ page }) => {
  await page.setViewportSize({ width: 768, height: 1024 });
  await page.goto("/");
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/11-home-768.png`, fullPage: true });

  await page.fill('input[type="date"]', "1984-02-05");
  await page.fill('input[type="time"]', "10:30");
  await page.click("button.submit");
  await page.waitForSelector(".pillar-tile", { timeout: 20000 });
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${OUT}/12-chart-768.png`, fullPage: true });

  // 768 下侧栏为抽屉
  await openDrawer(page);
  await page.waitForTimeout(320);
  await page.screenshot({ path: `${OUT}/13-drawer-768.png` });
  await nav(page, "关系");
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${OUT}/14-relations-768.png`, fullPage: true });
});

/* -------------------------------- 375 ------------------------------- */

test("375 home + chart + temporal", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT}/20-home-375.png`, fullPage: true });

  await page.fill('input[type="date"]', "1984-02-05");
  await page.fill('input[type="time"]', "10:30");
  await page.click("button.submit");
  await page.waitForSelector(".pillar-tile", { timeout: 20000 });
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/21-chart-375.png`, fullPage: true });
});

test("375 temporal rail", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");
  await page.fill('input[type="date"]', "2003-08-18");
  await page.fill('input[type="time"]', "14:30");
  await page.click("button.submit");
  await page.waitForSelector(".pillar-tile", { timeout: 20000 });

  await nav(page, "时序");
  await page.locator(".temporal-controls select").first().selectOption({ index: 1 });
  await page.locator(".temporal-controls select").nth(1).selectOption({ index: 1 });
  await page.click('.temporal-controls button:has-text("分析")');
  await page.waitForSelector("text=逐层状态回放", { timeout: 30000 });
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/22-temporal-375.png`, fullPage: true });
});

test("375 knowledge graph", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");
  await page.fill('input[type="date"]', "1984-02-05");
  await page.fill('input[type="time"]', "10:30");
  await page.click("button.submit");
  await page.waitForSelector(".pillar-tile", { timeout: 20000 });

  await nav(page, "知识图谱");
  await page.waitForSelector(".graph-svg", { timeout: 25000 });
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT}/23-knowledge-375.png`, fullPage: true });
});
