/**
 * E2E 共享工具。
 *
 * 导航模型（M42 视觉重构后）：
 *  - 桌面（> 900px）：左侧「研究路径」常驻，.sidebar-toggle 被 CSS 隐藏；
 *  - 移动（≤ 900px）：侧栏为 fixed 抽屉，收起时仍在 DOM 中但被 translateX 移出视口。
 *    注意：此时元素的 boundingBox 非空，`isVisible()` 会返回 true，
 *    因此不能靠 isVisible 判断，必须先显式展开抽屉。
 */
import { expect, type Page } from "@playwright/test";

/** 判断抽屉是否已展开。 */
async function drawerOpen(page: Page): Promise<boolean> {
  return page
    .locator(".app-sidebar")
    .evaluate(el => el.classList.contains("is-open"))
    .catch(() => false);
}

/** 收起抽屉（幂等，与上一次运行状态无关）。 */
export async function closeDrawer(page: Page) {
  if (!(await drawerOpen(page))) return;
  await page.click(".sidebar-scrim");
  await page.waitForFunction(
    () => !document.querySelector(".app-sidebar")?.classList.contains("is-open"),
  );
}

/** 展开抽屉（幂等），并等待 transform 过渡结束。 */
export async function openDrawer(page: Page) {
  await closeDrawer(page);
  await page.click(".sidebar-toggle");
  await page.waitForFunction(() => {
    const el = document.querySelector(".app-sidebar");
    return Boolean(el?.classList.contains("is-open"))
      && Math.abs(el!.getBoundingClientRect().left) < 1;
  });
}

/**
 * 通过研究路径导航到某个工作区。
 * 桌面直接点击；移动端先展开抽屉。全流程幂等。
 */
export async function navigateTo(page: Page, label: string) {
  const toggleVisible = await page.locator(".sidebar-toggle").isVisible();
  if (toggleVisible) {
    await openDrawer(page);
  } else {
    await closeDrawer(page);
  }
  await page.locator(".side-nav button", { hasText: label }).click();
  await expect(page.locator(".app-sidebar")).not.toHaveClass(/is-open/);
}
