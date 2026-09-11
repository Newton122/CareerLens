"""Tests for editing a posted job and an interview's joining details.

Both endpoints let one user change a row addressed by id, so the ownership
checks matter more than the happy paths: the interesting assertions here are
the ones proving another employer cannot edit someone else's posting and that
a hostile meeting link never reaches the database.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from ai_job_intelligence.conftest import TEST_PASSWORD

SOON = (datetime.utcnow() + timedelta(days=10)).isoformat()
LATER = (datetime.utcnow() + timedelta(days=20)).isoformat()


@pytest.fixture
def posted_job(client, employer):
    r = client.post(
        "/api/jobs",
        json={
            "title": "Platform Engineer",
            "description": "Own the deployment pipeline end to end.",
            "location": "Nairobi",
            "salary_min": 100,
            "salary_max": 200,
            "required_skills": ["Terraform", "AWS"],
            "benefits": ["Remote"],
        },
        headers=employer,
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture(scope="module")
def other_employer(client):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "rival@test.com",
            "password": TEST_PASSWORD,
            "name": "Rival Corp",
            "role": "employer",
        },
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# --- editing a posting ---------------------------------------------------


def test_edit_updates_only_the_fields_sent(client, employer, posted_job):
    r = client.patch(
        f"/api/jobs/{posted_job['id']}",
        json={"title": "Senior Platform Engineer"},
        headers=employer,
    )
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["title"] == "Senior Platform Engineer"
    # Everything the request did not mention survives untouched.
    assert body["location"] == "Nairobi"
    assert body["required_skills"] == ["Terraform", "AWS"]
    assert body["salary_min"] == 100


def test_edit_persists(client, employer, posted_job):
    client.patch(
        f"/api/jobs/{posted_job['id']}",
        json={"location": "Mombasa", "required_skills": ["Go", "Kubernetes"]},
        headers=employer,
    )
    again = client.get(f"/api/jobs/{posted_job['id']}", headers=employer)
    assert again.json()["location"] == "Mombasa"
    assert again.json()["required_skills"] == ["Go", "Kubernetes"]


def test_status_can_close_a_posting(client, employer, posted_job):
    r = client.patch(
        f"/api/jobs/{posted_job['id']}", json={"status": "closed"}, headers=employer
    )
    assert r.status_code == 200
    assert r.json()["status"] == "closed"


def test_unknown_status_is_rejected(client, employer, posted_job):
    r = client.patch(
        f"/api/jobs/{posted_job['id']}", json={"status": "archived"}, headers=employer
    )
    assert r.status_code == 422


def test_inverted_salary_range_is_rejected(client, employer, posted_job):
    r = client.patch(
        f"/api/jobs/{posted_job['id']}", json={"salary_min": 500}, headers=employer
    )
    # 500 against the stored max of 200 -- caught even though only one end
    # of the range was sent.
    assert r.status_code == 400
    assert "maximum" in r.json()["detail"].lower()


def test_blank_title_is_rejected(client, employer, posted_job):
    r = client.patch(
        f"/api/jobs/{posted_job['id']}", json={"title": "   "}, headers=employer
    )
    assert r.status_code == 422


def test_another_employer_cannot_edit_and_gets_404(
    client, other_employer, posted_job
):
    r = client.patch(
        f"/api/jobs/{posted_job['id']}",
        json={"title": "Hijacked"},
        headers=other_employer,
    )
    # 404, not 403: a 403 would confirm the posting exists.
    assert r.status_code == 404


def test_editing_requires_authentication(client, posted_job):
    r = client.patch(f"/api/jobs/{posted_job['id']}", json={"title": "Anon"})
    assert r.status_code in (401, 403)


# --- interview joining details -------------------------------------------


@pytest.fixture(scope="module")
def interviewee(client):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "attendee@test.com",
            "password": TEST_PASSWORD,
            "name": "Amara Yusuf",
            "role": "job_seeker",
        },
    )
    assert r.status_code == 200, r.text
    return {
        "headers": {"Authorization": f"Bearer {r.json()['access_token']}"},
        "user_id": r.json()["user_id"],
    }


def _schedule(client, employer, interviewee, **extra):
    payload = {
        "candidate_user_id": interviewee["user_id"],
        "scheduled_at": SOON,
        **extra,
    }
    return client.post("/api/interviews", json=payload, headers=employer)


def test_meeting_details_round_trip(client, employer, interviewee):
    r = _schedule(
        client,
        employer,
        interviewee,
        mode="video",
        meeting_url="https://meet.example.com/abc-defg",
        dial_in="+254200000000",
        duration_minutes=30,
        timezone="Africa/Nairobi",
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["mode"] == "video"
    assert body["meeting_url"] == "https://meet.example.com/abc-defg"
    assert body["dial_in"] == "+254200000000"
    assert body["duration_minutes"] == 30
    assert body["timezone"] == "Africa/Nairobi"


def test_contact_email_defaults_to_the_employer(client, employer, interviewee):
    r = _schedule(client, employer, interviewee)
    assert r.status_code == 201
    # Never scheduled with no way to reach anyone.
    assert r.json()["contact_email"] == "employer@example.com"


def test_javascript_meeting_url_is_rejected(client, employer, interviewee):
    r = _schedule(
        client, employer, interviewee, meeting_url="javascript:alert(document.cookie)"
    )
    # This value would become the href of a "Join" button.
    assert r.status_code == 422


def test_unknown_mode_is_rejected(client, employer, interviewee):
    r = _schedule(client, employer, interviewee, mode="telepathy")
    assert r.status_code == 422


def test_absurd_duration_is_rejected(client, employer, interviewee):
    r = _schedule(client, employer, interviewee, duration_minutes=100000)
    assert r.status_code == 422


def test_candidate_sees_the_joining_details(client, employer, interviewee):
    _schedule(
        client,
        employer,
        interviewee,
        meeting_url="https://meet.example.com/shared-link",
    )
    r = client.get("/api/interviews", headers=interviewee["headers"])
    assert r.status_code == 200
    links = [i["meeting_url"] for i in r.json()]
    assert "https://meet.example.com/shared-link" in links


def test_employer_can_fix_a_broken_link(client, employer, interviewee):
    created = _schedule(
        client, employer, interviewee, meeting_url="https://meet.example.com/typo"
    ).json()

    r = client.patch(
        f"/api/interviews/{created['id']}/details",
        json={"meeting_url": "https://meet.example.com/correct"},
        headers=employer,
    )
    assert r.status_code == 200, r.text
    assert r.json()["meeting_url"] == "https://meet.example.com/correct"
    # An unrelated field is not disturbed by the edit.
    assert r.json()["scheduled_at"][:10] == created["scheduled_at"][:10]


def test_rescheduling_a_confirmed_interview_needs_reconfirmation(
    client, employer, interviewee
):
    created = _schedule(client, employer, interviewee).json()

    confirmed = client.patch(
        f"/api/interviews/{created['id']}",
        json={"status": "confirmed"},
        headers=interviewee["headers"],
    )
    assert confirmed.json()["status"] == "confirmed"

    moved = client.patch(
        f"/api/interviews/{created['id']}/details",
        json={"scheduled_at": LATER},
        headers=employer,
    )
    assert moved.status_code == 200, moved.text
    # The candidate agreed to the old time, not this one.
    assert moved.json()["status"] == "scheduled"


def test_candidate_cannot_edit_the_details(client, employer, interviewee):
    created = _schedule(client, employer, interviewee).json()
    r = client.patch(
        f"/api/interviews/{created['id']}/details",
        json={"meeting_url": "https://attacker.example.com/room"},
        headers=interviewee["headers"],
    )
    assert r.status_code == 404


def test_cancelled_interview_cannot_be_edited(client, employer, interviewee):
    created = _schedule(client, employer, interviewee).json()
    client.patch(
        f"/api/interviews/{created['id']}",
        json={"status": "cancelled"},
        headers=employer,
    )
    r = client.patch(
        f"/api/interviews/{created['id']}/details",
        json={"location": "Anywhere"},
        headers=employer,
    )
    assert r.status_code == 400
