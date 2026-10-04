import { test, expect } from "@playwright/test";

test("overseas timezone: NYC", async ({ page }) => {
  await page.goto("/");
  await page.fill('input[type="date"]', "1990-07-01");
  await page.fill('input[type="time"]', "08:00");
  await page.fill('input[type="number"]', "-4");
  await page.click("button.submit");
  await expect(page.locator(".pillar-card")).toHaveCount(4, { timeout: 15000 });
});
