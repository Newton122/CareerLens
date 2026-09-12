"""Shared fixtures.

The suite runs against PostgreSQL, inside a throwaway schema created here and
dropped when the session ends, so the tables and rows the developer actually
uses are never touched. The server is TEST_DATABASE_URL if set, otherwise
DATABASE_URL (from the environment or .env). The role needs permission to
create schemas in that database.
"""
from __future__ import annotations

import importlib
import os
import re
import sys
import time
import uuid
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import psycopg
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

# The suite expects development behaviour (demo seeding, relaxed rate limits).
# Pin it before any test module imports config, so a local .env with
# APP_ENV=production cannot leak in: load_dotenv never overrides a variable
# that is already set.
os.environ["APP_ENV"] = "development"
load_dotenv()

_server_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL") or ""
if not re.match(r"^postgres(ql)?(\+\w+)?://", _server_url):
    pytest.exit(
        "The test suite needs PostgreSQL: set TEST_DATABASE_URL (or "
        "DATABASE_URL) to a postgresql:// URL.",
        returncode=2,
    )

# libpq wants a plain postgresql:// URL; SQLAlchemy wants the driver named.
_libpq_url = re.sub(r"^postgres(ql)?(\+\w+)?://", "postgresql://", _server_url)
# The creation time is part of the name so a later run can tell a schema
# abandoned by a killed run (which never reaches pytest_sessionfinish) from
# one a concurrent run is still using.
TEST_SCHEMA = f"test_{int(time.time())}_{uuid.uuid4().hex[:8]}"
_STALE_AFTER_SECONDS = 6 * 60 * 60


def _is_abandoned(name: str) -> bool:
    stamped = re.fullmatch(r"test_(\d{10})_[0-9a-f]{8}", name)
    if stamped:
        return time.time() - int(stamped.group(1)) > _STALE_AFTER_SECONDS
    # The earlier naming scheme, which had no timestamp.
    return re.fullmatch(r"test_[0-9a-f]{12}", name) is not None


with psycopg.connect(_libpq_url, autocommit=True) as _conn:
    _conn.execute("SET lock_timeout = '5s'")
    for (_name,) in _conn.execute(
        "SELECT nspname FROM pg_namespace WHERE nspname LIKE 'test\\_%'"
    ).fetchall():
        if _is_abandoned(_name):
            try:
                _conn.execute(f'DROP SCHEMA IF EXISTS "{_name}" CASCADE')
            except psycopg.Error:
                pass  # in use or already gone; try again next run
    _conn.execute(f'CREATE SCHEMA "{TEST_SCHEMA}"')

# Every connection the app opens resolves unqualified table names to the
# throwaway schema only.
_parts = urlsplit(_libpq_url.replace("postgresql://", "postgresql+psycopg://", 1))
_query = parse_qsl(_parts.query) + [("options", f"-csearch_path={TEST_SCHEMA}")]
os.environ["DATABASE_URL"] = urlunsplit(_parts._replace(query=urlencode(_query)))


def pytest_sessionfinish(session, exitstatus):
    """Drop the throwaway schema, even when tests failed."""
    database = sys.modules.get("ai_job_intelligence.services.database")
    if database is not None:
        database.engine.dispose()
    try:
        with psycopg.connect(_libpq_url, autocommit=True) as conn:
            conn.execute("SET lock_timeout = '10s'")
            conn.execute(f'DROP SCHEMA IF EXISTS "{TEST_SCHEMA}" CASCADE')
    except psycopg.Error as exc:
        print(f"\nCould not drop test schema {TEST_SCHEMA}: {exc}")


# Must satisfy services/password_policy: long enough, not a common
# password, no long sequential or repeated runs.
TEST_PASSWORD = "orbital-kettle-parade-77"


@pytest.fixture(scope="session")
def app_module(tmp_path_factory):
    os.environ["GOOGLE_API_KEY"] = ""

    # Keep uploads out of the project's real upload directory, which holds CV
    # files that live rows still point at.
    uploads = tmp_path_factory.mktemp("uploads")
    os.environ["UPLOAD_DIR"] = str(uploads)
    os.environ["IMAGES_DIR"] = str(uploads / "images")

    # Re-import so config picks up the test upload directories and the engine
    # binds to the throwaway schema.
    # conftest itself is kept: re-importing it would run the set-up above
    # again and create a second schema that nothing drops.
    for mod in list(sys.modules):
        if mod.startswith("ai_job_intelligence") and mod != __name__:
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
        app_module._forgot_ip_limiter,
        app_module._forgot_account_limiter,
        app_module._resend_verification_limiter,
    )
    for limiter in limiters:
        limiter.clear()
    yield
    for limiter in limiters:
        limiter.clear()
