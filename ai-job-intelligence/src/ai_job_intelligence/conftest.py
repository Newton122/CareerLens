"""Shared fixtures.

The app is booted once per test session against a throwaway SQLite database so
the configured PostgreSQL instance is never touched.
"""
from __future__ import annotations

import importlib
import os
import sys

import pytest
from fastapi.testclient import TestClient

# Must satisfy services/password_policy: long enough, not a common
# password, no long sequential or repeated runs.
TEST_PASSWORD = "orbital-kettle-parade-77"


@pytest.fixture(scope="session")
def app_module(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["GOOGLE_API_KEY"] = ""

    # Keep uploads out of the project's real upload directory, which holds CV
    # files that live rows still point at.
    uploads = tmp_path_factory.mktemp("uploads")
    os.environ["UPLOAD_DIR"] = str(uploads)
    os.environ["IMAGES_DIR"] = str(uploads / "images")

    # Re-import so the engine binds to the test DATABASE_URL.
    for mod in list(sys.modules):
        if mod.startswith("ai_job_intelligence"):
            del sys.modules[mod]
    return importlib.import_module("ai_job_intelligence.main")


@pytest.fixture(scope="session")
def client(app_module):
    with TestClient(app_module.app) as c:
        yield c


@pytest.fixture(scope="session")
def seeker(client):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "seeker@test.com",
            "password": TEST_PASSWORD,
            "name": "Test Seeker",
            "role": "job_seeker",
        },
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def employer(client):
    r = client.post(
        "/api/auth/login",
        json={"email": "employer@example.com", "password": "password123"},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def admin(client):
    r = client.post(
        "/api/auth/login",
        json={"email": "admin@careerlens.ai", "password": "admin123"},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(autouse=True)
def _reset_rate_limiters(app_module):
    """Clear rate-limit state between tests.

    The limiters are module-level and keyed by client IP, which is the same
    string for every request TestClient makes. Without this, the tests that
    register accounts would exhaust the registration limit and every later test
    would fail for the wrong reason. Tests that exercise limiting drive it
    explicitly instead.
    """
    limiters = (
        app_module._demo_limiter,
        app_module._login_ip_limiter,
        app_module._login_account_limiter,
        app_module._register_limiter,
    )
    for limiter in limiters:
        limiter.clear()
    yield
    for limiter in limiters:
        limiter.clear()
