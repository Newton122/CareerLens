import { test, expect, SEEDED_ADMIN, signIn } from "./support/fixtures";

test.describe("admin", () => {
  test("dashboard and user management", async ({ page }) => {
    await signIn(page, SEEDED_ADMIN.email, SEEDED_ADMIN.password, "/admin/dashboard");
    await expect(page.getByText("System Dashboard")).toBeVisible();

    await page.goto("/admin/users");
    await expect(page.getByText("User Management")).toBeVisible();
    await expect(page.getByText(SEEDED_ADMIN.email).first()).toBeVisible();
  });

  test("a job seeker is kept out of the admin area", async ({ page }) => {
    await page.goto("/login");
    await page.evaluate(() => {
      localStorage.setItem("access_token", "not-a-real-token");
      localStorage.setItem("careerLens_role", "job_seeker");
    });
    await page.goto("/admin/dashboard");
    // Sent away from /admin (the fake token then fails at the API, which
    // signs the browser out and ends on /login).
    await expect(page).not.toHaveURL(/\/admin/);
  });
});
