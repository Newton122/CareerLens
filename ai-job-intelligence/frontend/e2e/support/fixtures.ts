import { test as base, expect, type Page } from "@playwright/test";

/**
 * Shared set-up for the end-to-end tests.
 *
 * The `page` fixture below fails a test on any uncaught JavaScript error or
 * any 5xx response from the API -- the problems that don't show up as a
 * failed click. Expected 4xx responses (a wrong password, say) are fine.
 */

export const API = process.env.E2E_API_BASE ?? "http://127.0.0.1:8111";

// Must satisfy the server's password policy.
export const PASSWORD = "orbital-kettle-parade-77";

// Accounts the development server seeds on an empty database.
export const SEEDED_EMPLOYER = { email: "employer@example.com", password: "password123" };
export const SEEDED_ADMIN = { email: "admin@careerlens.ai", password: "admin123" };

/** A unique address, so reruns never collide with earlier data. */
export function uniqueEmail(prefix: string): string {
  return `${prefix}.${Date.now()}.${Math.random().toString(36).slice(2, 7)}@e2e.test`;
}

export const test = base.extend<{ page: Page }>({
  // The callback is conventionally named `use`; renamed so the React hooks
  // lint rule doesn't mistake it for React's use().
  page: async ({ page }, runTest) => {
    const problems: string[] = [];
    page.on("pageerror", (error) => problems.push(`page error: ${error.message}`));
    page.on("response", (response) => {
      if (response.url().startsWith(API) && response.status() >= 500) {
        problems.push(`HTTP ${response.status()} ${response.request().method()} ${response.url()}`);
      }
    });
    await runTest(page);
    expect(problems, "browser errors or server failures during the test").toEqual([]);
  },
});

export { expect };

// --- helpers --------------------------------------------------------------

/** Wait for the API call a click triggers, and return it. */
export function waitForApi(page: Page, method: string, path: string) {
  return page.waitForResponse(
    (r) => r.request().method() === method && r.url().startsWith(API) && new URL(r.url()).pathname.startsWith(path),
  );
}

/** Press a button in the app's MessageDialog overlay (default: OK/Yes). */
export async function pressDialogButton(page: Page, name: RegExp = /^(OK|Yes)$/) {
  const overlay = page.locator("div.fixed.inset-0.z-50");
  await overlay.getByRole("button", { name }).last().click();
  await expect(overlay).toHaveCount(0);
}

/** Sign in through the real login form. */
export async function signIn(page: Page, email: string, password: string, landsOn: string) {
  await page.goto("/login");
  await page.getByPlaceholder("you@example.com").fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole("button", { name: /Sign In/ }).click();
  await page.waitForURL(`**${landsOn}`);
  // The "Login successful!" notice would cover the page.
  await pressDialogButton(page, /^OK$/);
}

/** Create an account through the API (for set-up, not what's being tested). */
export async function registerViaApi(email: string, role: "job_seeker" | "employer", name: string) {
  const response = await fetch(`${API}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password: PASSWORD, name, role }),
  });
  expect(response.status, await response.clone().text()).toBe(200);
  const body = await response.json();
  return { token: body.access_token as string, userId: body.user_id as number };
}

/** An authenticated API call for set-up steps. */
export async function apiAs(token: string, path: string, init: RequestInit = {}) {
  return fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...init.headers },
  });
}

/** A CV as a text file, built in the test so no binary fixtures are needed. */
export function cvFile(name: string, skills = "Python, FastAPI, PostgreSQL, Docker") {
  const text = [
    name,
    "Skills",
    skills,
    "Experience",
    "Backend engineer at Acme for 5 years, building REST APIs with Python and FastAPI",
    "Containerised our services and automated the release pipeline",
    "Education",
    "BSc Computer Science, University of Nairobi",
    "Projects",
    "Job matching platform using sentence embeddings",
  ].join("\n");
  return { name: "cv.txt", mimeType: "text/plain", buffer: Buffer.from(text) };
}

/** The smallest valid PNG (1x1 pixel), for profile-picture uploads. */
export const TINY_PNG = {
  name: "avatar.png",
  mimeType: "image/png",
  buffer: Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
    "base64",
  ),
};
