"""Tests for post-analysis guidance and the learning-resource lookup.

The resource tests never touch the network. A test that calls dev.to is not
testing this code -- it tests whether dev.to is up, fails on a train, and is
slow enough that people stop running the suite. Each source's HTTP layer is
replaced with a fake, which is also the only practical way to assert the
behaviour that actually matters here: what happens when a source is down.
"""
from __future__ import annotations

import pytest

from ai_job_intelligence.services import learning_resources as lr
from ai_job_intelligence.services.guidance import build_guidance


# --- guidance ------------------------------------------------------------


def test_missing_skills_produce_one_focused_action_not_two_per_skill():
    g = build_guidance(
        matched_skills=["Python"],
        missing_skills=["Go", "Rust", "Kubernetes", "Terraform", "AWS"],
        experience_match=80,
        education_match=80,
        match_score=45,
    )
    gap = [a for a in g if a["group"] == "gap"]
    # Five missing skills used to yield ten near-identical bullets.
    assert len(gap) == 2
    assert len(g) < 6


def test_the_first_action_names_the_skills_to_start_with():
    g = build_guidance(
        matched_skills=[],
        missing_skills=["Go", "Rust", "Kubernetes"],
        experience_match=None,
        education_match=None,
        match_score=20,
    )
    first = g[0]
    assert "Go" in first["detail"]
    assert first["skills"][:2] == ["Go", "Rust"]


def test_actions_are_ordered_by_priority():
    g = build_guidance(
        matched_skills=["Python"],
        missing_skills=["Go", "Rust", "Kubernetes"],
        experience_match=10,
        education_match=90,
        match_score=30,
    )
    priorities = [a["priority"] for a in g]
    assert priorities == sorted(priorities)


def test_a_strong_match_is_told_to_apply():
    g = build_guidance(
        matched_skills=["Python", "Django"],
        missing_skills=[],
        experience_match=90,
        education_match=90,
        match_score=88,
        job_title="Backend Engineer",
    )
    assert any("Apply now" in a["title"] for a in g)


def test_a_perfect_match_still_gets_advice():
    g = build_guidance(
        matched_skills=[],
        missing_skills=[],
        experience_match=None,
        education_match=None,
        match_score=100,
    )
    assert len(g) >= 1
    assert g[0]["detail"]


def test_unstated_requirements_produce_no_action():
    # None means "the posting never asked", which must not be advised on.
    g = build_guidance(
        matched_skills=["Python"],
        missing_skills=[],
        experience_match=None,
        education_match=None,
        match_score=80,
    )
    assert not any("education" in a["title"].lower() for a in g)


# --- learning resources --------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_cache():
    lr.clear_cache()
    yield
    lr.clear_cache()


def test_official_docs_lead_when_they_exist(monkeypatch):
    monkeypatch.setattr(lr, "NETWORK_SOURCES", [])
    found = lr.resources_for_skill("Python")
    assert found.resources[0].kind == "docs"
    assert "docs.python.org" in found.resources[0].url


def test_every_source_failing_degrades_rather_than_raises(monkeypatch):
    def boom(client, skill):
        raise RuntimeError("network down")

    monkeypatch.setattr(lr, "NETWORK_SOURCES", [boom, boom, boom])
    found = lr.resources_for_skill("Kubernetes")

    assert found.degraded is True
    # The curated entry still stands: a dead API must not hide known-good docs.
    assert any(r.kind == "docs" for r in found.resources)


def test_one_source_failing_keeps_the_others(monkeypatch):
    def boom(client, skill):
        raise RuntimeError("down")

    def ok(client, skill):
        return [lr.Resource(title="A repo", url="https://example.com/r", source="GitHub", kind="repo")]

    monkeypatch.setattr(lr, "NETWORK_SOURCES", [boom, ok])
    found = lr.resources_for_skill("Go")

    assert found.degraded is False
    assert any(r.url == "https://example.com/r" for r in found.resources)


def test_a_degraded_lookup_is_not_cached(monkeypatch):
    calls = []

    def boom(client, skill):
        calls.append(1)
        raise RuntimeError("down")

    monkeypatch.setattr(lr, "NETWORK_SOURCES", [boom])
    lr.resources_for_skill("Rust")
    lr.resources_for_skill("Rust")
    # Serving an empty panel for six hours after one blip would be worse than
    # retrying.
    assert len(calls) == 2


def test_a_successful_lookup_is_cached(monkeypatch):
    calls = []

    def ok(client, skill):
        calls.append(1)
        return [lr.Resource(title="X", url="https://example.com/x", source="S", kind="article")]

    monkeypatch.setattr(lr, "NETWORK_SOURCES", [ok])
    lr.resources_for_skill("Elixir")
    lr.resources_for_skill("Elixir")
    assert len(calls) == 1


def test_duplicate_urls_are_collapsed(monkeypatch):
    def a(client, skill):
        return [lr.Resource(title="One", url="https://same.example/x", source="A", kind="article")]

    def b(client, skill):
        return [lr.Resource(title="Two", url="https://same.example/x", source="B", kind="repo")]

    monkeypatch.setattr(lr, "NETWORK_SOURCES", [a, b])
    found = lr.resources_for_skill("Zig")
    assert len(found.resources) == 1


def test_tag_normalisation_handles_punctuation():
    assert lr._tag_for("C#") == "csharp"
    assert lr._tag_for("Node.js") == "node"
    assert lr._tag_for("scikit-learn") == "scikitlearn"
    assert lr._tag_for("  Machine Learning ") == "machinelearning"


def test_teaching_content_outranks_commentary():
    assert lr._teaching_rank("A beginner's guide to Go", "") == 0
    assert lr._teaching_rank("Why our startup failed", "") == 1


def test_endpoint_requires_a_skill(client, seeker):
    r = client.get("/api/learning-resources?skills=", headers=seeker)
    assert r.status_code == 400


def test_endpoint_requires_authentication(client):
    r = client.get("/api/learning-resources?skills=Python")
    assert r.status_code in (401, 403)


def test_endpoint_returns_a_block_per_skill(client, seeker, monkeypatch):
    import ai_job_intelligence.main as main

    monkeypatch.setattr(
        main.learning_resources, "NETWORK_SOURCES", []
    )
    r = client.get("/api/learning-resources?skills=Python,Docker", headers=seeker)
    assert r.status_code == 200
    blocks = r.json()["skills"]
    assert [b["skill"] for b in blocks] == ["Python", "Docker"]
