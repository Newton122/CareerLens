"""Stripe subscriptions: checkout, the customer portal, and webhook sync.

How a payment turns into Pro access
-----------------------------------
1. The pricing page calls ``create_checkout_session`` (through
   POST /api/billing/checkout). The server picks the price from the
   whitelist, and Stripe returns a URL to a Stripe-hosted payment page.
2. The browser goes there. The card number is typed into *Stripe's* page, so
   it never touches this server or this database. (That is what keeps this
   app out of PCI card-data scope.)
3. Stripe charges the card and creates a Subscription.
4. Stripe sends signed webhook events to POST /api/billing/webhook.
   ``process_event`` verifies nothing is replayed, fetches the subscription's
   current state from Stripe, and saves it in ``subscriptions``.
5. services/entitlements.py reads that table on every premium request.

The browser is redirected back to the success page around step 3-4, but that
redirect grants nothing. Anyone can type a success URL into their address
bar. Only a verified webhook -- or the server asking Stripe itself, in
``confirm_checkout_session`` -- ever changes a subscription row.

The "re-fetch" rule
-------------------
Webhook events are not guaranteed to arrive in order, or only once. A
``customer.subscription.updated`` can arrive before the ``...created`` that
preceded it, and the snapshot inside an old event can be staler than one
already saved. So the payload of an event is used only to learn *which*
subscription changed; its current state is always fetched fresh from Stripe
(``sync_subscription``). Whatever order events arrive in, the row ends up
matching what Stripe says now.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import stripe
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from ai_job_intelligence.clock import utcnow
from ai_job_intelligence.config import (
    BILLING_ENABLED,
    FRONTEND_URL,
    STRIPE_SECRET_KEY,
)
from ai_job_intelligence.models.billing import (
    BillingCustomer,
    StripeEvent,
    Subscription,
)
from ai_job_intelligence.models.user import User
from ai_job_intelligence.services.database import SessionLocal
from ai_job_intelligence.services.entitlements import active_subscription
from ai_job_intelligence.services.plans import (
    PLAN_UNKNOWN,
    plan_for_price,
    price_id_for,
    sellable_intervals,
)

logger = logging.getLogger(__name__)

# Advisory-lock namespaces (see _lock). Distinct from the quota lock's.
_CUSTOMER_LOCK_NAMESPACE = 7302
_SUBSCRIPTION_LOCK_NAMESPACE = 7303

# Statuses after which Stripe will never charge this subscription again.
FINISHED_STATUSES = frozenset({"canceled", "incomplete_expired"})


class BillingNotConfigured(Exception):
    """Stripe keys or price ids are missing from the environment."""


class BillingError(Exception):
    """A billing request this server refuses, with an HTTP status to use."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


# --- The Stripe client -----------------------------------------------------

_client: stripe.StripeClient | None = None


def stripe_client() -> stripe.StripeClient:
    """The one StripeClient, created on first use.

    ``StripeClient`` is Stripe's current recommended interface: the key is
    held by this object instead of a module-wide ``stripe.api_key`` global.
    ``max_network_retries`` makes the SDK retry a failed call; Stripe
    attaches an idempotency key to those retries itself, so a retried
    "create" can never create twice.
    """
    global _client
    if not STRIPE_SECRET_KEY:
        raise BillingNotConfigured("STRIPE_SECRET_KEY is not set")
    if _client is None:
        _client = stripe.StripeClient(STRIPE_SECRET_KEY, max_network_retries=2)
    return _client


def _as_dict(obj: Any) -> dict:
    """Stripe objects -> plain dicts, so everything below works on plain data
    (and tests can hand in plain dicts)."""
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return dict(obj)


def _id_of(value: Any) -> str | None:
    """Stripe fields like ``customer`` hold either an id or, when expanded,
    the whole object. Return the id either way."""
    if value is None or isinstance(value, str):
        return value
    return value.get("id")


def _timestamp(value: int | None) -> datetime | None:
    """Stripe sends Unix seconds; the database stores naive UTC."""
    if value is None:
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc).replace(tzinfo=None)


def _lock(db, namespace: int, key: str | int) -> None:
    """Hold a PostgreSQL advisory lock until this transaction ends.

    ``hashtext`` turns a string key such as "sub_123" into the integer the
    lock function needs. Two transactions asking for the same (namespace,
    key) run one after the other; different keys never wait on each other.
    """
    db.execute(
        text("SELECT pg_advisory_xact_lock(:ns, hashtext(:key))"),
        {"ns": namespace, "key": str(key)},
    )


