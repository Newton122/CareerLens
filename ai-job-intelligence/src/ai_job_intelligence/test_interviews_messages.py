"""Tests for interviews and direct messaging.

Both endpoints previously returned a fabricated success response without
persisting anything, so these assert that data actually survives the request
and that each side can only take the actions that belong to it.
"""
from __future__ import annotations

from datetime import timedelta

import pytest

from ai_job_intelligence.clock import utcnow
from ai_job_intelligence.conftest import TEST_PASSWORD

CANDIDATE_CV = b"""Dana Okoro
Skills
Python, Django, PostgreSQL
Experience
Backend Developer, 4 years building web services
Education
BSc Software Engineering
"""

SOON = (utcnow() + timedelta(days=7)).isoformat()


@pytest.fixture(scope="module")
def candidate(client):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "dana@test.com",
            "password": TEST_PASSWORD,
            "name": "Dana Okoro",
            "role": "job_seeker",
        },
    )
    assert r.status_code == 200, r.text
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    up = client.post(
        "/api/upload-cv",
        files={"file": ("dana.txt", CANDIDATE_CV, "text/plain")},
        headers=headers,
    )
    assert up.status_code == 200, up.text
    return {
        "headers": headers,
        "user_id": r.json()["user_id"],
        "cv_id": int(up.json()["cv_id"]),
    }


# --- interviews ----------------------------------------------------------


