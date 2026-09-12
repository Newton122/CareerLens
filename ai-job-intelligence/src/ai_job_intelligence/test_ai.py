"""Tests for reading a job description with the rule-based extractor.

This file used to be a script that printed results when pytest imported it
(and could call Gemini at that moment if a key was set). It now asserts what
the deterministic extractor must find, with ``use_llm=False`` so the test
never depends on the network.
"""
from __future__ import annotations

from ai_job_intelligence.services.ai_service import analyze_job_description

JOB = """
We are looking for a backend developer with strong Python and FastAPI
experience.

The candidate should have experience working with PostgreSQL, REST APIs,
Docker and Git.

At least 2 years of backend development experience is preferred.
A degree in Computer Science or a related field is required.
AWS experience is a plus.
"""


def test_rules_extract_every_named_technology():
    result = analyze_job_description(JOB, use_llm=False)
    assert set(result.technical_skills) == {
        "Python", "FastAPI", "PostgreSQL", "REST", "Docker", "Git", "AWS",
    }


def test_rules_extract_years_and_education():
    result = analyze_job_description(JOB, use_llm=False)
    assert result.experience_requirements == ["2 years"]
    assert result.education_requirements_list == [
        "Bachelor's degree in Computer Science or related field"
    ]


def test_unstated_requirements_stay_empty():
    result = analyze_job_description(
        "Friendly barista wanted for weekend shifts in our cafe.", use_llm=False
    )
    assert result.technical_skills == []
    assert result.experience_requirements == []
    assert result.education_requirements_list == []
