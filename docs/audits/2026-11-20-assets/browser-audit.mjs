import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import { join } from "node:path";

const require = createRequire("C:/Project/tianze/apps/web/package.json");
const { chromium, expect } = require("@playwright/test");
const output = "C:/Project/tianze/apps/web/test-results/audit-20261120";
await mkdir(join(output, "evidence"), { recursive: true });
const browser = await chromium.launch({ headless: true });
const results = [];

async function navigate(page, label) {
  await page.locator(".side-nav").getByRole("button", { name: label, exact: true }).click();
}

async function chart(page) {
  await page.goto("http://127.0.0.1:5183");
  await page.locator('input[type="date"]').fill("1984-02-05");
  await page.locator('input[type="time"]').fill("10:30");
  await page.locator("button.submit").click();
  await expect(page.locator(".pillar-card")).toHaveCount(4);
}

async function configured(page) {
  await page.route("**/api/v1/ai-config/status", route => route.fulfill({ json: {
    configured: true, source: "ui", model: "audit-fixture", baseUrl: "https://example.invalid/v1", preset: "custom",
  } }));
}

async function screenshot(page, name, selector) {
  if (selector === ".ai-modal") {
    await page.locator(".ai-modal button").last().scrollIntoViewIfNeeded();
  }
  if (selector === ".temporal-workspace") {
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
    await page.screenshot({ path: join(output, "evidence", `${name}.png`) });
    return `${name}.png`;
  }
  const target = selector ? page.locator(selector) : page;
  await target.screenshot({ path: join(output, "evidence", `${name}.png`), ...(selector ? {} : { fullPage: true }) });
  return `${name}.png`;
}

async function audit(id, action, viewport = { width: 1440, height: 1000 }) {
  const page = await browser.newPage({ viewport });
  page.setDefaultTimeout(12000);
  await page.emulateMedia({ reducedMotion: "reduce" });
  const pageErrors = [];
  page.on("pageerror", error => pageErrors.push(error.message));
  try {
    results.push({ id, observed: true, ...await action(page), pageErrors });
  } catch (error) {
    results.push({ id, observed: false, error: error.message, pageErrors });
    await screenshot(page, `${id}-incomplete`).catch(() => {});
  } finally {
    await page.close();
    await writeFile(join(output, "browser-audit.json"), JSON.stringify(results, null, 2));
    console.log(JSON.stringify(results.at(-1)));
  }
}

await audit("F01-draft-mismatch", async page => {
  await chart(page);
  const originalPillars = await page.locator(".pillar-card").allTextContents();
  await page.getByRole("button", { name: "调整参数", exact: true }).click();
  await page.locator('#workspace-parameters input[type="date"]').fill("1990-07-12");
  await page.getByRole("button", { name: "收起", exact: true }).click();
  await navigate(page, "研究报告");
  const reportedBirth = await page.locator(".report-sub").innerText();
  const reportedPillars = await page.locator(".pillar-card").allTextContents();
  expect(reportedBirth).toContain("1990-07-12");
  expect(reportedPillars).toEqual(originalPillars);
  const evidence = await screenshot(page, "F01-report-draft", ".report-cover");
  await navigate(page, "岁运时序");
  await page.locator(".temporal-controls select").nth(0).selectOption({ index: 1 });
  const requestPromise = page.waitForRequest(request => request.url().endsWith("/analyze"));
  const responsePromise = page.waitForResponse(response => response.url().endsWith("/analyze"));
  await page.locator(".temporal-controls button").click();
  const request = (await requestPromise).postDataJSON();
  const response = await (await responsePromise).json();
  expect(request.birthInfo.date).toBe("1990-07-12");
  await expect(page.getByText("逐层状态回放", { exact: true })).toBeVisible();
  return { originalBirth: "1984-02-05", originalPillars, reportedBirth, reportedPillars, temporalRequestBirth: request.birthInfo, temporalNatal: response.temporal?.context, evidence: [evidence, await screenshot(page, "F01-mixed-natal", ".temporal-workspace")] };
});

