# Billing: Stripe subscriptions (test mode)

CareerLens sells **Pro** as a monthly or yearly subscription through Stripe
Checkout. Everything runs in Stripe **test mode**: the server refuses to start
with a live key, so no real card can ever be charged.

## How it fits together

```
Pricing page ── POST /api/billing/checkout {plan:"pro", interval:"year"} ──▶ FastAPI
                   (a plan NAME, never a price id)                             │
                                         server maps it via services/plans.py ▼
Browser ◀─────────────── Stripe Checkout URL ◀───── Stripe API (price_... from env)
   │  card typed on Stripe's page, never on ours
   ▼
Stripe ── signed webhook ──▶ POST /api/billing/webhook
                                1. verify Stripe-Signature on the raw bytes
                                2. INSERT event id  (stripe_events, dedupe)
                                3. re-fetch the subscription from Stripe
                                4. upsert subscriptions row, COMMIT
Premium endpoint ──▶ services/entitlements.py reads subscriptions ──▶ allow or 402
```

| File | Job |
|---|---|
| `services/plans.py` | What each plan includes; the (plan, interval) → price whitelist |
| `services/billing.py` | Talks to Stripe: checkout, portal, webhook processing, sync |
| `services/entitlements.py` | Decides access from the database; quotas with a per-user lock |
| `billing_routes.py` | The `/api/billing/*` endpoints |
| `models/billing.py`, `models/usage_event.py` | The four tables (migration `0003`) |
| `test_billing.py` | 39 tests, including forged/replayed/duplicate/out-of-order webhooks |

The rules that keep it honest:

- **The browser never sets a plan.** No endpoint writes a plan from a request
  body. Only the webhook, or the server asking Stripe itself, writes
  `subscriptions`.
- **The success page grants nothing.** It asks the server and waits until the
  server says Pro.
- **Webhooks are verified, deduplicated, and order-independent.** The event
  says *which* subscription changed. Its current state is always fetched fresh
  from Stripe.

## One-time Stripe setup (about 10 minutes)

1. **Create a Stripe account** at <https://dashboard.stripe.com/register>, and
   make sure **Test mode** is switched on (top right).
2. **API key:** go to Developers → API keys and copy the **Secret key**
   (`sk_test_...`).
3. **Product and prices:** go to Product catalog → Add product, name it
   "CareerLens Pro", and add two **recurring** prices:
   - $29.00 USD, billed **monthly**
   - $276.00 USD, billed **yearly** (that's $23/month, shown on the page as "Save 21%")

   Copy both price IDs (`price_...`). The pricing page reads the amounts from
   Stripe, so if you choose different prices the page follows automatically.
4. **Customer portal:** go to Settings → Billing → Customer portal and press
   **Save** (Stripe refuses portal sessions until you do). To let users switch
   between monthly and yearly, enable "Customers can switch plans" and add the
   CareerLens Pro product.
5. **Failed payments:** under Settings → Billing → Subscriptions and emails,
   decide what happens when all retries fail. "Cancel the subscription" or
   "mark as unpaid" both end Pro access here.
6. **The Stripe CLI** forwards webhooks to your laptop, which Stripe can't
   reach directly. Install it (see <https://docs.stripe.com/stripe-cli>),
   then run:

   ```bash
   stripe login
   stripe listen --forward-to localhost:8000/api/billing/webhook
   ```

   It prints a signing secret, `whsec_...`. That's your `STRIPE_WEBHOOK_SECRET`
   for local development. Keep `stripe listen` running while you test.

7. **Add to `ai-job-intelligence/.env`** (gitignored), then **restart uvicorn**
   (`--reload` does not notice `.env` changes):

   ```
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   STRIPE_PRICE_PRO_MONTHLY=price_...
   STRIPE_PRICE_PRO_YEARLY=price_...
   ```

## Try it

1. Sign in as a new job seeker (Free: 2 CV uploads, 5 analyses and 2 Career
   Insights sessions a month; a session lasts 24 hours). Upload a third CV
   and you'll be offered Pro.
2. On `/pricing`, pick Monthly or Annual and choose **Upgrade to Pro**.
3. Pay with `4242 4242 4242 4242`, any future expiry date, and any CVC.
4. You land on `/billing`, which says *Confirming…* and then *Welcome to Pro*.
   In the `stripe listen` terminal you'll see the events arrive with `200`s.

Other test cards: `4000 0000 0000 9995` is declined (checkout fails, nothing
changes), and `4000 0025 0000 3155` asks for 3-D Secure authentication first.

A *failed renewal* (`past_due`) can't be produced by a card at checkout, since
the first charge has to succeed to create the subscription. Stripe simulates
renewals with **test clocks**, simulated time you can fast-forward
(<https://docs.stripe.com/billing/testing/test-clocks>). The automated tests
in `test_billing.py` cover `past_due` → `unpaid` directly.

Watch the state change in Postgres while you click:

```sql
SELECT user_id, plan, status, billing_interval, current_period_end, cancel_at_period_end
FROM subscriptions ORDER BY updated_at DESC;
SELECT id, type, processed_at FROM stripe_events ORDER BY processed_at DESC LIMIT 10;
```

To replay lifecycle events without clicking through the UI:
`stripe trigger customer.subscription.updated`. Note that a triggered event
creates its own test customer, so the server logs "matches no CareerLens
user". That's the intended behaviour, not a bug.

## Deploying (Render)

Add the four variables in the Render dashboard. For production, **don't** use
the `stripe listen` secret. Instead, add an endpoint under Developers → Webhooks
pointing at `https://<your-api>.onrender.com/api/billing/webhook`, subscribe it
to the events in `billing.HANDLED_EVENT_TYPES`, and use *that* endpoint's
signing secret.
