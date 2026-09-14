"""Subscriptions, webhooks and plan limits, through the real code path.

No request leaves the machine. ``FakeStripe`` stands in for Stripe's API:
it remembers customers, checkout sessions and subscriptions in memory, and
the test decides what state each subscription is in -- the way a real card
payment, a failed renewal or a cancellation would leave it.

Webhooks are signed exactly the way Stripe signs them (``_signed``), so the
real signature check in billing_routes.stripe_webhook runs on every one.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import sys
import time
import uuid
from datetime import timedelta
from types import SimpleNamespace

import pytest
from jose import jwt

from ai_job_intelligence.conftest import TEST_PASSWORD

WEBHOOK_SECRET = "whsec_careerlens_suite"  # matches conftest
MONTHLY = "price_test_pro_monthly"
YEARLY = "price_test_pro_yearly"

CV_TEXT = """Ada Example
Skills
Python, SQL, Docker, AWS, FastAPI
Experience
Software Engineer, 4 years building Python APIs with FastAPI and PostgreSQL
Education
BSc Computer Science
"""
JOB = {
    "job_title": "Backend Engineer",
    "company": "Acme",
    "job_description": "We need a Python engineer with FastAPI, SQL and Docker "
    "experience to build APIs. 3+ years of experience required.",
}


# --- A fake Stripe -----------------------------------------------------------


class FakeStripe:
    """The parts of ``stripe.StripeClient`` the app uses, in memory."""

    def __init__(self):
        self.customers: list[str] = []
        self.checkouts: dict[str, dict] = {}
        self.subscriptions: dict[str, dict] = {}
        self.expired: list[str] = []
        self.canceled: list[str] = []
        self.retrieve_calls = 0
        self.fail_retrieve = False
        self.prices = {
            MONTHLY: {"id": MONTHLY, "active": True, "unit_amount": 2900,
                      "currency": "usd", "recurring": {"interval": "month"}},
            YEARLY: {"id": YEARLY, "active": True, "unit_amount": 27600,
                     "currency": "usd", "recurring": {"interval": "year"}},
        }
        ns = SimpleNamespace
        self.v1 = ns(
            customers=ns(create=self._create_customer),
            prices=ns(retrieve=lambda price_id: dict(self.prices[price_id])),
            checkout=ns(sessions=ns(
                create=self._create_checkout,
                list=self._list_checkouts,
                expire=self._expire_checkout,
                retrieve=lambda sid: dict(self.checkouts[sid]),
            )),
            subscriptions=ns(retrieve=self._retrieve_sub, cancel=self._cancel_sub),
            billing_portal=ns(sessions=ns(
                create=lambda params: ns(url=f"https://billing.stripe.test/{params['customer']}")
            )),
        )

    def _create_customer(self, params):
        cid = f"cus_{uuid.uuid4().hex[:10]}"
        self.customers.append(cid)
        return SimpleNamespace(id=cid)

    def _create_checkout(self, params):
        sid = f"cs_test_{uuid.uuid4().hex[:12]}"
        self.checkouts[sid] = {**params, "id": sid, "status": "open", "subscription": None}
        return SimpleNamespace(id=sid, url=f"https://checkout.stripe.test/{sid}")

    def _list_checkouts(self, params):
        data = [
            SimpleNamespace(id=s["id"]) for s in self.checkouts.values()
            if s["customer"] == params["customer"] and s["status"] == "open"
        ]
        return SimpleNamespace(data=data)

    def _expire_checkout(self, sid):
        self.checkouts[sid]["status"] = "expired"
        self.expired.append(sid)

    def _retrieve_sub(self, sub_id):
        self.retrieve_calls += 1
        if self.fail_retrieve:
            raise RuntimeError("Stripe is down")
        return json.loads(json.dumps(self.subscriptions[sub_id]))  # a fresh copy

    def _cancel_sub(self, sub_id):
        self.canceled.append(sub_id)
        self.subscriptions[sub_id]["status"] = "canceled"

    # What a customer does on Stripe's pages:

    def pay(self, session_id, status="active"):
        """Complete a checkout: the card is charged, a subscription exists."""
        session = self.checkouts[session_id]
        price = session["line_items"][0]["price"]
        now = int(time.time())
        days = 365 if price == YEARLY else 30
        sub_id = f"sub_{uuid.uuid4().hex[:12]}"
        self.subscriptions[sub_id] = {
            "id": sub_id,
            "object": "subscription",
            "customer": session["customer"],
            "status": status,
            "cancel_at_period_end": False,
            "canceled_at": None,
            "ended_at": None,
            "metadata": session["subscription_data"]["metadata"],
            "items": {"data": [{
                "price": {"id": price},
                "current_period_start": now,
                "current_period_end": now + days * 86400,
            }]},
        }
        session.update(status="complete", subscription=sub_id)
        return sub_id


@pytest.fixture
def stripe_fake(app_module, monkeypatch):
    fake = FakeStripe()
    monkeypatch.setattr(app_module.billing, "stripe_client", lambda: fake)
    monkeypatch.setattr(app_module.billing, "_catalog_cache", None)
    return fake


# --- Helpers -----------------------------------------------------------------


def _register(client, role="job_seeker") -> dict:
    email = f"billing-{uuid.uuid4().hex[:10]}@test.com"
    r = client.post(
        "/api/auth/register",
        json={"email": email, "password": TEST_PASSWORD, "name": "B", "role": role},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _signed(event: dict, secret: str = WEBHOOK_SECRET) -> tuple[bytes, dict]:
    """Sign an event the way Stripe does.

    Header: ``t=<unix time>,v1=<hex HMAC-SHA256 of "<t>.<raw body>">``. The
    server recomputes the HMAC with its own copy of the secret; only a sender
    who knows the secret can produce a match.
    """
    body = json.dumps(event).encode()
    t = int(time.time())
    mac = hmac.new(secret.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    return body, {"Stripe-Signature": f"t={t},v1={mac}", "Content-Type": "application/json"}


def _event(event_type: str, obj: dict, event_id: str | None = None) -> dict:
    return {
        "id": event_id or f"evt_{uuid.uuid4().hex[:14]}",
        "object": "event",
        "type": event_type,
        "data": {"object": obj},
    }


def _deliver(client, event: dict):
    body, headers = _signed(event)
    return client.post("/api/billing/webhook", content=body, headers=headers)


def _subscription_event(fake, sub_id, event_type="customer.subscription.updated"):
    """An event carrying a snapshot of the subscription as Stripe has it now."""
    return _event(event_type, json.loads(json.dumps(fake.subscriptions[sub_id])))


def _user_id(headers) -> int:
    return int(jwt.get_unverified_claims(headers["Authorization"].split()[1])["sub"])


def _plan(client, headers) -> dict:
    r = client.get("/api/billing/subscription", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def _checkout(client, headers, interval="month") -> str:
    r = client.post(
        "/api/billing/checkout", json={"plan": "pro", "interval": interval}, headers=headers
    )
    assert r.status_code == 200, r.text
    return r.json()["url"].rsplit("/", 1)[-1]  # the session id


def _subscribe(client, fake, headers, interval="month") -> str:
    """Full happy path: checkout, pay, webhook. Returns the subscription id."""
    session_id = _checkout(client, headers, interval)
    sub_id = fake.pay(session_id)
    r = _deliver(client, _event("checkout.session.completed", {
        "id": session_id, "object": "checkout.session", "mode": "subscription",
        "subscription": sub_id, "customer": fake.checkouts[session_id]["customer"],
    }))
    assert r.status_code == 200, r.text
    return sub_id


def _upload(client, headers, name="cv.txt"):
    return client.post(
        "/api/upload-cv", files={"file": (name, CV_TEXT, "text/plain")}, headers=headers
    )


# --- Configuration ------------------------------------------------------------


def test_live_stripe_keys_are_refused(app_module, monkeypatch):
    """Test mode only: a live key must stop the server from starting."""
    config = sys.modules["ai_job_intelligence.config"]
    for key in ("sk_live_abc123", "rk_live_abc123", "not-a-stripe-key"):
        monkeypatch.setenv("STRIPE_SECRET_KEY", key)
        with pytest.raises(RuntimeError):
            config._resolve_stripe_secret_key()
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_abc123")
    assert config._resolve_stripe_secret_key() == "sk_test_abc123"


def test_plans_show_prices_read_from_stripe(client, stripe_fake):
    body = client.get("/api/billing/plans").json()
    amounts = {(p["interval"], p["unit_amount"]) for p in body["prices"]}
    assert amounts == {("month", 2900), ("year", 27600)}
    assert body["plans"]["free"]["limits"] == {
        "cv_uploads_per_month": 2, "analyses_per_month": 5, "insight_sessions_per_month": 2
    }
    assert set(body["plans"]["pro"]["limits"].values()) == {None}


def test_a_price_in_the_wrong_slot_is_not_sold(client, stripe_fake):
    """STRIPE_PRICE_PRO_MONTHLY pointing at a yearly price would make the
    Monthly toggle charge for a year. That price must be withheld."""
    stripe_fake.prices[MONTHLY]["recurring"]["interval"] = "year"
    body = client.get("/api/billing/plans").json()
    assert [p["interval"] for p in body["prices"]] == ["year"]

    r = client.post("/api/billing/checkout", json={"plan": "pro", "interval": "month"},
                    headers=_register(client))
    assert r.status_code == 400


# --- Never trusting the browser ------------------------------------------------


def test_a_new_user_is_on_the_free_plan(client):
    body = _plan(client, _register(client))
    assert body["plan"] == "free"
    assert body["status"] is None
    assert body["usage"]["cv_uploads_this_month"]["limit"] == 2
    assert body["usage"]["analyses_this_month"]["limit"] == 5
    assert body["usage"]["insight_sessions_this_month"]["limit"] == 2


@pytest.mark.parametrize("payload", [
    {"plan": "pro", "interval": "month", "price_id": "price_cheap"},  # smuggled price
    {"plan": "enterprise", "interval": "month"},                       # not self-serve
    {"plan": "pro", "interval": "week"},                               # no such interval
    {"price_id": MONTHLY},                                             # price instead of plan
])
def test_checkout_only_accepts_whitelisted_plan_names(client, stripe_fake, payload):
    r = client.post("/api/billing/checkout", json=payload, headers=_register(client))
    assert r.status_code == 422
    assert stripe_fake.checkouts == {}


def test_checkout_charges_the_server_chosen_price(client, stripe_fake):
    headers = _register(client)
    session_id = _checkout(client, headers, "year")
    session = stripe_fake.checkouts[session_id]
    assert session["line_items"] == [{"price": YEARLY, "quantity": 1}]
    assert session["mode"] == "subscription"
    assert session["success_url"].endswith("session_id={CHECKOUT_SESSION_ID}")


def test_profile_updates_cannot_set_a_plan(client):
    headers = _register(client)
    client.put("/api/profile", json={"name": "x", "plan": "pro", "status": "active"},
               headers=headers)
    assert _plan(client, headers)["plan"] == "free"


def test_reaching_the_success_page_grants_nothing(client, stripe_fake):
    """Paying and being redirected back is not enough by itself: until the
    webhook (or a server-side check with Stripe) confirms it, still Free."""
    headers = _register(client)
    stripe_fake.pay(_checkout(client, headers))
    body = _plan(client, headers)
    assert body["plan"] == "free"
    assert body["usage"]["cv_uploads_this_month"]["limit"] == 2


def test_employers_cannot_buy_the_job_seeker_plan(client, stripe_fake):
    r = client.post("/api/billing/checkout", json={"plan": "pro", "interval": "month"},
                    headers=_register(client, role="employer"))
    assert r.status_code == 403


# --- Webhook authenticity ------------------------------------------------------


def test_unsigned_or_forged_webhooks_are_rejected(client, stripe_fake):
    headers = _register(client)
    session_id = _checkout(client, headers)
    sub_id = stripe_fake.pay(session_id)
    event = _subscription_event(stripe_fake, sub_id)

    body, good_headers = _signed(event)
    # No signature at all.
    assert client.post("/api/billing/webhook", content=body,
                       headers={"Content-Type": "application/json"}).status_code == 400
    # Signed with the wrong secret (an attacker's guess).
    forged_body, forged_headers = _signed(event, secret="whsec_attacker")
    assert client.post("/api/billing/webhook", content=forged_body,
                       headers=forged_headers).status_code == 400
    # A real signature, but the body was altered after signing.
    tampered = body.replace(b'"active"', b'"trialing"')
    assert client.post("/api/billing/webhook", content=tampered,
                       headers=good_headers).status_code == 400

    assert _plan(client, headers)["plan"] == "free"


def test_a_replayed_old_webhook_is_rejected(client, stripe_fake):
    """The signed timestamp must be recent, so a captured request can't be
    re-sent next week."""
    event = _event("customer.subscription.updated", {"id": "sub_x"})
    body = json.dumps(event).encode()
    t = int(time.time()) - 3600
    mac = hmac.new(WEBHOOK_SECRET.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    r = client.post("/api/billing/webhook", content=body,
                    headers={"Stripe-Signature": f"t={t},v1={mac}"})
    assert r.status_code == 400


# --- The subscription lifecycle ------------------------------------------------


def test_payment_then_webhook_makes_the_user_pro(client, stripe_fake):
    headers = _register(client)
    assert _plan(client, headers)["usage"]["analyses_this_month"]["limit"] == 5

    _subscribe(client, stripe_fake, headers, interval="year")

    body = _plan(client, headers)
    assert body["plan"] == "pro"
    assert body["status"] == "active"
    assert body["billing_interval"] == "year"
    assert all(u["limit"] is None for u in body["usage"].values())


def test_the_same_event_delivered_twice_is_processed_once(client, stripe_fake):
    headers = _register(client)
    sub_id = stripe_fake.pay(_checkout(client, headers))
    event = _subscription_event(stripe_fake, sub_id, "customer.subscription.created")

    first = _deliver(client, event)
    calls = stripe_fake.retrieve_calls
    second = _deliver(client, event)

    assert first.json()["outcome"] == "processed"
    assert second.json()["outcome"] == "duplicate"
    assert stripe_fake.retrieve_calls == calls  # the duplicate did no work


def test_events_arriving_out_of_order_still_end_in_stripes_current_state(
    client, stripe_fake
):
    """The event payload is only used to learn *which* subscription changed.
    Here a stale "created" (saying active) arrives after the subscription was
    already canceled; the row must say canceled, because that is what Stripe
    says now."""
    headers = _register(client)
    sub_id = _subscribe(client, stripe_fake, headers)
    stale = _subscription_event(stripe_fake, sub_id, "customer.subscription.created")

    stripe_fake.subscriptions[sub_id]["status"] = "canceled"
    _deliver(client, _subscription_event(stripe_fake, sub_id, "customer.subscription.deleted"))
    _deliver(client, stale)  # late, and wrong

    assert _plan(client, headers)["plan"] == "free"


def test_a_failed_renewal_keeps_access_while_stripe_retries(client, stripe_fake):
    headers = _register(client)
    sub_id = _subscribe(client, stripe_fake, headers)

    stripe_fake.subscriptions[sub_id]["status"] = "past_due"
    _deliver(client, _event("invoice.payment_failed", {
        "id": "in_1", "object": "invoice",
        "parent": {"subscription_details": {"subscription": sub_id}},
    }))
    body = _plan(client, headers)
    assert body["plan"] == "pro"
    assert body["payment_issue"] is True

    # Retries exhausted: Stripe marks it unpaid -> access ends.
    stripe_fake.subscriptions[sub_id]["status"] = "unpaid"
    _deliver(client, _subscription_event(stripe_fake, sub_id))
    assert _plan(client, headers)["plan"] == "free"


def test_cancelling_keeps_access_until_the_paid_period_ends(client, stripe_fake):
    headers = _register(client)
    sub_id = _subscribe(client, stripe_fake, headers)

    # The user clicks "Cancel" in the portal: Stripe schedules the end.
    stripe_fake.subscriptions[sub_id]["cancel_at_period_end"] = True
    _deliver(client, _subscription_event(stripe_fake, sub_id))
    body = _plan(client, headers)
    assert body["plan"] == "pro"
    assert body["cancel_at_period_end"] is True

    # The period ends: Stripe deletes the subscription.
    stripe_fake.subscriptions[sub_id]["status"] = "canceled"
    _deliver(client, _subscription_event(stripe_fake, sub_id, "customer.subscription.deleted"))
    assert _plan(client, headers)["plan"] == "free"


def test_renewal_moves_the_period_forward(client, stripe_fake):
    headers = _register(client)
    sub_id = _subscribe(client, stripe_fake, headers)
    before = _plan(client, headers)["current_period_end"]

    item = stripe_fake.subscriptions[sub_id]["items"]["data"][0]
    item["current_period_start"] = item["current_period_end"]
    item["current_period_end"] += 30 * 86400
    _deliver(client, _event("invoice.paid", {
        "id": "in_2", "object": "invoice",
        "parent": {"subscription_details": {"subscription": sub_id}},
    }))
    assert _plan(client, headers)["current_period_end"] > before


def test_a_failed_webhook_is_retried_not_lost(client, stripe_fake):
    """If processing fails, the event must not be marked as done -- the 500
    tells Stripe to send it again, and the retry must then work."""
    headers = _register(client)
    sub_id = stripe_fake.pay(_checkout(client, headers))
    event = _subscription_event(stripe_fake, sub_id, "customer.subscription.created")

    stripe_fake.fail_retrieve = True
    assert _deliver(client, event).status_code == 500
    assert _plan(client, headers)["plan"] == "free"

    stripe_fake.fail_retrieve = False
    retry = _deliver(client, event)
    assert retry.json()["outcome"] == "processed"
    assert _plan(client, headers)["plan"] == "pro"


def test_a_price_outside_the_whitelist_grants_nothing(client, stripe_fake):
    headers = _register(client)
    sub_id = stripe_fake.pay(_checkout(client, headers))
    stripe_fake.subscriptions[sub_id]["items"]["data"][0]["price"]["id"] = "price_mystery"
    _deliver(client, _subscription_event(stripe_fake, sub_id))
    assert _plan(client, headers)["plan"] == "free"


def test_a_subscription_left_active_long_after_its_period_is_distrusted(
    client, stripe_fake
):
    """Safety net for lost webhooks: still "active" a week past the end of
    the paid period means we missed the cancellation."""
    headers = _register(client)
    sub_id = _subscribe(client, stripe_fake, headers)
    item = stripe_fake.subscriptions[sub_id]["items"]["data"][0]
    item["current_period_end"] = int(time.time()) - 8 * 86400
    _deliver(client, _subscription_event(stripe_fake, sub_id))
    assert _plan(client, headers)["plan"] == "free"


# --- Checkout guard rails --------------------------------------------------------


def test_checkout_is_refused_while_already_subscribed(client, stripe_fake):
    headers = _register(client)
    _subscribe(client, stripe_fake, headers)
    r = client.post("/api/billing/checkout", json={"plan": "pro", "interval": "year"},
                    headers=headers)
    assert r.status_code == 409


def test_a_second_checkout_reuses_the_customer_and_closes_the_first(client, stripe_fake):
    """Two tabs, two clicks: one Stripe customer, and only one open checkout,
    so the user cannot pay twice."""
    headers = _register(client)
    first = _checkout(client, headers)
    second = _checkout(client, headers)
    assert len(stripe_fake.customers) == 1
    assert stripe_fake.checkouts[first]["customer"] == stripe_fake.checkouts[second]["customer"]
    assert stripe_fake.expired == [first]
    assert stripe_fake.checkouts[second]["status"] == "open"


def test_confirm_syncs_the_users_own_checkout_without_waiting(client, stripe_fake):
    headers = _register(client)
    session_id = _checkout(client, headers)
    stripe_fake.pay(session_id)
    r = client.post("/api/billing/checkout/confirm", json={"session_id": session_id},
                    headers=headers)
    assert r.status_code == 200
    assert r.json()["plan"] == "pro"


def test_confirm_refuses_someone_elses_checkout(client, stripe_fake):
    owner, other = _register(client), _register(client)
    session_id = _checkout(client, owner)
    stripe_fake.pay(session_id)
    r = client.post("/api/billing/checkout/confirm", json={"session_id": session_id},
                    headers=other)
    assert r.status_code == 404
    assert _plan(client, other)["plan"] == "free"


def test_confirm_before_payment_changes_nothing(client, stripe_fake):
    headers = _register(client)
    session_id = _checkout(client, headers)  # opened, never paid
    r = client.post("/api/billing/checkout/confirm", json={"session_id": session_id},
                    headers=headers)
    assert r.status_code == 200
    assert r.json()["plan"] == "free"


def test_portal_needs_a_billing_account(client, stripe_fake):
    headers = _register(client)
    assert client.post("/api/billing/portal", headers=headers).status_code == 404
    _checkout(client, headers)  # creates the Stripe customer
    r = client.post("/api/billing/portal", headers=headers)
    assert r.status_code == 200
    assert r.json()["url"].startswith("https://billing.stripe.test/cus_")


# --- Plan limits -----------------------------------------------------------------


def test_free_plan_allows_two_cv_uploads_a_month_and_deleting_does_not_refund(client):
    headers = _register(client)
    assert _upload(client, headers, "first.txt").status_code == 200
    assert _upload(client, headers, "second.txt").status_code == 200
    third = _upload(client, headers, "third.txt")
    assert third.status_code == 402
    assert "uploaded 2 CVs this month" in third.json()["detail"]
    assert len(client.get("/api/cvs", headers=headers).json()) == 2

    # Deleting every CV must not hand the month's uploads back.
    assert client.post("/api/reset-data", headers=headers).status_code == 200
    assert client.get("/api/cvs", headers=headers).json() == []
    assert _upload(client, headers, "fourth.txt").status_code == 402
    assert _plan(client, headers)["usage"]["cv_uploads_this_month"]["used"] == 2


def test_free_plan_allows_five_analyses_a_month_and_deleting_does_not_refund(client):
    headers = _register(client)
    cv_id = int(_upload(client, headers).json()["cv_id"])
    ids = []
    for _ in range(5):
        r = client.post("/api/analyze", json={"cv_id": cv_id, **JOB}, headers=headers)
        assert r.status_code == 200, r.text
        ids.append(r.json()["analysis_id"])

    assert client.post("/api/analyze", json={"cv_id": cv_id, **JOB},
                       headers=headers).status_code == 402

    # Deleting past analyses must not hand the allowance back.
    client.delete(f"/api/analyses/{ids[0]}", headers=headers)
    assert client.post("/api/analyze", json={"cv_id": cv_id, **JOB},
                       headers=headers).status_code == 402
    assert _plan(client, headers)["usage"]["analyses_this_month"]["used"] == 5


def test_pro_removes_the_limits(client, stripe_fake):
    headers = _register(client)
    _subscribe(client, stripe_fake, headers)
    for name in ("a.txt", "b.txt", "c.txt"):
        assert _upload(client, headers, name).status_code == 200
    cv_id = int(client.get("/api/cvs", headers=headers).json()[0]["id"])
    for _ in range(6):
        assert client.post("/api/analyze", json={"cv_id": cv_id, **JOB},
                           headers=headers).status_code == 200


def test_after_downgrading_existing_cvs_stay_but_no_new_ones(client, stripe_fake):
    headers = _register(client)
    sub_id = _subscribe(client, stripe_fake, headers)
    _upload(client, headers, "a.txt")
    _upload(client, headers, "b.txt")

    stripe_fake.subscriptions[sub_id]["status"] = "canceled"
    _deliver(client, _subscription_event(stripe_fake, sub_id, "customer.subscription.deleted"))

    # Both CVs stay; and the two uploaded this month already fill the Free
    # allowance, so a third is refused.
    assert len(client.get("/api/cvs", headers=headers).json()) == 2
    assert _upload(client, headers, "c.txt").status_code == 402


# --- Career Insights sessions ---------------------------------------------------


def _insights(client, headers):
    return client.get("/api/career-insights", headers=headers)


def _sessions(client, headers) -> dict:
    return _plan(client, headers)["usage"]["insight_sessions_this_month"]


def test_free_plan_gets_two_insight_sessions_and_refreshing_is_free(
    client, app_module, monkeypatch
):
    headers = _register(client)
    _upload(client, headers)

    # Opening the page, then refreshing it twice: one session, not three.
    for _ in range(3):
        assert _insights(client, headers).status_code == 200
    assert _sessions(client, headers)["used"] == 1
    assert _sessions(client, headers)["session_expires_at"] is not None

    # "A day later": with a zero-length session every request needs a new one.
    monkeypatch.setattr(app_module.entitlements, "INSIGHT_SESSION_LENGTH", timedelta(0))
    assert _insights(client, headers).status_code == 200   # session 2 of 2
    refused = _insights(client, headers)
    assert refused.status_code == 402
    assert "Career Insights sessions" in refused.json()["detail"]
    assert _sessions(client, headers)["used"] == 2


def test_opening_insights_without_a_cv_uses_no_session(client):
    headers = _register(client)
    body = _insights(client, headers).json()
    assert body["market_value"] == "Upload your CV"
    assert _sessions(client, headers)["used"] == 0


def test_pro_insights_are_unlimited(client, stripe_fake, app_module, monkeypatch):
    headers = _register(client)
    _subscribe(client, stripe_fake, headers)
    _upload(client, headers)
    monkeypatch.setattr(app_module.entitlements, "INSIGHT_SESSION_LENGTH", timedelta(0))
    for _ in range(4):
        assert _insights(client, headers).status_code == 200
    assert _sessions(client, headers)["used"] == 0


def test_two_requests_starting_a_session_together_use_only_one(client, app_module):
    """First load in development fetches twice at once (React strict mode).
    The second request must wait for the first, then find its session."""
    import threading

    entitlements = app_module.entitlements
    user_id = _user_id(_register(client))

    a = app_module.SessionLocal()
    entitlements.open_insight_session(a, user_id)  # started, not committed

    def request_b():
        b = app_module.SessionLocal()
        try:
            entitlements.open_insight_session(b, user_id)
            b.commit()
        finally:
            b.close()

    thread = threading.Thread(target=request_b)
    thread.start()
    thread.join(timeout=1.0)
    assert thread.is_alive(), "B should be waiting on A's lock"
    a.commit()
    a.close()
    thread.join(timeout=10)

    check = app_module.SessionLocal()
    try:
        assert entitlements.used_this_month(check, user_id, "insight_session") == 1
    finally:
        check.close()


# --- Account deletion --------------------------------------------------------------


def test_deleting_a_subscriber_cancels_their_stripe_subscription(client, stripe_fake, admin):
    headers = _register(client)
    sub_id = _subscribe(client, stripe_fake, headers)
    user_id = _user_id(headers)

    # Stripe unreachable: the account must NOT be deleted with a live subscription.
    original = stripe_fake.v1.subscriptions.cancel
    stripe_fake.v1.subscriptions.cancel = lambda _id: (_ for _ in ()).throw(RuntimeError("down"))
    assert client.delete(f"/api/admin/users/{user_id}", headers=admin).status_code == 502
    assert _plan(client, headers)["plan"] == "pro"

    stripe_fake.v1.subscriptions.cancel = original
    assert client.delete(f"/api/admin/users/{user_id}", headers=admin).status_code == 200
    assert stripe_fake.canceled == [sub_id]


def test_simultaneous_requests_cannot_both_take_the_last_analysis(client, app_module):
    """The check-then-act race, run for real on two database connections.

    A Free user has used 4 of 5. Request A reserves the 5th and has not
    committed yet. Request B arrives at that moment: without the advisory
    lock it would also count 4 and pass. With it, B waits for A's commit,
    then counts 5 and is refused.
    """
    import threading

    from fastapi import HTTPException

    entitlements = app_module.entitlements
    user_id = _user_id(_register(client))

    db = app_module.SessionLocal()
    for _ in range(4):
        entitlements.reserve_analysis(db, user_id)
    db.commit()

    a = app_module.SessionLocal()
    entitlements.reserve_analysis(a, user_id)  # the 5th, not yet committed

    outcome = {}

    def request_b():
        b = app_module.SessionLocal()
        try:
            entitlements.reserve_analysis(b, user_id)
            b.commit()
            outcome["b"] = "allowed"
        except HTTPException as exc:
            b.rollback()
            outcome["b"] = exc.status_code
        finally:
            b.close()

    thread = threading.Thread(target=request_b)
    thread.start()
    thread.join(timeout=1.0)
    assert thread.is_alive(), "B should be waiting on A's lock, not deciding already"

    a.commit()
    a.close()
    thread.join(timeout=10)
    db.close()

    assert outcome["b"] == 402
    check = app_module.SessionLocal()
    try:
        assert entitlements.analyses_used_this_month(check, user_id) == 5
    finally:
        check.close()