await audit("F02-temporal-race", async page => {
  await chart(page);
  await navigate(page, "岁运时序");
  await page.locator(".temporal-controls select").nth(0).selectOption({ index: 1 });
  const years = page.locator(".temporal-controls select").nth(1);
  await years.selectOption({ index: 1 });
  const requestedYear = await years.inputValue();
  let release;
  let arrived;
  const held = new Promise(resolve => { release = resolve; });
  const received = new Promise(resolve => { arrived = resolve; });
  let context;
  await page.route("**/api/v1/analyze", async route => {
    const response = await route.fetch();
    const body = await response.json();
    context = body.temporal?.context;
    arrived();
    await held;
    await route.fulfill({ response });
  });
  await page.locator(".temporal-controls button").click();
  await received;
  await years.selectOption({ index: 2 });
  const selectedYear = await years.inputValue();
  release();
  await expect(page.getByText("逐层状态回放", { exact: true })).toBeVisible();
  expect(selectedYear).not.toBe(requestedYear);
  return { requestedYear, selectedYear, renderedOldContext: context, evidence: [await screenshot(page, "F02-temporal-race", ".temporal-workspace")] };
});

await audit("F03-grounding-report", async page => {
  await configured(page);
  await page.route("**/api/v1/interpret", route => route.fulfill({ json: { interpretation: {
    summary: "审计专用响应：此段未通过事实一致性校验。", groundingPassed: false,
    groundingIssues: [{ severity: "error", type: "audit", detail: "审计构造的引用偏差，不是真实模型输出。" }], sections: [],
  } } }));
  await chart(page);
  await navigate(page, "AI 解读");
  await page.getByRole("button", { name: "生成 AI 解读", exact: true }).click();
  await expect(page.locator(".is-warn-state")).toBeVisible();
  const warning = await page.locator(".is-warn-state").innerText();
  const first = await screenshot(page, "F03-ai-warning", ".workspace-ai");
  await navigate(page, "研究报告");
  await expect(page.locator("#sec-ai")).toContainText("以上 AI 文本已通过事实一致性校验");
  return { fixture: true, warning, reportText: await page.locator("#sec-ai").innerText(), evidence: [first, await screenshot(page, "F03-report-false-pass", "#sec-ai")] };
});

await audit("F04-stale-ai", async page => {
  await configured(page);
  let release;
  let arrived;
  const held = new Promise(resolve => { release = resolve; });
  const received = new Promise(resolve => { arrived = resolve; });
  await page.route("**/api/v1/interpret", async route => {
    arrived();
    await held;
    await route.fulfill({ json: { interpretation: { summary: "审计专用：1984-02-05 旧命例的迟到解读", groundingPassed: true, sections: [] } } });
  });
  await chart(page);
  await navigate(page, "AI 解读");
  await page.getByRole("button", { name: "生成 AI 解读", exact: true }).click();
  await received;
  await page.getByRole("button", { name: "调整参数", exact: true }).click();
  await page.locator('#workspace-parameters input[type="date"]').fill("1990-07-12");
  await page.locator(".app-topbar").getByRole("button", { name: "重新排盘", exact: true }).click();
  await expect(page.locator(".pillar-card")).toHaveCount(4);
  release();
  await navigate(page, "AI 解读");
  await expect(page.locator(".verdict-text")).toContainText("旧命例");
  await navigate(page, "研究报告");
  return { fixture: true, birth: await page.locator(".report-sub").innerText(), oldInterpretation: await page.locator("#sec-ai").innerText(), evidence: [await screenshot(page, "F04-stale-ai", "#sec-ai")] };
});

