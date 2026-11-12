import { defineConfig } from "@playwright/test";

// Runs against an already-running stack (`make up`, or backend + `npm run dev`).
export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  workers: 1, // the journey mutates one demo student
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    launchOptions: process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {},
    trace: "retain-on-failure",
  },
});
