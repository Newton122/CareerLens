"""Row-level persistence of embedding vectors for CVs and jobs.

Layering
--------
``embedding_service``  loads the model and encodes raw text.
``vector_store``       vector representation, serialisation, ranking (pure).
``semantic_index``     this module: reads and writes vectors on DB rows.

Endpoints only ever talk to this module, so replacing brute-force search with
pgvector later is a change here rather than across every route.

Vectors are written when a CV is uploaded or a job is created, and backfilled
transparently on first read for rows that predate the columns or were embedded
by an older model version.
"""
from __future__ import annotations

import json
import logging

import numpy as np

from ai_job_intelligence.models.cv import CV
from ai_job_intelligence.models.job import Job
from ai_job_intelligence.schemas import CandidateProfile
from ai_job_intelligence.services import vector_store
from ai_job_intelligence.services.vector_store import EMBEDDING_VERSION

logger = logging.getLogger(__name__)


def _parse_skills(raw: str | None) -> list[str]:
    try:
        value = json.loads(raw or "[]")
        return [str(v) for v in value] if isinstance(value, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


# --- writing -------------------------------------------------------------


def set_cv_embedding(cv: CV, profile: CandidateProfile) -> np.ndarray:
    """Compute and attach a CV's vector (caller commits)."""
    vec = vector_store.encode(vector_store.profile_to_text(profile))
    cv.embedding = vector_store.serialize(vec)
    cv.embedding_version = EMBEDDING_VERSION
    return vec


def set_job_embedding(job: Job) -> np.ndarray:
    """Compute and attach a job's vector (caller commits)."""
    vec = vector_store.encode(
        vector_store.job_to_text(
            job.title, job.description, _parse_skills(job.required_skills)
        )
    )
    job.embedding = vector_store.serialize(vec)
    job.embedding_version = EMBEDDING_VERSION
    return vec


# --- reading -------------------------------------------------------------


def _fresh(blob: str | None, version: int | None) -> np.ndarray | None:
    if version != EMBEDDING_VERSION:
        return None
    return vector_store.deserialize(blob)


def get_cv_vector(db, cv: CV, profile: CandidateProfile) -> np.ndarray:
    """Return a CV's vector, computing and caching it if absent or stale."""
    cached = _fresh(cv.embedding, cv.embedding_version)
    if cached is not None:
        return cached

    vec = set_cv_embedding(cv, profile)
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Could not cache embedding for CV %s", cv.id)
    return vec


def get_job_vectors(db, jobs: list[Job]) -> dict[int, np.ndarray]:
    """Return {job_id: vector} for ``jobs``, backfilling in one commit."""
    vectors: dict[int, np.ndarray] = {}
    dirty = False

    for job in jobs:
        cached = _fresh(job.embedding, job.embedding_version)
        if cached is None:
            cached = set_job_embedding(job)
            dirty = True
        vectors[job.id] = cached

    if dirty:
        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Could not cache job embeddings during bulk read")

    return vectors


def get_cv_vectors(db, cvs: list[CV], profiles: dict[int, CandidateProfile]) -> dict[int, np.ndarray]:
    """Return {cv_id: vector} for ``cvs``, backfilling in one commit."""
    vectors: dict[int, np.ndarray] = {}
    dirty = False

    for cv in cvs:
        cached = _fresh(cv.embedding, cv.embedding_version)
        if cached is None:
            profile = profiles.get(cv.id)
            if profile is None:
                continue
            cached = set_cv_embedding(cv, profile)
            dirty = True
        vectors[cv.id] = cached

    if dirty:
        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Could not cache CV embeddings during bulk read")

    return vectors


# --- search --------------------------------------------------------------


def rank_jobs_for_cv(
    db,
    cv: CV,
    profile: CandidateProfile,
    jobs: list[Job],
    *,
    top_k: int | None = None,
) -> list[tuple[Job, float]]:
    """Order ``jobs`` by semantic closeness to a candidate profile."""
    if not jobs:
        return []

    query = get_cv_vector(db, cv, profile)
    vectors = get_job_vectors(db, jobs)
    by_id = {job.id: job for job in jobs}

    return [
        (by_id[job_id], score)
        for job_id, score in vector_store.rank(query, vectors, top_k=top_k)
        if job_id in by_id
    ]


def rank_cvs_for_query(
    db,
    query_text: str,
    cvs: list[CV],
    profiles: dict[int, CandidateProfile],
    *,
    top_k: int | None = None,
    min_score: float | None = None,
) -> list[tuple[CV, float]]:
    """Order ``cvs`` by semantic closeness to a free-text query."""
    if not cvs or not query_text.strip():
        return []

    query = vector_store.encode(query_text)
    vectors = get_cv_vectors(db, cvs, profiles)
    by_id = {cv.id: cv for cv in cvs}

    return [
        (by_id[cv_id], score)
        for cv_id, score in vector_store.rank(
            query, vectors, top_k=top_k, min_score=min_score
        )
        if cv_id in by_id
    ]
