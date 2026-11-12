import { execSync } from "node:child_process";
import path from "node:path";
import { expect, test } from "@playwright/test";

const cleanup = () =>
  execSync("uv run python -m scripts.delete_users e2e-", { cwd: path.resolve(__dirname, "../../backend"), stdio: "inherit" });
test.beforeAll(cleanup);
test.afterAll(cleanup);

test("admin manages users, reads the endpoint list, and finds the change in the logs", async ({ page, browser }) => {
  await page.goto("/login");
  await page.getByRole("button", { name: "Faculty / Management" }).click();
  await page.getByRole("button", { name: /Richard Hale/ }).click();
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/admin$/);

  // --- create an account
  await page.getByRole("link", { name: "Users", exact: true }).click();
  await page.getByRole("button", { name: "Add user" }).click();
  const form = page.locator("form").filter({ hasText: "Create account" });
  await form.getByLabel("Full name").fill("E2E Tester");
  await form.getByLabel("Email").fill("e2e-tester@example.edu");
  await form.getByLabel("Role").selectOption("faculty");
  await form.getByLabel("Temporary password").fill("temporary-pass-1");
  await form.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByText("Account created.")).toBeVisible();
  await page.getByLabel("Search users").fill("e2e-tester");
  await page.getByRole("button", { name: "Apply" }).click();
  const row = page.getByRole("row", { name: /E2E Tester/ });
  await expect(row).toBeVisible();

  // --- the new account can sign in; then it is deactivated and cannot
  const other = await browser.newContext();
  const signIn = async () => {
    const p = await other.newPage();
    await p.goto("/login");
    await p.getByRole("button", { name: "Faculty / Management" }).click();
    await p.getByLabel("Email").fill("e2e-tester@example.edu");
    await p.getByLabel("Password").fill("temporary-pass-1");
    await p.getByRole("button", { name: "Sign in" }).click();
    return p;
  };
  const ok = await signIn();
  await expect(ok).toHaveURL(/\/faculty/, { timeout: 20_000 });

  await row.getByRole("button", { name: "Deactivate" }).click();
  await expect(page.getByText("E2E Tester was deactivated and signed out.")).toBeVisible();
  await expect(row.getByText("Deactivated")).toBeVisible();
  await ok.goto("/faculty");
  await expect(ok).toHaveURL(/\/login/); // the existing session is cut off at once
  await other.close();

  // --- you cannot lock yourself out
  await page.getByLabel("Search users").fill("richard");
  await page.getByRole("button", { name: "Apply" }).click();
  await expect(page.getByRole("button", { name: "Deactivate" })).toBeDisabled();
  await expect(page.getByLabel("Role for Prof. Richard Hale")).toBeDisabled();

  // --- roles and endpoints are read from the real guards
  await page.getByRole("link", { name: "Roles & endpoints" }).click();
  await expect(page.getByRole("heading", { name: "Roles & endpoints", level: 1 })).toBeVisible();
  await page.getByLabel("Search endpoints").fill("/admin/users");
  await expect(page.getByText("/api/v1/admin/users", { exact: true }).first()).toBeVisible();
  await page.getByLabel("Search endpoints").fill("");
  await page.getByLabel("Can be called by").selectOption("public");
  await expect(page.getByText("/api/v1/auth/login")).toBeVisible();

  // --- the audit trail shows who did what
  await page.getByRole("link", { name: "Logs" }).click();
  await page.getByLabel("Search messages").fill("e2e-tester@example.edu");
  await expect(page.getByText(/created faculty account e2e-tester@example.edu/).first()).toBeVisible();
  await expect(page.getByText(/changed e2e-tester@example.edu: deactivated/).first()).toBeVisible();

  // --- issues and system load
  await page.getByRole("link", { name: "Issues" }).click();
  await expect(page.getByRole("heading", { name: "Issues", level: 1 })).toBeVisible();
  await page.getByRole("link", { name: "System" }).click();
  await expect(page.getByRole("heading", { name: "Services" })).toBeVisible();
  await expect(page.getByText("postgres", { exact: true })).toBeVisible();
});
