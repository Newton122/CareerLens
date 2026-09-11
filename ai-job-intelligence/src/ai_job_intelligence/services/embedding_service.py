from __future__ import annotations

import math
import re
from collections import Counter
from functools import lru_cache

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - optional heavy dependency
    SentenceTransformer = None

MODEL_NAME = "all-MiniLM-L6-v2"

model = None
if SentenceTransformer is not None:
    model = SentenceTransformer(MODEL_NAME)

_FALLBACK_DIM = 256


def _stable_hash(token: str) -> int:
    """Deterministic token hash.

    Python's built-in hash() is randomised per process (PYTHONHASHSEED), which
    would make the fallback embeddings differ between restarts and therefore
    make match scores irreproducible.
    """
    h = 2166136261
    for ch in token:
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h


def _fallback_embedding(text: str, dim: int = _FALLBACK_DIM) -> list[float]:
    """Deterministic lightweight embedding fallback using token counts."""
    words = re.findall(r"\w+", text.lower())
    counts = Counter(words)
    vec = [0.0] * dim
    for tok, cnt in counts.items():
        vec[_stable_hash(tok) % dim] += float(cnt)
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def create_embedding(text: str) -> list[float]:
    """Convert text into a semantic embedding."""
    if model is not None:
        emb = model.encode(text, normalize_embeddings=True)
        try:
            return emb.tolist()
        except Exception:
            return list(map(float, emb))

    return _fallback_embedding(text)


@lru_cache(maxsize=4096)
def _cached_embedding(text: str) -> tuple[float, ...]:
    return tuple(create_embedding(text))


def _encode_many(texts: list[str]) -> list[tuple[float, ...]]:
    """Embed a list of texts, reusing cached vectors where possible."""
    return [_cached_embedding(t) for t in texts]


def _dot(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return float(sum(x * y for x, y in zip(a, b)))


def calculate_similarity(text_a: str, text_b: str) -> float:
    """Cosine similarity between two pieces of text (vectors are normalised)."""
    if not text_a or not text_b:
        return 0.0
    return _dot(_cached_embedding(text_a), _cached_embedding(text_b))


def max_similarity(query: str, candidates: list[str]) -> float:
    """Highest similarity between ``query`` and any single ``candidates`` entry.

    Comparing a short skill name against one other short skill name is a
    meaningful cosine score. Comparing it against a whole concatenated CV is
    not -- the signal is drowned out by unrelated text -- which is why callers
    should match skill-to-skill rather than skill-to-document.
    """
    if not query or not candidates:
        return 0.0
    q = _cached_embedding(query)
    return max((_dot(q, c) for c in _encode_many(candidates)), default=0.0)
