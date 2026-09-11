import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests for CareerLens.
 *
 * These exist because the Python suite cannot see the browser. The demo page
 * once rendered its submit button `disabled` after two runs, so clicking it
 * did nothing at all — no request, no error. TypeScript compiled it, `next
 * build` accepted it, and every backend test passed. Only a real browser
 * catches that class of bug, and the same is true of hydration mismatches.
 *
 * Both servers are started automatically. The API runs against a throwaway
 * SQLite database so a test run never touches development data.
 */
const API_PORT = 8111;

// Tests talk to the API directly for setup (creating accounts), so they need
// the same base URL the servers are started on.
process.env.E2E_API_BASE = `http://127.0.0.1:${API_PORT}`;

const WEB_PORT = 3111;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false, // the API rate-limits per IP; parallel runs collide
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",

  timeout: 60_000,
  expect: { timeout: 10_000 },

  use: {
    baseURL: `http://127.0.0.1:${WEB_PORT}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },

  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],

  webServer: [
    {
      command: `.venv/bin/python -m uvicorn ai_job_intelligence.main:app --port ${API_PORT}`,
      cwd: "..",
      env: {
        // A fresh SQLite file per run keeps the developer's Postgres and
        // uploads directory completely untouched.
        DATABASE_URL: "sqlite:///./e2e-test.db",
        // The test frontend runs on its own port, which the browser's CORS
        // check would otherwise reject.
        CORS_ORIGINS: `http://127.0.0.1:${WEB_PORT},http://localhost:${WEB_PORT}`,
        GOOGLE_API_KEY: "",
        APP_ENV: "development",
        UPLOAD_DIR: "./.e2e-uploads",
      },
      url: `http://127.0.0.1:${API_PORT}/`,
      reuseExistingServer: false,
      timeout: 180_000, // first boot loads the sentence-transformers model
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      // A production build, not `next dev`, for two reasons: Next refuses to
      // run a second dev server from the same directory (so this would clash
      // with the one you already have open), and NEXT_PUBLIC_* values are
      // inlined at build time, so the API base must be set for the build too.
      command: `npm run build && npm run start -- --port ${WEB_PORT}`,
      url: `http://127.0.0.1:${WEB_PORT}`,
      reuseExistingServer: false,
      timeout: 180_000,
      env: { NEXT_PUBLIC_API_BASE: `http://127.0.0.1:${API_PORT}` },
      stdout: "pipe",
      stderr: "pipe",
    },
  ],
});
