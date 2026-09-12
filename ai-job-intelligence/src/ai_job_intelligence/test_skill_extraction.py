"""Tests for reading skills out of a CV that does not list them.

Written against the reported failure: "the skills are there but the AI cannot
extract them". Three separate defects caused it, and each has a test here so
none of them can come back quietly.
"""
from __future__ import annotations

import pytest

from ai_job_intelligence.services.ai_service import (
    analyze_cv_text,
    analyze_job_description,
    _extract_experience,
    _extract_skills,
)
from ai_job_intelligence.services.cv_sections import heading_section, split_sections
from ai_job_intelligence.services.matcher import analyze_match
from ai_job_intelligence.services.skill_evidence import implied_skills


PROSE_CV = """Marcus Bell
PROFESSIONAL EXPERIENCE
Platform Engineer, Northwind (2019-2024)
- Automated our entire release pipeline using GitHub Actions
- Containerised twelve services and ran them on a managed cluster in production
- Wrote infrastructure definitions so environments could be rebuilt from scratch
PROJECTS
Cost dashboard: a small Flask app reading billing data from Redis
"""

CHEF_CV = """Luca Moretti
PROFESSIONAL EXPERIENCE
Head Chef, 12 years running a fine dining kitchen brigade
- Managed food safety compliance and menu planning across two sites
EDUCATION
Diploma in Culinary Arts
"""

PLATFORM_JD = (
    "We need a Platform Engineer with CI/CD, Docker, Kubernetes, "
    "Terraform and Python experience."
)


# --- section headings ----------------------------------------------------


@pytest.mark.parametrize(
    "heading",
    [
        "EXPERIENCE",
        "Experience",
        "Work Experience",
        "PROFESSIONAL EXPERIENCE",
        "Employment History",
        "WORK HISTORY",
        "Experience:",
        "Professional Background",
        "--- Experience ---",
    ],
)
def test_every_common_experience_heading_is_recognised(heading):
    # Five of these used to yield an empty experience list, taking the
    # experience score and every skill named only in a job description with
    # them.
    assert heading_section(heading) == "experience"


def test_a_job_title_is_not_mistaken_for_a_heading():
    assert heading_section("Network Engineer") is None
    assert heading_section("I have five years of experience building services") is None


def test_experience_is_extracted_under_an_unusual_heading():
    lines = _extract_experience(PROSE_CV)
    assert lines, "PROFESSIONAL EXPERIENCE produced no experience lines"
    assert any("Containerised" in line for line in lines)


# --- the skill cap -------------------------------------------------------


def test_a_long_skills_list_is_not_truncated():
    listed = [
        "Python", "Java", "Go", "Rust", "Docker", "Kubernetes", "Terraform",
        "AWS", "Azure", "React", "Vue", "Angular", "Django", "Flask",
        "Redis", "PostgreSQL", "MongoDB",
    ]
    skills, _ = _extract_skills("Skills\n" + ", ".join(listed))
    # The old cap kept twelve and silently dropped the last five.
    assert len(skills) > 12
    for expected in ("Django", "Flask", "Redis", "PostgreSQL", "MongoDB"):
        assert expected in skills, f"{expected} was dropped"


# --- skills named only in prose -----------------------------------------


def test_skills_are_found_in_experience_prose():
    profile = analyze_cv_text(PROSE_CV)
    # Never appear under a "Skills" heading -- this CV has none.
    assert "Flask" in profile.technical_skills
    assert "Redis" in profile.technical_skills


def test_evidence_records_where_a_skill_was_found():
    profile = analyze_cv_text(PROSE_CV)
    by_skill = {e.skill: e for e in profile.skill_evidence}
    assert "Flask" in by_skill
    assert by_skill["Flask"].source in ("projects", "experience")
    assert by_skill["Flask"].context, "no sentence recorded as evidence"


# --- implied skills ------------------------------------------------------


