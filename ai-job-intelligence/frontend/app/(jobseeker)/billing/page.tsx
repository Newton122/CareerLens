"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import {
  FaCrown,
  FaCreditCard,
  FaExclamationTriangle,
  FaLock,
  FaCheckCircle,
} from "react-icons/fa";
import { apiCall } from "@/components/api";
import {
  PLAN_CHANGED_EVENT,
  PLAN_LABEL,
  fetchSubscription,
  formatDate,
  formatTime,
  openBillingPortal,
  type SubscriptionInfo,
  type Usage,
} from "@/components/billing";
import LoadingSpinner from "@/components/LoadingSpinner";

// How long the success page waits for Stripe's webhook before giving up
// and saying so. Usually it lands within a couple of seconds.
const CONFIRM_TIMEOUT_MS = 30_000;
const POLL_EVERY_MS = 2_000;

type Confirming = "idle" | "waiting" | "confirmed" | "timeout";

function BillingContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [info, setInfo] = useState<SubscriptionInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [confirming, setConfirming] = useState<Confirming>(
    searchParams.get("checkout") === "success" ? "waiting" : "idle",
  );
  const [portalError, setPortalError] = useState<string | null>(null);
  const [openingPortal, setOpeningPortal] = useState(false);

  // Coming back from Stripe Checkout?
  //
  // Arriving at this URL proves nothing -- anyone can type it. So the page
  // does not show "You're Pro!" because of the URL. It asks the server,
  // which asks Stripe (checkout/confirm) and also receives the webhook, and
  // shows Pro only once the server says so.
  //
  // Each run of this effect has its own `active` flag, and cleanup turns it
  // off. React's development mode runs effects twice on purpose (mount,
  // cleanup, mount) to catch code that can't survive that; the first run
  // simply stops, and the second does the work. Calling checkout/confirm
  // twice is harmless -- the server treats it as "sync from Stripe again".
  useEffect(() => {
    let active = true;
    const sessionId = searchParams.get("session_id");
    const deadline = Date.now() + CONFIRM_TIMEOUT_MS;

    async function refresh(): Promise<SubscriptionInfo | null> {
      const data = await fetchSubscription();
      if (active && data) setInfo(data);
      return data;
    }

    async function waitForPro() {
      // One server-side check with Stripe, in case the webhook is slow...
      if (sessionId) {
        await apiCall("/api/billing/checkout/confirm", {
          method: "POST",
          body: JSON.stringify({ session_id: sessionId }),
        }).catch(() => undefined);
      }
      // ...then poll until the server reports the paid plan.
      while (active && Date.now() < deadline) {
        const data = await refresh();
        if (!active) return;
        if (data && data.plan !== "free") {
          setConfirming("confirmed");
          window.dispatchEvent(new Event(PLAN_CHANGED_EVENT));
          // Drop ?checkout=success so a reload doesn't re-run this.
          router.replace("/billing");
          return;
        }
        await new Promise((resolve) => setTimeout(resolve, POLL_EVERY_MS));
      }
      if (active) setConfirming("timeout");
    }

    (async () => {
      await refresh();
      if (active) setLoading(false);
      if (searchParams.get("checkout") === "success") await waitForPro();
    })();

    return () => {
      active = false;
    };
  }, [router, searchParams]);

  async function manage() {
    setPortalError(null);
    setOpeningPortal(true);
    try {
      await openBillingPortal();
    } catch (err) {
      setPortalError(err instanceof Error ? err.message : "Could not open the billing portal.");
      setOpeningPortal(false);
    }
  }

  if (loading || !info) {
    return (
      <div className="max-w-3xl mx-auto py-16">
        <LoadingSpinner />
      </div>
    );
  }

  const isPaid = info.plan !== "free";
  const renewal = formatDate(info.current_period_end);

  return (
    <div className="min-h-screen text-neutral-100">
      <div className="max-w-3xl mx-auto px-4 py-6">
        <div className="page-header">
          <div>
            <h1 className="page-title">Billing</h1>
            <p className="page-subtitle">Your plan, usage and payment details</p>
          </div>
        </div>

        {confirming === "waiting" && (
          <div className="card mb-6 flex items-center gap-4 border-indigo-500/30">
            <div className="w-6 h-6 border-2 border-indigo-400/30 border-t-indigo-400 rounded-full animate-spin shrink-0" />
            <div>
              <p className="item-title">Confirming your payment with Stripe…</p>
              <p className="meta mt-0.5">
                This usually takes a few seconds. You can leave this page; Pro
                switches on as soon as Stripe confirms.
              </p>
            </div>
          </div>
        )}
        {confirming === "confirmed" && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="card mb-6 flex items-center gap-4 border-emerald-500/30 bg-emerald-500/5"
          >
            <FaCheckCircle className="w-6 h-6 text-emerald-400 shrink-0" />
            <div>
              <p className="item-title">Welcome to CareerLens Pro</p>
              <p className="meta mt-0.5">
                Your payment is confirmed and every Pro feature is unlocked.
              </p>
            </div>
          </motion.div>
        )}
        {confirming === "timeout" && (
          <div className="card mb-6 flex items-start gap-4 border-amber-500/30 bg-amber-500/5">
            <FaExclamationTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <p className="item-title">Still waiting for Stripe</p>
              <p className="meta mt-0.5">
                We haven&apos;t received the payment confirmation yet. If you were
                charged, Pro will switch on automatically once it arrives; refresh
                this page in a minute.
              </p>
            </div>
          </div>
        )}

        {info.payment_issue && (
          <div className="card mb-6 flex items-start gap-4 border-rose-500/30 bg-rose-500/5">
            <FaExclamationTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <p className="item-title">Your last payment failed</p>
              <p className="meta mt-0.5">
                Stripe will retry automatically and you keep Pro for now. Update
                your card to avoid losing access.
              </p>
              <button onClick={manage} className="btn-danger btn-small mt-3">
                Update payment method
              </button>
            </div>
          </div>
        )}

        {/* Current plan */}
        <section className="card mb-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex items-start gap-4">
              <div
                className={`w-11 h-11 rounded-lg flex items-center justify-center shrink-0 ${
                  isPaid
                    ? "bg-gradient-to-br from-blue-600 to-emerald-500"
                    : "bg-neutral-800 border border-neutral-700"
                }`}
              >
                <FaCrown className={`w-5 h-5 ${isPaid ? "text-white" : "text-neutral-500"}`} />
              </div>
              <div>
                <p className="eyebrow">Current plan</p>
                <p className="text-2xl font-semibold text-neutral-50 mt-1">
                  {PLAN_LABEL[info.plan] ?? info.plan}
                  {info.billing_interval && (
                    <span className="text-base font-normal text-neutral-400">
                      {" "}· billed {info.billing_interval === "year" ? "yearly" : "monthly"}
                    </span>
                  )}
                </p>
                {isPaid && renewal && (
                  <p className="meta mt-1">
                    {info.cancel_at_period_end
                      ? `Cancelled. Pro stays active until ${renewal}, and you won't be charged again.`
                      : `Renews on ${renewal}.`}
                  </p>
                )}
                {!isPaid && (
                  <p className="meta mt-1">
                    Each month: 2 CV uploads, 5 job-match analyses and 2 Career
                    Insights sessions.
                  </p>
                )}
              </div>
            </div>
            {info.status && (
              <span
                className={
                  info.status === "active" || info.status === "trialing"
                    ? "chip-positive"
                    : "chip-negative"
                }
              >
                {info.status.replace("_", " ")}
              </span>
            )}
          </div>

          <div className="rule my-5" />

          <div className="flex flex-wrap gap-3">
            {!isPaid && (
              <button onClick={() => router.push("/pricing")} className="btn-primary">
                <FaCrown className="w-4 h-4" /> Upgrade to Pro
              </button>
            )}
            {info.has_billing_account && (
              <button onClick={manage} disabled={openingPortal} className="btn-secondary">
                <FaCreditCard className="w-4 h-4" />
                {openingPortal
                  ? "Opening Stripe…"
                  : isPaid
                    ? "Manage subscription"
                    : "Invoices & payment details"}
              </button>
            )}
          </div>
          {isPaid && (
            <p className="meta mt-3">
              Cancel, switch between monthly and yearly, update your card or
              download invoices in Stripe&apos;s secure billing portal.
            </p>
          )}
          {portalError && <p className="text-sm text-rose-300 mt-3">{portalError}</p>}
        </section>

        {/* Usage */}
        <section className="card mb-6">
          <h2 className="section-title mb-4">Usage</h2>
          <div className="space-y-5">
            <UsageRow label="CV uploads this month" usage={info.usage.cv_uploads_this_month} />
            <UsageRow label="Job-match analyses this month" usage={info.usage.analyses_this_month} />
            <UsageRow
              label="Career Insights sessions this month"
              usage={info.usage.insight_sessions_this_month}
              extra={
                info.usage.insight_sessions_this_month.limit !== null
                  ? info.usage.insight_sessions_this_month.session_expires_at
                    ? `Current session open until ${formatTime(info.usage.insight_sessions_this_month.session_expires_at)}.`
                    : "A session starts when you open Career Insights and lasts 24 hours."
                  : undefined
              }
            />
          </div>
          {!isPaid && (
            <p className="meta mt-5">
              Free allowances reset on {formatDate(info.usage.analyses_this_month.resets_at)}.
            </p>
          )}
        </section>

        <p className="flex items-center gap-2 meta">
          <FaLock className="w-3 h-3" />
          Payments are handled by Stripe (test mode). CareerLens never sees your
          card number.
        </p>
      </div>
    </div>
  );
}

