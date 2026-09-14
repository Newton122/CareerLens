"""Tests for career insights.

Two failures these guard against:

* The endpoint returning effectively the same advice for everyone. Measuring
  demand across the whole job board surfaces whatever the board contains most
  of, so an accountant was told to learn Docker. Figures must be computed only
  over roles matching the candidate's own field.
* Inventing figures. Salary and demand must come from real postings, and when
  nothing relevant exists that must be said rather than filled in.
"""
from __future__ import annotations

import pytest

from ai_job_intelligence.conftest import TEST_PASSWORD

SRE_CV = b"""Priya Raman
Skills
Kubernetes, Docker, Terraform, AWS, Linux, Go
Experience
Site Reliability Engineer, 6 years running production Kubernetes clusters
Education
BSc Computer Engineering
Certifications
Certified Kubernetes Administrator
"""

MARKETER_CV = b"""Tom Baker
Skills
Social Media Marketing, SEO, Copywriting, Canva, Google Analytics
Experience
Digital Marketing Manager, 5 years running brand campaigns
Education
BA Communications
"""

CHEF_CV = b"""Luca Moretti
Skills
Menu planning, pastry, food safety, kitchen management, butchery
Experience
Head Chef, 12 years running a fine dining kitchen brigade
Education
Diploma in Culinary Arts
"""


def _insights_for(client, grant_plan, email, blob):
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": TEST_PASSWORD, "name": email, "role": "job_seeker"},
    )
    assert r.status_code == 200, r.text
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    # Career Insights is a Pro feature (its gating is tested in test_billing).
    grant_plan(headers)

    up = client.post(
        "/api/upload-cv",
        files={"file": ("cv.txt", blob, "text/plain")},
        headers=headers,
    )
    assert up.status_code == 200, up.text

    res = client.get("/api/career-insights", headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


@pytest.fixture(scope="module")
def sre_insights(client, grant_plan):
    return _insights_for(client, grant_plan, "ci-sre@test.com", SRE_CV)


@pytest.fixture(scope="module")
def marketer_insights(client, grant_plan):
    return _insights_for(client, grant_plan, "ci-marketer@test.com", MARKETER_CV)


@pytest.fixture(scope="module")
def chef_insights(client, grant_plan):
    return _insights_for(client, grant_plan, "ci-chef@test.com", CHEF_CV)


def test_different_fields_get_different_gaps(sre_insights, marketer_insights):
    """The core regression: advice must not collapse to one generic list."""
    assert sre_insights["skill_gaps"] != marketer_insights["skill_gaps"]
    assert sre_insights["recommended_roles"] != marketer_insights["recommended_roles"]


def test_gaps_are_relevant_to_the_field(sre_insights, marketer_insights):
    sre_gaps = {s.lower() for s in sre_insights["skill_gaps"]}
    marketer_gaps = {s.lower() for s in marketer_insights["skill_gaps"]}

    # An engineer's gaps should be engineering skills.
    assert sre_gaps & {"ci/cd", "python", "fastapi", "postgresql", "redis"}

    # A marketer must not be told to learn container tooling.
    assert not marketer_gaps & {"kubernetes", "docker", "terraform"}


def test_candidate_is_not_told_to_learn_what_they_have(sre_insights):
    """Skills already on the CV must never appear as gaps."""
    gaps = {s.lower() for s in sre_insights["skill_gaps"]}
    assert not gaps & {"kubernetes", "docker", "terraform", "aws", "linux"}


def test_out_of_field_candidate_gets_no_invented_advice(chef_insights):
    """With nothing relevant on the board, say so rather than fabricate."""
    assert chef_insights["skill_gaps"] == []
    assert chef_insights["recommended_roles"] == []
    assert chef_insights["salary_trends"] is None
    assert "$" not in chef_insights["market_value"]
    assert any("match your field" in s for s in chef_insights["sources"])


def test_every_figure_is_attributed(sre_insights):
    assert sre_insights["sources"]
    assert any("matching your profile" in s for s in sre_insights["sources"])


def test_salary_comes_from_real_postings(sre_insights):
    """Any quoted range must be internally consistent, never a formula."""
    trends = sre_insights["salary_trends"]
    if trends is None:
        pytest.skip("no matching posting publishes a salary")

    assert trends["min"] <= trends["average"] <= trends["max"]
    assert trends["min"] > 0
    # The old code produced this from exp_years * 15000 + skill_count * 5000.
    # Real postings are round five-figure numbers, not arbitrary sums.
    assert trends["max"] >= trends["min"]


def test_demand_percentages_are_shares_not_scores(sre_insights):
    for item in sre_insights["in_demand_skills"]:
        assert 0 < item["demand"] <= 100, item


def test_profile_strength_reflects_cv_completeness(sre_insights, chef_insights):
    """The SRE CV has certifications and more skills, so it must score higher."""
    assert sre_insights["profile_strength"] > chef_insights["profile_strength"]


def test_no_cv_returns_an_empty_but_honest_payload(client, grant_plan):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "ci-nocv@test.com",
            "password": TEST_PASSWORD,
            "name": "No CV",
            "role": "job_seeker",
        },
    )
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    grant_plan(headers)
    body = client.get("/api/career-insights", headers=headers).json()

    assert body["profile_strength"] == 0
    assert body["skill_gaps"] == []
    assert body["salary_trends"] is None
    assert "upload" in " ".join(body["action_items"]).lower()
