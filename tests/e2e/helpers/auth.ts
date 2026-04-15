import { expect, type Page } from "@playwright/test";

const demoPassword = process.env.BOOTSTRAP_DEMO_PASSWORD ?? "Daizhang#2026!";

export async function loginAs(page: Page, username: string, expectedPath: RegExp) {
  await page.goto("/login");
  await expect(page.getByText("登录").first()).toBeVisible();

  const localLoginToggle = page.getByRole("button", { name: /展开本地登录|收起本地登录/ });
  if (await localLoginToggle.isVisible()) {
    await localLoginToggle.click();
  }

  await page.getByLabel("账号").fill(username);
  await page.getByLabel("密码").fill(demoPassword);
  await page.getByRole("button", { name: /本地账号进入系统|进入系统/ }).click();

  await expect(page).toHaveURL(expectedPath);
}
