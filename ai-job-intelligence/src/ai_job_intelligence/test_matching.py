"""Unit tests for skill extraction and job/candidate matching.

These pin the false-positive behaviour that used to inflate every match score:
the matcher accepted a requirement if *any single token* of it appeared as a
substring anywhere in the CV.
"""
from __future__ import annotations

import pytest

from ai_job_intelligence.conftest import TEST_PASSWORD
from ai_job_intelligence.schemas import JobRequirements
from ai_job_intelligence.services.ai_service import analyze_cv_text
from ai_job_intelligence.services.matcher import analyze_match

ENGINEERING_ROLE = JobRequirements(
    technical_skills=["R", "Go", "C", "Machine Learning", "Kubernetes", "Rust"],
    soft_skills=[],
    required_experience="5 years",
    education_requirements="Bachelor's degree in Computer Science",
    certifications=[],
    keywords=[],
)

MARKETING_CV = """Jane Smith
Skills
Social Media Marketing, SEO, Canva, Copywriting
Experience
Marketing Assistant at a retail brand, always learning and ready to go the extra mile
Education
BA Communications
"""

GO_DEVELOPER_CV = """Sam Patel
Skills
Go, Kubernetes, Docker, PostgreSQL
Experience
Backend engineer writing Golang microservices for 5 years
Education
BSc Computer Science
"""


def test_ordinary_english_words_are_not_extracted_as_skills():
    """'ready to go the extra mile' must not yield the Go language."""
    profile = analyze_cv_text(MARKETING_CV)
    assert "Go" not in profile.technical_skills


def test_listed_skills_are_still_extracted():
    """A skills list of 'Go, Kubernetes, ...' must still yield Go."""
    profile = analyze_cv_text(GO_DEVELOPER_CV)
    assert "Go" in profile.technical_skills
    assert "Kubernetes" in profile.technical_skills


def test_unrelated_cv_does_not_match_engineering_role():
    result = analyze_match(
        candidate=analyze_cv_text(MARKETING_CV),
        requirements=ENGINEERING_ROLE,
    )
    assert result["matched_skills"] == []
    assert result["match_score"] < 30


def test_relevant_cv_matches_engineering_role():
    result = analyze_match(
        candidate=analyze_cv_text(GO_DEVELOPER_CV),
        requirements=ENGINEERING_ROLE,
    )
    assert "Go" in result["matched_skills"]
    assert "Kubernetes" in result["matched_skills"]
    assert "Rust" in result["missing_skills"]


@pytest.mark.parametrize("skill", ["R", "C", "Rust"])
def test_absent_short_skills_reported_missing(skill):
    result = analyze_match(
        candidate=analyze_cv_text(GO_DEVELOPER_CV),
        requirements=ENGINEERING_ROLE,
    )
    assert skill in result["missing_skills"]


def test_empty_requirements_do_not_crash():
    empty = JobRequirements(
        technical_skills=[],
        soft_skills=[],
        required_experience="",
        education_requirements="",
        certifications=[],
        keywords=[],
    )
    result = analyze_match(candidate=analyze_cv_text(GO_DEVELOPER_CV), requirements=empty)
    assert result["matched_skills"] == []
    assert isinstance(result["match_score"], int)


# --- scoring only what the posting actually states -------------------------


SKILLS_ONLY_ROLE = JobRequirements(
    technical_skills=["Python", "Docker"],
    soft_skills=[],
    required_experience="",
    education_requirements="",
    certifications=[],
    keywords=[],
)

MATCHING_CV = "Skills\nPython, Docker, Kubernetes\n"


def test_unstated_requirements_are_not_scored():
    """A posting that states no experience/education must not hand out marks."""
    result = analyze_match(
        candidate=analyze_cv_text(MATCHING_CV),
        requirements=SKILLS_ONLY_ROLE,
    )
    assert result["experience_match"] is None
    assert result["education_match"] is None
    assert "scored on skills" in result["summary"]


def test_unmet_stated_requirement_scores_zero_not_null():
    """Null means 'not asked for'; zero means 'asked for and missing'."""
    role = JobRequirements(
        technical_skills=["Python"],
        soft_skills=[],
        required_experience="5 years",
        education_requirements="Bachelor's degree",
        certifications=[],
        keywords=[],
    )
    # A CV with skills but no experience or education sections at all.
    result = analyze_match(
        candidate=analyze_cv_text("Skills\nPython\n"),
        requirements=role,
    )
    assert result["experience_match"] == 0
    assert result["education_match"] == 0


def test_missing_skills_still_lower_the_score():
    """Renormalised weighting must not make a poor skill match look good."""
    role = JobRequirements(
        technical_skills=["Python", "Rust", "Kubernetes", "Terraform"],
        soft_skills=[],
        required_experience="",
        education_requirements="",
        certifications=[],
        keywords=[],
    )
    result = analyze_match(
        candidate=analyze_cv_text("Skills\nPython\n"),
        requirements=role,
    )
    assert result["match_score"] < 60, result["match_score"]
    assert len(result["missing_skills"]) >= 3


# --- the employer's "required skills" field counts ------------------------
# Matching used to read requirements only from the description text, so a
# skill the employer typed into the posting's skills field but did not repeat
# in the prose was never scored for anyone.


def _seeker_with_cv(client, email: str, cv: bytes) -> dict:
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": TEST_PASSWORD, "name": "M", "role": "job_seeker"},
    )
    assert r.status_code == 200, r.text
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    up = client.post(
        "/api/upload-cv", files={"file": ("cv.txt", cv, "text/plain")}, headers=headers
    )
    assert up.status_code == 200, up.text
    return headers


def test_listed_required_skills_are_scored_even_if_not_in_the_description(client, employer):
    job = client.post(
        "/api/jobs",
        json={
            "title": "Platform Engineer",
            # Names Python only; Terraform lives solely in required_skills,
            # typed in lowercase the way employers usually do.
            "description": "Join our platform team writing Python services.",
            "location": "Remote",
            "required_skills": ["python", "terraform"],
        },
        headers=employer,
    )
    assert job.status_code == 201, job.text
    job_id = job.json()["id"]

    without = _seeker_with_cv(
        client, "listed.without@test.com", b"Skills\nPython, Django\nExperience\nPython developer for 4 years\n"
    )
    with_it = _seeker_with_cv(
        client, "listed.with@test.com", b"Skills\nPython, Terraform\nExperience\nPython developer for 4 years\n"
    )

    missing = client.get(f"/api/jobs/{job_id}", headers=without).json()
    covered = client.get(f"/api/jobs/{job_id}", headers=with_it).json()

    # Shown with its proper spelling, and not double-counted with "python".
    assert missing["skill_gaps"] == ["Terraform"]
    assert covered["skill_gaps"] == []
    assert covered["match_score"] > missing["match_score"]