# --- Prices shown on the pricing page --------------------------------------

_CATALOG_TTL_SECONDS = 600
_catalog_cache: tuple[float, list[dict]] | None = None


def price_catalog() -> list[dict]:
    """The sellable prices, with amounts read from Stripe itself.

    The pricing page renders these numbers, so the amount a user sees is
    the amount Stripe will charge -- there is no second copy of "$29" in the
    code to drift out of date.

    It also checks the configuration: if STRIPE_PRICE_PRO_MONTHLY were
    accidentally set to the *yearly* price, the Monthly toggle would charge a
    year. A price whose billing interval does not match its slot, or that has
    been archived in Stripe, is left out (and logged), which also makes
    checkout refuse it.

    Cached for 10 minutes. A failure is not cached, so the next call retries.
    """
    global _catalog_cache
    if not BILLING_ENABLED:
        return []
    now = time.monotonic()
    if _catalog_cache and _catalog_cache[0] > now:
        return _catalog_cache[1]

    catalog: list[dict] = []
    try:
        for plan, interval, price_id in sellable_intervals():
            price = _as_dict(stripe_client().v1.prices.retrieve(price_id))
            recurring = price.get("recurring") or {}
            if not price.get("active") or recurring.get("interval") != interval:
                logger.error(
                    "Stripe price %s is configured as %s/%s but is %s, billed per %s. "
                    "Fix the STRIPE_PRICE_* variables.",
                    price_id,
                    plan,
                    interval,
                    "active" if price.get("active") else "archived",
                    recurring.get("interval"),
                )
                continue
            catalog.append(
                {
                    "plan": plan,
                    "interval": interval,
                    "unit_amount": price.get("unit_amount"),  # smallest unit: cents
                    "currency": price.get("currency"),
                }
            )
    except stripe.StripeError as exc:
        logger.error("Could not load prices from Stripe: %s", exc)
        return []

    _catalog_cache = (now + _CATALOG_TTL_SECONDS, catalog)
    return catalog


# --- Customers -------------------------------------------------------------


def get_or_create_customer(db, user: User) -> str:
    """This user's Stripe Customer id, creating the Customer on first use.

    Runs under a per-user lock so two quick clicks cannot create two
    Customers. The caller commits.
    """
    _lock(db, _CUSTOMER_LOCK_NAMESPACE, user.id)
    row = db.get(BillingCustomer, user.id)
    if row is not None:
        return row.stripe_customer_id

    customer = stripe_client().v1.customers.create(
        params={
            "email": user.email,
            # Recorded on Stripe's side too, so the Stripe dashboard shows
            # which CareerLens user a customer is.
            "metadata": {"user_id": str(user.id)},
        }
    )
    db.add(BillingCustomer(user_id=user.id, stripe_customer_id=customer.id))
    db.flush()
    return customer.id


def _forget_customer(db, user_id: int) -> None:
    """Drop a stored Customer id that Stripe no longer knows.

    Happens in test mode when you press "Delete all test data" in the Stripe
    dashboard: our row still points at a Customer that is gone.
    """
    db.query(BillingCustomer).filter(BillingCustomer.user_id == user_id).delete()
    db.flush()


def _is_missing_customer(exc: stripe.StripeError) -> bool:
    return (
        isinstance(exc, stripe.InvalidRequestError)
        and getattr(exc, "code", None) == "resource_missing"
        and getattr(exc, "param", None) == "customer"
    )


# --- Checkout --------------------------------------------------------------