await audit("F05-save-network", async page => {
  await page.route("**/api/v1/ai-config/set", route => route.abort("failed"));
  await page.goto("http://127.0.0.1:5183");
  await page.getByRole("button", { name: "AI 设置", exact: true }).click();
  await page.getByLabel("API Key", { exact: true }).fill("audit-not-a-secret");
  await page.getByLabel("Base URL", { exact: true }).fill("https://example.invalid/v1");
  await page.getByLabel("模型名称", { exact: true }).fill("audit-fixture");
  const errorPromise = page.waitForEvent("pageerror");
  await page.getByRole("button", { name: "保存配置", exact: true }).click();
  const error = await errorPromise;
  await expect(page.getByRole("button", { name: "保存中…", exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "关闭", exact: true }).first().click();
  await page.getByRole("button", { name: "AI 设置", exact: true }).click();
  await expect(page.getByRole("button", { name: "保存中…", exact: true })).toBeDisabled();
  return { injected: "set request aborted in browser, not sent to backend", error: error.message, persistsAfterReopen: true, evidence: [await screenshot(page, "F05-save-stuck", ".ai-modal")] };
});

await audit("F06-clear-error", async page => {
  await configured(page);
  await page.route("**/api/v1/ai-config/clear", route => route.fulfill({ status: 500, json: { ok: false, error: { message: "审计模拟清除失败" } } }));
  await page.goto("http://127.0.0.1:5183");
  await page.getByRole("button", { name: "AI 设置", exact: true }).click();
  await page.getByRole("button", { name: "清除配置", exact: true }).click();
  await expect(page.locator(".msg-ok")).toContainText("UI 配置已清除");
  await expect(page.locator(".ai-status-meta")).toContainText("页面配置");
  return { fixture: true, message: await page.locator(".msg-ok").innerText(), status: await page.locator(".ai-status-meta").innerText(), evidence: [await screenshot(page, "F06-clear-false-success", ".ai-modal")] };
});

await audit("F07-resize-inert", async page => {
  await chart(page);
  await page.locator(".sidebar-toggle").click();
  await page.setViewportSize({ width: 1440, height: 1000 });
  await expect(page.locator(".sidebar-toggle")).not.toBeVisible();
  const inert = await page.locator(".app-main").evaluate(element => element.inert);
  expect(inert).toBe(true);
  let clickBlocked = false;
  try { await page.getByRole("button", { name: "调整参数", exact: true }).click({ trial: true, timeout: 1200 }); }
  catch { clickBlocked = true; }
  expect(clickBlocked).toBe(true);
  const evidence = await screenshot(page, "F07-resize-locked");
  await page.keyboard.press("Escape");
  await expect(page.locator(".app-main")).not.toHaveAttribute("inert");
  return { viewportFrom: 375, viewportTo: 1440, inert, clickBlocked, escapeRecovers: true, evidence: [evidence] };
}, { width: 375, height: 812 });

await audit("F08-nested-focus", async page => {
  await chart(page);
  await page.locator(".sidebar-toggle").click();
  await page.locator(".side-foot").getByRole("button", { name: "AI 设置", exact: true }).click();
  const close = page.getByRole("dialog", { name: "AI 服务设置" }).getByRole("button", { name: "关闭", exact: true }).first();
  await expect(close).toBeFocused();
  const focusSteps = [];
  for (const step of [1, 2, 3]) {
    await page.keyboard.press("Tab");
    focusSteps.push({ step, active: await page.evaluate(() => document.activeElement?.outerHTML) });
  }
  await expect(close).toBeFocused();
  return { focusSteps, evidence: [await screenshot(page, "F08-keyboard-trap")] };
}, { width: 375, height: 812 });

await audit("F09-partial-knowledge", async page => {
  await page.route("**/api/v1/knowledge/rules", route => route.fulfill({ status: 500, json: { error: "审计模拟规则目录不可用" } }));
  await chart(page);
  await navigate(page, "知识图谱");
  await expect(page.locator(".graph-node").first()).toBeVisible();
  await page.getByRole("tab", { name: /规则目录检索/ }).click();
  await expect(page.getByText("无匹配规则。", { exact: true })).toBeVisible();
  const alerts = await page.getByRole("alert").count();
  expect(alerts).toBe(0);
  return { fixture: true, failedEndpoint: "/knowledge/rules", alerts, metrics: await page.locator(".metric-val").allTextContents(), evidence: [await screenshot(page, "F09-partial-knowledge", ".workspace-knowledge")] };
});

await browser.close();
console.log(`Observed ${results.filter(result => result.observed).length}/${results.length} targeted conditions.`);
