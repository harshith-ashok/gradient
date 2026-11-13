import { execSync } from "node:child_process";
import { readFileSync } from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";

// The question bank is fixed seed data, so the test can tell right answers from wrong ones
// without any help from the backend (the API never reveals answers before a quiz is submitted).
type Course = { topics: { subtopics: { questions: { text: string; options: string[]; answer: number }[] }[] }[] };
const fixture: Course[] = JSON.parse(
  readFileSync(path.resolve(__dirname, "../../backend/app/seed/fixtures/courses.json"), "utf8"),
);
const correct = new Map<string, string>();
for (const c of fixture)
  for (const t of c.topics)
    for (const s of t.subtopics) for (const q of s.questions) correct.set(q.text, q.options[q.answer]);

/** Answer every question in the quiz runner, all right or all wrong, then submit. */
async function answerQuiz(page: Page, right: boolean) {
  for (;;) {
    const text = (await page.locator("[data-question]").first().getAttribute("data-question"))!.trim();  // raw Markdown source
    const answer = correct.get(text);
    expect(answer, `unknown question: ${text}`).toBeTruthy();
    const options = page.locator(".opt");
    const n = await options.count();
    let target = -1;
    for (let i = 0; i < n; i++) {
      const label = (await options.nth(i).locator("[data-option]").getAttribute("data-option"))!.trim();
      if (right ? label === answer : label !== answer) { target = i; break; }
    }
    await options.nth(target).click();
    const submit = page.getByRole("button", { name: "Submit answers" });
    if (await submit.isVisible()) { await submit.click(); return; }
    await page.getByRole("button", { name: "Next question" }).click();
  }
}

// Fatima is the demo "new student": start from, and leave behind, a clean slate.
const resetFatima = () =>
  execSync("uv run python -m scripts.reset_student u-fatima", { cwd: path.resolve(__dirname, "../../backend"), stdio: "inherit" });
test.beforeAll(resetFatima);
test.afterAll(resetFatima);

test("a new student enrols, studies, fails a quiz, recovers and sees progress", async ({ page, context }) => {
  // --- sign in through the real form
  await page.goto("/login");
  await page.getByRole("button", { name: /Fatima Khan/ }).click();
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/student$/);
  await expect(page.getByText("You have not started a course yet")).toBeVisible();

  // --- enrol: pre-test (answered all wrong, so the plan needs full study)
  await page.getByRole("link", { name: "Courses", exact: true }).first().click();
  await page
    .locator("article")
    .filter({ has: page.getByRole("heading", { name: "Programming in C", exact: true }) })
    .getByRole("link", { name: "Enrol" })
    .click();
  await expect(page.getByRole("heading", { name: /Pre-test: Programming in C/ })).toBeVisible();
  await page.getByRole("button", { name: "Begin pre-test" }).click();
  await answerQuiz(page, false);
  await expect(page.getByRole("heading", { name: "Your pre-test results" })).toBeVisible();
  await expect(page.getByText(/personalised plan covers 14 tasks/)).toBeVisible();
  await page.getByRole("link", { name: "View my study plan" }).click();
  await expect(page.getByText("Day 1", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Plan created from your pre-test")).toBeVisible();

  // --- study the first sub-topic; the access token expires mid-session and the call still works
  await page.getByRole("link", { name: "Open →" }).first().click();
  await expect(page.getByRole("button", { name: "Mark as studied" })).toBeVisible();
  await context.clearCookies({ name: "access_token" });
  await page.getByRole("button", { name: "Mark as studied" }).click();
  await expect(page.getByText("Marked as studied.")).toBeVisible();
  await expect(page.getByText("Studied", { exact: true })).toBeVisible();

  // --- flashcards flip
  await page.getByRole("tab", { name: /Flashcards/ }).click();
  await expect(page.getByText("Card 1 of 3")).toBeVisible();
  await page.getByRole("button", { name: "Reveal answer" }).click();
  await expect(page.getByRole("button", { name: "Show prompt" })).toBeVisible();

  // --- take the quiz and fail it: the plan adapts
  await page.getByRole("link", { name: "Take the quiz" }).click();
  await page.getByRole("button", { name: "Start quiz" }).click();
  await answerQuiz(page, false);
  await expect(page.getByText("Below pass mark").first()).toBeVisible();
  await expect(page.getByText("Your plan has been adjusted.")).toBeVisible();
  await expect(page.getByText(/Remediation: /)).toBeVisible();
  await expect(page.getByText(/Retake quiz: /)).toBeVisible();

  // --- the plan page explains what changed
  await page.getByRole("link", { name: "Study plan" }).first().click();
  await expect(page.getByText("Rescheduled", { exact: true })).toBeVisible();
  await expect(page.getByText(/below the 70% threshold/)).toBeVisible();

  // --- change daily study time: plan is recalculated
  await page.getByLabel("Daily study time").selectOption("120");
  await expect(page.getByText("Plan recalculated for your new daily study time.")).toBeVisible();
  await expect(page.getByText(/Daily study time set to 120 minutes/)).toBeVisible();

  // --- open the remediation task from the plan, then retake the quiz and pass: level goes up
  await page.locator(".task", { hasText: "Remediation:" }).getByRole("link", { name: "Open →" }).click();
  await expect(page.getByText("A different way to think about it")).toBeVisible();
  await page.getByRole("link", { name: "Retake the quiz" }).click();
  await page.getByRole("button", { name: "Start quiz" }).click();
  await answerQuiz(page, true);
  await expect(page.getByText("Passed", { exact: true })).toBeVisible();
  await expect(page.getByText(/Level up:/)).toBeVisible();

  // --- on-demand practice
  await page.goto("/student/practice");
  await page.getByPlaceholder(/Quiz me on/).fill("arrays");
  await page.getByRole("button", { name: "Start quiz" }).first().click();
  await page.getByRole("button", { name: "Start quiz" }).click();
  await answerQuiz(page, true);
  await expect(page.getByText("Passed", { exact: true })).toBeVisible();

  // --- progress shows the full history
  await page.goto("/student/progress");
  await expect(page.getByRole("heading", { name: "Quiz history" })).toBeVisible();
  await expect(page.getByText("Diagnostic")).toBeVisible();
  await expect(page.getByText("Below pass mark").first()).toBeVisible();
  await expect(page.getByText("Passed").first()).toBeVisible();

  // --- sign out
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login/);
  await page.goto("/student");
  await expect(page).toHaveURL(/\/login\?redirect=/);
});
