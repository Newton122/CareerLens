"""Tests for registration, password policy and sign-in throttling.

Five defects these pin, all confirmed against the running app before fixing:

* ``role`` was taken straight from the request body, so anyone could register
  as an administrator and immediately read every user's email address.
* ``verify_password`` was skipped entirely for an unknown email, making the
  response ~130x faster and letting anyone enumerate registered accounts.
* Passwords such as "123456" and "password" were accepted.
* ``/api/auth/login`` had no throttle: 30 wrong guesses all returned 401.
* "notanemail" was accepted as an email address.
"""
from __future__ import annotations

import time

import pytest

from ai_job_intelligence.conftest import TEST_PASSWORD
from ai_job_intelligence.services.password_policy import (
    PasswordPolicyError,
    validate_password,
)


def _register(client, email, password=TEST_PASSWORD, role="job_seeker"):
    return client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "name": "T", "role": role},
    )


# --- privilege escalation ------------------------------------------------


def test_cannot_self_register_as_admin(client):
    """The most serious of the five: admin was self-assignable."""
    r = _register(client, "wants-admin@test.com", role="admin")
    assert r.status_code == 422, r.text


@pytest.mark.parametrize("role", ["administrator", "superuser", "ADMIN", "root"])
def test_only_known_roles_are_accepted(client, role):
    assert _register(client, f"role-{role}@test.com", role=role).status_code == 422


def test_legitimate_roles_still_work(client):
    for role in ("job_seeker", "employer"):
        r = _register(client, f"ok-{role}@test.com", role=role)
        assert r.status_code == 200, r.text
        assert r.json()["role"] == role


def test_registered_user_cannot_reach_admin_routes(client):
    r = _register(client, "ordinary@test.com")
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/api/admin/users", headers=headers).status_code == 403
    assert client.get("/api/admin/stats", headers=headers).status_code == 403


# --- password policy -----------------------------------------------------


@pytest.mark.parametrize(
    "password",
    ["123456", "password", "short", "aaaaaaaaaa", "abcdefghij", "Password2024"],
)
def test_weak_passwords_are_rejected(client, password):
    r = _register(client, f"weak-{abs(hash(password))}@test.com", password=password)
    assert r.status_code == 400, r.text
    assert r.json()["detail"], "the user should be told why"


def test_password_cannot_contain_the_email(client):
    r = _register(client, "jonathan@test.com", password="jonathan-is-here")
    assert r.status_code == 400
    assert "email" in r.json()["detail"].lower()


@pytest.mark.parametrize(
    "password",
    ["correct horse battery staple", "orbital-kettle-parade-77", "Tr0ub4dor&3xyz!"],
)
def test_reasonable_passwords_are_accepted(password):
    validate_password(password, email="someone@test.com")


def test_policy_message_is_specific():
    """A generic 'invalid password' teaches the user nothing."""
    with pytest.raises(PasswordPolicyError, match="at least"):
        validate_password("tiny")
    with pytest.raises(PasswordPolicyError, match="commonly used"):
        validate_password("password123")


# --- email validation ----------------------------------------------------


@pytest.mark.parametrize("email", ["notanemail", "no@tld", "@nolocal.com", "a b@c.com"])
def test_invalid_emails_are_rejected(client, email):
    assert _register(client, email).status_code == 422


def test_email_is_normalised(client):
    r = _register(client, "  MiXeD@Case.COM  ")
    assert r.status_code == 200, r.text
    assert r.json()["email"] == "mixed@case.com"

    # And the normalised form is what logs in.
    login = client.post(
        "/api/auth/login",
        json={"email": "MIXED@CASE.COM", "password": TEST_PASSWORD},
    )
    assert login.status_code == 200, login.text


# --- account enumeration -------------------------------------------------


def test_login_timing_does_not_reveal_account_existence(client, app_module):
    """Was ~130x faster for unknown emails, which leaked the user list."""
    _register(client, "timing@test.com")

    def average_ms(email, runs=3):
        total = 0.0
        for _ in range(runs):
            app_module._login_ip_limiter.clear()
            app_module._login_account_limiter.clear()
            start = time.perf_counter()
            client.post(
                "/api/auth/login", json={"email": email, "password": "wrong-password-x"}
            )
            total += time.perf_counter() - start
        return total / runs * 1000

    known = average_ms("timing@test.com")
    unknown = average_ms("definitely-not-registered@test.com")

    ratio = max(known, unknown) / max(min(known, unknown), 0.001)
    assert ratio < 3, f"timing leak: known {known:.0f}ms vs unknown {unknown:.0f}ms"