def create_checkout_session(db, user: User, plan: str, interval: str) -> str:
    """Start paying for ``plan``; returns the Stripe Checkout URL.

    Refuses (rather than guessing) when:
    * the (plan, interval) pair is not in the whitelist, or its Stripe price
      failed the catalog check -- 400;
    * the user already has a subscription granting access -- 409. Changing
      interval or cancelling happens in the customer portal instead, which
      modifies the existing subscription rather than adding a second one.
    """
    if not BILLING_ENABLED:
        raise BillingNotConfigured("Stripe is not configured")

    price_id = price_id_for(plan, interval)
    offered = {(p["plan"], p["interval"]) for p in price_catalog()}
    if price_id is None or (plan, interval) not in offered:
        raise BillingError("That plan is not available right now.", 400)

    # Duplicate prevention, part 1: no second subscription while one is live.
    if active_subscription(db, user.id) is not None:
        raise BillingError(
            "You already have an active subscription. Manage it from the "
            "Billing page.",
            409,
        )

    for attempt in range(2):
        customer_id = get_or_create_customer(db, user)
        try:
            _expire_open_checkouts(customer_id)
            session = stripe_client().v1.checkout.sessions.create(
                params={
                    "mode": "subscription",
                    "customer": customer_id,
                    "line_items": [{"price": price_id, "quantity": 1}],
                    # Three places to find the user again later. The webhook
                    # uses the customer id first; these are the fallbacks.
                    "client_reference_id": str(user.id),
                    "metadata": {"user_id": str(user.id)},
                    "subscription_data": {"metadata": {"user_id": str(user.id)}},
                    # {CHECKOUT_SESSION_ID} is filled in by Stripe on redirect.
                    "success_url": f"{FRONTEND_URL}/billing?checkout=success"
                    "&session_id={CHECKOUT_SESSION_ID}",
                    "cancel_url": f"{FRONTEND_URL}/pricing?checkout=canceled",
                }
            )
            db.commit()  # keep the Customer mapping; releases the lock
            return session.url
        except stripe.StripeError as exc:
            if attempt == 0 and _is_missing_customer(exc):
                logger.warning(
                    "Stripe customer %s for user %s no longer exists; creating a new one",
                    customer_id,
                    user.id,
                )
                _forget_customer(db, user.id)
                continue
            db.rollback()
            raise
    raise BillingError("Could not start checkout.", 502)  # pragma: no cover


def _expire_open_checkouts(customer_id: str) -> None:
    """Duplicate prevention, part 2: at most one open Checkout per customer.

    Part 1 (the active-subscription check) cannot see a checkout that is open
    but not yet paid. Without this, a user could open Checkout in two tabs,
    pay in both, and end up with two subscriptions. Expiring the older
    session first means the earlier tab's payment page stops working.
    """
    sessions = stripe_client().v1.checkout.sessions.list(
        params={"customer": customer_id, "status": "open", "limit": 10}
    )
    for session in sessions.data:
        try:
            stripe_client().v1.checkout.sessions.expire(session.id)
        except stripe.StripeError as exc:
            # Most likely it completed a moment ago; the webhook handles it.
            logger.info("Could not expire checkout %s: %s", session.id, exc)


def confirm_checkout_session(db, user_id: int, session_id: str) -> Subscription | None:
    """Sync a just-finished checkout without waiting for the webhook.

    The success page calls this with the ``session_id`` from its URL. That id
    is only a hint: the session is fetched *from Stripe*, and must belong to
    this user (client_reference_id) or the request is refused as not found.
    Then exactly the same sync as the webhook runs. The worst anyone can do
    with a made-up or stolen id is ask the server to re-read Stripe.

    Why have it at all? Locally, webhooks only arrive while ``stripe listen``
    is running, and in production they can lag the redirect by a few seconds.
    This lets the success page show the new plan immediately either way.
    """
    session = _as_dict(stripe_client().v1.checkout.sessions.retrieve(session_id))
    if session.get("client_reference_id") != str(user_id):
        raise BillingError("Checkout session not found.", 404)
    subscription_id = _id_of(session.get("subscription"))
    if session.get("status") != "complete" or not subscription_id:
        return None  # not paid yet; the page keeps waiting
    row = sync_subscription(db, subscription_id)
    db.commit()
    return row


# --- Customer portal -------------------------------------------------------


def create_portal_session(db, user_id: int) -> str:
    """A link to Stripe's hosted billing portal for this user.

    The portal is where users cancel, switch monthly/yearly, update their
    card and download invoices. Whatever they change there reaches us the
    same way as everything else: as a webhook.

    One-time setup: in test mode, open Settings > Billing > Customer portal
    in the Stripe dashboard and press Save, or Stripe refuses to create
    portal sessions.
    """
    row = db.get(BillingCustomer, user_id)
    if row is None:
        raise BillingError("You don't have a billing account yet.", 404)
    session = stripe_client().v1.billing_portal.sessions.create(
        params={"customer": row.stripe_customer_id, "return_url": f"{FRONTEND_URL}/billing"}
    )
    return session.url


# --- Syncing subscription state --------------------------------------------


