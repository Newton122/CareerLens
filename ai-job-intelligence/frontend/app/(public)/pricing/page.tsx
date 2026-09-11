"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  FaCheck,
  FaTimes,
  FaRocket,
  FaCrown,
  FaBuilding,
  FaQuestion,
  FaChevronDown,
} from "react-icons/fa";

const plans = [
  {
    name: "Starter",
    price: "Free",
    period: "",
    description: "Perfect for exploring opportunities and trying our AI features",
    icon: FaRocket,
    color: "from-neutral-500 to-neutral-600",
    features: {
      cvs: "1 CV",
      analyses: "5 per month",
      matches: "Basic job matching",
      insights: false,
      recommendations: false,
      coverLetter: false,
      priority: false,
      api: false,
      support: false,
    },
    cta: "Get Started",
    popular: false,
  },
  {
    name: "Pro",
    price: "$29",
    period: "/month",
    description: "For serious job seekers who want the full AI advantage",
    icon: FaCrown,
    color: "from-blue-600 to-emerald-500",
    features: {
      cvs: "Unlimited CVs",
      analyses: "Unlimited",
      matches: "Priority matching",
      insights: true,
      recommendations: true,
      coverLetter: true,
      priority: true,
      api: false,
      support: false,
    },
    cta: "Start Free Trial",
    popular: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    description: "For teams, recruiters, and organizations at scale",
    icon: FaBuilding,
    color: "from-emerald-500 to-teal-600",
    features: {
      cvs: "Unlimited everything",
      analyses: "Unlimited",
      matches: "Custom AI models",
      insights: true,
      recommendations: true,
      coverLetter: true,
      priority: true,
      api: true,
      support: true,
    },
    cta: "Contact Sales",
    popular: false,
  },
];

const featureLabels: Record<string, string> = {
  cvs: "CV Uploads",
  analyses: "AI Analyses",
  matches: "Job Matching",
  insights: "Advanced Insights",
  recommendations: "Career Recommendations",
  coverLetter: "Cover Letter Generation",
  priority: "Priority Support",
  api: "API Access",
  support: "Dedicated Account Manager",
};

const faqs = [
  {
    question: "Can I switch plans at any time?",
    answer:
      "Yes! You can upgrade or downgrade your plan at any time. Changes take effect immediately, and we'll prorate any billing differences.",
  },
  {
    question: "Is there a free trial for Pro?",
    answer:
      "Absolutely! Pro comes with a 14-day free trial. No credit card required to start.",
  },
  {
    question: "What payment methods do you accept?",
    answer:
      "We accept all major credit cards (Visa, MasterCard, Amex), PayPal, and bank transfers for annual plans.",
  },
  {
    question: "Can I get a refund?",
    answer:
      "Yes, we offer a 30-day money-back guarantee on all paid plans. No questions asked.",
  },
  {
    question: "What happens to my data if I cancel?",
    answer:
      "Your data remains accessible for 30 days after cancellation. You can export everything during this period.",
  },
  {
    question: "Do you offer discounts for students?",
    answer:
      "Yes! Students get 50% off Pro plans. Verify your student status to unlock the discount.",
  },
];

export default function PricingPage() {
  const router = useRouter();
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const [isAnnual, setIsAnnual] = useState(true);

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
          {isAnnual && (
            <span className="px-2 py-1 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-medium">
              Save 20%
            </span>
          )}
        </motion.div>

        <motion.div
          className="grid md:grid-cols-3 gap-6 lg:gap-8 mb-24"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          {plans.map((plan) => (
            <motion.div
              key={plan.name}
              whileHover={{ y: -5, transition: { duration: 0.2 } }}
              className={`relative p-8 rounded-lg ${
                plan.popular
                  ? "bg-neutral-800 border-2 border-blue-500/50 shadow-xl shadow-blue-500/10"
                  : "bg-neutral-800/50 border border-neutral-700/50"
              }`}
            >
              {plan.popular && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                  <span className="px-4 py-1 rounded-full bg-gradient-to-r from-blue-600 to-emerald-500 text-white text-xs font-medium">
                    Recommended
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
              <div className="flex items-baseline gap-1 mb-2">
                <span className="text-4xl font-bold text-neutral-50">
                  {plan.price === "$29"
                    ? isAnnual
                      ? "$23"
                      : "$29"
                    : plan.price}
                </span>
                {plan.period && (
                  <span className="text-neutral-400">{plan.period}</span>
                )}
              </div>
              <p className="text-neutral-400 text-sm mb-6">{plan.description}</p>

              <motion.button
                onClick={() => router.push("/register")}
                className={`w-full py-3 rounded-lg font-medium mb-8 transition-all duration-300 ${
                  plan.popular
                    ? "bg-gradient-to-r from-blue-600 to-emerald-500 text-white hover:shadow-lg hover:shadow-blue-500/25"
                    : "bg-neutral-700/50 text-neutral-200 border border-neutral-600/50 hover:bg-neutral-700"
                }`}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {plan.cta}
              </motion.button>

              <ul className="space-y-3">
                {Object.entries(plan.features).map(([key, value]) => (
                  <li key={key} className="flex items-center gap-3">
                    {value ? (
                      <FaCheck className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                    ) : (
                      <FaTimes className="w-4 h-4 text-neutral-600 flex-shrink-0" />
                    )}
                    <span
                      className={`text-sm ${
                        value ? "text-neutral-300" : "text-neutral-500"
                      }`}
                    >
                      {typeof value === "string"
                        ? value
                        : featureLabels[key]}
                    </span>
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </motion.div>

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
                    {plans.map((plan) => (
                      <td key={plan.name} className="py-4 px-4 text-center">
                      {typeof plan.features[key as keyof typeof plan.features] ===
                      "string" ? (
                        <span className="text-sm text-neutral-200">
                          {
                            plan.features[
                              key as keyof typeof plan.features
                            ] as string
                          }
                        </span>
                      ) : plan.features[
                          key as keyof typeof plan.features
                        ] ? (
                        <FaCheck className="w-5 h-5 text-emerald-500 mx-auto" />
                      ) : (
                        <FaTimes className="w-5 h-5 text-neutral-600 mx-auto" />
                      )}
                      </td>
                    ))}
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