def test_described_work_implies_the_tool():
    hits = {h.skill for h in implied_skills(
        "Containerised twelve services and ran them on a managed cluster. "
        "Automated the release pipeline. Wrote infrastructure definitions."
    )}
    assert {"Docker", "Kubernetes", "Terraform", "CI/CD"} <= hits


def test_implication_carries_the_sentence_that_earned_it():
    hits = implied_skills("Containerised twelve services and ran them in production")
    docker = next(h for h in hits if h.skill == "Docker")
    assert "Containeris" in docker.context


# --- end to end ----------------------------------------------------------


def test_a_prose_cv_now_matches_a_matching_job():
    result = analyze_match(
        candidate=analyze_cv_text(PROSE_CV),
        requirements=analyze_job_description(PLATFORM_JD),
    )
    # This CV previously scored zero against this posting.
    assert result["match_score"] >= 50
    assert {"Docker", "Kubernetes"} <= set(result["matched_skills"])


def test_a_match_explains_itself():
    result = analyze_match(
        candidate=analyze_cv_text(PROSE_CV),
        requirements=analyze_job_description(PLATFORM_JD),
    )
    evidence = result["match_evidence"]
    assert "Docker" in evidence
    assert evidence["Docker"]["how"] in ("experience", "projects", "described")
    assert evidence["Docker"]["detail"]


def test_a_skill_genuinely_absent_stays_missing():
    result = analyze_match(
        candidate=analyze_cv_text(PROSE_CV),
        requirements=analyze_job_description(PLATFORM_JD),
    )
    # Nothing in that CV mentions or implies Python.
    assert "Python" in result["missing_skills"]


def test_an_unrelated_cv_does_not_match_a_technical_job():
    result = analyze_match(
        candidate=analyze_cv_text(CHEF_CV),
        requirements=analyze_job_description(PLATFORM_JD),
    )
    # Reading prose must not become a licence to invent skills.
    assert result["matched_skills"] == []
    assert result["match_score"] < 20


# --- education, certifications and projects -------------------------------
# These used their own scanners that only recognised a line *starting* with
# the exact word, and when nothing was found they inserted text the CV never
# contained ("Bachelor's degree in Computer Science or related field").



@pytest.mark.parametrize(
    "heading, section",
    [
        ("LICENSES & CERTIFICATIONS", "certifications"),
        ("Education and Training", "education"),
        ("Skills / Tools", "skills"),
        ("Projects + Open Source", "projects"),
        # Job titles that merely contain a section word are not headings.
        ("Research and Development Engineer", None),
        ("Sales & Marketing Manager", None),
    ],
)
def test_compound_headings(heading, section):
    assert heading_section(heading) == section


def test_sections_under_any_heading_name_are_found():
    profile = analyze_cv_text(
        "Ann Lee\n"
        "ACADEMIC BACKGROUND\nBSc Statistics, University of Nairobi (2019)\n"
        "LICENSES & CERTIFICATIONS\nGoogle Data Analytics Certificate\n"
        "SELECTED PROJECTS\nBuilt a churn model in Python for a telecom dataset\n"
    )
    assert profile.education == ["BSc Statistics, University of Nairobi (2019)"]
    assert profile.certifications == ["Google Data Analytics Certificate"]
    assert profile.projects == ["Built a churn model in Python for a telecom dataset"]


def test_no_heading_means_the_cvs_own_words_not_invented_ones():
    profile = analyze_cv_text(
        "Bob Kim\nI hold a degree in engineering and have 5 years in sales.\n"
    )
    assert profile.education == [
        "I hold a degree in engineering and have 5 years in sales."
    ]
    assert "Bachelor's degree in Computer Science or related field" not in profile.education


def test_nothing_is_invented_for_a_cv_that_says_nothing():
    profile = analyze_cv_text("Carol\nSkills\nPython\n")
    assert profile.education == []
    assert profile.experience == []
    assert profile.certifications == []
