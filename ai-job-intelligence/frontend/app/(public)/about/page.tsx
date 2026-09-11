"use client";

import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import {
  FaBrain,
  FaUserCheck,
  FaEye,
  FaBolt,
  FaArrowRight,
} from "react-icons/fa";

const values = [
  {
    icon: FaBrain,
    title: "AI-Powered Accuracy",
    description:
      "Semantic matching that reads past keywords to the meaning behind a skill, so a good fit is not missed over vocabulary.",
    color: "from-blue-500 to-blue-600",
  },
  {
    icon: FaUserCheck,
    title: "User-Centric Design",
    description:
      "Every screen exists to answer a real question: where do I stand, what is missing, and what should I do next?",
    color: "from-emerald-500 to-emerald-600",
  },
  {
    icon: FaEye,
    title: "Transparency",
    description:
      "Scores come with their reasoning. You always see which skills matched, which did not, and why the number moved.",
    color: "from-blue-500 to-emerald-500",
  },
  {
    icon: FaBolt,
    title: "Continuous Innovation",
    description:
      "The matching engine evolves as the market does, layering deterministic rules, embeddings, and language models.",
    color: "from-emerald-500 to-blue-600",
  },
];

export default function AboutPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen">
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
        <motion.div
          className="max-w-3xl"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <span className="text-sm font-medium text-blue-400 uppercase tracking-wider">
            About
          </span>
          <h1 className="text-4xl sm:text-5xl font-bold mt-4 mb-6 leading-tight">
            Career decisions deserve better than{" "}
            <span className="gradient-text">guesswork</span>
          </h1>
          <p className="text-neutral-400 text-lg leading-relaxed">
            CareerLens is career and hiring intelligence built on a simple
            conviction: the gap between what someone can do and what a role
            requires should be measurable, explainable, and closeable.
          </p>
        </motion.div>
      </section>

      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-16 lg:pb-24">
        <div className="grid md:grid-cols-2 gap-6">
          <motion.div
            className="p-8 rounded-lg bg-neutral-800/50 border border-neutral-700/50"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <h2 className="text-2xl font-bold text-neutral-50 mb-3">
              Our Mission
            </h2>
            <p className="text-neutral-400 leading-relaxed">
              To give job seekers and employers the same quality of career
              intelligence, making talent discovery and career development more
              intuitive, efficient, and equitable.
            </p>
          </motion.div>

          <motion.div
            className="p-8 rounded-lg bg-neutral-800/50 border border-neutral-700/50"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <h2 className="text-2xl font-bold text-neutral-50 mb-3">Our Story</h2>
            <p className="text-neutral-400 leading-relaxed">
              CareerLens started from a mismatch problem: strong candidates
              filtered out by keyword search, and employers missing people they
              would have hired. Semantic matching closes that gap from both
              sides.
            </p>
          </motion.div>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-20 lg:pb-32">
        <motion.div
          className="text-center max-w-3xl mx-auto mb-12"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          <span className="text-sm font-medium text-blue-400 uppercase tracking-wider">
            Values
          </span>
          <h2 className="text-3xl sm:text-4xl font-bold mt-4">
            What we hold to
          </h2>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-6">
          {values.map((value, i) => (
            <motion.div
              key={value.title}
              className="group p-6 rounded-lg bg-neutral-800/50 border border-neutral-700/50 hover:border-blue-500/30 transition-all duration-300"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08 }}
              whileHover={{ y: -5 }}
            >
              <div
                className={`w-12 h-12 rounded-lg bg-gradient-to-br ${value.color} flex items-center justify-center mb-4 shadow-lg group-hover:scale-110 transition-transform duration-300`}
              >
                <value.icon className="w-5 h-5 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-neutral-50 mb-2">
                {value.title}
              </h3>
              <p className="text-neutral-400 text-sm leading-relaxed">
                {value.description}
              </p>
            </motion.div>
          ))}
        </div>

        <motion.div
          className="mt-16 text-center"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
        >
          <button
            onClick={() => router.push("/register")}
            className="btn-primary inline-flex items-center gap-2"
          >
            Get started free
            <FaArrowRight className="w-4 h-4" />
          </button>
        </motion.div>
      </section>
    </div>
  );
}
