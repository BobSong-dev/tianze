import { test, expect } from "@playwright/test";

test("temporal workspace: select luck → year → analyze delta", async ({ page }) => {
  await page.goto("/");
  await page.fill('input[type="date"]', "2003-08-18");
  await page.fill('input[type="time"]', "14:30");
  await page.click("button.submit");
  await expect(page.locator(".pillar-card")).toHaveCount(4, { timeout: 15000 });

  await page.locator("nav.tabs button", { hasText: "时序" }).click();
  await expect(page.locator("h2", { hasText: "时序工作台" })).toBeVisible();

  // 选择大运 → 流年 → 分析
  const luckSelect = page.locator(".temporal-controls select").first();
  await luckSelect.selectOption({ index: 1 });
  const yearSelect = page.locator(".temporal-controls select").nth(1);
  await yearSelect.selectOption({ index: 1 });
  await page.click('.temporal-controls button:has-text("分析")');

  // 岁运上下文链：原局 → 大运 → 流年
  await expect(page.locator(".ctx-chip.natal")).toBeVisible();
  await expect(page.locator(".ctx-chip.luck")).toBeVisible();
  await expect(page.locator(".ctx-chip.annual")).toBeVisible();

  // 规则触发区渲染（至少 TR-SPZY-28 流年即太岁必触发）
  await expect(page.locator(".candidate-block").first()).toBeVisible({ timeout: 15000 });
  await expect(page.locator("text=TR-SPZY-28").first()).toBeVisible();

  // Delta 区渲染
  await expect(page.locator("h3", { hasText: "完整 Temporal Delta" })).toBeVisible();
  // 边界声明
  await expect(page.locator("text=不构成任何吉凶或事件预测")).toBeVisible();
});

test("event themes render with status and disclaimer", async ({ page }) => {
  await page.goto("/");
  await page.fill('input[type="date"]', "1984-02-05");
  await page.fill('input[type="time"]', "10:30");
  await page.click("button.submit");
  await expect(page.locator(".pillar-card")).toHaveCount(4, { timeout: 15000 });

  await page.locator("nav.tabs button", { hasText: "时序" }).click();
  await page.locator(".temporal-controls select").first().selectOption({ index: 1 });
  await page.locator(".temporal-controls select").nth(1).selectOption({ index: 1 });
  await page.click('.temporal-controls button:has-text("分析")');

  await expect(page.locator("h3", { hasText: "事件主题" })).toBeVisible({ timeout: 15000 });
  // M41-hotfix：状态徽章中文化（原码保留在 title 悬停），受控词汇表同步更新
  const badges = await page.locator(".candidate-block .badge").allTextContents();
  const statuses = badges.filter(b => ["候选", "倾向支持", "两说并存", "阻断", "待定"].includes(b));
  expect(statuses.length).toBeGreaterThan(0);
  expect(badges).not.toContain("CONFIRMED");
  expect(badges).not.toContain("已确认");
  // 非概率声明
  await expect(page.locator("text=非概率").first()).toBeVisible();
});
