"""What each plan includes, and which Stripe prices are allowed to sell it.

This module is pure data and lookups: no database, no Stripe calls. Everything
that asks "what may a Pro user do?" or "which price is Pro yearly?" asks here,
so the answer is written down exactly once.

The price whitelist
-------------------
The browser asks for a plan by *name* -- ``{"plan": "pro", "interval": "year"}``
-- and never by Stripe price id. The server turns that name into a price id
using the table below, which is built from environment variables.

Why not just accept a price id from the browser? Because the request body is
entirely under the user's control. If the checkout endpoint passed a supplied
price id straight to Stripe, anyone could open dev tools and substitute a
different price from the same Stripe account -- a cheaper one, a test price,
a price for a different product. With a whitelist, the only prices that can
ever reach Stripe are the ones this server was configured with.

The same table is used in reverse by the webhook: a subscription whose price
is not in it is recorded as plan "unknown", which grants nothing.
"""
from __future__ import annotations

from dataclasses import dataclass

from ai_job_intelligence.config import (
    STRIPE_PRICE_PRO_MONTHLY,
    STRIPE_PRICE_PRO_YEARLY,
)

PLAN_FREE = "free"
PLAN_PRO = "pro"
PLAN_ENTERPRISE = "enterprise"
PLAN_UNKNOWN = "unknown"

INTERVAL_MONTH = "month"
INTERVAL_YEAR = "year"


@dataclass(frozen=True)
class PlanLimits:
    """Monthly caps for a plan (reset on the 1st, UTC). ``None`` = unlimited.

    * cv_uploads_per_month -- CVs uploaded this month. Deleting one does not
      give the upload back (it is counted in the usage ledger).
    * analyses_per_month -- job-match analyses (POST /api/analyze).
    * insight_sessions_per_month -- Career Insights *sessions*. A session
      starts when the page is first opened and lasts 24 hours; reopening or
      refreshing within that window is free. Counting page loads instead
      would let a refresh -- or React's development double-render -- use up
      the whole allowance in one visit. Advanced insights and career
      recommendations are both on that page, so one cap covers both.
    """

    cv_uploads_per_month: int | None
    analyses_per_month: int | None
    insight_sessions_per_month: int | None


PLAN_LIMITS: dict[str, PlanLimits] = {
    PLAN_FREE: PlanLimits(
        cv_uploads_per_month=2, analyses_per_month=5, insight_sessions_per_month=2
    ),
    PLAN_PRO: PlanLimits(None, None, None),
    PLAN_ENTERPRISE: PlanLimits(None, None, None),
}

# Features only paid plans get at all (checked by
# services/entitlements.require_feature). Empty for now: everything the app
# offers is metered for Free rather than withheld. Cover letter generation
# goes here when it is built.
PLAN_FEATURES: dict[str, frozenset[str]] = {
    PLAN_FREE: frozenset(),
    PLAN_PRO: frozenset(),
    PLAN_ENTERPRISE: frozenset(),
}

# Which plan a user with *no* qualifying subscription is on.
DEFAULT_PLAN = PLAN_FREE


def _price_table() -> dict[tuple[str, str], str]:
    """(plan, interval) -> Stripe price id, for every price configured.

    Only Pro is sold through self-serve Checkout. Enterprise is "contact us";
    if you later sell it through Stripe, add its prices here and nowhere else.
    """
    table = {
        (PLAN_PRO, INTERVAL_MONTH): STRIPE_PRICE_PRO_MONTHLY,
        (PLAN_PRO, INTERVAL_YEAR): STRIPE_PRICE_PRO_YEARLY,
    }
    return {key: price for key, price in table.items() if price}


def price_id_for(plan: str, interval: str) -> str | None:
    """The price to charge for ``plan`` billed every ``interval``, or None.

    None means "not something this server sells" -- the caller must refuse
    the request, never fall back to some other price.
    """
    return _price_table().get((plan, interval))


def plan_for_price(price_id: str | None) -> tuple[str, str | None]:
    """Reverse lookup: which (plan, interval) a Stripe price id stands for.

    An id not in the whitelist returns (PLAN_UNKNOWN, None). Such a
    subscription is still recorded -- the database mirrors Stripe -- but
    grants no features, because nobody decided what it should unlock.
    """
    for (plan, interval), known in _price_table().items():
        if price_id and price_id == known:
            return plan, interval
    return PLAN_UNKNOWN, None


def sellable_intervals() -> list[tuple[str, str, str]]:
    """Every (plan, interval, price_id) a user can currently check out."""
    return [(plan, interval, price) for (plan, interval), price in _price_table().items()]
