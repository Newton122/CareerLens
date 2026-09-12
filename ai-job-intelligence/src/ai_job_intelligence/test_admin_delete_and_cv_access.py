"""Tests for deleting accounts and for who may open a CV file.

Deleting a user used to fail with a 500 whenever they had any data: the
profile, CVs, applications and so on still pointed at the ``users`` row, and
PostgreSQL refuses to break a foreign key. Resetting your own data failed the
same way once an interview referenced one of your CVs.

Separately, the employer candidate page offered "View CV", but the download
route only served a CV to its owner or an admin, so every employer got a 404.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from ai_job_intelligence.clock import utcnow
from ai_job_intelligence.conftest import TEST_PASSWORD

CV_TEXT = b"""Robin Achieng
Skills
Python, FastAPI, PostgreSQL, Docker
Experience
Backend Developer at Acme for 4 years building REST APIs
Education
BSc Computer Science
"""

SOON = (utcnow() + timedelta(days=7)).isoformat()


def _register(client, email: str, role: str, name: str) -> dict:
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": TEST_PASSWORD, "name": name, "role": role},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    return {
        "headers": {"Authorization": f"Bearer {body['access_token']}"},
        "user_id": body["user_id"],
    }


def _upload_cv(client, headers: dict, name: str = "cv.txt") -> int:
    r = client.post(
        "/api/upload-cv",
        files={"file": (name, CV_TEXT, "text/plain")},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    return int(r.json()["cv_id"])


def _stored_path(app_module, cv_id: int) -> Path:
    db = app_module.SessionLocal()
    try:
        return Path(db.get(app_module.CV, cv_id).file_path)
    finally:
        db.close()


# --- who may open a CV ---------------------------------------------------


def test_employer_can_open_a_job_seekers_cv(client, employer):
    seeker = _register(client, "cvaccess.seeker@test.com", "job_seeker", "Robin")
    cv_id = _upload_cv(client, seeker["headers"])

    r = client.get(f"/api/cvs/{cv_id}/download", headers=employer)

    assert r.status_code == 200, r.text
    assert r.content == CV_TEXT


def test_employer_cannot_open_a_cv_that_is_not_a_job_seekers(client, employer):
    # Candidate search only ever shows job seekers, so a CV uploaded by
    # another employer is not something an employer has a reason to open.
    other = _register(client, "cvaccess.employer@test.com", "employer", "Other Co")
    cv_id = _upload_cv(client, other["headers"])

    r = client.get(f"/api/cvs/{cv_id}/download", headers=employer)

    assert r.status_code == 404


def test_job_seeker_still_cannot_open_another_job_seekers_cv(client):
    owner = _register(client, "cvaccess.owner@test.com", "job_seeker", "Owner")
    snoop = _register(client, "cvaccess.snoop@test.com", "job_seeker", "Snoop")
    cv_id = _upload_cv(client, owner["headers"])

    r = client.get(f"/api/cvs/{cv_id}/download", headers=snoop["headers"])

    assert r.status_code == 404


# --- deleting a job seeker ----------------------------------------------


def test_admin_can_delete_a_job_seeker_with_data(client, app_module, admin, employer):
    seeker = _register(client, "delete.seeker@test.com", "job_seeker", "Leaving Seeker")
    headers = seeker["headers"]
    cv_id = _upload_cv(client, headers)
    cv_file = _stored_path(app_module, cv_id)

    # Give the account every kind of data that points at it.
    analysis = client.post(
        "/api/analyze",
        json={
            "cv_id": cv_id,
            "job_title": "Backend Engineer",
            "job_description": "We need Python, FastAPI and PostgreSQL, 3+ years.",
        },
        headers=headers,
    )
    assert analysis.status_code == 200, analysis.text
    job_id = client.get("/api/jobs", headers=employer).json()[0]["id"]
    assert client.post("/api/saved-jobs", json={"job_id": job_id}, headers=headers).status_code == 201
    assert client.post("/api/applications", json={"job_id": job_id}, headers=headers).status_code == 201
    interview = client.post(
        "/api/interviews",
        json={"candidate_user_id": seeker["user_id"], "scheduled_at": SOON},
        headers=employer,
    )
    assert interview.status_code == 201, interview.text
    assert client.post(
        "/api/messages",
        json={"recipient_user_id": seeker["user_id"], "content": "Hello"},
        headers=employer,
    ).status_code == 201
    image = client.post(
        "/api/upload-image",
        files={"file": ("me.png", b"\x89PNG fake", "image/png")},
        headers=headers,
    )
    assert image.status_code == 200, image.text

    r = client.delete(f"/api/admin/users/{seeker['user_id']}", headers=admin)

    assert r.status_code == 200, r.text
    assert client.get(f"/api/admin/users/{seeker['user_id']}", headers=admin).status_code == 404
    login = client.post(
        "/api/auth/login",
        json={"email": "delete.seeker@test.com", "password": TEST_PASSWORD},
    )
    assert login.status_code == 401
    # The other side no longer sees an interview or thread with a ghost.
    interview_ids = [i["id"] for i in client.get("/api/interviews", headers=employer).json()]
    assert interview.json()["id"] not in interview_ids
    partners = [c["user_id"] for c in client.get("/api/messages", headers=employer).json()]
    assert seeker["user_id"] not in partners
    applicants = client.get(f"/api/jobs/{job_id}/applications", headers=employer)
    if applicants.status_code == 200:
        assert "delete.seeker@test.com" not in [a["candidate_email"] for a in applicants.json()]
    # Their uploaded file went with them.
    assert not cv_file.exists()


# --- deleting an employer -------------------------------------------------


def test_admin_can_delete_an_employer_with_postings(client, admin):
    boss = _register(client, "delete.employer@test.com", "employer", "Closing Down Ltd")
    seeker = _register(client, "delete.applicant@test.com", "job_seeker", "Applicant")
    _upload_cv(client, seeker["headers"])

    job = client.post(
        "/api/jobs",
        json={
            "title": "Short-lived Role",
            "description": "Python developer needed for a short project.",
            "location": "Remote",
            "required_skills": ["Python"],
        },
        headers=boss["headers"],
    )
    assert job.status_code == 201, job.text
    job_id = job.json()["id"]
    assert client.post("/api/saved-jobs", json={"job_id": job_id}, headers=seeker["headers"]).status_code == 201
    assert client.post("/api/applications", json={"job_id": job_id}, headers=seeker["headers"]).status_code == 201
    assert client.post(
        "/api/interviews",
        json={"candidate_user_id": seeker["user_id"], "job_id": job_id, "scheduled_at": SOON},
        headers=boss["headers"],
    ).status_code == 201
    assert client.post(
        "/api/messages",
        json={"recipient_user_id": boss["user_id"], "content": "About the role", "job_id": job_id},
        headers=seeker["headers"],
    ).status_code == 201

    r = client.delete(f"/api/admin/users/{boss['user_id']}", headers=admin)

    assert r.status_code == 200, r.text
    assert client.get(f"/api/jobs/{job_id}", headers=seeker["headers"]).status_code == 404
    assert job_id not in [a["job_id"] for a in client.get("/api/applications", headers=seeker["headers"]).json()]
    assert job_id not in [s["job_id"] for s in client.get("/api/saved-jobs", headers=seeker["headers"]).json()]
    assert client.get("/api/interviews", headers=seeker["headers"]).json() == []


def test_admin_still_cannot_delete_themselves(client, admin):
    me = client.get("/api/admin/users", headers=admin).json()
    admin_id = next(u["id"] for u in me if u["email"] == "admin@careerlens.ai")

    r = client.delete(f"/api/admin/users/{admin_id}", headers=admin)

    assert r.status_code == 400


# --- resetting your own data ---------------------------------------------


def test_reset_data_works_when_an_interview_references_the_cv(client, app_module, employer):
    seeker = _register(client, "reset.seeker@test.com", "job_seeker", "Resetter")
    cv_id = _upload_cv(client, seeker["headers"])
    cv_file = _stored_path(app_module, cv_id)
    # Booked from the CV, so the interview row points at it.
    interview = client.post(
        "/api/interviews",
        json={"candidate_id": cv_id, "scheduled_at": SOON},
        headers=employer,
    )
    assert interview.status_code == 201, interview.text

    r = client.post("/api/reset-data", headers=seeker["headers"])

    assert r.status_code == 200, r.text
    assert client.get("/api/cvs", headers=seeker["headers"]).json() == []
    assert not cv_file.exists()
    # The interview itself is a booking between two people, not CV data, so it
    # survives the reset; it simply no longer points at the deleted CV.
    kept = [i for i in client.get("/api/interviews", headers=employer).json()
            if i["id"] == interview.json()["id"]]
    assert kept and kept[0]["cv_id"] is None
