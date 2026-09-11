"""End-to-end tests for embedding persistence and semantic search."""
from __future__ import annotations

import sys

import pytest

from ai_job_intelligence.conftest import TEST_PASSWORD

DEVOPS_CV = b"""Priya Raman
Skills
Kubernetes, Docker, Terraform, AWS, Linux, CI/CD, Go
Experience
Site Reliability Engineer, 6 years running production Kubernetes clusters
Automated cloud provisioning and on-call incident response
Education
BSc Computer Engineering
"""

MARKETING_CV = b"""Tom Baker
Skills
Social Media Marketing, SEO, Copywriting, Canva, Google Analytics
Experience
Digital Marketing Manager, 5 years running brand campaigns
Education
BA Communications
"""


@pytest.fixture(scope="module")
def live(app_module):
    return {
        "semantic_index": sys.modules["ai_job_intelligence.services.semantic_index"],
        "vector_store": sys.modules["ai_job_intelligence.services.vector_store"],
    }


def _register(client, email, role="job_seeker"):
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": TEST_PASSWORD, "name": email, "role": role},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def two_candidates(client):
    """Upload two very different CVs and return their ids."""
    ids = {}
    for label, email, blob in [
        ("devops", "devops@test.com", DEVOPS_CV),
        ("marketing", "marketing@test.com", MARKETING_CV),
    ]:
        headers = _register(client, email)
        r = client.post(
            "/api/upload-cv",
            files={"file": (f"{label}.txt", blob, "text/plain")},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        ids[label] = int(r.json()["cv_id"])
    return ids


def test_upload_stores_an_embedding(app_module, live, two_candidates):
    db = app_module.SessionLocal()
    try:
        cv = db.get(app_module.CV, two_candidates["devops"])
        assert cv.embedding, "upload should store a vector"
        assert cv.embedding_version == live["vector_store"].EMBEDDING_VERSION

        vec = live["vector_store"].deserialize(cv.embedding)
        assert vec is not None
        assert vec.shape == (live["vector_store"].EMBEDDING_DIM,)
    finally:
        db.close()


def test_created_job_stores_an_embedding(app_module, live, client, employer):
    r = client.post(
        "/api/jobs",
        json={
            "title": "Site Reliability Engineer",
            "description": "Run our Kubernetes clusters and cloud infrastructure on AWS.",
            "location": "Remote",
            "required_skills": ["Kubernetes", "AWS", "Terraform"],
            "benefits": ["Remote"],
        },
        headers=employer,
    )
    assert r.status_code == 201, r.text

    db = app_module.SessionLocal()
    try:
        job = db.get(app_module.Job, r.json()["id"])
        assert job.embedding
        assert job.embedding_version == live["vector_store"].EMBEDDING_VERSION
    finally:
        db.close()


def _positions(results, ids):
    """Rank positions of the given CV ids within a result list."""
    order = [int(c["id"]) for c in results]
    return {label: order.index(cv_id) for label, cv_id in ids.items() if cv_id in order}


def test_semantic_candidate_search_ranks_by_meaning(client, employer, two_candidates):
    """The query names no skill explicitly -- only the meaning matches.

    Other test modules share this database and upload their own CVs, so this
    asserts the *relative* order of the two CVs it controls rather than
    claiming a specific one is first overall.
    """
    r = client.get(
        "/api/candidates",
        params={"q": "someone who can run our cloud infrastructure and deployments"},
        headers=employer,
    )
    assert r.status_code == 200, r.text
    results = r.json()
    assert results, "semantic search returned nothing"

    pos = _positions(results, two_candidates)
    assert pos["devops"] < pos["marketing"], (
        "the SRE should outrank the marketer for an infrastructure query"
    )
    assert results[0]["semantic_score"] is not None


def test_semantic_search_flips_for_a_different_query(client, employer, two_candidates):
    """The same two CVs must swap order when the query changes meaning."""
    r = client.get(
        "/api/candidates",
        params={"q": "brand campaigns, content and social media growth"},
        headers=employer,
    )
    assert r.status_code == 200, r.text
    results = r.json()
    assert results

    pos = _positions(results, two_candidates)
    assert "marketing" in pos, "the marketer should match a marketing query"
    # The SRE may be filtered out entirely by the relevance floor, which is the
    # correct outcome; if present, it must rank below the marketer.
    assert pos.get("devops", len(results)) > pos["marketing"]


def test_candidate_search_without_query_is_unchanged(client, employer, two_candidates):
    """The added parameter must not alter the existing contract."""
    r = client.get("/api/candidates", headers=employer)
    assert r.status_code == 200, r.text
    results = r.json()
    assert len(results) >= 2
    assert all(c["semantic_score"] is None for c in results)


def test_recommendations_include_semantic_score(client):
    """Self-contained: this user uploads its own CV rather than relying on
    another test module having run first."""
    headers = _register(client, "recs@test.com")
    up = client.post(
        "/api/upload-cv",
        files={"file": ("devops.txt", DEVOPS_CV, "text/plain")},
        headers=headers,
    )
    assert up.status_code == 200, up.text

    r = client.get("/api/job-recommendations", headers=headers)
    assert r.status_code == 200, r.text
    jobs = r.json()["jobs"]
    assert jobs
    for job in jobs:
        assert -1.0 <= job["semantic_score"] <= 1.0


def test_stale_embedding_version_is_rebuilt(app_module, live, client, employer, two_candidates):
    vs = live["vector_store"]
    db = app_module.SessionLocal()
    try:
        cv = db.get(app_module.CV, two_candidates["devops"])
        cv.embedding_version = vs.EMBEDDING_VERSION - 1
        db.commit()
    finally:
        db.close()

    assert client.get(
        "/api/candidates", params={"q": "kubernetes"}, headers=employer
    ).status_code == 200

    db = app_module.SessionLocal()
    try:
        cv = db.get(app_module.CV, two_candidates["devops"])
        assert cv.embedding_version == vs.EMBEDDING_VERSION
    finally:
        db.close()
