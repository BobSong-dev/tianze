import { test, expect } from "@playwright/test";
import { navigateTo } from "./helpers";

const routes = [
  ["overview", "命盘总览"], ["strength", "旺衰"], ["pattern", "格局"],
  ["relations", "关系"], ["structure", "结构"], ["tiaohou", "调候"],
  ["advanced", "高级结构"], ["temporal", "岁运时序"], ["knowledge", "知识图谱"],
  ["ai", "AI 解读"], ["report", "研究报告"],
];

for (const width of [375, 768, 1440]) {
  test(`redesign: all workspaces at ${width}px`, async ({ page }) => {
    test.setTimeout(120000);
    const errors: string[] = [];
    page.on("pageerror", error => errors.push(error.message));
    await page.setViewportSize({ width, height: 960 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/");
    await expect(page.locator("h1")).toContainText("观天时");
    await page.screenshot({ path: `test-results/redesign/home-${width}.png`, fullPage: true });
    await page.getByLabel("选择节气").selectOption("冬至");
    await expect(page.locator(".astrolabe-readout")).toContainText("阴极阳生");
    await page.locator('input[type="date"]').fill("1984-02-05");
    await page.locator('input[type="time"]').fill("10:30");
    await page.locator("button.submit").click();
    await expect(page.locator(".pillar-card")).toHaveCount(4);

    for (const [id, label] of routes) {
      await navigateTo(page, label);
      await expect(page.locator(`.workspace-${id}`)).toBeVisible();
      if (id === "knowledge") await expect(page.locator(".metric-val").first()).not.toBeEmpty();
      if (id === "temporal") {
        await page.locator(".temporal-controls select").nth(0).selectOption({ index: 1 });
        await page.locator(".temporal-controls select").nth(1).selectOption({ index: 1 });
        await page.locator(".temporal-controls button").click();
        await expect(page.getByText("逐层状态回放", { exact: true })).toBeVisible();
      }
      const dimensions = await page.evaluate(() => ({
        page: document.documentElement.scrollWidth,
        viewport: window.innerWidth,
      }));
      expect(dimensions.page, `${id} horizontal overflow at ${width}`).toBeLessThanOrEqual(dimensions.viewport + 1);
      await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
      await page.screenshot({ path: `test-results/redesign/${id}-${width}.png` });
      if (id === "knowledge") {
        for (const label of ["规则目录检索", "知识规模与漏斗", "审计门与覆盖率", "AI 评测对比", "复核队列与发布"]) {
          await page.getByRole("tab", { name: new RegExp(label) }).click();
          expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width + 1);
        }
      }
    }
    expect(errors).toEqual([]);
  });
}

test("redesign: modal keyboard focus and restore", async ({ page }) => {
  await page.goto("/");
  const trigger = page.getByRole("button", { name: "AI 设置", exact: true });
  await trigger.click();
  const dialog = page.getByRole("dialog", { name: "AI 服务设置" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("button", { name: "关闭", exact: true }).first()).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  expect(await dialog.evaluate(element => element.contains(document.activeElement))).toBe(true);
  await page.keyboard.press("Tab");
  await expect(dialog.getByRole("button", { name: "关闭", exact: true }).first()).toBeFocused();
  await page.screenshot({ path: "test-results/redesign/ai-settings.png" });
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(trigger).toBeFocused();
});

test("redesign: graph controls, tabs, and empty search", async ({ page }) => {
  await page.goto("/");
  await page.locator("button.submit").click();
  await expect(page.locator(".pillar-card")).toHaveCount(4);
  await navigateTo(page, "知识图谱");
  const graph = page.locator(".graph-svg");
  await expect(page.locator(".graph-node").first()).toBeVisible();
  const original = await graph.getAttribute("viewBox");
  await page.getByRole("button", { name: "放大", exact: true }).click();
  expect(await graph.getAttribute("viewBox")).not.toBe(original);
  await page.getByRole("button", { name: "重置视图", exact: true }).click();
  await expect(graph).toHaveAttribute("viewBox", original!);
  await page.locator(".graph-node").first().focus();
  await page.keyboard.press("Enter");
  await expect(page.locator(".graph-node.is-selected")).toHaveCount(1);
  await page.getByRole("tab", { name: /规则关系图谱/ }).focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.locator("#tab-rules")).toBeFocused();
  await expect(page.locator("#panel-rules")).toBeVisible();
  const search = page.locator('#panel-rules input');
  await search.fill("not-a-real-rule-000");
  await expect(page.getByText("无匹配规则。", { exact: true })).toBeVisible();
  await search.fill("");
  await expect(page.locator(".rule-card").first()).toBeVisible();
});

test("redesign: narrow, landscape, and large text", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  for (const size of [{ width: 320, height: 740 }, { width: 812, height: 375 }, { width: 1024, height: 768 }]) {
    await page.setViewportSize(size);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(size.width + 1);
  }
  await page.setViewportSize({ width: 375, height: 812 });
  await page.locator("button.submit").click();
  await expect(page.locator(".pillar-card")).toHaveCount(4);
  await page.addStyleTag({ content: "html { font-size: 200%; }" });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(376);
  await navigateTo(page, "研究报告");
  await page.emulateMedia({ media: "print" });
  await expect(page.locator(".app-sidebar")).not.toBeVisible();
  await expect(page.locator(".report-title")).toBeVisible();
});

test("redesign: knowledge unavailable gives recoverable error", async ({ page }) => {
  await page.goto("/");
  await page.locator("button.submit").click();
  await expect(page.locator(".pillar-card")).toHaveCount(4);
  await page.route("**/api/v1/knowledge/**", route => route.abort());
  await navigateTo(page, "知识图谱");
  await expect(page.getByRole("alert")).toContainText("暂时无法加载");
  await page.unroute("**/api/v1/knowledge/**");
  await page.getByRole("button", { name: "重新加载" }).click();
  await expect(page.getByRole("alert")).not.toBeVisible();
  await expect(page.locator(".graph-node").first()).toBeVisible();
});
