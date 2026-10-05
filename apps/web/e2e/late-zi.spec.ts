import { test, expect } from "@playwright/test";

test("late zi: sect1 vs sect2 produce different day pillar", async ({ page }) => {
  await page.goto("/");
  await page.fill('input[type="date"]', "1986-04-21");
  await page.fill('input[type="time"]', "23:30");
  await page.getByLabel("晚子时流派").selectOption("1");
  await page.click("button.submit");
  await expect(page.locator(".pillar-card").nth(3)).toBeVisible({ timeout: 15000 });
  const day1 = await page.locator(".pillar-card").nth(2).textContent();
  await page.getByLabel("晚子时流派").selectOption("2");
  await page.click("button.submit");
  await expect(page.locator(".pillar-card").nth(3)).toBeVisible({ timeout: 15000 });
  const day2 = await page.locator(".pillar-card").nth(2).textContent();
  expect(day1).not.toBe(day2);
});
