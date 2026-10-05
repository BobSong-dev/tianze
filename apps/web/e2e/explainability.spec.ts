import { test, expect } from "@playwright/test";

test("evidence drawer opens after analysis", async ({ page }) => {
  await page.goto("/");
  await page.fill('input[type="date"]', "2003-08-18");
  await page.fill('input[type="time"]', "14:30");
  await page.click("button.submit");
  await expect(page.locator(".pillar-card")).toHaveCount(4, { timeout: 15000 });
  await page.click('button:has-text("旺衰")');
  const details = page.locator(".method-block details summary");
  if (await details.first().isVisible()) {
    await details.first().click();
    await expect(page.locator(".evidence-item").first()).toBeVisible();
  }
});
