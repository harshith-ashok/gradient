import { expect, test, type Page } from "@playwright/test";

const TITLE = `E2E double ${Date.now()}`;

async function type(page: Page, label: string, code: string) {
  const editor = page.getByRole("group", { name: label }).locator(".cm-content");
  await editor.click();
  await page.keyboard.press("ControlOrMeta+a");
  await page.keyboard.press("Delete");
  await page.keyboard.type(code);
}

test("faculty writes a coding challenge, a student solves it in the sandbox", async ({ page, browser }) => {
  test.setTimeout(120_000);
  page.on("dialog", (d) => d.accept());

  // --- faculty adds a challenge and checks its tests with a reference solution
  await page.goto("/login");
  await page.getByRole("button", { name: "Faculty / Management" }).click();
  await page.getByRole("button", { name: /Ananya Rao/ }).click();
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/faculty/);
  await page.goto("/faculty/courses/c-cs101");
  await page.getByRole("button", { name: "+ Challenge" }).click();
  const challenge = page.locator("section").filter({ hasText: "Coding challenges" }).locator("fieldset").last();
  await challenge.getByLabel("Title", { exact: true }).fill(TITLE);
  await page.getByLabel("Statement (Markdown)").fill("Read an integer `n` and print `2n`.");
  await page.getByLabel("Test 1 input").fill("3\n");
  await page.getByLabel("Test 1 expected output").fill("6\n");
  await page.getByLabel("Test 2 input").fill("10\n");
  await page.getByLabel("Test 2 expected output").fill("20\n");
  await page.getByRole("button", { name: "Save challenge" }).click();
  await expect(page.getByText("Challenge saved.")).toBeVisible();

  await page.getByText("Check the tests with a reference solution").click();
  await type(page, "Reference solution", "n = int(input())\nprint(n * 2)\n");
  await page.getByRole("button", { name: "Run against all tests" }).click();
  await expect(page.getByText("Accepted")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText("2 of 2 tests passed")).toBeVisible();

  // --- a student finds it, runs the samples, fails a hidden test, then solves it
  const ctx = await browser.newContext();
  const s = await ctx.newPage();
  await s.goto("/login");
  await s.getByRole("button", { name: /Fatima Khan/ }).click();
  await s.getByRole("button", { name: "Sign in" }).click();
  await expect(s).toHaveURL(/\/student/);
  await s.goto("/student/courses/c-cs101/subtopics/c-vars");
  await s.getByRole("link", { name: TITLE }).click();
  await expect(s.getByRole("heading", { name: TITLE, level: 1 })).toBeVisible();
  await expect(s.getByText("1 more hidden test is checked")).toBeVisible();

  await type(s, "Python code editor", "n = int(input())\nprint(6 if n == 3 else 0)\n");
  await s.getByRole("button", { name: "Run samples" }).click();
  await expect(s.getByRole("status").getByText("Accepted")).toBeVisible({ timeout: 60_000 });
  await s.getByRole("button", { name: "Submit", exact: true }).click();
  await expect(s.getByRole("status").getByText("Wrong answer").first()).toBeVisible({ timeout: 60_000 });
  await expect(s.getByText("1 of 2 tests passed")).toBeVisible();
  await expect(s.getByText("Test 2 (hidden)")).toBeVisible();

  await type(s, "Python code editor", "n = int(input())\nprint(n * 2)\n");
  await s.getByRole("button", { name: "Submit", exact: true }).click();
  await expect(s.getByText("2 of 2 tests passed")).toBeVisible({ timeout: 60_000 });
  await expect(s.getByText("Solved", { exact: true })).toBeVisible();
  await ctx.close();

  // --- tidy up
  await challenge.getByRole("button", { name: "Delete", exact: true }).click();
  await expect(page.getByText(TITLE)).toHaveCount(0);
});
