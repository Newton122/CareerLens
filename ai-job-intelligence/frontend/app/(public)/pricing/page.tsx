"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  FaCheck,
  FaTimes,
  FaRocket,
  FaCrown,
  FaBuilding,
  FaChevronDown,
  FaLock,
} from "react-icons/fa";
import { useAuth } from "@/components/AuthProvider";
import {
  fetchPlans,
  formatMoney,
  startCheckout,
  useSubscription,
  type Interval,
  type PriceInfo,
} from "@/components/billing";

// Shown only if the live prices can't be loaded (Stripe not configured yet,
// or unreachable). When they can, the numbers on this page come from Stripe
// via GET /api/billing/plans, so the page can't disagree with the charge.
const FALLBACK_PRICES: PriceInfo[] = [
  { plan: "pro", interval: "month", unit_amount: 2900, currency: "usd" },
  { plan: "pro", interval: "year", unit_amount: 27600, currency: "usd" },
];

const COMING_SOON = "Coming soon";

type FeatureValue = boolean | string;

const plans = [
  {
    id: "free",
    name: "Starter",
    description: "Perfect for exploring opportunities and trying our AI features",
    icon: FaRocket,
    color: "from-neutral-500 to-neutral-600",
    features: {
      cvs: "2 per month",
      analyses: "5 per month",
      matches: "Job recommendations",
      insights: "2 sessions per month",
      recommendations: "Within Insights",
      coverLetter: false,
      priority: false,
      api: false,
      support: false,
    } as Record<string, FeatureValue>,
    popular: false,
  },
  {
    id: "pro",
    name: "Pro",
    description: "For serious job seekers who want the full AI advantage",
    icon: FaCrown,
    color: "from-blue-600 to-emerald-500",
    features: {
      cvs: "Unlimited CVs",
      analyses: "Unlimited",
      matches: "Job recommendations",
      insights: true,
      recommendations: true,
      coverLetter: COMING_SOON,
      priority: true,
      api: false,
      support: false,
    } as Record<string, FeatureValue>,
    popular: true,
  },
  {
    id: "enterprise",
    name: "Enterprise",
    description: "For teams, recruiters, and organizations at scale",
    icon: FaBuilding,
    color: "from-emerald-500 to-teal-600",
    features: {
      cvs: "Unlimited everything",
      analyses: "Unlimited",
      matches: "Custom AI models",
      insights: true,
      recommendations: true,
      coverLetter: COMING_SOON,
      priority: true,
      api: true,
      support: true,
    } as Record<string, FeatureValue>,
    popular: false,
  },
];

const featureLabels: Record<string, string> = {
  cvs: "CV Uploads",
  analyses: "AI Job-Match Analyses",
  matches: "Job Matching",
  insights: "Advanced Insights",
  recommendations: "Career Recommendations",
  coverLetter: "Cover Letter Generation",
  priority: "Priority Support",
  api: "API Access",
  support: "Dedicated Account Manager",
};

// Every answer here describes what the app actually does.
const faqs = [
  {
    question: "How is Pro billed?",
    answer:
      "Monthly or yearly, through Stripe. You enter your card on Stripe's secure checkout page; CareerLens never sees or stores your card number.",
  },
  {
    question: "Can I cancel at any time?",
    answer:
      "Yes, from the Billing page. You keep Pro until the end of the period you've already paid for, and you won't be charged again.",
  },
  {
    question: "Can I switch between monthly and annual?",
    answer:
      "Yes. Open the Billing page and choose Manage subscription. Stripe adjusts the price for the time remaining on your current period.",
  },
  {
    question: "What happens if a payment fails?",
    answer:
      "Stripe retries the card over the following days and you keep Pro in the meantime. Update your card from the Billing page to fix it straight away.",
  },
  {
    question: "What happens to my data if I go back to Free?",
    answer:
      "Nothing is deleted. Your CVs and past analyses stay available. The Free limits apply only to new uploads and new analyses.",
  },
  {
    question: "Is cover letter generation available yet?",
    answer:
      "Not yet. It's on the roadmap and will be included in Pro when it ships. We list it as \"Coming soon\" so you know exactly what you're paying for today.",
  },
];

function PricingContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { token, role } = useAuth();
  const subscription = useSubscription(Boolean(token));
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const [isAnnual, setIsAnnual] = useState(true);
  const [prices, setPrices] = useState<PriceInfo[] | null>(null);
  const [billingEnabled, setBillingEnabled] = useState(false);
  const [redirecting, setRedirecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canceled = searchParams.get("checkout") === "canceled";
  const interval: Interval = isAnnual ? "year" : "month";

  useEffect(() => {
    let active = true;
    fetchPlans().then((data) => {
      if (!active) return;
      setBillingEnabled(Boolean(data?.billing_enabled && data.prices.length));
      setPrices(data?.prices.length ? data.prices : FALLBACK_PRICES);
    });
    return () => {
      active = false;
    };
  }, []);

  const shown = prices ?? FALLBACK_PRICES;
  const monthly = shown.find((p) => p.plan === "pro" && p.interval === "month");
  const yearly = shown.find((p) => p.plan === "pro" && p.interval === "year");
  // Computed from the two real prices rather than hard-coded "20%".
  const saving =
    monthly?.unit_amount && yearly?.unit_amount
      ? Math.round((1 - yearly.unit_amount / (monthly.unit_amount * 12)) * 100)
      : 0;

  const currentPlan = token ? subscription?.plan ?? null : null;
  const isJobSeeker = !token || role === "job_seeker";

  function priceFor(planId: string) {
    if (planId === "free") return { amount: "$0", period: "", note: "Free forever" };
    if (planId === "enterprise") return { amount: "Custom", period: "", note: "Talk to us" };
    const price = isAnnual ? yearly : monthly;
    if (!price?.unit_amount) return { amount: "—", period: "", note: "" };
    if (isAnnual) {
      return {
        amount: formatMoney(Math.round(price.unit_amount / 12), price.currency),
        period: "/month",
        note: `Billed ${formatMoney(price.unit_amount, price.currency)} once a year`,
      };
    }
    return { amount: formatMoney(price.unit_amount, price.currency), period: "/month", note: "Billed monthly" };
  }

  async function choosePro() {
    setError(null);
    if (!token) {
      router.push("/register");
      return;
    }
    if (currentPlan === "pro" || currentPlan === "enterprise") {
      router.push("/billing");
      return;
    }
    setRedirecting(true);
    try {
      // The server picks the Stripe price for this interval and returns a
      // Checkout URL; the browser then leaves for Stripe's page.
      await startCheckout(interval);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start checkout.");
      setRedirecting(false);
    }
  }

  function ctaFor(planId: string): { label: string; onClick: () => void; disabled?: boolean } {
    if (planId === "enterprise") {
      return { label: "Contact Sales", onClick: () => router.push("/contact") };
    }
    if (planId === "free") {
      if (!token) return { label: "Get Started", onClick: () => router.push("/register") };
      if (currentPlan === "free") return { label: "Your current plan", onClick: () => {}, disabled: true };
      return { label: "Included", onClick: () => router.push("/billing"), disabled: true };
    }
    // Pro
    if (!isJobSeeker) return { label: "For job seekers", onClick: () => {}, disabled: true };
    if (currentPlan === "pro") return { label: "Manage subscription", onClick: () => router.push("/billing") };
    if (token && !billingEnabled) return { label: "Payments not available yet", onClick: () => {}, disabled: true };
    return {
      label: redirecting ? "Opening secure checkout…" : "Upgrade to Pro",
      onClick: choosePro,
      disabled: redirecting,
    };
  }

  return (
    <div className="min-h-screen">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
        <motion.div
          className="text-center max-w-3xl mx-auto mb-12"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <span className="text-sm font-medium text-blue-400 uppercase tracking-wider">
            Pricing
          </span>
          <h1 className="text-4xl sm:text-5xl font-bold mt-4 mb-4">
            Invest in Your{" "}
            <span className="gradient-text">Career Future</span>
          </h1>
          <p className="text-lg text-neutral-400">
            Choose the plan that fits your goals. Start free, upgrade when
            you&apos;re ready.
          </p>
        </motion.div>

        {canceled && (
          <div className="max-w-2xl mx-auto mb-8 rounded-lg border border-neutral-700 bg-neutral-800/60 px-5 py-4 text-sm text-neutral-300">
            Checkout was canceled. You haven&apos;t been charged, and you can
            upgrade whenever you like.
          </div>
        )}
        {error && (
          <div className="max-w-2xl mx-auto mb-8 rounded-lg border border-rose-500/30 bg-rose-500/10 px-5 py-4 text-sm text-rose-300">
            {error}
          </div>
        )}

        <motion.div
          className="flex items-center justify-center gap-4 mb-12"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
        >
          <span
            className={`text-sm font-medium ${
              !isAnnual ? "text-neutral-50" : "text-neutral-400"
            }`}
          >
            Monthly
          </span>
          <button
            onClick={() => setIsAnnual(!isAnnual)}
            role="switch"
            aria-checked={isAnnual}
            aria-label="Bill annually"
            className={`relative w-14 h-7 rounded-full transition-colors duration-300 ${
              isAnnual ? "bg-blue-600" : "bg-neutral-700"
            }`}
          >
            <motion.div
              className="absolute top-1 w-5 h-5 rounded-full bg-neutral-800 shadow-md"
              animate={{ left: isAnnual ? "calc(100% - 1.375rem)" : "0.25rem" }}
              transition={{ type: "spring", stiffness: 500, damping: 30 }}
            />
          </button>
          <span
            className={`text-sm font-medium ${
              isAnnual ? "text-neutral-50" : "text-neutral-400"
            }`}
          >
            Annual
          </span>
          {isAnnual && saving > 0 && (
            <span className="px-2 py-1 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-medium">
              Save {saving}%
            </span>
          )}
        </motion.div>

        <motion.div
          className="grid md:grid-cols-3 gap-6 lg:gap-8 mb-10"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          {plans.map((plan) => {
            const price = priceFor(plan.id);
            const cta = ctaFor(plan.id);
            const isCurrent = currentPlan === plan.id;
            return (
              <motion.div
                key={plan.name}
                whileHover={{ y: -5, transition: { duration: 0.2 } }}
                className={`relative p-8 rounded-lg ${
                  plan.popular
                    ? "bg-neutral-800 border-2 border-blue-500/50 shadow-xl shadow-blue-500/10"
                    : "bg-neutral-800/50 border border-neutral-700/50"
                }`}
              >
                {(plan.popular || isCurrent) && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                    <span
                      className={`px-4 py-1 rounded-full text-xs font-medium ${
                        isCurrent
                          ? "bg-emerald-500 text-neutral-950"
                          : "bg-gradient-to-r from-blue-600 to-emerald-500 text-white"
                      }`}
                    >
                      {isCurrent ? "Your plan" : "Recommended"}
                    </span>
                  </div>
                )}

                <div
                  className={`w-12 h-12 rounded-lg bg-gradient-to-br ${plan.color} flex items-center justify-center mb-4`}
                >
                  <plan.icon className="w-6 h-6 text-white" />
                </div>

                <h3 className="text-xl font-semibold text-neutral-50 mb-2">
                  {plan.name}
                </h3>
                <div className="flex items-baseline gap-1 mb-1">
                  <span className="text-4xl font-bold text-neutral-50 tabular-nums">
                    {price.amount}
                  </span>
                  {price.period && (
                    <span className="text-neutral-400">{price.period}</span>
                  )}
                </div>
                <p className="meta mb-3 min-h-5">{price.note}</p>
                <p className="text-neutral-400 text-sm mb-6">{plan.description}</p>

                <motion.button
                  onClick={cta.onClick}
                  disabled={cta.disabled}
                  className={`w-full py-3 rounded-lg font-medium mb-8 transition-all duration-300 disabled:opacity-60 disabled:cursor-default ${
                    plan.popular
                      ? "bg-gradient-to-r from-blue-600 to-emerald-500 text-white hover:shadow-lg hover:shadow-blue-500/25"
                      : "bg-neutral-700/50 text-neutral-200 border border-neutral-600/50 hover:bg-neutral-700"
                  }`}
                  whileHover={cta.disabled ? undefined : { scale: 1.02 }}
                  whileTap={cta.disabled ? undefined : { scale: 0.98 }}
                >
                  {cta.label}
                </motion.button>

                <ul className="space-y-3">
                  {Object.entries(plan.features).map(([key, value]) => (
                    <li key={key} className="flex items-center gap-3">
                      {value ? (
                        <FaCheck
                          className={`w-4 h-4 flex-shrink-0 ${
                            value === COMING_SOON ? "text-neutral-500" : "text-emerald-500"
                          }`}
                        />
                      ) : (
                        <FaTimes className="w-4 h-4 text-neutral-600 flex-shrink-0" />
                      )}
                      <span
                        className={`text-sm ${
                          value && value !== COMING_SOON ? "text-neutral-300" : "text-neutral-500"
                        }`}
                      >
                        {value === COMING_SOON ? (
                          <>
                            {featureLabels[key]}{" "}
                            <span className="chip ml-1 py-0.5">Coming soon</span>
                          </>
                        ) : typeof value === "string" ? (
                          value
                        ) : (
                          featureLabels[key]
                        )}
                      </span>
                    </li>
                  ))}
                </ul>
              </motion.div>
            );
          })}
        </motion.div>

        {/* Honest about where payment happens, and that this is a sandbox. */}
        <div className="max-w-3xl mx-auto mb-24 flex flex-col sm:flex-row items-center justify-center gap-3 text-center text-sm text-neutral-500">
          <FaLock className="w-3.5 h-3.5 shrink-0" />
          <span>
            Payments are processed by Stripe; CareerLens never stores card details.
            This site runs in Stripe <strong className="text-neutral-300">test mode</strong>:
            no real money moves. Use card 4242 4242 4242 4242, any future date, any CVC.
          </span>
        </div>

        <motion.section
          className="mb-24"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="text-2xl sm:text-3xl font-bold text-center mb-8">
            Compare Plans
          </h2>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[600px]">
              <thead>
                <tr className="border-b border-neutral-700/50">
                  <th className="text-left py-4 px-4 text-sm font-medium text-neutral-400">
                    Feature
                  </th>
                  {plans.map((plan) => (
                    <th
                      key={plan.name}
                      className="text-center py-4 px-4 text-sm font-medium text-neutral-200"
                    >
                      {plan.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.entries(featureLabels).map(([key, label]) => (
                  <tr
                    key={key}
                    className="border-b border-neutral-800/50 hover:bg-neutral-800/30 transition-colors"
                  >
                    <td className="py-4 px-4 text-sm text-neutral-300">
                      {label}
                    </td>
                    {plans.map((plan) => {
                      const value = plan.features[key];
                      return (
                        <td key={plan.name} className="py-4 px-4 text-center">
                          {value === COMING_SOON ? (
                            <span className="chip">Coming soon</span>
                          ) : typeof value === "string" ? (
                            <span className="text-sm text-neutral-200">{value}</span>
                          ) : value ? (
                            <FaCheck className="w-5 h-5 text-emerald-500 mx-auto" />
                          ) : (
                            <FaTimes className="w-5 h-5 text-neutral-600 mx-auto" />
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.section>

        <motion.section
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <h2 className="text-2xl sm:text-3xl font-bold text-center mb-8">
            Frequently Asked Questions
          </h2>

          <div className="max-w-3xl mx-auto space-y-4">
            {faqs.map((faq, index) => (
              <motion.div
                key={index}
                className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 overflow-hidden"
                initial={false}
              >
                <button
                  onClick={() => setOpenFaq(openFaq === index ? null : index)}
                  className="w-full flex items-center justify-between p-5 text-left"
                  aria-expanded={openFaq === index}
                >
                  <span className="font-medium text-neutral-200">{faq.question}</span>
                  <motion.div
                    animate={{ rotate: openFaq === index ? 180 : 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <FaChevronDown className="w-4 h-4 text-neutral-400" />
                  </motion.div>
                </button>
                <AnimatePresence>
                  {openFaq === index && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.3 }}
                      className="overflow-hidden"
                    >
                      <p className="px-5 pb-5 text-neutral-400 text-sm leading-relaxed">
                        {faq.answer}
                      </p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            ))}
          </div>
        </motion.section>
      </div>
    </div>
  );
}

// useSearchParams (for ?checkout=canceled) needs a Suspense boundary so
// Next.js can pre-render the rest of the page.
export default function PricingPage() {
  return (
    <Suspense fallback={<div className="min-h-screen" />}>
      <PricingContent />
    </Suspense>
  );
}
