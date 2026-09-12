"""Tests for text similarity from the embedding model.

This file used to be a script that printed one similarity score. It now
checks the properties the matcher relies on.
"""
from __future__ import annotations

import pytest

from ai_job_intelligence.services.embedding_service import calculate_similarity

JOB = "Develop RESTful backend APIs using Python."
RELATED = "Built web APIs and backend services with Python and FastAPI."
UNRELATED = "Managed a bakery's weekend flower deliveries."


def test_related_text_scores_well_above_unrelated_text():
    related = calculate_similarity(JOB, RELATED)
    unrelated = calculate_similarity(JOB, UNRELATED)
    # The matcher's thresholds (0.55 and 0.75) assume a clear gap like this.
    assert related > 0.6
    assert unrelated < 0.3
    assert related - unrelated > 0.4


def test_identical_text_is_a_perfect_match():
    assert calculate_similarity(JOB, JOB) == pytest.approx(1.0, abs=1e-4)


def test_empty_text_is_no_match():
    assert calculate_similarity("", JOB) == 0.0
    assert calculate_similarity(JOB, "") == 0.0
