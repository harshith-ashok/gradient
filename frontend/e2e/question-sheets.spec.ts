import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";

test("faculty exports questions to Excel and checks the file before importing it back", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("button", { name: "Faculty / Management" }).click();
  await page.getByRole("button", { name: /Ananya Rao/ }).click();
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/faculty/);
  await page.goto("/faculty/courses/c-cs101");
  await expect(page.getByRole("button", { name: "Save changes" }).or(page.getByRole("button", { name: "Saved" }))).toBeVisible();

  await page.getByText("Import or export questions (Excel)").click();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Export questions (.xlsx)" }).click(),
  ]);
  expect(download.suggestedFilename()).toMatch(/questions\.xlsx$/);
  const file = await download.path();
  expect(readFileSync(file).subarray(0, 2).toString()).toBe("PK"); // a real .xlsx (zip) file

  // The untouched export is valid and would change nothing, so there is nothing to import.
  await page.locator('input[type="file"]').setInputFiles(file);
  await page.getByRole("button", { name: "Check file" }).click();
  await expect(page.getByText("The file is valid. This is what importing will do:")).toBeVisible();
  await expect(page.getByText(/0 added · 0 updated · 0 removed/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Import", exact: true })).toBeDisabled();

  // A file that is not a workbook is refused with a clear message.
  await page.locator('input[type="file"]').setInputFiles({ name: "q.xlsx", mimeType: "text/plain", buffer: Buffer.from("a,b\n1,2") });
  await page.getByRole("button", { name: "Check file" }).click();
  await expect(page.getByText(/could not be read as an Excel workbook|upload an \.xlsx file/)).toBeVisible();
});
