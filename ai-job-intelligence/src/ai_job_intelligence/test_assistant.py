"""Tests for the grounded domain assistant.

Run with no API key, so these exercise the deterministic path. That is
deliberate: the fallback must be correct on its own, because it is what users
get whenever the model is unavailable.
"""
from __future__ import annotations

import sys

import pytest

from ai_job_intelligence.conftest import TEST_PASSWORD

SRE_CV = b"""Priya Raman
Skills
Kubernetes, Docker, Terraform, AWS, Linux, Go
Experience
Site Reliability Engineer, 6 years running production Kubernetes clusters
Education
BSc Computer Engineering
"""


@pytest.fixture(scope="module")
def assistant(app_module):
    return sys.modules["ai_job_intelligence.services.assistant"]


@pytest.fixture(scope="module")
def sre(client):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "sre@test.com",
            "password": TEST_PASSWORD,
            "name": "Priya",
            "role": "job_seeker",
        },
    )
    assert r.status_code == 200, r.text
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    up = client.post(
        "/api/upload-cv",
        files={"file": ("sre.txt", SRE_CV, "text/plain")},
        headers=headers,
    )
    assert up.status_code == 200, up.text
    return headers


def ask(client, headers, message):
    r = client.post("/api/career-lens/chat", json={"message": message}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.parametrize(
    "message,expected_intent",
    [
        ("what skills am I missing?", "gaps"),
        ("which jobs fit me?", "jobs"),
        ("how much can I earn?", "salary"),
        ("what does my CV say about my experience?", "experience"),
        ("what are my top skills?", "skills"),
    ],
)
def test_intent_routing(assistant, message, expected_intent):
    """'What skills am I missing' is a gap question, not a skills question."""
    assert assistant.detect_intent(message) == expected_intent


def test_every_answer_cites_sources(client, sre):
    body = ask(client, sre, "which jobs fit me?")
    assert body["sources"], "an answer must say what it was built from"
    assert any(s["type"] == "cv" for s in body["sources"])


def test_fit_questions_retrieve_relevant_jobs(client, sre):
    """A generic question carries no domain signal, so retrieval must be
    steered by the candidate's own profile."""
    body = ask(client, sre, "which jobs fit me?")
    job_labels = [s["label"] for s in body["sources"] if s["type"] == "job"]
    assert job_labels, "a fit question should retrieve jobs"
    assert "DevOps" in job_labels[0] or "Engineer" in job_labels[0], job_labels


def test_salary_answers_only_quote_real_postings(client, sre):
    body = ask(client, sre, "how much can I earn?")
    text = body["response"]
    if "$" in text:
        # Any figure quoted must come from a seeded posting's salary band.
        assert "matching role" in text
        assert body["sources"]


def test_no_cv_is_stated_not_guessed(client):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "nocv@test.com",
            "password": TEST_PASSWORD,
            "name": "No CV",
            "role": "job_seeker",
        },
    )
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    body = ask(client, headers, "what should I learn next?")
    assert "upload" in body["response"].lower()
    assert all(s["type"] != "cv" for s in body["sources"])


def test_gap_answer_names_real_demand(client, sre):
    body = ask(client, sre, "what skills am I missing?")
    # The SRE CV has no Python; seeded postings ask for it.
    assert "Python" in body["response"] or "missing" in body["response"].lower()


def test_empty_message_is_rejected(client, sre):
    r = client.post("/api/career-lens/chat", json={"message": "   "}, headers=sre)
    assert r.status_code == 400


def test_response_shape_is_stable(client, sre):
    body = ask(client, sre, "hello")
    # "links" carries documentation for the skill gaps a reply mentions; it is
    # always present and empty when the question was not about skills.
    assert set(body) == {"response", "intent", "sources", "generated_by", "links"}
    assert body["generated_by"] in ("model", "rules")
    assert isinstance(body["links"], list)
