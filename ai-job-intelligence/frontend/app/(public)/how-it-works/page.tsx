"use client";

import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import {
  FaUpload,
  FaBrain,
  FaSearch,
  FaChartLine,
  FaPaperPlane,
  FaArrowRight,
} from "react-icons/fa";

const steps = [
  {
    icon: FaUpload,
    title: "Upload your CV",
    description:
      "Drop in a PDF, text file, or even a photo. CareerLens extracts the text and reads it into a structured profile.",
    color: "from-blue-500 to-blue-600",
  },
  {
    icon: FaBrain,
    title: "Get analyzed",
    description:
      "Skills, experience, education, projects, and certifications are pulled out and scored for completeness.",
    color: "from-emerald-500 to-emerald-600",
  },
  {
    icon: FaSearch,
    title: "Discover matching roles",
    description:
      "Every open role is scored against your profile, so the list you see is ranked by genuine fit rather than recency.",
    color: "from-blue-500 to-emerald-500",
  },
  {
    icon: FaChartLine,
    title: "Close your skill gaps",
    description:
      "See exactly which skills you are missing, ranked by how often real open roles ask for them.",
    color: "from-emerald-500 to-blue-600",
  },
  {
    icon: FaPaperPlane,
    title: "Apply and track",
    description:
      "Apply from inside CareerLens and follow every application through one pipeline instead of a spreadsheet.",
    color: "from-blue-600 to-emerald-500",
  },
];

export default function HowItWorksPage() {
  const router = useRouter();

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
            How it works
          </span>
          <h1 className="text-4xl sm:text-5xl font-bold mt-4 mb-6 leading-tight">
            From CV to offer, in{" "}
            <span className="gradient-text">five steps</span>
          </h1>
          <p className="text-neutral-400 text-lg leading-relaxed">
            No black box. Each stage tells you what it found and what it means
            for your next move.
          </p>
        </motion.div>
      </section>

      <section className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pb-20 lg:pb-32">
        <div className="relative">
          {/* Spine connecting the steps on large screens. */}
          <div
            className="hidden sm:block absolute left-6 top-6 bottom-6 w-px bg-gradient-to-b from-blue-500/40 via-emerald-500/30 to-transparent"
            aria-hidden="true"
          />

          <div className="space-y-6">
            {steps.map((step, i) => (
              <motion.div
                key={step.title}
                className="group relative flex gap-5 p-6 rounded-lg bg-neutral-800/50 border border-neutral-700/50 hover:border-blue-500/30 transition-all duration-300"
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.08 }}
              >
                <div className="shrink-0">
                  <div
                    className={`w-12 h-12 rounded-lg bg-gradient-to-br ${step.color} flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform duration-300`}
                  >
                    <step.icon className="w-5 h-5 text-white" />
                  </div>
                </div>
                <div className="min-w-0">
                  <div className="flex items-baseline gap-3 mb-2">
                    <span className="text-xs font-semibold text-blue-400 tabular-nums">
                      STEP {i + 1}
                    </span>
                  </div>
                  <h2 className="text-lg font-semibold text-neutral-50 mb-2">
                    {step.title}
                  </h2>
                  <p className="text-neutral-400 text-sm leading-relaxed">
                    {step.description}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        <motion.div
          className="mt-16 text-center"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
        >
          <p className="text-neutral-400 mb-6">
            Want to see it before signing up?
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <button
              onClick={() => router.push("/demo-analysis")}
              className="btn-secondary inline-flex items-center gap-2"
            >
              Try the live demo
            </button>
            <button
              onClick={() => router.push("/register")}
              className="btn-primary inline-flex items-center gap-2"
            >
              Create free account
              <FaArrowRight className="w-4 h-4" />
            </button>
          </div>
        </motion.div>
      </section>
    </div>
  );
}