def _user_for_subscription(db, sub: dict) -> int | None:
    """Which CareerLens user a Stripe subscription belongs to.

    First by Customer (every checkout uses a Customer this server created and
    recorded). Failing that, by the ``user_id`` metadata this server set at
    checkout -- which then also records the Customer, so the portal works.
    """
    customer_id = _id_of(sub.get("customer"))
    row = (
        db.query(BillingCustomer)
        .filter(BillingCustomer.stripe_customer_id == customer_id)
        .one_or_none()
    )
    if row is not None:
        return row.user_id

    raw = (sub.get("metadata") or {}).get("user_id")
    if raw and raw.isdigit() and db.get(User, int(raw)) is not None:
        user_id = int(raw)
        if db.get(BillingCustomer, user_id) is None:
            db.add(BillingCustomer(user_id=user_id, stripe_customer_id=customer_id))
            db.flush()
        return user_id
    return None


def _primary_item(sub: dict) -> dict:
    """The subscription item carrying the plan's price.

    CareerLens sells one item per subscription. If there were several, the
    first one with a whitelisted price wins.
    """
    items = (sub.get("items") or {}).get("data") or []
    for item in items:
        if plan_for_price(_id_of(item.get("price")))[0] != PLAN_UNKNOWN:
            return item
    return items[0] if items else {}


def upsert_subscription(db, sub: dict) -> Subscription | None:
    """Save Stripe's view of one subscription. The caller commits.

    Uses INSERT ... ON CONFLICT (stripe_subscription_id) DO UPDATE: the first
    event for a subscription inserts its row, every later one updates that
    same row. Running it twice with the same data changes nothing, which is
    what makes it safe to call from every kind of event.

    Note the period dates come from the subscription *item*, not the
    subscription. Stripe moved them there in API version 2025-03-31, so
    older tutorials reading ``subscription.current_period_end`` get nothing.
    """
    user_id = _user_for_subscription(db, sub)
    if user_id is None:
        # Created outside this app (by hand in the dashboard, say). Recording
        # the event but not the subscription is the right outcome: retrying
        # would never make it resolvable.
        logger.error(
            "Stripe subscription %s (customer %s) matches no CareerLens user; not saved",
            sub.get("id"),
            _id_of(sub.get("customer")),
        )
        return None

    item = _primary_item(sub)
    price_id = _id_of(item.get("price")) or ""
    plan, interval = plan_for_price(price_id)
    if plan == PLAN_UNKNOWN:
        logger.error(
            "Subscription %s uses price %s, which is not in the price whitelist; "
            "it is saved but grants nothing",
            sub.get("id"),
            price_id,
        )

    now = utcnow()
    values = {
        "user_id": user_id,
        "plan": plan,
        "status": sub.get("status") or "unknown",
        "stripe_customer_id": _id_of(sub.get("customer")),
        "stripe_price_id": price_id,
        "billing_interval": interval,
        "current_period_start": _timestamp(item.get("current_period_start")),
        "current_period_end": _timestamp(item.get("current_period_end")),
        "cancel_at_period_end": bool(sub.get("cancel_at_period_end")),
        "canceled_at": _timestamp(sub.get("canceled_at")),
        "ended_at": _timestamp(sub.get("ended_at")),
        "updated_at": now,
    }
    statement = (
        pg_insert(Subscription)
        .values(stripe_subscription_id=sub["id"], created_at=now, **values)
        .on_conflict_do_update(index_elements=["stripe_subscription_id"], set_=values)
    )
    db.execute(statement)

    row = (
        db.query(Subscription)
        .filter(Subscription.stripe_subscription_id == sub["id"])
        .populate_existing()
        .one()
    )
    _warn_on_duplicate(db, row)
    return row


def _warn_on_duplicate(db, row: Subscription) -> None:
    """Flag a second live subscription for the same user.

    Checkout tries hard to prevent this (see create_checkout_session), so if
    it happens a human should look -- most likely refund one in the Stripe
    dashboard. It is logged rather than refused: this table records what
    Stripe says is true. Refusing to save it would not un-charge the card,
    and would make Stripe retry the webhook for days.
    """
    if row.status in FINISHED_STATUSES:
        return
    others = (
        db.query(Subscription.stripe_subscription_id)
        .filter(
            Subscription.user_id == row.user_id,
            Subscription.id != row.id,
            Subscription.status.notin_(FINISHED_STATUSES),
        )
        .all()
    )
    if others:
        logger.error(
            "User %s has more than one live subscription: %s and %s",
            row.user_id,
            row.stripe_subscription_id,
            ", ".join(s for (s,) in others),
        )


