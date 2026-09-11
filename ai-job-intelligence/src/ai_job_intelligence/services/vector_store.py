"""Storage and search for semantic embedding vectors.

Every CV profile and every job posting is turned into a single 384-dimension
vector by the sentence-transformers model in ``embedding_service``. Vectors
live on the row they describe, so semantic search is a numeric comparison
rather than a re-encode of every document on every request.

Why base64 float32 rather than JSON
-----------------------------------
A 384-float vector is ~8.4 KB as JSON text but 1.5 KB as raw float32, ~2 KB
once base64-encoded, and it decodes straight into a numpy array with no
per-element Python parsing.

Why brute force rather than an index
------------------------------------
The vectors are L2-normalised, so cosine similarity is a plain dot product and
ranking N rows is a single matrix multiply. At this project's scale that is
exact and effectively instant. It stays reasonable into the low thousands of
rows; past that the fix is pgvector with an HNSW index, which is why every
vector read and write in the app goes through this module -- swapping the
backend should not touch call sites.
"""
from __future__ import annotations

import base64
import logging

import numpy as np

from ai_job_intelligence.schemas import CandidateProfile
from ai_job_intelligence.services.embedding_service import (
    MODEL_NAME,
    create_embedding,
)

logger = logging.getLogger(__name__)

# Bump when the model or the text-building functions below change, so stored
# vectors that are no longer comparable get rebuilt instead of silently
# producing meaningless similarities.
EMBEDDING_VERSION = 1
EMBEDDING_MODEL = MODEL_NAME
EMBEDDING_DIM = 384

_DTYPE = np.float32


# --- encoding ------------------------------------------------------------


def profile_to_text(profile: CandidateProfile) -> str:
    """Flatten a candidate profile into the text that gets embedded.

    Skills are repeated ahead of the free text because they are the strongest
    signal for role fit; experience and projects add the context that
    distinguishes two candidates listing the same skills.
    """
    parts = [
        " ".join(profile.technical_skills),
        " ".join(profile.technical_skills),
        " ".join(profile.soft_skills),
        " ".join(profile.experience),
        " ".join(profile.projects),
        " ".join(profile.education),
        " ".join(profile.certifications),
    ]
    return "\n".join(p for p in parts if p.strip())


def job_to_text(
    title: str,
    description: str,
    required_skills: list[str] | None = None,
) -> str:
    """Flatten a job posting into the text that gets embedded."""
    parts = [title or "", " ".join(required_skills or []), description or ""]
    return "\n".join(p for p in parts if p.strip())


def encode(text: str) -> np.ndarray:
    """Embed text as a normalised float32 vector."""
    vec = np.asarray(create_embedding(text or ""), dtype=_DTYPE)
    norm = float(np.linalg.norm(vec))
    if norm:
        vec = vec / norm
    return vec


# --- serialisation -------------------------------------------------------


def serialize(vec: np.ndarray) -> str:
    return base64.b64encode(np.asarray(vec, dtype=_DTYPE).tobytes()).decode("ascii")


def deserialize(blob: str | None) -> np.ndarray | None:
    if not blob:
        return None
    try:
        vec = np.frombuffer(base64.b64decode(blob), dtype=_DTYPE)
    except Exception:
        logger.warning("Discarding unreadable embedding blob")
        return None
    if vec.size != EMBEDDING_DIM:
        logger.warning(
            "Discarding embedding of wrong size: %s (expected %s)",
            vec.size,
            EMBEDDING_DIM,
        )
        return None
    return vec


# --- search --------------------------------------------------------------


def similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity. Inputs are normalised, so this is a dot product."""
    return float(np.dot(a, b))


def rank(
    query: np.ndarray,
    candidates: dict[int, np.ndarray],
    *,
    top_k: int | None = None,
    min_score: float | None = None,
) -> list[tuple[int, float]]:
    """Rank ``candidates`` by cosine similarity to ``query``, best first.

    Returns (id, score) pairs. Scoring every row is one matrix multiply, so
    this does not loop in Python.
    """
    if not candidates:
        return []

    ids = list(candidates.keys())
    matrix = np.vstack([candidates[i] for i in ids])
    scores = matrix @ query

    order = np.argsort(-scores)
    results = [(ids[i], float(scores[i])) for i in order]

    if min_score is not None:
        results = [r for r in results if r[1] >= min_score]
    if top_k is not None:
        results = results[:top_k]
    return results
