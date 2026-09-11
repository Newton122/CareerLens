"""Cached access to the structured profile parsed from a CV.

Parsing a CV is pure and deterministic but not free: it scans the whole
document for sections, runs the skill vocabulary over every token, and builds
several lists. Endpoints such as the employer candidate search used to redo
that work for every candidate on every request.

The parsed profile is therefore stored on the CV row at upload time. This
module is the single place that reads it back, rebuilding it transparently when
it is missing (rows created before the column existed) or stale (produced by an
older extractor).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

from ai_job_intelligence.models.cv import CV
from ai_job_intelligence.schemas import CandidateProfile
from ai_job_intelligence.services.ai_service import PROFILE_VERSION, analyze_cv_text

logger = logging.getLogger(__name__)


def build_profile(cv_text: str) -> CandidateProfile:
    """Parse CV text into a structured profile."""
    return analyze_cv_text(cv_text or "")


def _load_cached(cv: CV) -> CandidateProfile | None:
    """Return the stored profile if present and produced by this extractor."""
    if not cv.profile_json or cv.profile_version != PROFILE_VERSION:
        return None
    try:
        return CandidateProfile(**json.loads(cv.profile_json))
    except Exception:
        # A malformed or schema-drifted cache entry is not an error worth
        # failing a request over -- fall through and rebuild it.
        logger.warning("Discarding unreadable cached profile for CV %s", cv.id)
        return None


def store_profile(cv: CV, profile: CandidateProfile) -> None:
    """Attach a parsed profile to a CV row (caller commits)."""
    cv.profile_json = profile.model_dump_json()
    cv.profile_version = PROFILE_VERSION
    cv.profile_parsed_at = datetime.utcnow()


def get_candidate_profile(db, cv: CV) -> CandidateProfile:
    """Return the structured profile for ``cv``, parsing and caching if needed.

    Safe to call from read-only endpoints: if writing the backfill fails, the
    freshly parsed profile is still returned and the request succeeds.
    """
    cached = _load_cached(cv)
    if cached is not None:
        return cached

    profile = build_profile(cv.extracted_text)

    try:
        store_profile(cv, profile)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Could not cache parsed profile for CV %s", cv.id)

    return profile


def get_profiles_for_cvs(db, cvs: list[CV]) -> dict[int, CandidateProfile]:
    """Bulk variant: resolve profiles for many CVs with a single commit.

    Used by the employer candidate search, which would otherwise commit once
    per candidate while backfilling.
    """
    profiles: dict[int, CandidateProfile] = {}
    dirty = False

    for cv in cvs:
        cached = _load_cached(cv)
        if cached is None:
            cached = build_profile(cv.extracted_text)
            store_profile(cv, cached)
            dirty = True
        profiles[cv.id] = cached

    if dirty:
        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Could not cache parsed profiles during bulk read")

    return profiles
