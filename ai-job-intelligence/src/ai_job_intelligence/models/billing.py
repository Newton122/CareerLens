"""The local mirror of billing state that lives in Stripe.

Stripe is where money moves; this database is where the app decides what a
user may do. These tables are how the second learns about the first. They are
written **only** by the server -- by the webhook handler, or by the server
asking Stripe directly -- never from anything the browser sends. That is the
whole security model: a user cannot become Pro by editing a request, because
no request they can make writes to these tables.

Three tables, three jobs:

* ``billing_customers`` -- which Stripe Customer belongs to which user.
* ``subscriptions`` -- one row per Stripe Subscription, kept after it ends.
* ``stripe_events`` -- webhook events already processed (idempotency).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from ai_job_intelligence.clock import utcnow
from ai_job_intelligence.database import Base


class BillingCustomer(Base):
    """Links a CareerLens user to their Stripe Customer (``cus_...``).

    A Stripe Customer is created the first time a user starts checkout, before
    any subscription exists. It gets its own table, rather than living only on
    ``subscriptions``, so that someone who opens Checkout, closes the tab, and
    tries again next week reuses the same Customer instead of leaving a trail
    of duplicates in Stripe.

    ``user_id`` as the primary key is the database-level guarantee of exactly
    one Stripe Customer per user.
    """

    __tablename__ = "billing_customers"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    stripe_customer_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )


class Subscription(Base):
    """One Stripe Subscription (``sub_...``), as last reported by Stripe.

    A user who subscribes, cancels, and subscribes again gets two rows: Stripe
    creates a new Subscription each time, and keeping the old row preserves the
    history. Which row grants access is decided in services/entitlements.py.

    ``status`` and ``plan`` are stored as plain strings with no CHECK
    constraint, on purpose. This table *mirrors* Stripe. If Stripe introduces a
    new status, a constraint would make the webhook fail to save it -- and a
    failing webhook is retried by Stripe for days. Instead the mirror records
    whatever Stripe says, and the entitlement code only grants access for
    statuses it explicitly knows are good ("fail closed").
    """

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # "pro" | "enterprise", derived from the price via the whitelist in
    # services/plans.py -- or "unknown" for a price this app did not sell.
    plan: Mapped[str] = mapped_column(String(20), nullable=False)
    # Stripe's own status string: active, trialing, past_due, canceled,
    # unpaid, incomplete, incomplete_expired, paused.
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    stripe_customer_id: Mapped[str] = mapped_column(String(255), nullable=False)
    # Unique: the webhook upserts on this, so the same Stripe subscription can
    # never produce two rows no matter how many times its events arrive.
    stripe_subscription_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )
    stripe_price_id: Mapped[str] = mapped_column(String(255), nullable=False)
    # "month" | "year"
    billing_interval: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # The paid-for window. Access runs until current_period_end even after the
    # user cancels (cancel_at_period_end=True): they paid for that time.
    current_period_start: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    __table_args__ = (
        # The entitlement check runs on every premium request and asks
        # "does this user have a subscription in a good status?" -- exactly
        # the shape of this index.
        Index("ix_subscriptions_user_id_status", "user_id", "status"),
    )


class StripeEvent(Base):
    """A webhook event this server has already processed.

    Stripe delivers webhooks *at least once*: after a timeout, a network blip
    or a deploy, the same event (same ``evt_...`` id) can arrive again. The
    handler inserts the id here in the same database transaction as the change
    the event causes. So either both are saved or neither is, and a second
    delivery finds the id already present and does nothing.
    """

    __tablename__ = "stripe_events"

    # Stripe's event id is already globally unique; use it as the key.
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
