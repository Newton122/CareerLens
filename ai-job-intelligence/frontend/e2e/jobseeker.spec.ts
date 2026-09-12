import {
  test,
  expect,
  API,
  PASSWORD,
  TINY_PNG,
  cvFile,
  pressDialogButton,
  registerViaApi,
  signIn,
  uniqueEmail,
  waitForApi,
} from "./support/fixtures";

// One job seeker walks through the whole product, in order.
test.describe.serial("job seeker journey", () => {
  const email = uniqueEmail("seeker");
  let jobId: number;

  test.beforeAll(async () => {
    await registerViaApi(email, "job_seeker", "Journey Seeker");
  });

  test("upload a CV, see its skills and where they were found", async ({ page }) => {
    await signIn(page, email, PASSWORD, "/dashboard");
    await page.goto("/cv");
    const uploaded = waitForApi(page, "POST", "/api/upload-cv");
    await page.locator("#cv-upload").setInputFiles(cvFile("Journey Seeker"));
    expect((await uploaded).status()).toBe(200);
    await page.waitForURL("**/analyze?cv_id=*");

    // Skills are labelled by evidence, not by a made-up proficiency.
    await expect(page.getByText("Skills & Evidence")).toBeVisible();
    await expect(page.getByText("Demonstrated").first()).toBeVisible();
  });

  test("find matching jobs and analyse one", async ({ page }) => {
    await signIn(page, email, PASSWORD, "/dashboard");
    await page.goto("/cv");
    await page.getByRole("button", { name: "Analysis" }).first().click();
    await page.waitForURL("**/analyze?cv_id=*");

    const recommended = waitForApi(page, "GET", "/api/job-recommendations");
    await page.getByRole("button", { name: /Find Matching Jobs/ }).click();
    expect((await recommended).status()).toBe(200);

    const analyzed = waitForApi(page, "POST", "/api/analyze");
    await page.getByRole("button", { name: /Analyze This Job/ }).first().click();
    expect((await analyzed).status()).toBe(200);
    await page.waitForURL("**/results/*");
    await expect(page.getByText("What to do next")).toBeVisible();
  });

  test("save, reload, unsave and save a job again", async ({ page }) => {
    await signIn(page, email, PASSWORD, "/dashboard");
    const token = await page.evaluate(() => localStorage.getItem("access_token"));
    const jobs = await (await fetch(`${API}/api/jobs`, { headers: { Authorization: `Bearer ${token}` } })).json();
    jobId = jobs[0].id;

    await page.goto(`/jobs/${jobId}`);
    const saved = waitForApi(page, "POST", "/api/saved-jobs");
    await page.getByRole("button", { name: /^Save$/ }).click();
    expect((await saved).status()).toBe(201);
    await pressDialogButton(page, /^OK$/);

    // The saved state comes from the server, so it survives a reload.
    await page.reload();
    const toggle = page.getByRole("button", { name: /\[OK\] Saved/ });
    await expect(toggle).toBeVisible();

    const removed = waitForApi(page, "DELETE", `/api/saved-jobs/${jobId}`);
    await toggle.click();
    expect((await removed).status()).toBe(200);
    await pressDialogButton(page, /^OK$/);

    await page.getByRole("button", { name: /^Save$/ }).click();
    await pressDialogButton(page, /^OK$/);
    await page.goto("/saved-jobs");
    await expect(page.getByText(jobs[0].title).first()).toBeVisible();
  });

  test("apply for the job and see it in applications", async ({ page }) => {
    await signIn(page, email, PASSWORD, "/dashboard");
    await page.goto(`/jobs/${jobId}`);
    const applied = waitForApi(page, "POST", "/api/applications");
    await page.getByRole("button", { name: /Apply Now/ }).click();
    expect((await applied).status()).toBe(201);
    await page.waitForURL("**/applications");
    await expect(page.getByRole("heading", { name: "My Applications" })).toBeVisible();
  });

  test("career insights and the CareerLens chat", async ({ page }) => {
    await signIn(page, email, PASSWORD, "/dashboard");
    await page.goto("/career-insights");
    await expect(page.getByText("How these figures were calculated")).toBeVisible();

    await page.goto("/career-lens");
    await page.getByPlaceholder(/Ask about your skills/).fill("What skills should I learn next?");
    const answered = waitForApi(page, "POST", "/api/career-lens/chat");
    await page.keyboard.press("Enter");
    expect((await answered).status()).toBe(200);
  });

  test("edit the profile and upload a photo", async ({ page }) => {
    await signIn(page, email, PASSWORD, "/dashboard");
    await page.goto("/profile");
    await page.locator('input[name="name"]').fill("Journey Seeker Updated");
    const saved = waitForApi(page, "PUT", "/api/profile");
    await page.getByRole("button", { name: /Save Profile/ }).click();
    expect((await saved).status()).toBe(200);
    await pressDialogButton(page, /^OK$/);

    const uploaded = waitForApi(page, "POST", "/api/upload-image");
    await page.locator('input[type="file"]').setInputFiles(TINY_PNG);
    expect((await uploaded).status()).toBe(200);
    const photo = page.locator(`img[src^="${API}/api/images/"]`);
    await expect(photo).toBeVisible();
    expect(await photo.evaluate((img: HTMLImageElement) => img.naturalWidth)).toBeGreaterThan(0);
  });
});
