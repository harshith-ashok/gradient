import { expect, test } from "@playwright/test";

test("management reviews progress, finds a student, and changes the pass mark", async ({ page, browser }) => {
  // --- staff portal sign-in lands on the management dashboard
  await page.goto("/login");
  await page.getByRole("button", { name: "Faculty / Management" }).click();
  await page.getByRole("button", { name: /Richard Hale/ }).click();
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.getByRole("heading", { name: "Student progress" })).toBeVisible();
  await expect(page.getByText("Students registered")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Courses" })).toBeVisible();

  // --- role fences: management cannot open the student area
  await page.goto("/student");
  await expect(page).toHaveURL(/\/admin$/);

  // --- filters: search narrows the table, and the URL keeps the state
  await page.getByLabel("Search students").fill("meera");
  await page.getByRole("button", { name: "Apply" }).click();
  await expect(page).toHaveURL(/q=meera/);
  await expect(page.getByRole("link", { name: "Meera Iyer" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Daniel Okafor" })).toHaveCount(0);
  await page.getByRole("link", { name: "Clear" }).click();
  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.getByLabel("Search students")).toHaveValue("");
  await page.getByLabel("Status").selectOption("attention");
  await page.getByRole("button", { name: "Apply" }).click();
  await expect(page).toHaveURL(/status=attention/);
  const badges = page.locator("tbody td .badge");
  await expect(badges.first()).toHaveText("Needs attention");
  expect(await badges.allTextContents()).not.toContain("On track"); // every row matches the filter

  // --- student detail (read-only) shows quiz history and the failed attempt
  await page.goto("/admin?q=meera");
  await page.getByRole("link", { name: "Meera Iyer" }).click();
  await expect(page.getByRole("heading", { name: "Meera Iyer", level: 1 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Quiz history" })).toBeVisible();
  await expect(page.getByText("Below pass mark").first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Open →" })).toHaveCount(0); // locked for management

  // --- change the global pass mark and give one course its own
  await page.getByRole("link", { name: "Pass mark" }).first().click();
  await expect(page.getByRole("heading", { name: "Quiz pass mark", level: 1 })).toBeVisible();
  const save = page.getByRole("button", { name: "Save settings" });
  await expect(save).toBeDisabled(); // nothing changed yet
  await page.getByLabel("Override pass mark for Programming in C", { exact: true }).check();
  await page.getByLabel("Pass mark for Programming in C", { exact: true }).fill("85");
  await expect(page.getByText("Unsaved changes")).toBeVisible();
  await save.click();
  await expect(page.getByText("Pass mark settings saved.")).toBeVisible();
  await expect(page.getByText("Unsaved changes")).toHaveCount(0);

  // --- invalid values cannot be saved
  await page.getByLabel("Pass mark for Programming in C", { exact: true }).fill("20");
  await expect(save).toBeDisabled();
  await expect(page.getByText(/whole numbers from 40 to 100/)).toBeVisible();

  // --- a student now sees the new pass mark on the course page
  const student = await (await browser.newContext()).newPage();
  await student.goto("/login");
  await student.getByRole("button", { name: /Meera Iyer/ }).click();
  await student.getByRole("button", { name: "Sign in" }).click();
  await expect(student).toHaveURL(/\/student$/);
  await student.goto("/student/courses/c-cs101");
  await expect(student.getByText("Quiz pass mark").locator("xpath=following-sibling::div[1]")).toHaveText("85%");

  // --- put the demo data back
  await page.reload();
  await page.getByLabel("Override pass mark for Programming in C", { exact: true }).uncheck();
  await page.getByRole("button", { name: "Save settings" }).click();
  await expect(page.getByText("Pass mark settings saved.")).toBeVisible();
  await student.reload();
  await expect(student.getByText("Quiz pass mark").locator("xpath=following-sibling::div[1]")).toHaveText("70%");

  // --- sign out
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login/);
});

test("faculty and students cannot reach management pages", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("button", { name: /Meera Iyer/ }).click();
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/student$/);
  await page.goto("/admin/settings");
  await expect(page).toHaveURL(/\/student$/);
  const r = await page.request.get("/api/v1/admin/overview");
  expect(r.status()).toBe(403);
});
