"""Sentence embeddings: text in, 384 numbers out.

The model is all-MiniLM-L6-v2, run with ONNX Runtime rather than PyTorch.

Why ONNX Runtime
----------------
The same model used to run through sentence-transformers, which pulls in
PyTorch. That alone took the backend to ~570 MB of memory, over the 512 MB a
small Render instance has, and made every deploy install ~1.5 GB of packages.
ONNX Runtime executes the model's official ONNX export (published in the same
Hugging Face repository) at roughly 230 MB, with a far smaller install.

Why it is the *same* model, not an approximation
------------------------------------------------
sentence-transformers does three things around the network: tokenise with
truncation at 256 tokens, average the token vectors weighted by the attention
mask ("mean pooling"), and scale the result to length 1. ``_embed`` below does
exactly those three steps. Measured against sentence-transformers on the
project's own CVs and job texts, the largest difference in any vector
component was 2.4e-7 (floating-point rounding), so vectors stored before the
switch remain valid and every matching threshold keeps its meaning.

(A packaged alternative, fastembed, was tried first. It produced identical
vectors up to 128 tokens but different ones for longer texts -- and CVs are
long -- so it was rejected.)

The model is loaded on first use, and the download is cached in
``EMBEDDING_CACHE_DIR`` (default: ``ai-job-intelligence/.model_cache``).
Running this module directly pre-downloads it, which the Render build does so
the server never downloads at start-up:

    PYTHONPATH=src python -m ai_job_intelligence.services.embedding_service
"""
from __future__ import annotations

import logging
import math
import os
import re
import threading
from collections import Counter
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

# Download the model over plain HTTPS rather than Hugging Face's newer "Xet"
# transfer protocol. On a slow connection Xet was seen to stall indefinitely
# at 0 bytes while plain HTTPS kept going; for one 90 MB file its speed-ups
# don't matter, and a build that hangs does. Must be set before
# huggingface_hub is first imported (it reads the setting at import); set
# HF_HUB_DISABLE_XET=0 to override.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

MODEL_NAME = "all-MiniLM-L6-v2"
MODEL_REPO = f"sentence-transformers/{MODEL_NAME}"
# A fixed commit of the model repository, so the files -- and therefore every
# vector -- can never change underneath the ones stored in the database.
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
MAX_TOKENS = 256  # what the model was trained with; sentence-transformers' default

CACHE_DIR = Path(
    os.getenv("EMBEDDING_CACHE_DIR")
    or Path(__file__).resolve().parents[3] / ".model_cache"
)

_FALLBACK_DIM = 256

_lock = threading.Lock()
_session = None
_tokenizer = None
_input_names: set[str] = set()
_load_failed = False


def _model_file(filename: str) -> str:
    """Path to a model file, downloading it only if it isn't cached yet."""
    from huggingface_hub import hf_hub_download

    kwargs = dict(
        repo_id=MODEL_REPO,
        filename=filename,
        revision=MODEL_REVISION,
        cache_dir=str(CACHE_DIR),
    )
    try:
        # No network at all when the file is already here.
        return hf_hub_download(local_files_only=True, **kwargs)
    except Exception:
        return hf_hub_download(**kwargs)


def _load() -> bool:
    """Load the tokenizer and model once. False if they cannot be loaded."""
    global _session, _tokenizer, _input_names, _load_failed
    if _session is not None:
        return True
    if _load_failed:
        return False
    with _lock:
        if _session is not None:
            return True
        try:
            import onnxruntime as ort
            from tokenizers import Tokenizer

            tokenizer = Tokenizer.from_file(_model_file("tokenizer.json"))
            tokenizer.enable_truncation(max_length=MAX_TOKENS)
            tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")

            options = ort.SessionOptions()
            # One inference thread per request keeps memory flat and plays
            # well with the web server's own thread pool.
            options.intra_op_num_threads = 1
            session = ort.InferenceSession(
                _model_file("onnx/model.onnx"),
                sess_options=options,
                providers=["CPUExecutionProvider"],
            )
            _input_names = {i.name for i in session.get_inputs()}
            _tokenizer, _session = tokenizer, session
            logger.info("Loaded embedding model %s (ONNX Runtime)", MODEL_NAME)
            return True
        except Exception:
            _load_failed = True
            logger.exception(
                "Could not load the embedding model; using the simple "
                "word-count fallback, so semantic matching will be weak."
            )
            return False


def warm_up() -> None:
    """Load the model now rather than on the first request that needs it."""
    _load()


def _embed(texts: list[str]):
    """Mean-pooled, length-1 vectors for ``texts`` (numpy array, one row each)."""
    import numpy as np

    encodings = _tokenizer.encode_batch(texts)
    ids = np.array([e.ids for e in encodings], dtype=np.int64)
    mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
    feeds = {"input_ids": ids, "attention_mask": mask}
    if "token_type_ids" in _input_names:
        feeds["token_type_ids"] = np.zeros_like(ids)

    token_vectors = _session.run(None, feeds)[0]          # (texts, tokens, 384)
    weights = mask[..., None].astype(np.float32)          # ignore padding
    pooled = (token_vectors * weights).sum(axis=1) / np.clip(
        weights.sum(axis=1), 1e-9, None
    )
    norms = np.linalg.norm(pooled, axis=1, keepdims=True)
    return pooled / np.clip(norms, 1e-12, None)


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
    if _load():
        return _embed([text])[0].tolist()
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


if __name__ == "__main__":
    # Pre-download the model (used by the Render build command).
    logging.basicConfig(level=logging.INFO)
    if not _load():
        raise SystemExit("Embedding model could not be loaded")
    print(f"{MODEL_NAME} ready in {CACHE_DIR}")
