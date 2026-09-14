"""HTTP endpoints for billing: /api/billing/*.

A FastAPI ``APIRouter`` is a group of endpoints defined outside main.py and
attached there with ``app.include_router``. All of billing lives here, so the
whole payment surface of the API can be read in one file:

    GET  /api/billing/plans              public: plans, limits, live prices
    GET  /api/billing/subscription       my plan, status, usage
    POST /api/billing/checkout           start paying -> Stripe Checkout URL
    POST /api/billing/checkout/confirm   success page: sync my new checkout
    POST /api/billing/portal             manage/cancel -> Stripe portal URL
    POST /api/billing/webhook            Stripe -> us (signed, no login)

Notice what is missing: there is no endpoint that sets a plan. The only
writers of subscription state are the webhook and ``checkout/confirm``, and
both copy what *Stripe* reports.
"""
from __future__ import annotations

import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from ai_job_intelligence.config import BILLING_ENABLED, STRIPE_WEBHOOK_SECRET
from ai_job_intelligence.models.billing import BillingCustomer
from ai_job_intelligence.models.user import User
from ai_job_intelligence.models.user_profile import UserProfile
from ai_job_intelligence.schemas import CheckoutConfirmRequest, CheckoutRequest
from ai_job_intelligence.services import billing, entitlements
from ai_job_intelligence.services.auth_dependency import get_current_user_id
from ai_job_intelligence.services.database import SessionLocal
from ai_job_intelligence.services.plans import (
    PLAN_FEATURES,
    PLAN_LIMITS,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["billing"])


def _raise_http(exc: Exception) -> None:
    """Translate billing failures into HTTP errors the frontend can show.

    Stripe's own error text is logged, not returned: it can mention internal
    ids and configuration that users have no reason to see.
    """
    if isinstance(exc, billing.BillingNotConfigured):
        raise HTTPException(503, "Payments are not set up on this server yet.")
    if isinstance(exc, billing.BillingError):
        raise HTTPException(exc.status_code, str(exc))
    if isinstance(exc, stripe.StripeError):
        logger.error("Stripe API error: %s", exc)
        raise HTTPException(502, "The payment provider could not be reached. Please try again.")
    raise exc


def _subscription_view(db, user_id: int) -> dict:
    ent = entitlements.get_entitlements(db, user_id)
    sub = ent.subscription
    return {
        "plan": ent.plan,
        "features": sorted(ent.features),
        "status": sub.status if sub else None,
        "billing_interval": sub.billing_interval if sub else None,
        "current_period_end": (
            sub.current_period_end.isoformat() + "Z"
            if sub and sub.current_period_end
            else None
        ),
        "cancel_at_period_end": bool(sub and sub.cancel_at_period_end),
        # True when a renewal payment failed and Stripe is retrying.
        "payment_issue": bool(sub and sub.status == "past_due"),
        "has_billing_account": db.get(BillingCustomer, user_id) is not None,
        "billing_enabled": BILLING_ENABLED,
        "usage": entitlements.usage_summary(db, user_id),
    }


@router.get("/plans")
def get_plans() -> dict:
    """Public: what each plan includes, and the live prices from Stripe."""
    return {
        "billing_enabled": BILLING_ENABLED,
        "prices": billing.price_catalog(),
        "plans": {
            name: {
                "limits": {
                    "cv_uploads_per_month": PLAN_LIMITS[name].cv_uploads_per_month,
                    "analyses_per_month": PLAN_LIMITS[name].analyses_per_month,
                    "insight_sessions_per_month": PLAN_LIMITS[name].insight_sessions_per_month,
                },
                "features": sorted(PLAN_FEATURES[name]),
            }
            for name in PLAN_LIMITS
        },
    }


@router.get("/subscription")
def get_my_subscription(current_user_id: int = Depends(get_current_user_id)) -> dict:
    db = SessionLocal()
    try:
        return _subscription_view(db, current_user_id)
    finally:
        db.close()


