import { test, expect, type Page } from "@playwright/test";
import { navigateTo, openDrawer } from "./helpers";

async function chart(page: Page) {
  await page.goto("/");
  await page.locator('input[type="date"]').fill("1984-02-05");
  await page.locator('input[type="time"]').fill("10:30");
  await page.locator("button.submit").click();
  await expect(page.locator(".pillar-card")).toHaveCount(4);
}

async function configureFixture(page: Page) {
  await page.route("**/api/v1/ai-config/status", route => route.fulfill({ json: {
    configured: true, source: "ui", model: "regression-fixture", preset: "custom", baseUrl: "https://example.invalid/v1",
  } }));
}

test("F01: unsubmitted birth cannot change report or temporal inputs", async ({ page }) => {
  await chart(page);
  const pillars = await page.locator(".pillar-card").allTextContents();
  await page.getByRole("button", { name: "调整参数", exact: true }).click();
  await page.locator('#workspace-parameters input[type="date"]').fill("1990-07-12");
  await page.getByRole("button", { name: "收起", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("尚未重新排盘");
  await navigateTo(page, "研究报告");
  await expect(page.locator(".report-sub")).toContainText("1984-02-05");
  expect(await page.locator(".pillar-card").allTextContents()).toEqual(pillars);
  await navigateTo(page, "岁运时序");
  await page.locator(".temporal-controls select").first().selectOption({ index: 1 });
  const request = page.waitForRequest(request => request.url().endsWith("/analyze"));
  await page.locator(".temporal-controls button").click();
  expect((await request).postDataJSON().birthInfo.date).toBe("1984-02-05");
  await expect(page.getByText("逐层状态回放", { exact: true })).toBeVisible();
  await page.screenshot({ path: "test-results/fixes/F01-snapshot.png" });
});

test("F02: stale temporal response never replaces a new selection", async ({ page }) => {
  await chart(page);
  await navigateTo(page, "岁运时序");
  await page.locator(".temporal-controls select").first().selectOption({ index: 1 });
  const years = page.locator(".temporal-controls select").nth(1);
  await years.selectOption({ index: 1 });
  let release!: () => void;
  let arrived!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  const received = new Promise<void>(resolve => { arrived = resolve; });
  await page.route("**/api/v1/analyze", async route => {
    const response = await route.fetch();
    arrived();
    await held;
    await route.fulfill({ response });
  });
  await page.locator(".temporal-controls button").click();
  await received;
  await years.selectOption({ index: 2 });
  const response = page.waitForResponse(response => response.url().endsWith("/analyze"));
  release();
  await response;
  await expect(page.getByText("逐层状态回放", { exact: true })).not.toBeVisible();
  await expect(page.locator(".temporal-workspace")).toHaveAttribute("aria-busy", "false");
  await page.unroute("**/api/v1/analyze");
  await page.locator(".temporal-controls button").click();
  await expect(page.getByText("逐层状态回放", { exact: true })).toBeVisible();
  await expect(page.locator(".time-stop").nth(2)).toContainText(await years.inputValue());
});

for (const grounding of [true, false, undefined]) {
  test(`F03: report accurately shows grounding ${grounding}`, async ({ page }) => {
    await configureFixture(page);
    await page.route("**/api/v1/interpret", route => route.fulfill({ json: { interpretation: {
      summary: "测试解读", groundingPassed: grounding, sections: [],
      groundingIssues: grounding === false ? [{ detail: "测试引用偏差", type: "test", severity: "error" }] : [],
    } } }));
    await chart(page);
    await navigateTo(page, "AI 解读");
    await page.getByRole("button", { name: "生成 AI 解读", exact: true }).click();
    await expect(page.locator(".verdict-text")).toContainText("测试解读");
    await navigateTo(page, "研究报告");
    const expected = grounding === true ? "已通过事实一致性校验" : grounding === false ? "未通过事实一致性校验" : "校验状态未知";
    await expect(page.locator("#sec-ai")).toContainText(expected);
    await page.emulateMedia({ media: "print" });
    await expect(page.locator("#sec-ai")).toContainText(expected);
    if (grounding !== true) await expect(page.locator("#sec-ai")).not.toContainText("已通过事实一致性校验");
    await page.locator("#sec-ai").screenshot({ path: `test-results/fixes/F03-grounding-${grounding}.png` });
  });
}

test("F04: AI from a previous chart is discarded", async ({ page }) => {
  await configureFixture(page);
  let release!: () => void;
  let arrived!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  const received = new Promise<void>(resolve => { arrived = resolve; });
  await page.route("**/api/v1/interpret", async route => {
    arrived();
    await held;
    await route.fulfill({ json: { interpretation: { summary: "OLD-CHART-FIXTURE", groundingPassed: true } } });
  });
  await chart(page);
  await navigateTo(page, "AI 解读");
  await page.getByRole("button", { name: "生成 AI 解读", exact: true }).click();
  await received;
  await page.getByRole("button", { name: "调整参数", exact: true }).click();
  await page.locator('#workspace-parameters input[type="date"]').fill("1990-07-12");
  await page.locator(".app-topbar").getByRole("button", { name: "重新排盘", exact: true }).click();
  await expect(page.locator(".pillar-card")).toHaveCount(4);
  const response = page.waitForResponse(response => response.url().endsWith("/interpret"));
  release();
  await response;
  await navigateTo(page, "AI 解读");
  await expect(page.getByRole("button", { name: "生成 AI 解读", exact: true })).toBeVisible();
  await navigateTo(page, "研究报告");
  await expect(page.locator(".report-sub")).toContainText("1990-07-12");
  await expect(page.locator("#sec-ai")).not.toContainText("OLD-CHART-FIXTURE");
});

test("F05/F06: configuration failures recover without false success", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await configureFixture(page);
  await page.route("**/api/v1/ai-config/set", route => route.abort());
  await page.route("**/api/v1/ai-config/clear", route => route.fulfill({ status: 500, json: { ok: false } }));
  await page.goto("/");
  await page.getByRole("button", { name: "AI 设置", exact: true }).click();
  await page.getByLabel("API Key", { exact: true }).fill("test-not-a-secret");
  await page.getByRole("button", { name: "保存配置", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("保存失败");
  await expect(page.getByRole("button", { name: "保存配置", exact: true })).toBeEnabled();
  await expect(page.getByLabel("API Key", { exact: true })).toHaveValue("test-not-a-secret");
  await page.getByRole("button", { name: "清除配置", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("清除失败");
  await expect(page.locator(".msg-ok")).toHaveCount(0);
  await page.screenshot({ path: "test-results/fixes/F06-clear-error.png" });
  await page.unroute("**/api/v1/ai-config/set");
  await page.route("**/api/v1/ai-config/set", route => route.fulfill({ json: { ok: true } }));
  await page.getByRole("button", { name: "保存配置", exact: true }).click();
  await expect(page.locator(".msg-ok")).toContainText("已保存");
  expect(errors).toEqual([]);
});

test("F07/F08: drawer resizing and nested settings preserve keyboard access", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await chart(page);
  await openDrawer(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await expect(page.locator(".app-main")).not.toHaveAttribute("inert");
  await page.getByRole("button", { name: "调整参数", exact: true }).click();
  await page.setViewportSize({ width: 375, height: 812 });
  await openDrawer(page);
  await page.locator(".side-foot").getByRole("button", { name: "AI 设置", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "AI 服务设置" });
  await expect(dialog).toBeVisible();
  await expect(page.locator(".app-sidebar")).not.toHaveClass(/is-open/);
  const close = dialog.getByRole("button", { name: "关闭", exact: true }).first();
  await expect(close).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(close).not.toBeFocused();
  expect(await dialog.evaluate(element => element.contains(document.activeElement))).toBe(true);
  await page.keyboard.press("Escape");
  await expect(page.locator(".sidebar-toggle")).toBeFocused();
});

test("F09: partial rule failure is not an empty search and can retry", async ({ page }) => {
  await page.route("**/api/v1/knowledge/rules", route => route.fulfill({ status: 500, json: { error: "unavailable" } }));
  await chart(page);
  await navigateTo(page, "知识图谱");
  await expect(page.getByRole("alert")).toContainText("规则目录暂时无法加载");
  await page.getByRole("tab", { name: /规则目录检索/ }).click();
  await expect(page.getByText("无匹配规则。", { exact: true })).not.toBeVisible();
  await page.screenshot({ path: "test-results/fixes/F09-partial-error.png" });
  await page.unroute("**/api/v1/knowledge/rules");
  await page.getByRole("button", { name: "重新加载", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await expect(page.locator(".rule-card").first()).toBeVisible();
});
test("report retains its chart after a failed recalculation and allows retry", async ({ page }) => {
  await page.goto("/");
  await page.locator('input[type="date"]').fill("2003-08-01");
  await page.getByRole("button", { name: /高级选项/ }).click();
  await page.getByPlaceholder(/116.4/).fill("87.6");
  await page.locator("button.submit").click();
  await expect(page.locator(".layman-lines")).toContainText("金最少（0 处）");
  await navigateTo(page, "研究报告");
  await expect(page.locator("#sec-basic")).toContainText("87.6°（仅记录）");
  await page.route("**/api/v1/analyze", route => route.fulfill({ status: 503, json: {} }), { times: 1 });
  await page.locator(".app-topbar").getByRole("button", { name: "重新排盘" }).click();
  await expect(page.getByRole("alert")).toContainText("上次成功的结果");
  await expect(page.locator("#sec-basic")).toContainText("2003-08-01");
  await page.getByRole("button", { name: "重试排盘" }).click();
  await expect(page.locator(".layman-lines")).toBeVisible();
});
