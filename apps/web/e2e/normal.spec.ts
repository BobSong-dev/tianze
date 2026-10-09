import { test, expect } from "@playwright/test";

test("normal case: full analysis flow", async ({ page }) => {
  await page.goto("/");
  await page.fill('input[type="date"]', "2003-08-18");
  await page.fill('input[type="time"]', "14:30");
  await page.click("button.submit");
  await expect(page.locator(".pillar-card")).toHaveCount(4, { timeout: 15000 });
  await expect(page.locator(".pillar-tile .gz-stem").first()).toContainText("癸");
  await page.click('button:has-text("旺衰")');
  await expect(page.locator(".method-block")).toHaveCount(3);
  await expect(page.locator("text=dimension")).toBeVisible();
  await expect(page.locator("text=weighted")).toBeVisible();
  await expect(page.locator("text=fuyi")).toBeVisible();
  await page.click('button:has-text("格局")');
  await expect(page.locator(".candidate-block, .status, .panel h2").first()).toBeVisible();
  await page.click('button:has-text("调候")');
  await expect(page.locator(".tiaohou-item").first()).toBeVisible();
  await page.locator("nav.tabs button", { hasText: "高级" }).click();
  await expect(page.locator("text=特殊格局候选")).toBeVisible();
});
