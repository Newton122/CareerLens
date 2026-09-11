"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import { FaChevronDown, FaArrowRight } from "react-icons/fa";

const faqs = [
  {
    question: "How does CareerLens match me with jobs?",
    answer:
      "Your CV is parsed into a structured profile, then each open role is scored against it. Matching runs in layers: an exact check on extracted skills, a word-boundary search of your CV text, and finally semantic similarity using embeddings, so a role asking for 'ML' can still match a CV that says 'machine learning'.",
  },
  {
    question: "Why did a skill show as missing when it is on my CV?",
    answer:
      "Usually because it appears only in prose rather than in a skills list. Listing skills as discrete items, for example 'Python, Go, Kubernetes', gives the parser a much stronger signal, especially for short names like Go, R, or C that are also ordinary English words.",
  },
  {
    question: "What does the match score actually mean?",
    answer:
      "It is a weighted blend: 50% skill coverage against the role's requirements, 30% experience alignment, and 20% education fit. Every analysis lists which skills matched and which did not, so you can see how the number was reached.",
  },
  {
    question: "Is my data safe?",
    answer:
      "Your CV and analyses are tied to your account and are only visible to you. Employers browsing candidates see profile information, never your raw uploaded file, unless you apply to their role.",
  },
  {
    question: "Can I use CareerLens for free?",
    answer:
      "Yes. The free tier covers CV upload, analysis, job discovery, and match scoring. You can also try the analyzer without an account at all from the demo page.",
  },
  {
    question: "Do I need a new CV for every application?",
    answer:
      "No, but tailoring helps. Each analysis returns specific recommendations for that role, so you can adjust one CV per application rather than rewriting from scratch.",
  },
];

export default function FAQPage() {
  const router = useRouter();
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  return (
    <div className="min-h-screen">
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
        <motion.div
          className="text-center max-w-3xl mx-auto"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <span className="text-sm font-medium text-blue-400 uppercase tracking-wider">
            FAQ
          </span>
          <h1 className="text-4xl sm:text-5xl font-bold mt-4 mb-6 leading-tight">
            Questions, <span className="gradient-text">answered</span>
          </h1>
          <p className="text-neutral-400 text-lg leading-relaxed">
            How the matching works, what the scores mean, and what happens to
            your data.
          </p>
        </motion.div>
      </section>

      <section className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 pb-20 lg:pb-32">
        <div className="space-y-3">
          {faqs.map((faq, i) => {
            const isOpen = openIndex === i;
            return (
              <motion.div
                key={faq.question}
                className={`rounded-lg border transition-colors duration-300 ${
                  isOpen
                    ? "bg-neutral-800/70 border-blue-500/30"
                    : "bg-neutral-800/50 border-neutral-700/50 hover:border-neutral-600"
                }`}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.05 }}
              >
                <button
                  onClick={() => setOpenIndex(isOpen ? null : i)}
                  aria-expanded={isOpen}
                  className="w-full flex items-center justify-between gap-4 text-left px-6 py-5"
                >
                  <h2 className="text-base font-semibold text-neutral-50">
                    {faq.question}
                  </h2>
                  <motion.span
                    animate={{ rotate: isOpen ? 180 : 0 }}
                    transition={{ duration: 0.2 }}
                    className={`shrink-0 ${
                      isOpen ? "text-blue-400" : "text-neutral-500"
                    }`}
                  >
                    <FaChevronDown className="w-4 h-4" />
                  </motion.span>
                </button>

                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.25, ease: "easeInOut" }}
                      className="overflow-hidden"
                    >
                      <p className="px-6 pb-5 text-neutral-400 text-sm leading-relaxed">
                        {faq.answer}
                      </p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </div>

        <motion.div
          className="mt-12 p-8 rounded-lg bg-neutral-800/50 border border-neutral-700/50 text-center"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
        >
          <h2 className="text-xl font-semibold text-neutral-50 mb-2">
            Still stuck?
          </h2>
          <p className="text-neutral-400 text-sm mb-6">
            Send us a message and we will get back to you, usually within a day.
          </p>
          <button
            onClick={() => router.push("/contact")}
            className="btn-primary inline-flex items-center gap-2"
          >
            Contact support
            <FaArrowRight className="w-4 h-4" />
          </button>
        </motion.div>
      </section>
    </div>
  );
}
