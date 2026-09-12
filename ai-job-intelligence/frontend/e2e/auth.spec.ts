import {
  test,
  expect,
  PASSWORD,
  pressDialogButton,
  signIn,
  uniqueEmail,
  waitForApi,
} from "./support/fixtures";

test.describe("accounts", () => {
  test("register as a job seeker, sign in, see the email reminder, sign out", async ({ page }) => {
    const email = uniqueEmail("register");

    await page.goto("/register");
    await page.getByRole("button", { name: /looking for a job/ }).click();
    await page.getByRole("button", { name: /Continue/ }).click();
    await page.getByPlaceholder("Your name").fill("E2E Seeker");
    await page.getByPlaceholder("you@example.com").fill(email);
    await page.getByPlaceholder("At least 10 characters").fill(PASSWORD);
    const passwords = page.locator('input[type="password"]');
    if ((await passwords.count()) > 1) await passwords.nth(1).fill(PASSWORD);
    const registered = waitForApi(page, "POST", "/api/auth/register");
    await page.getByRole("button", { name: /Create Account/ }).click();
    expect((await registered).status()).toBe(200);
    await page.waitForURL("**/login");

    await signIn(page, email, PASSWORD, "/dashboard");
    await expect(page.getByText("Please confirm your email address")).toBeVisible();

    await page.getByRole("button", { name: /Logout/ }).filter({ visible: true }).click();
    await page.waitForURL("**/login");
    expect(await page.evaluate(() => localStorage.getItem("access_token"))).toBeNull();
  });

  test("a wrong password is refused with a clear message", async ({ page }) => {
    await page.goto("/login");
    await page.getByPlaceholder("you@example.com").fill("nobody@e2e.test");
    await page.locator('input[type="password"]').fill("not-the-password-42");
    await page.getByRole("button", { name: /Sign In/ }).click();
    await expect(page.getByText("Invalid email or password")).toBeVisible();
    await pressDialogButton(page, /^OK$/);
    expect(new URL(page.url()).pathname).toBe("/login");
  });

  test("forgot password gives the same answer for any address", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("button", { name: "Forgot password?" }).click();
    await page.waitForURL("**/forgot-password");
    await page.getByPlaceholder("you@example.com").fill("nobody@e2e.test");
    await page.getByRole("button", { name: /Send reset link/ }).click();
    await expect(page.getByText(/If an account exists for that email/)).toBeVisible();
  });

  test("a bad reset link explains itself and offers a new one", async ({ page }) => {
    await page.goto("/reset-password?token=not-a-real-token-123");
    await page.locator('input[type="password"]').first().fill("lantern-orchard-voyage-19");
    await page.locator('input[type="password"]').nth(1).fill("lantern-orchard-voyage-19");
    await page.getByRole("button", { name: /Change password/ }).click();
    await expect(page.getByText(/invalid or has expired/)).toBeVisible();
    await expect(page.getByRole("button", { name: /Request a new link/ })).toBeVisible();
  });

  test("a bad verification link explains itself", async ({ page }) => {
    await page.goto("/verify-email?token=not-a-real-token-123");
    await expect(page.getByRole("heading", { name: /couldn't confirm your email/ })).toBeVisible();
  });
});
