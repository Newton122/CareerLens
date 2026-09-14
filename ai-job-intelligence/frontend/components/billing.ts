"use client";

/**
 * Billing on the frontend: reading the plan, and starting Stripe flows.
 *
 * What this file deliberately cannot do is *grant* anything. The plan shown
 * here is read from GET /api/billing/subscription, which the server computes
 * from subscription rows written only by Stripe webhooks. Editing the value
 * in the browser would change a label and nothing else -- every premium API
 * call is re-checked on the server and answered 402 if the plan lacks it.
 */

import { useEffect, useState } from "react";
import { apiCall } from "@/components/api";
import { describeApiError } from "@/components/format";

/** HTTP 402 Payment Required: signed in, but the plan doesn't cover this. */
export const PAYMENT_REQUIRED = 402;

/** Fired after the plan may have changed, so every badge refreshes. */
export const PLAN_CHANGED_EVENT = "careerlens-plan-changed";

export type Interval = "month" | "year";
export type PlanName = "free" | "pro" | "enterprise";

export interface PriceInfo {
  plan: string;
  interval: Interval;
  /** In the currency's smallest unit (cents), exactly as Stripe reports it. */
  unit_amount: number | null;
  currency: string;
}

export interface PlansResponse {
  billing_enabled: boolean;
  prices: PriceInfo[];
  plans: Record<
    string,
    {
      /** Monthly caps; null = unlimited. */
      limits: {
        cv_uploads_per_month: number | null;
        analyses_per_month: number | null;
        insight_sessions_per_month: number | null;
      };
      features: string[];
    }
  >;
}

/** One monthly quota. Resets on the 1st (UTC). */
export interface Usage {
  used: number;
  /** null = unlimited */
  limit: number | null;
  resets_at: string;
}

export interface SubscriptionInfo {
  plan: PlanName;
  features: string[];
  status: string | null;
  billing_interval: Interval | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  payment_issue: boolean;
  has_billing_account: boolean;
  billing_enabled: boolean;
  usage: {
    cv_uploads_this_month: Usage;
    analyses_this_month: Usage;
    /** A session lasts 24 hours from when Career Insights was first opened. */
    insight_sessions_this_month: Usage & { session_expires_at: string | null };
  };
}

export async function fetchPlans(): Promise<PlansResponse | null> {
  try {
    const response = await apiCall("/api/billing/plans");
    return response.ok ? response.json() : null;
  } catch {
    return null;
  }
}

export async function fetchSubscription(): Promise<SubscriptionInfo | null> {
  try {
    const response = await apiCall("/api/billing/subscription");
    return response.ok ? response.json() : null;
  } catch {
    return null;
  }
}

/** The signed-in user's plan, kept fresh when PLAN_CHANGED_EVENT fires. */
export function useSubscription(enabled = true): SubscriptionInfo | null {
  const [info, setInfo] = useState<SubscriptionInfo | null>(null);
  useEffect(() => {
    if (!enabled) return;
    let active = true;
    const load = () =>
      fetchSubscription().then((data) => {
        if (active && data) setInfo(data);
      });
    load();
    window.addEventListener(PLAN_CHANGED_EVENT, load);
    return () => {
      active = false;
      window.removeEventListener(PLAN_CHANGED_EVENT, load);
    };
  }, [enabled]);
  return info;
}

async function redirectTo(endpoint: string, body?: object): Promise<void> {
  const response = await apiCall(endpoint, {
    method: "POST",
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.url) {
    throw new Error(describeApiError(data, "Could not reach the payment page. Please try again."));
  }
  // A full-page navigation to Stripe's own domain: the card form lives there,
  // not in this app, so card numbers never pass through CareerLens.
  window.location.assign(data.url);
}

/**
 * Go to Stripe Checkout for Pro. Only the plan *name* and interval are sent;
 * the server decides which Stripe price that means.
 */
export function startCheckout(interval: Interval): Promise<void> {
  return redirectTo("/api/billing/checkout", { plan: "pro", interval });
}

/** Stripe's hosted portal: cancel, switch interval, update card, invoices. */
export function openBillingPortal(): Promise<void> {
  return redirectTo("/api/billing/portal");
}

export function formatMoney(cents: number, currency: string): string {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: currency.toUpperCase(),
    minimumFractionDigits: cents % 100 === 0 ? 0 : 2,
  }).format(cents / 100);
}

export function formatTime(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleString(undefined, {
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDate(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export const PLAN_LABEL: Record<string, string> = {
  free: "Free",
  pro: "Pro",
  enterprise: "Enterprise",
};
