"""End-to-end smoke tests covering the startup path and every major endpoint.

These run against a throwaway SQLite database so they never touch the
configured PostgreSQL instance. Several cases pin bugs that previously broke
the app outright -- see the comments on each.
"""
from __future__ import annotations

import pytest

CV_TEXT = b"""John Doe
Experience
Senior Backend Engineer at Acme, 6 years building APIs with Python and FastAPI
Built data pipelines on AWS with Docker and PostgreSQL
Education
BSc Computer Science, University of Nairobi
Skills
Python, FastAPI, PostgreSQL, AWS, Docker, Redis
Projects
Realtime analytics platform handling 2M events per day
"""


def test_startup_seeds_jobs(client):
    """Regression: the seeder used to raise TypeError and abort startup."""
    r = client.get("/")
    assert r.status_code == 200


def test_seeded_jobs_have_decoded_list_columns(client, seeker):
    """Regression: seeder wrote raw Python lists into JSON Text columns."""
    r = client.get("/api/jobs", headers=seeker)
    assert r.status_code == 200, r.text
    jobs = r.json()
    assert len(jobs) == 8
    assert isinstance(jobs[0]["required_skills"], list)
    assert jobs[0]["required_skills"]
    assert isinstance(jobs[0]["benefits"], list)
    assert jobs[0]["benefits"]


@pytest.mark.parametrize(
    "email,password,expected_role",
    [
        ("admin@careerlens.ai", "admin123", "admin"),
        ("employer@example.com", "password123", "employer"),
    ],
)
def test_seeded_accounts_login_with_correct_role(client, email, password, expected_role):
    """Regression: seeded users were created without a profile, so had no role."""
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    assert r.json()["role"] == expected_role


def test_career_insights(client, seeker):
    """Regression: referenced an undefined `sorted_gaps`, always raising NameError."""
    r = client.get("/api/career-insights", headers=seeker)
    assert r.status_code == 200, r.text
    body = r.json()
    for item in body["in_demand_skills"]:
        assert 0 <= item["demand"] <= 100


def test_admin_user_detail(client, admin):
    """Regression: read Application.job_title, which does not exist."""
    headers = admin

    users = client.get("/api/admin/users", headers=headers)
    assert users.status_code == 200, users.text

    detail = client.get(f"/api/admin/users/{users.json()[0]['id']}", headers=headers)
    assert detail.status_code == 200, detail.text
    for app in detail.json()["applications"]:
        assert "job_title" in app


def test_cv_upload_and_analysis_flow(client, seeker):
    up = client.post(
        "/api/upload-cv",
        files={"file": ("cv.txt", CV_TEXT, "text/plain")},
        headers=seeker,
    )
    assert up.status_code == 200, up.text
    cv_id = int(up.json()["cv_id"])

    assert client.get(f"/api/cvs/{cv_id}/analysis", headers=seeker).status_code == 200

    analysis = client.post(
        "/api/analyze",
        json={
            "cv_id": cv_id,
            "job_title": "Backend Engineer",
            "job_description": (
                "We need Python, FastAPI, PostgreSQL, AWS, Docker and Kubernetes "
                "experience. 5+ years required. Bachelor degree."
            ),
        },
        headers=seeker,
    )
    assert analysis.status_code == 200, analysis.text
    body = analysis.json()
    assert "Python" in body["matched_skills"]
    # Kubernetes is genuinely absent from the CV and must not be claimed.
    assert "Kubernetes" in body["missing_skills"]

    assert (
        client.get(f"/api/job-recommendations?cv_id={cv_id}", headers=seeker).status_code
        == 200
    )


@pytest.mark.parametrize(
    "path",
    [
        "/api/profile",
        "/api/user/stats",
        "/api/applications",
        "/api/saved-jobs",
        "/api/cvs",
    ],
)
def test_jobseeker_endpoints_ok(client, seeker, path):
    assert client.get(path, headers=seeker).status_code == 200


def test_save_and_apply_flow(client, seeker):
    job_id = client.get("/api/jobs", headers=seeker).json()[0]["id"]

    assert client.post("/api/saved-jobs", json={"job_id": job_id}, headers=seeker).status_code == 201
    assert len(client.get("/api/saved-jobs", headers=seeker).json()) == 1
    assert client.post("/api/applications", json={"job_id": job_id}, headers=seeker).status_code == 201
    # Applying twice to the same job must be rejected.
    assert client.post("/api/applications", json={"job_id": job_id}, headers=seeker).status_code == 400


def test_employer_flow(client, employer):
    headers = employer

    assert client.get("/api/company", headers=headers).status_code == 200
    assert client.get("/api/candidates", headers=headers).status_code == 200

    created = client.post(
        "/api/jobs",
        json={
            "title": "QA Engineer",
            "description": "Testing with Python and Selenium",
            "location": "Remote",
            "required_skills": ["Python", "Selenium"],
            "benefits": ["Remote"],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["required_skills"] == ["Python", "Selenium"]


def test_unauthenticated_requests_are_rejected(client):
    assert client.get("/api/profile").status_code in (401, 403)
