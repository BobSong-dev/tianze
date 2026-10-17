import { test, type Page } from "@playwright/test";
import fs from "node:fs";

const OUT = "test-results/first-screen";
fs.mkdirSync(OUT, { recursive: true });

async function analyze(page: Page, date = "1984-02-05", time = "10:30") {
  await page.goto("/");
  await page.fill('input[type="date"]', date);
  await page.fill('input[type="time"]', time);
  await page.click("button.submit");
  await page.waitForSelector(".pillar-tile", { timeout: 20000 });
  await page.waitForTimeout(350);
}

/** 只截首屏：用户 10 秒内真正看到的东西 */
test("first screen: home", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/a-home-first-1440.png` });
  await page.screenshot({ path: `${OUT}/a-home-full-1440.png`, fullPage: true });
});

test("first screen: workspace", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await analyze(page);
  await page.screenshot({ path: `${OUT}/b-overview-first-1440.png` });
});

test("first screen: strength", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await analyze(page);
  await page.locator(".side-nav button", { hasText: "旺衰" }).click();
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${OUT}/c-strength-first-1440.png` });
});

test("first screen: mobile", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT}/d-home-first-375.png` });
  await analyze(page);
  await page.screenshot({ path: `${OUT}/e-overview-first-375.png` });
});
