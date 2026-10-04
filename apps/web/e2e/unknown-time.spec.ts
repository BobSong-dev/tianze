import { test, expect } from "@playwright/test";

test("unknown time: partial result with warning", async ({ page }) => {
  await page.goto("/");
  await page.fill('input[type="date"]', "1995-08-08");
  await page.uncheck('label.checkbox input[type="checkbox"]');
  await page.click("button.submit");
  await expect(page.locator(".pillar-card")).toHaveCount(3, { timeout: 15000 });
  await expect(page.locator(".fallback, .warning").first()).toBeVisible();
});
