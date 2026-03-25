import { expect, test } from "@playwright/test";

import { loginAs } from "./helpers/auth";

test("公开资料页可匿名访问", async ({ page }) => {
  await page.goto("/library/public");

  await expect(page.getByRole("heading", { name: "公开资料库" })).toBeVisible();
  await expect(page.getByText("当前公开条目")).toBeVisible();
  await expect(page.getByRole("link", { name: /返回登录/ })).toBeVisible();
});

test("桌面端老板主链路 smoke", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chromium", "仅桌面项目执行");

  await loginAs(page, "boss", /\/dashboard$/);
  await expect(page.getByText("工作台").first()).toBeVisible();
  await expect(page.getByRole("menuitem", { name: /到账核对/ })).toBeVisible();

  await page.getByRole("menuitem", { name: /客户开发/ }).click();
  await expect(page).toHaveURL(/\/leads$/);
  await expect(page.getByText("客户开发").first()).toBeVisible();

  await page.getByRole("menuitem", { name: /收费明细/ }).click();
  await expect(page).toHaveURL(/\/billing$/);
  await expect(page.getByText("收费明细").first()).toBeVisible();
});

test("移动端老板主链路 smoke", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile-chromium", "仅移动项目执行");

  await loginAs(page, "boss", /\/m\/todo$/);
  await expect(page.getByText("Todo").first()).toBeVisible();
  const mobileNav = page.locator(".mobile-shell-nav");

  await mobileNav.getByRole("button", { name: "开发", exact: true }).click();
  await expect(page).toHaveURL(/\/m\/leads$/);
  await expect(page.getByText("客户开发").first()).toBeVisible();

  await mobileNav.getByRole("button", { name: "收费", exact: true }).click();
  await expect(page).toHaveURL(/\/m\/billing$/);
  await expect(page.getByText("收费明细").first()).toBeVisible();

  await mobileNav.getByRole("button", { name: "更多", exact: true }).click();
  await expect(page).toHaveURL(/\/m\/more$/);
  await expect(page.getByText("更多").first()).toBeVisible();
});

test("管理员面板 smoke", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-chromium", "仅桌面项目执行");

  await loginAs(page, "admin", /\/dashboard$/);
  await page.goto("/admin/users");

  await expect(page).toHaveURL(/\/admin\/users$/);
  await expect(page.getByText("用户管理").first()).toBeVisible();
  await expect(page.getByText("数据授权").first()).toBeVisible();
});
