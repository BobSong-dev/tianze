import { test, expect } from "@playwright/test";

/**
 * 晚子时流派对照：同一出生时刻，sect1 与 sect2 应给出不同的日柱。
 *
 * M43 起参数区默认收起（工作区只保留一行"排盘参数"读数），
 * 调整前需先展开；这是产品行为变化，不是被测语义变化。
 */
test("late zi: sect1 vs sect2 produce different day pillar", async ({ page }) => {
  await page.goto("/");
  await page.fill('input[type="date"]', "1986-04-21");
  await page.fill('input[type="time"]', "23:30");
  await page.getByLabel("晚子时流派").selectOption("1");
  await page.click("button.submit");
  await expect(page.locator(".pillar-card").nth(3)).toBeVisible({ timeout: 15000 });
  const day1 = await page.locator(".pillar-card").nth(2).textContent();

  // 工作区内改流派：展开参数区再提交
  await page.click('button:has-text("调整参数")');
  await page.getByLabel("晚子时流派").selectOption("2");
  await page.click("button.submit");
  await expect(page.locator(".param-strip")).toContainText("晚子时流派 2");
  await expect(page.locator(".pillar-card").nth(2)).not.toHaveText(day1!);
});
