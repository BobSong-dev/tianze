import { test, expect } from "@playwright/test";
import { navigateTo } from "./helpers";

/**
 * M42：导航由顶部 Tab 改为左侧「研究路径」（.side-nav）。
 * 全部导航点击都限定在该容器内，避免与内容区的同名文字（如"调候"小节标题）冲突。
 */
test("normal case: full analysis flow", async ({ page }) => {
  await page.goto("/");
  await page.fill('input[type="date"]', "2003-08-18");
  await page.fill('input[type="time"]', "14:30");
  await page.click("button.submit");
  await expect(page.locator(".pillar-card")).toHaveCount(4, { timeout: 15000 });
  await expect(page.locator(".pillar-tile .gz-stem").first()).toContainText("癸");

  const nav = (label: string) => navigateTo(page, label);

  await nav("旺衰");
  await expect(page.locator(".method-block")).toHaveCount(3);
  await expect(page.locator("text=dimension")).toBeVisible();
  await expect(page.locator("text=weighted")).toBeVisible();
  await expect(page.locator("text=fuyi")).toBeVisible();

  await nav("格局");
  await expect(page.locator(".ev-card, .row-item, .panel h2").first()).toBeVisible();

  await nav("调候");
  await expect(page.locator(".tiaohou-item").first()).toBeVisible();

  await nav("高级结构");
  await expect(page.locator("text=特殊格局候选")).toBeVisible();
});
