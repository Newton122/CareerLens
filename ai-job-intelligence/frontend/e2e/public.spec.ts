import { test, expect, cvFile, waitForApi } from "./support/fixtures";

test.describe("public pages", () => {
  test("the landing page opens at / and stays there", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /Find Your Perfect/ })).toBeVisible();
    // It must not bounce anyone (signed in or not) to a dashboard.
    await page.waitForTimeout(1000);
    expect(new URL(page.url()).pathname).toBe("/");
  });

  for (const path of ["/about", "/how-it-works", "/pricing", "/faq", "/contact"]) {
    test(`${path} renders`, async ({ page }) => {
      await page.goto(path);
      await expect(page.locator("main")).toBeVisible();
      // The shared Navbar is there (these pages once had none).
      await expect(page.getByText("CareerLens").first()).toBeVisible();
    });
  }
});

test.describe("demo analysis (no account)", () => {
  test("scores a CV against a pasted job description", async ({ page }) => {
    await page.goto("/demo-analysis");
    await page.locator('input[type="file"]').setInputFiles(cvFile("Demo Person"));
    await page.getByPlaceholder("e.g. Senior Data Engineer").fill("Backend Engineer");
    await page
      .getByPlaceholder("Paste the full job description here...")
      .fill("We need a backend engineer with Python, FastAPI, PostgreSQL and Kubernetes. 3+ years.");

    const analyzed = waitForApi(page, "POST", "/api/demo/analyze");
    await page.getByRole("button", { name: /Analyze CV/ }).click();
    expect((await analyzed).status()).toBe(200);

    await expect(page.getByText("Match Score")).toBeVisible();
    await expect(page.getByText("How this score was calculated")).toBeVisible();
  });

  test("can run several analyses in a row", async ({ page }) => {
    // Regression: the submit button once stayed disabled after two runs.
    await page.goto("/demo-analysis");
    for (let run = 0; run < 3; run++) {
      await page.locator('input[type="file"]').setInputFiles(cvFile(`Run ${run}`));
      await page.getByPlaceholder("e.g. Senior Data Engineer").fill(`Role ${run}`);
      await page
        .getByPlaceholder("Paste the full job description here...")
        .fill("Python developer with SQL and Docker experience, 2 years or more.");
      const analyzed = waitForApi(page, "POST", "/api/demo/analyze");
      await page.getByRole("button", { name: /Analyze CV/ }).click();
      expect((await analyzed).status()).toBe(200);
    }
  });
});
