"""Tests for the persisted CV profile cache.

The point of the cache is that a CV is parsed exactly once, at upload, and
every later request reads the stored copy. These tests assert that directly by
counting how many times the parser actually runs.
"""
from __future__ import annotations

import json
import sys

import pytest

CV_TEXT = b"""Grace Hopper
Skills
Python, Kubernetes, PostgreSQL, Docker
Experience
Staff Engineer at Example Corp, 8 years building distributed systems
Education
PhD Mathematics, Yale
"""


@pytest.fixture(scope="module")
def uploaded_cv(client, seeker):
    r = client.post(
        "/api/upload-cv",
        files={"file": ("grace.txt", CV_TEXT, "text/plain")},
        headers=seeker,
    )
    assert r.status_code == 200, r.text
    return int(r.json()["cv_id"])


@pytest.fixture(scope="session")
def live_modules(app_module):
    """The re-imported package the running app actually uses.

    conftest reloads ai_job_intelligence after this test module was imported,
    so a module-level import here would refer to a discarded copy and patching
    it would have no effect on the app.
    """
    return {
        "cv_profile": sys.modules["ai_job_intelligence.services.cv_profile"],
        "ai_service": sys.modules["ai_job_intelligence.services.ai_service"],
    }


@pytest.fixture(scope="session")
def PROFILE_VERSION(live_modules):
    return live_modules["ai_service"].PROFILE_VERSION


@pytest.fixture
def parse_counter(monkeypatch, live_modules):
    """Count real parses, bypassing the memoisation on analyze_cv_text."""
    cv_profile = live_modules["cv_profile"]
    calls = {"n": 0}
    original = cv_profile.build_profile

    def counting(cv_text):
        calls["n"] += 1
        return original(cv_text)

    monkeypatch.setattr(cv_profile, "build_profile", counting)
    return calls


def _row(app_module, cv_id):
    db = app_module.SessionLocal()
    try:
        return db.get(app_module.CV, cv_id)
    finally:
        db.close()


def test_upload_persists_the_parsed_profile(app_module, uploaded_cv, PROFILE_VERSION):
    cv = _row(app_module, uploaded_cv)
    assert cv.profile_json, "upload should store the parsed profile"
    assert cv.profile_version == PROFILE_VERSION
    assert cv.profile_parsed_at is not None

    stored = json.loads(cv.profile_json)
    assert "Python" in stored["technical_skills"]
    assert "Kubernetes" in stored["technical_skills"]


def test_reads_do_not_reparse(client, seeker, uploaded_cv, parse_counter):
    """The whole point: repeated reads must not re-run the parser."""
    for _ in range(3):
        assert client.get(f"/api/cvs/{uploaded_cv}/analysis", headers=seeker).status_code == 200
        assert client.get("/api/career-insights", headers=seeker).status_code == 200
        assert client.get("/api/jobs", headers=seeker).status_code == 200

    assert parse_counter["n"] == 0


def test_stale_version_triggers_reparse(app_module, client, seeker, uploaded_cv, parse_counter, PROFILE_VERSION):
    """A profile written by an older extractor must not be trusted."""
    db = app_module.SessionLocal()
    try:
        cv = db.get(app_module.CV, uploaded_cv)
        cv.profile_version = PROFILE_VERSION - 1
        db.commit()
    finally:
        db.close()

    assert client.get(f"/api/cvs/{uploaded_cv}/analysis", headers=seeker).status_code == 200
    assert parse_counter["n"] == 1

    cv = _row(app_module, uploaded_cv)
    assert cv.profile_version == PROFILE_VERSION


def test_missing_profile_is_backfilled(app_module, client, seeker, uploaded_cv, parse_counter, PROFILE_VERSION):
    """Rows predating the cache columns get filled in on first read."""
    db = app_module.SessionLocal()
    try:
        cv = db.get(app_module.CV, uploaded_cv)
        cv.profile_json = None
        cv.profile_version = None
        db.commit()
    finally:
        db.close()

    assert client.get(f"/api/cvs/{uploaded_cv}/analysis", headers=seeker).status_code == 200
    assert parse_counter["n"] == 1

    cv = _row(app_module, uploaded_cv)
    assert cv.profile_json, "profile should have been backfilled"
    assert cv.profile_version == PROFILE_VERSION


def test_corrupt_cache_is_recovered(app_module, client, seeker, uploaded_cv, PROFILE_VERSION):
    """Unreadable JSON must rebuild the profile, not fail the request."""
    db = app_module.SessionLocal()
    try:
        cv = db.get(app_module.CV, uploaded_cv)
        cv.profile_json = "{not valid json"
        cv.profile_version = PROFILE_VERSION
        db.commit()
    finally:
        db.close()

    r = client.get(f"/api/cvs/{uploaded_cv}/analysis", headers=seeker)
    assert r.status_code == 200, r.text
    assert _row(app_module, uploaded_cv).profile_version == PROFILE_VERSION


def test_employer_search_parses_each_candidate_at_most_once(
    client, employer, uploaded_cv, parse_counter
):
    r = client.get("/api/candidates", headers=employer)
    assert r.status_code == 200, r.text
    # Every candidate CV was parsed at upload, so the search parses nothing.
    assert parse_counter["n"] == 0
