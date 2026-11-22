import { test, expect } from "@playwright/test";

test("full dashboard walkthrough", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Ticket · Ready for QA" })).toBeVisible();
  await page.screenshot({ path: "test-results/dashboard-01-home.png", fullPage: true });

  const issue = page.getByRole("spinbutton", { name: "GitHub issue number" });
  await issue.fill("1");
  await page.getByRole("button", { name: "Load" }).click();
  await expect(page.getByRole("textbox", { name: "Ticket markdown" })).toContainText("Test SauceDemo");
  await expect(page.getByText("Loaded from GitHub issue #1.")).toBeVisible();
  await page.screenshot({ path: "test-results/dashboard-02-github-loaded.png", fullPage: true });

  await expect(page.getByRole("textbox", { name: "Website to test" })).toHaveValue("https://www.saucedemo.com");
  await expect(page.getByRole("checkbox", { name: /Post the result/ })).toBeVisible();
  await page.getByRole("checkbox", { name: /Post the result/ }).check();
  await page.getByRole("checkbox", { name: "Show the browser window while testing" }).check();
  await page.screenshot({ path: "test-results/dashboard-03-options.png", fullPage: true });

  await expect(page.getByRole("button", { name: "Run issue #1" })).toBeEnabled();
});

test("dashboard loads and ticket controls are available", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Ticket · Ready for QA" })).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Ticket markdown" })).toBeVisible();
  await expect(page.getByRole("spinbutton", { name: "GitHub issue number" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Run agent" })).toBeVisible();
});

test("ticket markdown enables the run button", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("textbox", { name: "Ticket markdown" }).fill(
    "# Login test\nTarget URL: https://example.com\n\n## Acceptance Criteria\n- AC1: Login page is displayed",
  );

  await expect(page.getByRole("button", { name: "Run agent" })).toBeEnabled();
});

test("GitHub issue number can be entered", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("spinbutton", { name: "GitHub issue number" }).fill("42");
  await expect(page.getByRole("button", { name: "Load" })).toBeEnabled();
});
