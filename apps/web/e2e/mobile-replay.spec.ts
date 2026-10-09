/**
 * M39 · 移动端视口与回放交互验收（真实浏览器）。
 * - 375px 视口完成排盘→分析，总览无横向溢出；
 * - 时序工作台开启"状态回放"后出现逐层回放时间轴；
 * - 关系页出现合化状态区块（后端 combination_state 链）。
 */
import { expect, test } from "@playwright/test";

test.describe("M39 mobile & replay", () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test("375px: full analysis flow without horizontal overflow", async ({ page }) => {
    await page.goto("/");
    await page.fill('input[type="date"]', "1984-02-05");
    await page.fill('input[type="time"]', "14:30");
    await page.click("button.submit");
    await expect(page.locator(".summary-pillar")).toHaveCount(4, { timeout: 20000 });
    // 总览无横向溢出
    const overflow = await page.evaluate(() => {
      const el = document.querySelector(".panel");
      if (!el) return 0;
      return el.scrollWidth - el.clientWidth;
    });
    expect(overflow).toBeLessThanOrEqual(2);
    // 术语说明可展开
    await page.click("text=术语与状态说明");
    await expect(page.locator("text=候选（CANDIDATE）").first()).toBeVisible();
  });

  test("375px: relations tab shows combination states", async ({ page }) => {
    await page.goto("/");
    await page.fill('input[type="date"]', "1984-02-05");
    await page.fill('input[type="time"]', "14:30");
    await page.click("button.submit");
    await expect(page.locator(".summary-pillar").first()).toBeVisible({ timeout: 20000 });
    await page.click('button:has-text("关系")');
    await expect(page.locator("text=合化状态").first()).toBeVisible({ timeout: 15000 });
  });
});

test.describe("M39 replay interaction (desktop)", () => {
  test("replay timeline renders layered steps with rule link", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/");
  await page.fill('input[type="date"]', "2003-08-18");
  await page.fill('input[type="time"]', "14:30");
  await page.click("button.submit");
  await expect(page.locator(".pillar-card")).toHaveCount(4, { timeout: 15000 });

  await page.locator("nav.tabs button", { hasText: "时序" }).click();
  await page.locator(".temporal-controls select").first().selectOption({ index: 1 });
  await page.locator(".temporal-controls select").nth(1).selectOption({ index: 1 });
  await page.click('.temporal-controls button:has-text("分析")');

  // M31 起工作台默认带状态回放（includeTemporalReplay）
  await expect(page.locator("text=逐层状态回放").first()).toBeVisible({ timeout: 30000 });
  await expect(page.locator("text=TR-DTZ-10（虚神交互）").first()).toBeVisible();
  await expect(page.locator("text=不构成吉凶或事件预测").first()).toBeVisible();
});

});