function UsageRow({ label, usage, extra }: { label: string; usage: Usage; extra?: string }) {
  const unlimited = usage.limit === null;
  const pct = unlimited ? 0 : Math.min(100, (usage.used / Math.max(usage.limit!, 1)) * 100);
  const full = !unlimited && usage.used >= usage.limit!;
  return (
    <div>
      <div className="flex items-baseline justify-between gap-4 mb-2">
        <span className="text-sm text-neutral-300">{label}</span>
        <span className={`text-sm tabular-nums ${full ? "text-rose-300" : "text-neutral-400"}`}>
          {usage.used} {unlimited ? "· unlimited" : `of ${usage.limit}`}
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-neutral-800 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${
            unlimited
              ? "w-full bg-gradient-to-r from-blue-600/40 to-emerald-500/40"
              : full
                ? "bg-rose-400"
                : "bg-gradient-to-r from-blue-600 to-emerald-500"
          }`}
          style={unlimited ? undefined : { width: `${pct}%` }}
        />
      </div>
      {extra && <p className="meta mt-1.5">{extra}</p>}
    </div>
  );
}

// useSearchParams needs a Suspense boundary so Next.js can pre-render the rest.
export default function BillingPage() {
  return (
    <Suspense fallback={<div className="max-w-3xl mx-auto py-16"><LoadingSpinner /></div>}>
      <BillingContent />
    </Suspense>
  );
}