@router.post("/checkout")
def start_checkout(
    payload: CheckoutRequest,
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    """Create a Stripe Checkout Session and return its URL.

    The user id comes from the verified login token, never from the body,
    and the price comes from the server's whitelist, never from the body.
    """
    db = SessionLocal()
    try:
        profile = db.get(UserProfile, current_user_id)
        if profile is not None and profile.role != "job_seeker":
            # Pro's features (CV analyses, Career Insights) are job-seeker
            # features; an employer paying for them would get nothing.
            raise HTTPException(
                403, "Pro is a job-seeker plan. For teams, contact us about Enterprise."
            )
        user = db.get(User, current_user_id)
        try:
            url = billing.create_checkout_session(
                db, user, payload.plan, payload.interval
            )
        except Exception as exc:  # noqa: BLE001 -- mapped in _raise_http
            db.rollback()
            _raise_http(exc)
        return {"url": url}
    finally:
        db.close()


@router.post("/checkout/confirm")
def confirm_checkout(
    payload: CheckoutConfirmRequest,
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    db = SessionLocal()
    try:
        try:
            billing.confirm_checkout_session(db, current_user_id, payload.session_id)
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            _raise_http(exc)
        return _subscription_view(db, current_user_id)
    finally:
        db.close()


@router.post("/portal")
def open_portal(current_user_id: int = Depends(get_current_user_id)) -> dict:
    db = SessionLocal()
    try:
        try:
            url = billing.create_portal_session(db, current_user_id)
        except Exception as exc:  # noqa: BLE001
            _raise_http(exc)
        return {"url": url}
    finally:
        db.close()


@router.post("/webhook")
async def stripe_webhook(request: Request) -> dict:
    """Receive an event from Stripe.

    No login here -- Stripe is not a user. Authenticity comes from the
    ``Stripe-Signature`` header instead: Stripe signs every delivery with
    HMAC-SHA256 over ``"<timestamp>.<raw body>"`` using the endpoint's
    signing secret (whsec_...), which only Stripe and this server know.
    ``construct_event`` recomputes that signature and compares. It also
    rejects a timestamp older than 5 minutes, so a captured request cannot
    be replayed later.

    Two details that break signature checks when done differently:

    * The signature covers the *exact bytes* Stripe sent. They must be read
      raw (``await request.body()``), not parsed into JSON and re-serialised
      -- re-serialising can reorder keys or change spacing, and one changed
      byte makes the signature fail.
    * This is ``async def`` only so it can await the raw body. The actual
      work (database, Stripe API) is blocking, so it runs in a worker thread
      and does not stall the server's event loop.

    Responses mean something to Stripe: 2xx = delivered, anything else =
    retry later (with backoff, for up to three days). A bad signature gets
    400 -- that request did not come from Stripe, and there's nothing to
    retry.
    """
    if not STRIPE_WEBHOOK_SECRET:
        # Never fall back to accepting unsigned events.
        raise HTTPException(503, "Webhook signing secret is not configured.")

    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    if not signature:
        raise HTTPException(400, "Missing Stripe-Signature header.")

    try:
        event = stripe.Webhook.construct_event(payload, signature, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(400, "Invalid payload.")
    except stripe.SignatureVerificationError:
        logger.warning("Rejected a webhook with an invalid Stripe signature")
        raise HTTPException(400, "Invalid signature.")

    event_data = event.to_dict()
    try:
        outcome = await run_in_threadpool(billing.process_event, event_data)
    except Exception:
        # Logged with the traceback; Stripe will retry the delivery.
        logger.exception("Failed to process Stripe event %s", event_data.get("id"))
        raise HTTPException(500, "Event processing failed; it will be retried.")

    logger.info("Stripe event %s (%s): %s", event_data.get("id"), event_data.get("type"), outcome)
    return {"received": True, "outcome": outcome}
