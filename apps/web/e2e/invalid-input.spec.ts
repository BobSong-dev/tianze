import { test, expect } from "@playwright/test";

test("invalid date shows error", async ({ page }) => {
  await page.goto("/");
  await page.fill('input[type="date"]', "invalid-date");
  await page.click("button.submit");
  await expect(page.locator(".error")).toBeVisible({ timeout: 10000 });
});
