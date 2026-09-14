"""What the signed-in user is allowed to do, decided from the database only.

This is the authorization half of billing. services/billing.py *writes*
subscription state (from Stripe); this module *reads* it and answers two
questions for the rest of the app:

* Quotas   -- "may this user run another analysis?"  -> ``reserve_analysis``,
  ``reserve_cv_upload``, ``open_insight_session``
* Features -- "does this plan include X at all?"      -> ``require_feature``
  (no feature is Pro-only today; see services/plans.PLAN_FEATURES)

Nothing here trusts the browser. The frontend may *display* the plan (it
reads GET /api/billing/subscription), but every premium endpoint re-checks on
the server, so hiding or showing a button in the UI changes nothing about
what the API will actually do.

Why the refusal is HTTP 402
---------------------------
402 is "Payment Required". It tells the frontend "you are signed in and the
request was fine, but your plan does not cover it" -- different from 401 (not
signed in) and 403 (never allowed, whatever you pay). The frontend turns a 402
into an upgrade prompt. ``detail`` stays a plain string so the pages that
already print ``data.detail`` show a sensible message unchanged.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException
from sqlalchemy import text

from ai_job_intelligence.clock import utcnow
from ai_job_intelligence.models.billing import Subscription
from ai_job_intelligence.models.usage_event import (
    USAGE_ANALYSIS,
    USAGE_CV_UPLOAD,
    USAGE_INSIGHT_SESSION,
    UsageEvent,
)
from ai_job_intelligence.services.auth_dependency import get_current_user_id
from ai_job_intelligence.services.database import SessionLocal
from ai_job_intelligence.services.plans import (
    DEFAULT_PLAN,
    PLAN_FEATURES,
    PLAN_LIMITS,
    PlanLimits,
)

logger = logging.getLogger(__name__)

PAYMENT_REQUIRED = 402

# Stripe statuses that grant access. Everything else -- canceled, unpaid,
# incomplete, incomplete_expired, paused, and any status Stripe adds in future
# -- does not. This is "fail closed": an unrecognised state means no access.
#
# past_due is on the list deliberately. A renewal failed (expired card, say)
# and Stripe is retrying it over the next days. Cutting access at the first
# decline punishes people for their bank's hiccup; the UI shows a warning
# instead. If the retries all fail, Stripe moves the subscription to unpaid or
# canceled (your choice, under Settings > Billing > Subscriptions), the
# webhook records that, and access ends.
ENTITLING_STATUSES = frozenset({"active", "trialing", "past_due"})

# A safety net for lost webhooks. If a row still says "active" a week after
# its paid period ended, the renewal or cancellation event must have been
# missed (Stripe itself stops retrying a webhook after ~3 days). Such a row is
# not trusted. Normal renewals move current_period_end forward long before
# this matters.
STALE_SUBSCRIPTION_GRACE = timedelta(days=7)

# Advisory-lock namespace for per-user quota checks (see _lock_user_quota).
_QUOTA_LOCK_NAMESPACE = 7301


@dataclass(frozen=True)
class Entitlements:
    plan: str
    features: frozenset[str]
    limits: PlanLimits
    subscription: Subscription | None


def active_subscription(db, user_id: int) -> Subscription | None:
    """The subscription currently granting this user a paid plan, if any.

    A user who has never subscribed simply has no rows, and gets None.
    Normally there is at most one qualifying row; checkout refuses to start a
    second while one is active. If two ever exist, the one paid furthest into
    the future wins.
    """
    rows = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user_id,
            Subscription.status.in_(ENTITLING_STATUSES),
        )
        .order_by(Subscription.current_period_end.desc().nulls_last())
        .all()
    )
    now = utcnow()
    for row in rows:
        if row.plan not in PLAN_LIMITS:
            # Price not in the whitelist ("unknown"): grants nothing.
            continue
        if (
            row.current_period_end is not None
            and row.current_period_end + STALE_SUBSCRIPTION_GRACE < now
        ):
            logger.warning(
                "Subscription %s still says %s but its period ended on %s; "
                "ignoring it. Check that the Stripe webhook is being delivered.",
                row.stripe_subscription_id,
                row.status,
                row.current_period_end,
            )
            continue
        return row
    return None


def get_entitlements(db, user_id: int) -> Entitlements:
    sub = active_subscription(db, user_id)
    plan = sub.plan if sub else DEFAULT_PLAN
    return Entitlements(
        plan=plan,
        features=PLAN_FEATURES[plan],
        limits=PLAN_LIMITS[plan],
        subscription=sub,
    )


# --- Features --------------------------------------------------------------


def require_feature(feature: str):
    """A FastAPI dependency: the endpoint runs only if the plan includes it.

    Used as ``current_user_id: int = Depends(require_feature("..."))`` in
    place of ``Depends(get_current_user_id)``. It still authenticates first
    (401 for no/expired token), then checks the plan (402).
    """

    def dependency(current_user_id: int = Depends(get_current_user_id)) -> int:
        db = SessionLocal()
        try:
            if feature not in get_entitlements(db, current_user_id).features:
                raise HTTPException(
                    status_code=PAYMENT_REQUIRED,
                    detail="This feature is part of CareerLens Pro. "
                    "Upgrade on the pricing page to unlock it.",
                )
        finally:
            db.close()
        return current_user_id

    return dependency


# --- Quotas ----------------------------------------------------------------
#
# Every metered action follows the same four steps, in the transaction that
# performs the action:
#
#   1. lock   -- one request per user at a time (see _lock_user_quota)
#   2. count  -- this month's rows of that kind in usage_events
#   3. refuse -- 402 if the count has reached the plan's limit
#   4. record -- add a usage_events row; the caller's COMMIT saves it
#                together with the action, or its ROLLBACK drops both.

# Which PlanLimits field caps each kind of usage.
_LIMIT_FIELD = {
    USAGE_CV_UPLOAD: "cv_uploads_per_month",
    USAGE_ANALYSIS: "analyses_per_month",
    USAGE_INSIGHT_SESSION: "insight_sessions_per_month",
}

_LIMIT_MESSAGE = {
    USAGE_CV_UPLOAD: "You have uploaded {limit} CVs this month, the Free plan's "
    "allowance. Upgrade to Pro for unlimited uploads; the allowance resets on the 1st.",
    USAGE_ANALYSIS: "You have used all {limit} job-match analyses included in the "
    "Free plan this month. Upgrade to Pro for unlimited analyses; the allowance "
    "resets on the 1st.",
    USAGE_INSIGHT_SESSION: "You have used your {limit} Career Insights sessions for "
    "this month. Upgrade to Pro for unlimited insights; the allowance resets on the 1st.",
}

# How long one Career Insights session stays open after it starts.
INSIGHT_SESSION_LENGTH = timedelta(hours=24)


def month_start(now: datetime | None = None) -> datetime:
    """Midnight UTC on the 1st of the current month -- when quotas reset."""
    now = now or utcnow()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def next_month_start(now: datetime | None = None) -> datetime:
    start = month_start(now)
    return (start + timedelta(days=32)).replace(day=1)


def used_this_month(db, user_id: int, kind: str) -> int:
    return (
        db.query(UsageEvent)
        .filter(
            UsageEvent.user_id == user_id,
            UsageEvent.kind == kind,
            UsageEvent.created_at >= month_start(),
        )
        .count()
    )


def analyses_used_this_month(db, user_id: int) -> int:
    return used_this_month(db, user_id, USAGE_ANALYSIS)


def _limit_for(db, user_id: int, kind: str) -> int | None:
    limits = get_entitlements(db, user_id).limits
    return getattr(limits, _LIMIT_FIELD[kind])


def _lock_user_quota(db, user_id: int) -> None:
    """Serialise quota checks for one user until the transaction ends.

    Without this, two requests sent at the same moment by a Free user with 4
    of 5 analyses used would both count 4, both pass, and both save -- 6 of 5.
    The classic check-then-act race.

    ``pg_advisory_xact_lock`` takes a named lock that PostgreSQL releases by
    itself at COMMIT or ROLLBACK. The second request waits here until the
    first commits, then counts 5 and is refused. Other users are unaffected:
    the lock name includes the user id.
    """
    db.execute(
        text("SELECT pg_advisory_xact_lock(:ns, :uid)"),
        {"ns": _QUOTA_LOCK_NAMESPACE, "uid": user_id},
    )


def _refuse_if_used_up(db, user_id: int, kind: str) -> None:
    limit = _limit_for(db, user_id, kind)
    if limit is not None and used_this_month(db, user_id, kind) >= limit:
        raise HTTPException(
            status_code=PAYMENT_REQUIRED,
            detail=_LIMIT_MESSAGE[kind].format(limit=limit),
        )


def _reserve(db, user_id: int, kind: str) -> None:
    """Steps 1-4 above. The caller commits."""
    _lock_user_quota(db, user_id)
    _refuse_if_used_up(db, user_id, kind)
    db.add(UsageEvent(user_id=user_id, kind=kind))


# Fast, lock-free pre-checks: refuse *before* doing expensive work (storing
# and parsing a file, running an analysis). They decide nothing -- the
# reserve_* call just before saving is the check that counts.


def check_cv_quota(db, user_id: int) -> None:
    _refuse_if_used_up(db, user_id, USAGE_CV_UPLOAD)


def check_analysis_quota(db, user_id: int) -> None:
    _refuse_if_used_up(db, user_id, USAGE_ANALYSIS)


def reserve_cv_upload(db, user_id: int) -> None:
    """Count one CV upload, in the transaction that saves the CV."""
    _reserve(db, user_id, USAGE_CV_UPLOAD)


def reserve_analysis(db, user_id: int) -> None:
    """Count one analysis, in the transaction that saves the analysis.

    If saving the analysis fails and rolls back, the usage row disappears
    with it -- nobody is charged quota for an analysis they never got.
    """
    _reserve(db, user_id, USAGE_ANALYSIS)


def current_insight_session(db, user_id: int) -> UsageEvent | None:
    """The Career Insights session still open for this user, if any."""
    return (
        db.query(UsageEvent)
        .filter(
            UsageEvent.user_id == user_id,
            UsageEvent.kind == USAGE_INSIGHT_SESSION,
            UsageEvent.created_at > utcnow() - INSIGHT_SESSION_LENGTH,
        )
        .order_by(UsageEvent.created_at.desc())
        .first()
    )


def open_insight_session(db, user_id: int) -> None:
    """Allow one Career Insights request, starting a session if needed.

    Inside an open session (started less than 24 hours ago) this costs
    nothing. Otherwise it starts a new session, which uses one of the month's
    allowance, or answers 402 if none is left. The caller commits.

    The open-session check happens *after* taking the lock. The page asks for
    its data twice on first load in development (React's strict mode), and
    two browser tabs can ask at once; the second request waits for the
    first to commit, then finds its session and is free.
    """
    if _limit_for(db, user_id, USAGE_INSIGHT_SESSION) is None:
        return  # unlimited plan: nothing to count
    _lock_user_quota(db, user_id)
    if current_insight_session(db, user_id) is not None:
        return
    _refuse_if_used_up(db, user_id, USAGE_INSIGHT_SESSION)
    db.add(UsageEvent(user_id=user_id, kind=USAGE_INSIGHT_SESSION))


def usage_summary(db, user_id: int) -> dict:
    limits = get_entitlements(db, user_id).limits
    resets_at = next_month_start().isoformat() + "Z"

    def usage(kind: str) -> dict:
        return {
            "used": used_this_month(db, user_id, kind),
            "limit": getattr(limits, _LIMIT_FIELD[kind]),
            "resets_at": resets_at,
        }

    session = current_insight_session(db, user_id)
    insights = usage(USAGE_INSIGHT_SESSION)
    insights["session_expires_at"] = (
        (session.created_at + INSIGHT_SESSION_LENGTH).isoformat() + "Z"
        if session
        else None
    )
    return {
        "cv_uploads_this_month": usage(USAGE_CV_UPLOAD),
        "analyses_this_month": usage(USAGE_ANALYSIS),
        "insight_sessions_this_month": insights,
    }
