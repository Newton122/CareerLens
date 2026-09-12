"""Tests for password reset, email verification and session versioning.

Emails are captured instead of sent: ``send_email`` is replaced for the
duration of each test, so the links can be read straight out of the message.
"""
from __future__ import annotations

import logging
import re
from datetime import timedelta

import pytest

from ai_job_intelligence.conftest import TEST_PASSWORD

NEW_PASSWORD = "lantern-orchard-voyage-19"


@pytest.fixture
def outbox(app_module, monkeypatch):
    sent: list[dict] = []

    def capture(to, subject, body):
        sent.append({"to": to, "subject": subject, "body": body})
        return True

    monkeypatch.setattr(app_module.email_service, "send_email", capture)
    return sent


def _token_from(message: dict, path: str) -> str:
    match = re.search(rf"/{path}\?token=([\w-]+)", message["body"])
    assert match, message["body"]
    return match.group(1)


def _register(client, email: str) -> dict:
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": TEST_PASSWORD, "name": "R", "role": "job_seeker"},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _login(client, email: str, password: str):
    return client.post("/api/auth/login", json={"email": email, "password": password})


# --- email verification ----------------------------------------------------


def test_registering_sends_a_verification_link(client, app_module, outbox):
    headers = _register(client, "verify.me@test.com")

    assert len(outbox) == 1
    assert outbox[0]["to"] == "verify.me@test.com"
    assert f"{app_module.FRONTEND_URL}/verify-email?token=" in outbox[0]["body"]
    assert client.get("/api/profile", headers=headers).json()["email_verified"] is False

    token = _token_from(outbox[0], "verify-email")
    assert client.post("/api/auth/verify-email", json={"token": token}).status_code == 200
    assert client.get("/api/profile", headers=headers).json()["email_verified"] is True
    # A link works once.
    assert client.post("/api/auth/verify-email", json={"token": token}).status_code == 400


def test_resending_verification_replaces_the_old_link(client, outbox):
    headers = _register(client, "resend.me@test.com")
    first = _token_from(outbox[0], "verify-email")

    r = client.post("/api/auth/resend-verification", headers=headers)

    assert r.status_code == 200, r.text
    second = _token_from(outbox[-1], "verify-email")
    assert second != first
    assert client.post("/api/auth/verify-email", json={"token": first}).status_code == 400
    assert client.post("/api/auth/verify-email", json={"token": second}).status_code == 200
    again = client.post("/api/auth/resend-verification", headers=headers)
    assert "already confirmed" in again.json()["message"]


def test_an_unverified_account_can_still_sign_in(client, outbox):
    _register(client, "unverified@test.com")
    assert _login(client, "unverified@test.com", TEST_PASSWORD).status_code == 200


# --- password reset ---------------------------------------------------------


def test_forgot_password_answers_the_same_for_unknown_addresses(client, outbox):
    _register(client, "known@test.com")
    outbox.clear()

    known = client.post("/api/auth/forgot-password", json={"email": "known@test.com"})
    unknown = client.post("/api/auth/forgot-password", json={"email": "nobody@test.com"})

    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    # Only the real account gets an email.
    assert [m["to"] for m in outbox] == ["known@test.com"]


def test_full_reset_flow(client, outbox):
    old_headers = _register(client, "reset.flow@test.com")
    outbox.clear()
    client.post("/api/auth/forgot-password", json={"email": "Reset.Flow@test.com "})
    token = _token_from(outbox[0], "reset-password")

    r = client.post("/api/auth/reset-password", json={"token": token, "password": NEW_PASSWORD})

    assert r.status_code == 200, r.text
    assert _login(client, "reset.flow@test.com", TEST_PASSWORD).status_code == 401
    new_login = _login(client, "reset.flow@test.com", NEW_PASSWORD)
    assert new_login.status_code == 200
    # Signed out everywhere: the token from before the reset no longer works...
    stale = client.get("/api/profile", headers=old_headers)
    assert stale.status_code == 401
    assert "session has ended" in stale.json()["detail"]
    # ...but the new one does, and resetting proved the address.
    fresh = {"Authorization": f"Bearer {new_login.json()['access_token']}"}
    assert client.get("/api/profile", headers=fresh).json()["email_verified"] is True
    # The link is single-use.
    again = client.post("/api/auth/reset-password", json={"token": token, "password": NEW_PASSWORD})
    assert again.status_code == 400


