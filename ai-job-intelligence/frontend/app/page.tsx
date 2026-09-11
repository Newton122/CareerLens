"use client";

import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { motion } from "framer-motion";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import {
  FaRocket,
  FaSearch,
  FaBrain,
  FaChartLine,
  FaCheck,
  FaArrowRight,
  FaShieldAlt,
  FaBolt,
  FaGlobe,
} from "react-icons/fa";

const fadeInUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.6 },
};

const staggerContainer = {
  initial: { opacity: 0 },
  animate: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const staggerItem = {
  initial: { opacity: 0, y: 30 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true },
  transition: { duration: 0.5 },
};

const features = [
  {
    icon: FaBrain,
    title: "AI-Powered CV Analysis",
    description:
      "Our AI understands your skills, experience, and potential beyond keywords.",
    color: "from-blue-500 to-blue-600",
  },
  {
    icon: FaSearch,
    title: "Smart Job Discovery",
    description:
      "Find opportunities from multiple sources, ranked by your actual fit.",
    color: "from-emerald-500 to-teal-600",
  },
  {
    icon: FaChartLine,
    title: "Skill-Gap Insights",
    description:
      "Know exactly what skills to develop and how to improve your profile.",
    color: "from-emerald-500 to-teal-600",
  },
  {
    icon: FaShieldAlt,
    title: "Match Score Transparency",
    description:
      "See exactly why you match a role and what employers are looking for.",
    color: "from-amber-500 to-orange-600",
  },
  {
    icon: FaBolt,
    title: "Instant Recommendations",
    description:
      "Get personalized suggestions for CV improvements and career moves.",
    color: "from-rose-500 to-pink-600",
  },
  {
    icon: FaGlobe,
    title: "Multi-Source Jobs",
    description:
      "Access opportunities from job boards, companies, and direct postings.",
    color: "from-cyan-500 to-blue-600",
  },
];

const howItWorks = [
  {
    step: "01",
    title: "Build Your Profile",
    description:
      "Upload your CV and let our AI understand your unique skills, experience, education, and project history.",
  },
  {
    step: "02",
    title: "Discover Opportunities",
    description:
      "CareerLens finds and ranks relevant jobs based on your actual profile, not just keywords.",
  },
  {
    step: "03",
    title: "Apply with Confidence",
    description:
      "See your match score, missing skills, and AI recommendations before you apply anywhere.",
  },
  {
    step: "04",
    title: "Grow Your Career",
    description:
      "Track your progress, get insights, and continuously improve your career trajectory.",
  },
];

const pricingPlans = [
  {
    name: "Starter",
    price: "Free",
    description: "Perfect for exploring opportunities",
    features: [
      "1 CV upload",
      "Basic AI analysis",
      "Limited job matches",
      "Match score insights",
    ],
    cta: "Get Started",
    href: "/register",
    popular: false,
  },
  {
    name: "Professional",
    price: "$29",
    period: "/month",
    description: "For serious job seekers",
    features: [
      "Unlimited CVs",
      "Advanced AI insights",
      "Priority job matching",
      "Skill-gap analysis",
      "Cover letter generation",
      "Career recommendations",
    ],
    cta: "Start Free Trial",
    href: "/register",
    popular: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    description: "For teams and organizations",
    features: [
      "Everything in Pro",
      "Team management",
      "Analytics dashboard",
      "API access",
      "Dedicated support",
      "Custom integrations",
    ],
    cta: "Contact Sales",
    href: "/contact",
    popular: false,
  },
];

export default function Home() {
  const router = useRouter();
  const { token } = useAuth();

  return (
    <div className="min-h-screen bg-neutral-900 text-neutral-50">
      <Navbar />

      <main className="pt-20">
        <motion.section
          className="relative overflow-hidden"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8 }}
        >
          <div className="absolute inset-0 bg-gradient-to-b from-blue-600/10 via-transparent to-transparent" />
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[800px] bg-gradient-to-r from-blue-500/20 to-emerald-500/20 rounded-full blur-3xl" />

          <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-32">
            <div className="text-center max-w-4xl mx-auto">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.1 }}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-neutral-800/50 border border-neutral-700/50 text-sm text-neutral-300 mb-8"
              >
                <span>AI-Powered Career Intelligence</span>
              </motion.div>

              <motion.h1
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.2 }}
                className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight mb-6"
              >
                Find Your Perfect{" "}
                <span className="gradient-text">Career Match</span>{" "}
                with AI
              </motion.h1>

              <motion.p
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.3 }}
                className="text-lg sm:text-xl text-neutral-400 max-w-2xl mx-auto mb-10"
              >
                Stop applying blindly. CareerLens uses AI to understand your
                unique profile and connect you with opportunities that truly fit
                your skills and potential.
              </motion.p>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.4 }}
                className="flex flex-col sm:flex-row items-center justify-center gap-4"
              >
                <motion.button
                  onClick={() => router.push(token ? "/dashboard" : "/register")}
                  className="btn-primary text-lg px-8 py-4 flex items-center gap-2 w-full sm:w-auto justify-center"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <FaRocket className="w-5 h-5" />
                  {token ? "Go to Dashboard" : "Get Started Free"}
                </motion.button>
                <motion.button
                  onClick={() => router.push("/how-it-works")}
                  className="btn-secondary text-lg px-8 py-4 w-full sm:w-auto"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  See How It Works
                </motion.button>
                <motion.button
                  onClick={() => router.push("/demo-analysis")}
                  className="text-sm px-4 py-2 text-blue-400 hover:text-blue-300 underline underline-offset-4"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  Try Demo Analysis
                </motion.button>
              </motion.div>

              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.6, delay: 0.6 }}
                className="flex flex-wrap items-center justify-center gap-6 mt-10 text-sm text-neutral-400"
              >
                <span className="flex items-center gap-2">
                  <FaCheck className="w-4 h-4 text-emerald-500" />
                  Free to start
                </span>
                <span className="flex items-center gap-2">
                  <FaCheck className="w-4 h-4 text-emerald-500" />
                  AI-powered matching
                </span>
                <span className="flex items-center gap-2">
                  <FaCheck className="w-4 h-4 text-emerald-500" />
                  No credit card required
                </span>
              </motion.div>
            </div>
          </div>
        </motion.section>

        <motion.section
          id="features"
          className="py-20 lg:py-32"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <motion.div
              className="text-center max-w-3xl mx-auto mb-16"
              {...fadeInUp}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              initial={{ opacity: 0, y: 20 }}
            >
              <span className="text-sm font-medium text-blue-400 uppercase tracking-wider">
                Features
              </span>
              <h2 className="text-3xl sm:text-4xl font-bold mt-4 mb-4">
                Everything You Need to Land Your{" "}
                <span className="gradient-text">Dream Job</span>
              </h2>
              <p className="text-neutral-400 text-lg">
                Powerful AI tools that give you clarity, confidence, and a
                competitive edge in your job search.
              </p>
            </motion.div>

            <motion.div
              className="grid md:grid-cols-2 lg:grid-cols-3 gap-6"
              variants={staggerContainer}
              initial="initial"
              whileInView="animate"
              viewport={{ once: true }}
            >
              {features.map((feature) => (
                <motion.div
                  key={feature.title}
                  variants={staggerItem}
                  whileHover={{ y: -5, transition: { duration: 0.2 } }}
                  className="group p-6 rounded-lg bg-neutral-800/50 border border-neutral-700/50 hover:border-blue-500/30 transition-all duration-300"
                >
                  <div
                    className={`w-12 h-12 rounded-lg bg-gradient-to-br ${feature.color} flex items-center justify-center mb-4 shadow-lg group-hover:scale-110 transition-transform duration-300`}
                  >
                    <feature.icon className="w-6 h-6 text-white" />
                  </div>
                  <h3 className="text-lg font-semibold text-neutral-50 mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-neutral-400 text-sm leading-relaxed">
                    {feature.description}
                  </p>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </motion.section>

        <motion.section className="py-20 lg:py-32 bg-neutral-800/30">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <motion.div
              className="text-center max-w-3xl mx-auto mb-16"
              {...fadeInUp}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              initial={{ opacity: 0, y: 20 }}
            >
              <span className="text-sm font-medium text-blue-400 uppercase tracking-wider">
                How It Works
              </span>
              <h2 className="text-3xl sm:text-4xl font-bold mt-4 mb-4">
                Your Journey to the Perfect Role
              </h2>
              <p className="text-neutral-400 text-lg">
                Four simple steps to transform your career search with AI.
              </p>
            </motion.div>

            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
              {howItWorks.map((item, index) => (
                <motion.div
                  key={item.step}
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                  className="relative p-6 rounded-lg bg-neutral-800/50 border border-neutral-700/50"
                >
                  <span className="text-5xl font-black text-neutral-700/50">
                    {item.step}
                  </span>
                  <h3 className="text-lg font-semibold text-neutral-50 mt-2 mb-2">
                    {item.title}
                  </h3>
                  <p className="text-neutral-400 text-sm leading-relaxed">
                    {item.description}
                  </p>
                  {index < howItWorks.length - 1 && (
                    <FaArrowRight className="hidden lg:block absolute top-1/2 -right-5 w-5 h-5 text-neutral-600" />
                  )}
                </motion.div>
              ))}
            </div>
          </div>
        </motion.section>

        <motion.section
          id="for-job-seekers"
          className="py-20 lg:py-32"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
        >
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-3xl mx-auto">
              <motion.div
                initial={{ opacity: 0, x: -30 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6 }}
              >
                <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-600/10 border border-blue-500/20 text-sm text-blue-400 mb-6">
                  For Job Seekers
                </span>
                <h2 className="text-3xl sm:text-4xl font-bold mb-4">
                  Stop Applying Blindly
                </h2>
                <p className="text-neutral-400 text-lg mb-8">
                  Know which jobs fit your profile, what you&apos;re missing, and
                  what to improve before sending your application.
                </p>
                <ul className="space-y-4">
                  {[
                    "AI-powered CV analysis",
                    "Personalized job matching",
                    "Skill-gap analysis",
                    "AI application recommendations",
                    "Job discovery from multiple sources",
                  ].map((item) => (
                    <li key={item} className="flex items-center gap-3">
                      <div className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
                        <FaCheck className="w-3 h-3 text-emerald-500" />
                      </div>
                      <span className="text-neutral-300">{item}</span>
                    </li>
                  ))}
                </ul>
              </motion.div>
            </div>
          </div>
        </motion.section>

        <motion.section
          id="for-employers"
          className="py-20 lg:py-32 bg-neutral-800/30"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
        >
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-3xl mx-auto">
              <motion.div
                initial={{ opacity: 0, x: 30 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6 }}
              >
                <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-sm text-emerald-400 mb-6">
                  For Employers
                </span>
                <h2 className="text-3xl sm:text-4xl font-bold mb-4">
                  Find Candidates Who Actually Fit
                </h2>
                <p className="text-neutral-400 text-lg mb-8">
                  Post a role and let AI help you understand, rank, and
                  shortlist candidates based on the requirements that matter.
                </p>
                <ul className="space-y-4">
                  {[
                    "Create and manage job listings",
                    "AI candidate matching",
                    "Candidate skill analysis",
                    "Shortlist candidates faster",
                  ].map((item) => (
                    <li key={item} className="flex items-center gap-3">
                      <div className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
                        <FaCheck className="w-3 h-3 text-emerald-500" />
                      </div>
                      <span className="text-neutral-300">{item}</span>
                    </li>
                  ))}
                </ul>
              </motion.div>
            </div>
          </div>
        </motion.section>

        <motion.section className="py-20 lg:py-32">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <motion.div
              className="text-center max-w-3xl mx-auto mb-16"
              {...fadeInUp}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              initial={{ opacity: 0, y: 20 }}
            >
              <span className="text-sm font-medium text-blue-400 uppercase tracking-wider">
                Pricing
              </span>
              <h2 className="text-3xl sm:text-4xl font-bold mt-4 mb-4">
                Simple, Transparent Pricing
              </h2>
              <p className="text-neutral-400 text-lg">
                Start free and scale as you grow. No hidden fees.
              </p>
            </motion.div>

            <motion.div
              className="grid md:grid-cols-3 gap-6 lg:gap-8"
              variants={staggerContainer}
              initial="initial"
              whileInView="animate"
              viewport={{ once: true }}
            >
              {pricingPlans.map((plan) => (
                <motion.div
                  key={plan.name}
                  variants={staggerItem}
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
                        Most Popular
                      </span>
                    </div>
                  )}
                  <h3 className="text-xl font-semibold text-neutral-50 mb-2">
                    {plan.name}
                  </h3>
                  <div className="flex items-baseline gap-1 mb-2">
                    <span className="text-4xl font-bold text-neutral-50">
                      {plan.price}
                    </span>
                    {plan.period && (
                      <span className="text-neutral-400">{plan.period}</span>
                    )}
                  </div>
                  <p className="text-neutral-400 text-sm mb-6">
                    {plan.description}
                  </p>
                  <ul className="space-y-3 mb-8">
                    {plan.features.map((feature) => (
                      <li key={feature} className="flex items-center gap-3">
                        <FaCheck className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                        <span className="text-neutral-300 text-sm">{feature}</span>
                      </li>
                    ))}
                  </ul>
                  <motion.button
                    onClick={() => router.push(plan.href)}
                    className={`w-full py-3 rounded-lg font-medium transition-all duration-300 ${
                      plan.popular
                        ? "bg-gradient-to-r from-blue-600 to-emerald-500 text-white hover:shadow-lg hover:shadow-blue-500/25"
                        : "bg-neutral-700/50 text-neutral-200 border border-neutral-600/50 hover:bg-neutral-700"
                    }`}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    {plan.cta}
                  </motion.button>
                </motion.div>
              ))}
            </motion.div>

            <motion.div
              className="text-center mt-8"
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
            >
              <a
                href="/pricing"
                className="text-blue-400 hover:text-blue-300 text-sm font-medium inline-flex items-center gap-2 transition-colors"
              >
                View full comparison
                <FaArrowRight className="w-4 h-4" />
              </a>
            </motion.div>
          </div>
        </motion.section>

        <motion.section className="py-20 lg:py-32 relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-600/20 via-emerald-600/20 to-teal-600/20" />
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(99,102,241,0.15),transparent_70%)]" />
          <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
            >
              <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-4">
                Ready to Transform Your Career?
              </h2>
              <p className="text-lg text-neutral-400 mb-8 max-w-2xl mx-auto">
                Join thousands of professionals who found their perfect career
                match with CareerLens.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <motion.button
                  onClick={() => router.push("/register")}
                  className="btn-primary text-lg px-8 py-4 flex items-center gap-2"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <FaRocket className="w-5 h-5" />
                  Get Started for Free
                </motion.button>
                <motion.button
                  onClick={() => router.push("/contact")}
                  className="btn-secondary text-lg px-8 py-4"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  Talk to Sales
                </motion.button>
              </div>
            </motion.div>
          </div>
        </motion.section>
      </main>

      <Footer />
    </div>
  );
}
