import { execSync } from "node:child_process";
import path from "node:path";
import { expect, test } from "@playwright/test";

// Needs the stack started with LLM_PROVIDER=fake (`make e2e-faculty`), so no real model is involved.
test.skip(!process.env.E2E_FAKE_AI, "set E2E_FAKE_AI=1 with the stack running on the fake model");

const cleanup = () =>
  execSync("uv run python -m scripts.delete_courses E2E", { cwd: path.resolve(__dirname, "../../backend"), stdio: "inherit" });
test.beforeAll(cleanup);
test.afterAll(cleanup);

test("faculty uploads a syllabus, reviews and edits the draft, and publishes", async ({ page }) => {
  test.setTimeout(120_000);
  await page.goto("/login");
  await page.getByRole("button", { name: "Faculty / Management" }).click();
  await page.getByRole("button", { name: /Ananya Rao/ }).click();
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/faculty$/);

  // --- upload pasted text
  await page.getByRole("link", { name: "New course from syllabus" }).click();
  await page.getByLabel("Course code").fill("E2E 101");
  await page.getByLabel("Course title").fill("Browser Test Course");
  await page.getByRole("tab", { name: "Paste text" }).click();
  await page.getByLabel("Syllabus text").fill("1. Relational Model\n- tables and keys\n2. Query Languages\n- select and join\n");
  await page.getByRole("button", { name: "Upload and analyse" }).click();

  // --- pick topics (untick one), build sub-topics
  await expect(page.getByRole("heading", { name: "Choose the course topics" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Build 2 topics/ })).toBeVisible({ timeout: 60_000 });
  await page.getByRole("checkbox").last().uncheck();
  await page.getByRole("button", { name: /Build 1 topic/ }).click();
  await expect(page).toHaveURL(/\/faculty\/courses\/.*new=1/, { timeout: 60_000 });

  // --- generate study material for the whole course
  await expect(page.getByRole("heading", { name: "Browser Test Course", level: 1 })).toBeVisible();
  await page.getByRole("button", { name: /Generate study material for the whole course/ }).click();
  await expect(page.getByText("Study material generated. Review it below.")).toBeVisible({ timeout: 90_000 });

  // --- review: open a sub-topic, see every level filled in, edit a question, save
  const outline = page.getByRole("navigation", { name: "Course outline" });
  await outline.getByRole("button", { name: /Foundations/ }).click();
  await expect(outline.getByRole("button", { name: /Foundations.*4\/4/ })).toBeVisible();
  await page.getByRole("tab", { name: /expert/i }).click();
  await expect(page.locator("textarea").filter({ hasText: "expert level" }).first()).toBeVisible();
  const question = page.getByLabel("Question 1", { exact: true });
  await question.fill("An edited question: which statement is correct?");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByText("Saved.")).toBeVisible();
  await page.reload();
  await outline.getByRole("button", { name: /Foundations/ }).click();
  await expect(page.getByLabel("Question 1", { exact: true })).toHaveValue("An edited question: which statement is correct?");

  // --- publish; it shows in the student catalogue
  await page.getByRole("button", { name: "Publish", exact: true }).click();
  await expect(page.getByText("Published. Students can now enrol.")).toBeVisible();
  await page.goto("/faculty");
  await expect(page.locator("article").filter({ hasText: "Browser Test Course" }).getByText("Published")).toBeVisible();
});