def test_a_rejected_password_does_not_use_up_the_link(client, outbox):
    _register(client, "weak.reset@test.com")
    outbox.clear()
    client.post("/api/auth/forgot-password", json={"email": "weak.reset@test.com"})
    token = _token_from(outbox[0], "reset-password")

    weak = client.post("/api/auth/reset-password", json={"token": token, "password": "password1"})
    assert weak.status_code == 400

    ok = client.post("/api/auth/reset-password", json={"token": token, "password": NEW_PASSWORD})
    assert ok.status_code == 200, ok.text


def test_an_expired_reset_link_is_refused(client, app_module, outbox):
    _register(client, "expired.reset@test.com")
    outbox.clear()
    client.post("/api/auth/forgot-password", json={"email": "expired.reset@test.com"})
    token = _token_from(outbox[0], "reset-password")

    db = app_module.SessionLocal()
    try:
        row = db.query(app_module.AuthToken).order_by(app_module.AuthToken.id.desc()).first()
        row.expires_at = app_module.utcnow() - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()

    r = client.post("/api/auth/reset-password", json={"token": token, "password": NEW_PASSWORD})
    assert r.status_code == 400
    assert "expired" in r.json()["detail"]


def test_a_verification_link_cannot_reset_a_password(client, outbox):
    _register(client, "purpose.check@test.com")
    verify_token = _token_from(outbox[0], "verify-email")

    r = client.post("/api/auth/reset-password", json={"token": verify_token, "password": NEW_PASSWORD})

    assert r.status_code == 400


def test_only_a_hash_of_the_token_is_stored(client, app_module, outbox):
    _register(client, "hash.only@test.com")
    raw = _token_from(outbox[0], "verify-email")

    db = app_module.SessionLocal()
    try:
        stored = [t.token_hash for t in db.query(app_module.AuthToken).all()]
    finally:
        db.close()
    assert raw not in stored
    assert all(len(h) == 64 for h in stored)


def test_forgot_password_is_limited_per_address(client, outbox):
    _register(client, "flood.me@test.com")
    outbox.clear()

    replies = [
        client.post("/api/auth/forgot-password", json={"email": "flood.me@test.com"})
        for _ in range(5)
    ]

    assert all(r.status_code == 200 for r in replies)
    assert len(outbox) == 3  # the limit; the rest get the same reply, no email


def test_a_deleted_accounts_token_stops_working(client, admin, outbox):
    headers = _register(client, "soon.gone@test.com")
    me = client.get("/api/admin/users", headers=admin).json()
    user_id = next(u["id"] for u in me if u["email"] == "soon.gone@test.com")

    assert client.delete(f"/api/admin/users/{user_id}", headers=admin).status_code == 200

    assert client.get("/api/profile", headers=headers).status_code == 401


# --- the email sender itself ------------------------------------------------


def test_without_smtp_production_never_logs_the_link(app_module, monkeypatch, caplog):
    from ai_job_intelligence.services import email_service

    # Patch the config module email_service actually reads (another test may
    # have re-imported config since email_service was imported).
    monkeypatch.setattr(email_service.config, "SMTP_HOST", "")
    monkeypatch.setattr(email_service.config, "IS_PRODUCTION", True)
    with caplog.at_level(logging.WARNING):
        sent = email_service.send_password_reset("x@test.com", "https://app/reset?token=SECRET123", 60)

    assert sent is False
    assert "SECRET123" not in caplog.text
    assert "not configured" in caplog.text


def test_without_smtp_development_logs_the_email_for_local_testing(app_module, monkeypatch, caplog):
    from ai_job_intelligence.services import email_service

    # Patch the config module email_service actually reads (another test may
    # have re-imported config since email_service was imported).
    monkeypatch.setattr(email_service.config, "SMTP_HOST", "")
    monkeypatch.setattr(email_service.config, "IS_PRODUCTION", False)
    with caplog.at_level(logging.WARNING):
        email_service.send_password_reset("x@test.com", "https://app/reset?token=LOCAL456", 60)

    assert "LOCAL456" in caplog.text