def test_schedule_interview_persists(client, employer, candidate):
    r = client.post(
        "/api/interviews",
        json={
            "candidate_user_id": candidate["user_id"],
            "scheduled_at": SOON,
            "location": "Zoom",
            "notes": "Intro call",
        },
        headers=employer,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "scheduled"
    assert body["candidate_user_id"] == candidate["user_id"]
    assert body["location"] == "Zoom"

    # It must actually exist afterwards -- the old stub returned success and
    # stored nothing.
    listed = client.get("/api/interviews", headers=employer)
    assert listed.status_code == 200
    assert any(i["id"] == body["id"] for i in listed.json())


def test_candidate_sees_their_interview(client, candidate):
    listed = client.get("/api/interviews", headers=candidate["headers"])
    assert listed.status_code == 200, listed.text
    assert listed.json(), "the candidate should see interviews booked with them"
    assert all(
        i["candidate_user_id"] == candidate["user_id"] for i in listed.json()
    )


def test_legacy_cv_id_resolves_to_the_owner(client, employer, candidate):
    """The old UI sent a CV id as candidate_id; it must reach the CV's owner."""
    r = client.post(
        "/api/interviews",
        json={"candidate_id": candidate["cv_id"], "scheduled_at": SOON},
        headers=employer,
    )
    assert r.status_code == 201, r.text
    assert r.json()["candidate_user_id"] == candidate["user_id"]
    assert r.json()["cv_id"] == candidate["cv_id"]


def test_job_seekers_cannot_schedule_interviews(client, candidate):
    r = client.post(
        "/api/interviews",
        json={"candidate_user_id": 1, "scheduled_at": SOON},
        headers=candidate["headers"],
    )
    assert r.status_code == 403


def test_candidate_confirms_employer_cannot(client, employer, candidate):
    created = client.post(
        "/api/interviews",
        json={"candidate_user_id": candidate["user_id"], "scheduled_at": SOON},
        headers=employer,
    ).json()

    # The employer may not confirm on the candidate's behalf.
    wrong = client.patch(
        f"/api/interviews/{created['id']}",
        json={"status": "confirmed"},
        headers=employer,
    )
    assert wrong.status_code == 403

    ok = client.patch(
        f"/api/interviews/{created['id']}",
        json={"status": "confirmed"},
        headers=candidate["headers"],
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "confirmed"


def test_only_employer_cancels(client, employer, candidate):
    created = client.post(
        "/api/interviews",
        json={"candidate_user_id": candidate["user_id"], "scheduled_at": SOON},
        headers=employer,
    ).json()

    assert client.patch(
        f"/api/interviews/{created['id']}",
        json={"status": "cancelled"},
        headers=candidate["headers"],
    ).status_code == 403

    ok = client.patch(
        f"/api/interviews/{created['id']}",
        json={"status": "cancelled"},
        headers=employer,
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "cancelled"

    # A cancelled interview is closed.
    again = client.patch(
        f"/api/interviews/{created['id']}",
        json={"status": "confirmed"},
        headers=candidate["headers"],
    )
    assert again.status_code == 400


def test_unknown_status_rejected(client, employer, candidate):
    created = client.post(
        "/api/interviews",
        json={"candidate_user_id": candidate["user_id"], "scheduled_at": SOON},
        headers=employer,
    ).json()
    r = client.patch(
        f"/api/interviews/{created['id']}",
        json={"status": "rescheduled"},
        headers=employer,
    )
    assert r.status_code == 400


def test_outsiders_cannot_see_an_interview(client, employer, candidate):
    created = client.post(
        "/api/interviews",
        json={"candidate_user_id": candidate["user_id"], "scheduled_at": SOON},
        headers=employer,
    ).json()

    r = client.post(
        "/api/auth/register",
        json={
            "email": "nosy@test.com",
            "password": TEST_PASSWORD,
            "name": "Nosy",
            "role": "job_seeker",
        },
    )
    outsider = {"Authorization": f"Bearer {r.json()['access_token']}"}

    assert client.patch(
        f"/api/interviews/{created['id']}",
        json={"status": "confirmed"},
        headers=outsider,
    ).status_code == 404
    assert client.get("/api/interviews", headers=outsider).json() == []


# --- messages ------------------------------------------------------------


def test_message_round_trip(client, employer, candidate):
    sent = client.post(
        "/api/messages",
        json={
            "recipient_user_id": candidate["user_id"],
            "content": "Are you free to talk on Thursday?",
        },
        headers=employer,
    )
    assert sent.status_code == 201, sent.text
    assert sent.json()["body"] == "Are you free to talk on Thursday?"

    convos = client.get("/api/messages", headers=candidate["headers"])
    assert convos.status_code == 200
    assert convos.json(), "the message should appear in the candidate's inbox"
    assert convos.json()[0]["unread_count"] >= 1


def test_reading_a_thread_marks_it_read(client, employer, candidate):
    client.post(
        "/api/messages",
        json={"recipient_user_id": candidate["user_id"], "content": "Ping"},
        headers=employer,
    )
    before = client.get("/api/messages/unread/count", headers=candidate["headers"])
    assert before.json()["unread"] >= 1

    conversations = client.get("/api/messages", headers=candidate["headers"]).json()
    assert conversations
    other_id = conversations[0]["user_id"]

    thread = client.get(f"/api/messages/{other_id}", headers=candidate["headers"])
    assert thread.status_code == 200, thread.text

    after = client.get("/api/messages/unread/count", headers=candidate["headers"])
    assert after.json()["unread"] == 0


def test_candidate_can_reply(client, employer, candidate):
    employer_id = client.get("/api/messages", headers=candidate["headers"]).json()[0][
        "user_id"
    ]
    reply = client.post(
        "/api/messages",
        json={"recipient_user_id": employer_id, "content": "Thursday works."},
        headers=candidate["headers"],
    )
    assert reply.status_code == 201, reply.text

    thread = client.get(f"/api/messages/{employer_id}", headers=candidate["headers"])
    bodies = [m["body"] for m in thread.json()]
    assert "Thursday works." in bodies
    # Oldest first, so the conversation reads top to bottom.
    times = [m["created_at"] for m in thread.json()]
    assert times == sorted(times)


def test_cannot_message_yourself(client):
    r = client.post(
        "/api/auth/login",
        json={"email": "employer@example.com", "password": "password123"},
    )
    own_id = r.json()["user_id"]
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    sent = client.post(
        "/api/messages",
        json={"recipient_user_id": own_id, "content": "hi"},
        headers=headers,
    )
    assert sent.status_code == 400


def test_empty_message_rejected(client, employer, candidate):
    r = client.post(
        "/api/messages",
        json={"recipient_user_id": candidate["user_id"], "content": "   "},
        headers=employer,
    )
    assert r.status_code in (400, 422)


def test_thread_is_private(client, employer, candidate):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "eavesdrop@test.com",
            "password": TEST_PASSWORD,
            "name": "Eve",
            "role": "job_seeker",
        },
    )
    outsider = {"Authorization": f"Bearer {r.json()['access_token']}"}
    thread = client.get(f"/api/messages/{candidate['user_id']}", headers=outsider)
    assert thread.status_code == 200
    assert thread.json() == [], "an outsider must not see someone else's thread"


def test_unknown_recipient_is_404(client, employer):
    r = client.post(
        "/api/messages",
        json={"recipient_user_id": 999999, "content": "hello"},
        headers=employer,
    )
    assert r.status_code == 404
