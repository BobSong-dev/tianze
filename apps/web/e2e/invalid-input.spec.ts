import { test, expect } from "@playwright/test";

test("invalid date shows error", async ({ page }) => {
  // 原生 date input 拒绝畸形值（浏览器行为）；改为拦截 API 模拟后端 400 校验失败路径
  await page.route("**/api/v1/analyze", route => route.fulfill({
    status: 400,
    contentType: "application/json",
    body: JSON.stringify({ error: { code: "INVALID_BIRTH_INFO", message: "日期格式无效: 'invalid-date'", details: {} } }),
  }));
  await page.goto("/");
  await page.fill('input[type="date"]', "2003-08-18");
  await page.fill('input[type="time"]', "14:30");
  await page.click("button.submit");
  await expect(page.locator(".error")).toBeVisible({ timeout: 10000 });
});
