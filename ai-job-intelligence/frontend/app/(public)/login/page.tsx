"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { motion } from "framer-motion";
import {
  FaSignInAlt,
  FaEye,
  FaEyeSlash,
  FaArrowRight,
  FaShieldAlt,
  FaBolt,
  FaChartLine,
} from "react-icons/fa";

export default function LoginPage() {
  const router = useRouter();
  const { login, loading } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const features = [
    { icon: FaBolt, text: "AI-Powered Job Matching" },
    { icon: FaChartLine, text: "Career Intelligence" },
    { icon: FaShieldAlt, text: "Secure & Private" },
  ];

  return (
    <div className="min-h-screen bg-neutral-900 flex">
      <motion.div
        className="hidden lg:flex lg:w-1/2 relative overflow-hidden"
        initial={{ opacity: 0, x: -50 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.8 }}
      >
        <div className="absolute inset-0 bg-gradient-to-br from-blue-600/30 via-emerald-600/20 to-emerald-600/30" />
        <div className="absolute top-1/4 -left-20 w-96 h-96 bg-blue-600/20 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 -right-20 w-96 h-96 bg-emerald-500/20 rounded-full blur-3xl" />

        <div className="relative flex flex-col justify-center px-16 py-12">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.6 }}
          >
            <div
              className="flex items-center gap-3 mb-12 cursor-pointer"
              onClick={() => router.push("/")}
            >
              <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-blue-600 to-emerald-500 flex items-center justify-center shadow-lg shadow-blue-500/25">
                <span className="text-white font-black text-xl">C</span>
              </div>
              <span className="text-2xl font-bold text-neutral-50">
                Career<span className="text-blue-400">Lens</span>
              </span>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, duration: 0.6 }}
          >
            <h1 className="text-4xl font-bold text-neutral-50 mb-4">
              Welcome back to
              <br />
              <span className="gradient-text">CareerLens</span>
            </h1>
            <p className="text-lg text-neutral-400 mb-8">
              Sign in to continue your career journey with AI-powered insights.
            </p>
          </motion.div>

          <motion.div
            className="space-y-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.6 }}
          >
            {features.map((feature) => (
              <div key={feature.text} className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-neutral-800/50 border border-neutral-700/50 flex items-center justify-center">
                  <feature.icon className="w-5 h-5 text-blue-400" />
                </div>
                <span className="text-neutral-300">{feature.text}</span>
              </div>
            ))}
          </motion.div>
        </div>
      </motion.div>

      <div className="w-full lg:w-1/2 flex items-center justify-center p-8">
        <motion.div
          className="w-full max-w-md"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <div className="lg:hidden flex items-center gap-3 mb-8 justify-center">
            <div
              className="flex items-center gap-2 cursor-pointer"
              onClick={() => router.push("/")}
            >
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-600 to-emerald-500 flex items-center justify-center shadow-lg shadow-blue-500/25">
                <span className="text-white font-black text-lg">C</span>
              </div>
              <span className="text-xl font-bold text-neutral-50">
                Career<span className="text-blue-400">Lens</span>
              </span>
            </div>
          </div>

          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-neutral-50 mb-2">
              Welcome back
            </h2>
            <p className="text-neutral-400">Sign in to your account</p>
          </div>

          <form
            onSubmit={async (e) => {
              e.preventDefault();
              await login(email, password);
            }}
            className="space-y-5"
          >
            <div>
              <label className="block text-sm font-medium text-neutral-300 mb-2">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="input-premium"
                required
              />
            </div>

            <div>
              <div className="flex items-baseline justify-between mb-2">
                <label className="block text-sm font-medium text-neutral-300">
                  Password
                </label>
                <button
                  type="button"
                  onClick={() => router.push("/forgot-password")}
                  className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
                >
                  Forgot password?
                </button>
              </div>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="input-premium pr-12"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-200 transition-colors"
                >
                  {showPassword ? (
                    <FaEyeSlash className="w-5 h-5" />
                  ) : (
                    <FaEye className="w-5 h-5" />
                  )}
                </button>
              </div>
            </div>

            <motion.button
              type="submit"
              disabled={loading}
              className="btn-primary w-full flex items-center justify-center gap-2 py-3.5"
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <FaSignInAlt className="w-4 h-4" />
                  Sign In
                  <FaArrowRight className="w-4 h-4" />
                </>
              )}
            </motion.button>
          </form>

          <div className="mt-8 text-center text-neutral-400">
            Don&apos;t have an account?{" "}
            <button
              onClick={() => router.push("/register")}
              className="text-blue-400 hover:text-blue-300 font-medium transition-colors"
            >
              Create one free
            </button>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