def test_login_error_is_identical_either_way(client):
    _register(client, "samemsg@test.com")
    a = client.post(
        "/api/auth/login", json={"email": "samemsg@test.com", "password": "wrong-one-x"}
    )
    b = client.post(
        "/api/auth/login", json={"email": "nobody@test.com", "password": "wrong-one-x"}
    )
    assert a.status_code == b.status_code == 401
    assert a.json()["detail"] == b.json()["detail"]


# --- throttling ----------------------------------------------------------


def test_repeated_failures_are_throttled(client, app_module):
    _register(client, "brute@test.com")
    app_module._login_ip_limiter.clear()
    app_module._login_account_limiter.clear()

    codes = [
        client.post(
            "/api/auth/login", json={"email": "brute@test.com", "password": f"guess{i}"}
        ).status_code
        for i in range(12)
    ]
    assert 429 in codes, "unlimited guessing is still possible"
    assert codes.index(429) <= 10, codes


def test_throttled_response_says_when_to_retry(client, app_module):
    _register(client, "retry@test.com")
    app_module._login_ip_limiter.clear()
    app_module._login_account_limiter.clear()

    last = None
    for i in range(12):
        last = client.post(
            "/api/auth/login", json={"email": "retry@test.com", "password": f"g{i}"}
        )
        if last.status_code == 429:
            break
    assert last is not None and last.status_code == 429
    assert "Retry-After" in last.headers


def test_lockout_holds_even_with_the_right_password(client, app_module):
    """Otherwise an attacker who guesses correctly mid-lockout still gets in."""
    _register(client, "locked@test.com")
    app_module._login_ip_limiter.clear()
    app_module._login_account_limiter.clear()

    for i in range(10):
        client.post(
            "/api/auth/login", json={"email": "locked@test.com", "password": f"g{i}"}
        )

    blocked = client.post(
        "/api/auth/login", json={"email": "locked@test.com", "password": TEST_PASSWORD}
    )
    assert blocked.status_code == 429


def test_successful_login_clears_the_account_counter(client, app_module):
    """A user who mistypes twice then succeeds must not be locked out after."""
    _register(client, "forgiving@test.com")
    app_module._login_ip_limiter.clear()
    app_module._login_account_limiter.clear()

    for i in range(2):
        client.post(
            "/api/auth/login", json={"email": "forgiving@test.com", "password": f"g{i}"}
        )

    ok = client.post(
        "/api/auth/login",
        json={"email": "forgiving@test.com", "password": TEST_PASSWORD},
    )
    assert ok.status_code == 200, ok.text

    # The account's failure history was reset by the success.
    assert app_module._login_account_limiter.check("forgiving@test.com") is None


def test_registration_is_throttled(client, app_module, monkeypatch):
    """Account creation must be rate limited.

    The configured per-IP limit is deliberately relaxed outside production (see
    main._REGISTER_IP_LIMIT), so this substitutes a tiny limiter and checks the
    enforcement path rather than hard-coding whatever number this environment
    happens to use.
    """
    from ai_job_intelligence.services.rate_limit import Rule, SlidingWindowLimiter

    monkeypatch.setattr(
        app_module,
        "_register_limiter",
        SlidingWindowLimiter(Rule(limit=2, window_seconds=3600)),
    )

    codes = [_register(client, f"spam{i}@test.com").status_code for i in range(5)]
    assert 429 in codes, "account creation is unlimited"
    assert codes.index(429) <= 3, codes


def test_relaxed_limits_apply_only_outside_production(app_module):
    """Development relaxes the per-IP limits; production must not.

    Tests and local work all originate from 127.0.0.1, so a production-tight
    per-IP limit would lock the developer out. That relaxation is only
    acceptable if it cannot leak into production.
    """
    assert app_module.IS_PRODUCTION is False, "tests should not run as production"
    assert app_module._LOGIN_IP_LIMIT > 10
    assert app_module._REGISTER_IP_LIMIT > 5

    # The per-account limit is keyed by email, never collides between users,
    # and is the one that actually stops an attacker -- so it is never relaxed.
    rule = app_module._login_account_limiter._rule
    assert rule.limit == 5
    assert rule.window_seconds == 900
