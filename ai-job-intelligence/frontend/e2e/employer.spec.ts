import {
  test,
  expect,
  PASSWORD,
  SEEDED_EMPLOYER,
  apiAs,
  cvFile,
  pressDialogButton,
  registerViaApi,
  signIn,
  uniqueEmail,
  waitForApi,
} from "./support/fixtures";

// An employer posts a job, handles applicants, then books an interview and
// messages a candidate, who confirms and replies.
test.describe.serial("employer journey", () => {
  const stamp = Date.now();
  const candidateName = `Candidate ${stamp}`;
  const candidateEmail = uniqueEmail("candidate");
  const secondEmail = uniqueEmail("applicant");
  const jobTitle = `E2E Engineer ${stamp}`;
  let jobId: number;

  test("company profile, then post a job", async ({ page }) => {
    await signIn(page, SEEDED_EMPLOYER.email, SEEDED_EMPLOYER.password, "/employer/dashboard");

    await page.goto("/employer/company");
    await page.locator('input[name="name"]').fill("Example Corp");
    const companySaved = waitForApi(page, "POST", "/api/company");
    await page.getByRole("button", { name: /Save Changes/ }).click();
    expect((await companySaved).status()).toBe(200);
    await pressDialogButton(page, /^OK$/);

    await page.goto("/employer/jobs/new");
    await page.locator('input[name="title"]').fill(jobTitle);
    await page.locator('input[name="location"]').fill("Nairobi");
    await page.locator('input[name="salary_min"]').fill("50000");
    await page.locator('input[name="salary_max"]').fill("90000");
    await page.locator('textarea[name="description"]').fill("Build web services in Python and React, with SQL.");
    await page.locator('textarea[name="responsibilities"]').fill("Ship features, write tests");
    await page.locator('input[name="required_skills"]').fill("Python, React, SQL");
    await page.locator('input[name="experience_required"]').fill("3-5 years");
    await page.locator('input[name="education_required"]').fill("BSc Computer Science");
    await page.locator('input[name="benefits"]').fill("Remote, Health insurance");
    const created = waitForApi(page, "POST", "/api/jobs");
    await page.getByRole("button", { name: /Post Job/ }).click();
    const response = await created;
    expect(response.status()).toBe(201);
    jobId = (await response.json()).id;
  });

  test("edit the posting and publish the change", async ({ page }) => {
    await signIn(page, SEEDED_EMPLOYER.email, SEEDED_EMPLOYER.password, "/employer/dashboard");
    await page.goto(`/employer/jobs/${jobId}/edit`);
    const title = page.locator("label", { hasText: /^Title$/ }).locator("xpath=../following-sibling::input");
    await title.fill(`${jobTitle} II`);
    const published = waitForApi(page, "PATCH", `/api/jobs/${jobId}`);
    await page.getByRole("button", { name: /Publish changes/ }).click();
    expect((await published).status()).toBe(200);
  });

  test("accept one applicant and reject another", async ({ page }) => {
    // Two job seekers apply (set up through the API).
    for (const [email, name] of [[candidateEmail, candidateName], [secondEmail, "Second Applicant"]]) {
      const { token } = await registerViaApi(email, "job_seeker", name);
      const form = new FormData();
      const cv = cvFile(name);
      form.append("file", new Blob([cv.buffer], { type: cv.mimeType }), cv.name);
      const up = await fetch(`${process.env.E2E_API_BASE}/api/upload-cv`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      expect(up.status).toBe(200);
      const applied = await apiAs(token, "/api/applications", { method: "POST", body: JSON.stringify({ job_id: jobId }) });
      expect(applied.status).toBe(201);
    }

    await signIn(page, SEEDED_EMPLOYER.email, SEEDED_EMPLOYER.password, "/employer/dashboard");
    await page.goto(`/employer/jobs/${jobId}`);
    await expect(page.getByText(candidateName)).toBeVisible();

    const accepted = waitForApi(page, "POST", "/api/applications/");
    await page.getByRole("row", { name: new RegExp(candidateName) }).getByRole("button", { name: /^Accept$/ }).click();
    await pressDialogButton(page, /^Yes$/);
    expect((await accepted).status()).toBe(200);
    await pressDialogButton(page, /^OK$/);

    const rejected = waitForApi(page, "POST", "/api/applications/");
    await page.getByRole("row", { name: /Second Applicant/ }).getByRole("button", { name: /^Reject$/ }).click();
    await pressDialogButton(page, /^Yes$/);
    expect((await rejected).status()).toBe(200);
  });

  test("find the candidate, book an interview and send a message", async ({ page }) => {
    await signIn(page, SEEDED_EMPLOYER.email, SEEDED_EMPLOYER.password, "/employer/dashboard");
    await page.goto("/employer/candidates");
    const searched = waitForApi(page, "GET", "/api/candidates");
    await page.getByRole("button", { name: /^Search$/ }).click();
    expect((await searched).status()).toBe(200);
    await expect(page.getByText("profile score").first()).toBeVisible();
    await page.getByText(candidateName).click();
    await page.waitForURL("**/employer/candidates/*");

    // The employer can open the candidate's original CV file.
    const cvOpened = waitForApi(page, "GET", "/api/cvs/");
    await page.getByRole("button", { name: /View CV/ }).click();
    expect((await cvOpened).status()).toBe(200);

    await page.getByRole("button", { name: /Schedule Interview/ }).click();
    await page.locator("#link").fill("https://meet.example.com/e2e-room");
    const booked = waitForApi(page, "POST", "/api/interviews");
    await page.getByRole("button", { name: /^Schedule interview$/ }).click();
    expect((await booked).status()).toBe(201);
    await pressDialogButton(page, /^OK$/);

    await page.getByRole("button", { name: /Send Message/ }).first().click();
    await page.getByPlaceholder("Enter your message...").fill("Thanks for applying - see you at the interview!");
    const sent = waitForApi(page, "POST", "/api/messages");
    await page.locator('form button[type="submit"]').last().click();
    expect((await sent).status()).toBe(201);

    await page.goto("/employer/interviews");
    await expect(page.getByText("Join interview").first()).toBeVisible();
  });

  test("the candidate sees an unread badge, confirms and replies", async ({ page }) => {
    await signIn(page, candidateEmail, PASSWORD, "/dashboard");

    // The Messages link shows the unread count.
    await expect(page.getByLabel(/unread messages/).filter({ visible: true })).toHaveText("1");

    await page.goto("/interviews");
    const confirmed = waitForApi(page, "PATCH", "/api/interviews/");
    await page.getByRole("button", { name: /^Confirm$/ }).first().click();
    expect((await confirmed).status()).toBe(200);

    await page.goto("/messages");
    await page.getByText("see you at the interview", { exact: false }).first().click();
    await page.getByPlaceholder("Write a message…").fill("Thank you, I'll be there.");
    const replied = waitForApi(page, "POST", "/api/messages");
    await page.getByRole("button", { name: /Send/ }).last().click();
    expect((await replied).status()).toBe(201);
    // Reading the thread cleared the badge.
    await expect(page.getByLabel(/unread messages/)).toHaveCount(0);
  });
});