def sync_subscription(db, stripe_subscription_id: str) -> Subscription | None:
    """Fetch a subscription's *current* state from Stripe and save it.

    The lock makes two events for the same subscription, processed at the
    same moment by two workers, run one after the other. Without it, the one
    that fetched first could save last and overwrite newer state with older.
    """
    _lock(db, _SUBSCRIPTION_LOCK_NAMESPACE, stripe_subscription_id)
    sub = _as_dict(stripe_client().v1.subscriptions.retrieve(stripe_subscription_id))
    return upsert_subscription(db, sub)


# --- Webhook events --------------------------------------------------------


def subscription_id_from_event(event: dict) -> str | None:
    """Which subscription an event is about, or None if it isn't about one.

    Each event type keeps the id in a different place:

    * customer.subscription.*  -- the event object *is* the subscription.
    * invoice.*                -- ``parent.subscription_details.subscription``
      (API 2025-03-31 and later; it used to be ``invoice.subscription``).
    * checkout.session.*       -- ``subscription`` (subscription-mode only).
    """
    event_type = event.get("type") or ""
    obj = (event.get("data") or {}).get("object") or {}

    if event_type.startswith("customer.subscription."):
        return obj.get("id")
    if event_type.startswith("invoice."):
        parent = obj.get("parent") or {}
        details = parent.get("subscription_details") or {}
        return _id_of(details.get("subscription"))
    if event_type.startswith("checkout.session."):
        if obj.get("mode") != "subscription":
            return None
        return _id_of(obj.get("subscription"))
    return None


# The events worth subscribing to in the Stripe dashboard (or `stripe listen
# --events`). Anything else that arrives is recorded and ignored.
HANDLED_EVENT_TYPES = (
    "checkout.session.completed",       # first payment done
    "customer.subscription.created",
    "customer.subscription.updated",    # renewal, plan change, cancel scheduled
    "customer.subscription.deleted",    # subscription over -> back to Free
    "customer.subscription.paused",
    "customer.subscription.resumed",
    "invoice.paid",                     # renewal succeeded
    "invoice.payment_failed",           # renewal failed -> past_due
)


def process_event(event: dict) -> str:
    """Apply one *already signature-verified* webhook event.

    Returns "processed", "ignored" (not about a subscription) or
    "duplicate" (seen before). Raises on failure, which the endpoint turns
    into a 500 -- the signal for Stripe to deliver the event again later.

    Idempotency, step by step:
      1. INSERT the event id into stripe_events, ON CONFLICT DO NOTHING.
      2. No row inserted -> an earlier delivery already committed. Stop.
      3. Otherwise sync the subscription, in the same transaction.
      4. COMMIT: the event id and the state change are saved together.
    If step 3 fails, the rollback removes the event id too, so the retry is
    processed properly instead of being skipped as a duplicate.
    """
    db = SessionLocal()
    try:
        inserted = db.execute(
            pg_insert(StripeEvent)
            .values(id=event["id"], type=event.get("type") or "", processed_at=utcnow())
            .on_conflict_do_nothing(index_elements=["id"])
            .returning(StripeEvent.id)
        ).first()
        if inserted is None:
            db.rollback()
            logger.info("Stripe event %s already processed; skipping", event["id"])
            return "duplicate"

        subscription_id = subscription_id_from_event(event)
        if subscription_id is None:
            db.commit()
            return "ignored"

        sync_subscription(db, subscription_id)
        db.commit()
        return "processed"
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# --- Account deletion ------------------------------------------------------


def cancel_subscriptions_for_user(db, user_id: int) -> None:
    """Stop Stripe charging a user whose account is being deleted.

    Deleting our rows alone would leave the Stripe subscription running --
    and charging the card every month -- for an account that no longer
    exists. So the deletion calls Stripe first, and if Stripe cannot be
    reached the deletion is refused (the caller turns the exception into an
    error) rather than completed with a live subscription left behind.
    """
    live = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user_id,
            Subscription.status.notin_(FINISHED_STATUSES),
        )
        .all()
    )
    if not live:
        return
    for row in live:
        try:
            stripe_client().v1.subscriptions.cancel(row.stripe_subscription_id)
        except stripe.InvalidRequestError as exc:
            if getattr(exc, "code", None) == "resource_missing":
                continue  # already gone on Stripe's side
            raise
