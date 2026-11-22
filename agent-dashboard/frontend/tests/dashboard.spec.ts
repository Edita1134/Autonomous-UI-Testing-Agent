import { test, expect } from "@playwright/test";

test("complete dashboard walkthrough", async ({ page }) => {
  await page.route("**/api/progress**", (route) => route.fulfill({
    json: {
      run_id: "run-20261122-demo",
      status: "done",
      overall: "PASS",
      error: "",
      github_note: "Posted result to GitHub issue #1.",
      events: [
        { time: "12:00:01", text: "Running AC1: A standard user can log in successfully" },
        { time: "12:00:04", text: "Login completed successfully" },
        { time: "12:00:08", text: "Running AC2: The products page is displayed after login" },
        { time: "12:00:12", text: "Products page confirmed" },
        { time: "12:00:16", text: "Running AC3: The Sauce Labs Backpack can be added to the cart" },
        { time: "12:00:20", text: "Backpack added to cart" },
        { time: "12:00:24", text: "Running AC4: The cart badge shows 1 item" },
        { time: "12:00:28", text: "Overall result: PASS" },
      ],
      next: 8,
      screenshots: ["/evidence/run-20261121-203206/screenshots/003_AC1.3_click.png"],
    },
  }));

  await page.route("**/api/runs/run-20261122-demo", (route) => route.fulfill({
    json: {
      run_id: "run-20261122-demo",
      title: "Test SauceDemo login and cart workflow",
      target_url: "https://www.saucedemo.com",
      overall: "PASS",
      model: "gemini-3.5-flash-lite",
      duration_seconds: 28,
      video_files: [],
      screenshots: ["/evidence/run-20261121-203206/screenshots/003_AC1.3_click.png"],
      results: [
        { criterion: { id: "AC1", text: "A standard user can log in successfully" }, verdict: "PASS", reason: "Login completed", evidence: "Products page" },
        { criterion: { id: "AC2", text: "The products page is displayed after login" }, verdict: "PASS", reason: "Heading confirmed", evidence: "Products" },
        { criterion: { id: "AC3", text: "The Sauce Labs Backpack can be added to the cart" }, verdict: "PASS", reason: "Add action succeeded", evidence: "Remove" },
        { criterion: { id: "AC4", text: "The cart badge shows 1 item" }, verdict: "PASS", reason: "Badge confirmed", evidence: "1" },
      ],
    },
  }));

  await page.route("**/api/runs", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({ json: {
        run_id: "",
        criteria: [
          { id: "AC1", text: "A standard user can log in successfully" },
          { id: "AC2", text: "The products page is displayed after login" },
          { id: "AC3", text: "The Sauce Labs Backpack can be added to the cart" },
          { id: "AC4", text: "The cart badge shows 1 item" },
        ],
      } });
    } else {
      await route.continue();
    }
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Ticket · Ready for QA" })).toBeVisible();
  await page.waitForTimeout(1500);
  await page.screenshot({ path: "test-results/dashboard-01-home.png", fullPage: true });

  await page.getByRole("spinbutton", { name: "GitHub issue number" }).fill("1");
  await page.waitForTimeout(700);
  await page.getByRole("button", { name: "Load" }).click();
  await expect(page.getByText("Loaded from GitHub issue #1.")).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Website to test" })).toHaveValue("https://www.saucedemo.com");
  await page.waitForTimeout(1500);
  await page.screenshot({ path: "test-results/dashboard-02-github-loaded.png", fullPage: true });

  await page.getByRole("checkbox", { name: /Post the result/ }).check();
  await page.getByRole("checkbox", { name: "Show the browser window while testing" }).check();
  await page.waitForTimeout(1000);
  await page.screenshot({ path: "test-results/dashboard-03-options.png", fullPage: true });

  await page.getByRole("button", { name: "Run issue #1" }).click();
  await expect(page.getByText("Overall result: PASS")).toBeVisible({ timeout: 5000 });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: "test-results/dashboard-04-complete-run.png", fullPage: true });

  await page.getByRole("button", { name: "☾" }).click();
  await page.waitForTimeout(1000);
  await page.screenshot({ path: "test-results/dashboard-05-theme.png", fullPage: true });
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
  await page.getByRole("textbox", { name: "Ticket markdown" }).fill("# Login test\nTarget URL: https://example.com\n\n## Acceptance Criteria\n- AC1: Login page is displayed");
  await expect(page.getByRole("button", { name: "Run agent" })).toBeEnabled();
});

test("GitHub issue number can be entered", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("spinbutton", { name: "GitHub issue number" }).fill("42");
  await expect(page.getByRole("button", { name: "Load" })).toBeEnabled();
});
