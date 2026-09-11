"""Unit tests for the pure vector layer (no database)."""
from __future__ import annotations

import numpy as np
import pytest

from ai_job_intelligence.schemas import CandidateProfile
from ai_job_intelligence.services import vector_store as vs

BACKEND = "Python, Go, Kubernetes, Docker, PostgreSQL, AWS, Terraform"
MARKETING = "Social media marketing, SEO, copywriting, brand management, Canva"


def test_vectors_are_normalised():
    vec = vs.encode(BACKEND)
    assert vec.shape == (vs.EMBEDDING_DIM,)
    assert np.isclose(np.linalg.norm(vec), 1.0, atol=1e-4)


def test_serialisation_roundtrip():
    vec = vs.encode(BACKEND)
    restored = vs.deserialize(vs.serialize(vec))
    assert restored is not None
    assert np.allclose(vec, restored, atol=1e-6)


def test_base64_is_more_compact_than_json():
    vec = vs.encode(BACKEND)
    assert len(vs.serialize(vec)) < len(str(vec.tolist())) / 2


@pytest.mark.parametrize("blob", [None, "", "not base64 at all!!", "YWJj"])
def test_unreadable_blobs_return_none(blob):
    """A corrupt vector must degrade to None, never raise."""
    assert vs.deserialize(blob) is None


def test_related_text_scores_above_unrelated():
    query = vs.encode("backend engineer for cloud infrastructure")
    assert vs.similarity(query, vs.encode(BACKEND)) > vs.similarity(
        query, vs.encode(MARKETING)
    )


def test_rank_orders_by_similarity():
    query = vs.encode("devops and cloud infrastructure engineer")
    ranked = vs.rank(query, {1: vs.encode(BACKEND), 2: vs.encode(MARKETING)})
    assert [i for i, _ in ranked] == [1, 2]
    assert ranked[0][1] > ranked[1][1]


def test_rank_respects_top_k_and_floor():
    query = vs.encode("cloud infrastructure")
    candidates = {1: vs.encode(BACKEND), 2: vs.encode(MARKETING)}

    assert len(vs.rank(query, candidates, top_k=1)) == 1
    assert vs.rank(query, candidates, min_score=0.99) == []
    assert vs.rank(query, {}) == []


def test_profile_text_weights_skills():
    profile = CandidateProfile(
        technical_skills=["Kubernetes"],
        soft_skills=[],
        experience=["Managed deployments"],
        education=[],
        certifications=[],
        projects=[],
        keywords=[],
    )
    text = vs.profile_to_text(profile)
    # Skills appear twice by design, so they dominate the vector.
    assert text.count("Kubernetes") == 2
    assert "Managed deployments" in text


def test_empty_profile_still_encodes():
    empty = CandidateProfile()
    vec = vs.encode(vs.profile_to_text(empty))
    assert vec.shape == (vs.EMBEDDING_DIM,)
