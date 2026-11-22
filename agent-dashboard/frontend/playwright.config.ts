import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.UI_BASE_URL || "http://127.0.0.1:8765";

export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  use: {
    baseURL,
    headless: true,
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
