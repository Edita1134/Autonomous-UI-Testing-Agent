import { test, expect } from "@playwright/test";

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
