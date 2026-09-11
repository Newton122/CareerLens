"""Tests for file upload safety and the public demo endpoint.

Four defects these pin, all found by probing the running server:

* An unparseable PDF raised PyMuPDF's own exception, producing a bare 500 and
  logging the absolute server path of the temp file.
* The uploaded file was only deleted after a *successful* analysis, so every
  failed demo left a file on disk permanently.
* No size limit on a public, unauthenticated endpoint.
* /api/upload-cv wrote to ``UPLOAD_DIR / file.filename`` with the client's
  filename, so "../../evil.txt" escaped the upload directory.
"""
from __future__ import annotations

from pathlib import Path

import pytest

CV_BYTES = b"""Priya Raman
Skills
Kubernetes, Docker, Terraform, AWS, Go
Experience
Site Reliability Engineer, 6 years running production clusters
Education
BSc Computer Engineering
"""

JOB_DESCRIPTION = (
    "We need Kubernetes, Docker, Terraform and AWS experience. "
    "5+ years required. Bachelor degree preferred."
)


def _demo(client, *, file=("cv.txt", CV_BYTES, "text/plain"), title="SRE", desc=JOB_DESCRIPTION):
    return client.post(
        "/api/demo/analyze",
        files={"file": file},
        data={"job_title": title, "job_description": desc},
    )




# --- demo endpoint -------------------------------------------------------


def test_demo_returns_a_grounded_analysis(client):
    r = _demo(client)
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["match_score"] > 0
    assert "Kubernetes" in body["matched_skills"]
    assert body["detected_skills"]
    assert body["sources"], "the demo should show its working like the rest of the app"
    assert body["filename"] == "cv.txt"


def test_corrupt_pdf_is_a_400_not_a_500(client):
    r = _demo(client, file=("broken.pdf", b"this is not a pdf", "application/pdf"))
    assert r.status_code == 400, r.text
    detail = r.json()["detail"]
    assert "could not be read" in detail
    # The message must never leak where the file was written on the server.
    assert "/" not in detail or "uploads" not in detail


def test_oversized_upload_is_rejected(client):
    big = b"x" * (3 * 1024 * 1024)
    r = _demo(client, file=("big.pdf", big, "application/pdf"))
    assert r.status_code == 413, r.text
    assert "too large" in r.json()["detail"].lower()


def test_empty_file_is_rejected(client):
    r = _demo(client, file=("empty.txt", b"", "text/plain"))
    assert r.status_code == 400
    assert "empty" in r.json()["detail"].lower()


def test_short_job_description_is_rejected(client):
    """A three-word description yields a meaningless score, so refuse it."""
    r = _demo(client, desc="need k8s")
    assert r.status_code == 400
    assert "fuller job description" in r.json()["detail"]


def test_unsupported_extension_is_rejected(client):
    r = _demo(client, file=("resume.docx", b"whatever", "application/octet-stream"))
    assert r.status_code == 400
    assert "allowed" in r.json()["detail"].lower()


def test_failed_analysis_leaves_no_file_behind(client, app_module):
    """Regression: cleanup ran only on the success path."""
    upload_dir: Path = app_module.UPLOAD_DIR
    before = {p.name for p in upload_dir.iterdir()} if upload_dir.exists() else set()

    assert _demo(client, file=("broken.pdf", b"nope", "application/pdf")).status_code == 400
    assert _demo(client, file=("empty.txt", b"", "text/plain")).status_code == 400

    after = {p.name for p in upload_dir.iterdir()} if upload_dir.exists() else set()
    assert after == before, f"leaked: {after - before}"


def test_successful_analysis_also_cleans_up(client, app_module):
    upload_dir: Path = app_module.UPLOAD_DIR
    before = {p.name for p in upload_dir.iterdir()} if upload_dir.exists() else set()

    assert _demo(client).status_code == 200

    after = {p.name for p in upload_dir.iterdir()} if upload_dir.exists() else set()
    assert not {n for n in after - before if n.startswith("demo_")}


def test_demo_is_rate_limited(client, app_module):
    """The client-side counter is sessionStorage and trivially bypassed, so the
    server must enforce its own limit."""
    limit = app_module.DEMO_RATE_LIMIT
    for _ in range(limit):
        assert _demo(client).status_code == 200

    blocked = _demo(client)
    assert blocked.status_code == 429
    assert "limited" in blocked.json()["detail"].lower()


def test_unstated_requirements_are_reported_not_scored(client):
    """A skills-only posting must not silently award experience/education."""
    r = _demo(client, desc="We are looking for someone who knows Kubernetes and Docker well.")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["experience_match"] is None
    assert body["education_match"] is None
    assert any("not scored" in s for s in body["sources"])


# --- authenticated upload ------------------------------------------------


@pytest.mark.parametrize(
    "malicious",
    ["../../evil.txt", "../../../../tmp/pwned.txt", "/etc/passwd.txt"],
)
def test_upload_filenames_cannot_escape_the_upload_dir(client, seeker, app_module, malicious):
    upload_dir: Path = app_module.UPLOAD_DIR
    r = client.post(
        "/api/upload-cv",
        files={"file": (malicious, CV_BYTES, "text/plain")},
        headers=seeker,
    )
    assert r.status_code == 200, r.text

    # Every stored file must sit directly inside UPLOAD_DIR.
    for path in upload_dir.iterdir():
        assert path.parent.resolve() == upload_dir.resolve()

    # And nothing may appear at the traversal target.
    escaped = (upload_dir / malicious).resolve()
    if not str(escaped).startswith(str(upload_dir.resolve())):
        assert not escaped.exists(), f"file escaped to {escaped}"


def test_stored_filename_is_generated_not_client_supplied(client, seeker, app_module):
    r = client.post(
        "/api/upload-cv",
        files={"file": ("../../sneaky.txt", CV_BYTES, "text/plain")},
        headers=seeker,
    )
    assert r.status_code == 200
    # The display name keeps only the basename, with the traversal stripped.
    assert r.json()["filename"] == "sneaky.txt"


def test_oversized_cv_upload_is_rejected(client, seeker):
    big = b"x" * (6 * 1024 * 1024)
    r = client.post(
        "/api/upload-cv",
        files={"file": ("big.txt", big, "text/plain")},
        headers=seeker,
    )
    assert r.status_code == 413


def test_corrupt_cv_upload_is_a_400(client, seeker):
    r = client.post(
        "/api/upload-cv",
        files={"file": ("broken.pdf", b"not a pdf", "application/pdf")},
        headers=seeker,
    )
    assert r.status_code == 400
