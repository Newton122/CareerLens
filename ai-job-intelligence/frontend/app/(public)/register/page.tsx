"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { apiCall } from "@/components/api";
import {
  describeApiError,
  PASSWORD_MIN_LENGTH,
  passwordHint,
} from "@/components/format";
import MessageDialog from "@/components/MessageDialog";
import {
  FaUser,
  FaBuilding,
  FaArrowRight,
  FaArrowLeft,
  FaCheck,
  FaEye,
  FaEyeSlash,
} from "react-icons/fa";

type Role = "job_seeker" | "employer";

export default function RegisterPage() {
  const router = useRouter();
  const [role, setRole] = useState<Role | null>(null);
  const [step, setStep] = useState(1);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [dialog, setDialog] = useState<{
    open: boolean;
    title: string;
    message: string;
    type: "info" | "success" | "error" | "warning";
  }>({
    open: false,
    title: "",
    message: "",
    type: "info",
  });

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      const response = await apiCall("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, name, role }),
      });
      const data = await response.json();
      if (response.ok) {
        localStorage.setItem("careerLens_role", role || "job_seeker");
        setDialog({
          open: true,
          title: "Success",
          message: "Account created! Please log in.",
          type: "success",
        });
        router.push("/login");
      } else {
        setDialog({
          open: true,
          title: "Error",
          message: describeApiError(data, "Registration failed"),
          type: "error",
        });
      }
    } catch (err) {
      setDialog({
        open: true,
        title: "Error",
        message: err instanceof Error ? err.message : "Something went wrong",
        type: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-neutral-900">
      <div className="flex min-h-screen">
        <motion.div
          className="hidden lg:flex lg:w-1/2 relative overflow-hidden"
          initial={{ opacity: 0, x: -50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8 }}
        >
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/30 via-emerald-600/20 to-blue-600/30" />
          <div className="absolute top-1/3 -left-20 w-96 h-96 bg-emerald-500/20 rounded-full blur-3xl" />
          <div className="absolute bottom-1/3 -right-20 w-96 h-96 bg-blue-600/20 rounded-full blur-3xl" />

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
                Start your
                <br />
                <span className="gradient-text">career journey</span>
              </h1>
              <p className="text-lg text-neutral-400 mb-8">
                Join thousands of professionals finding their perfect career
                match with AI.
              </p>
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

            <AnimatePresence mode="wait">
              {step === 1 && (
                <motion.div
                  key="step1"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.3 }}
                >
                  <div className="text-center mb-8">
                    <h2 className="text-2xl font-bold text-neutral-50 mb-2">
                      What brings you here?
                    </h2>
                    <p className="text-neutral-400">
                      Choose the experience that&apos;s right for you
                    </p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
                    <motion.button
                      onClick={() => setRole("job_seeker")}
                      className={`relative p-6 rounded-lg text-left transition-all duration-300 ${
                        role === "job_seeker"
                          ? "bg-blue-600/10 border-2 border-blue-500/50"
                          : "bg-neutral-800/50 border border-neutral-700/50 hover:border-neutral-600"
                      }`}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      {role === "job_seeker" && (
                        <div className="absolute top-3 right-3 w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center">
                          <FaCheck className="w-3 h-3 text-white" />
                        </div>
                      )}
                      <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-blue-600 to-emerald-500 flex items-center justify-center mb-4">
                        <FaUser className="w-6 h-6 text-white" />
                      </div>
                      <h3 className="text-lg font-semibold text-neutral-50 mb-2">
                        I&apos;m looking for a job
                      </h3>
                      <p className="text-sm text-neutral-400 mb-4">
                        Find jobs that match your skills with AI analysis
                      </p>
                      <ul className="space-y-2">
                        {[
                          "AI CV analysis",
                          "Personalized matching",
                          "Skill-gap insights",
                        ].map((item) => (
                          <li
                            key={item}
                            className="flex items-center gap-2 text-sm text-neutral-300"
                          >
                            <FaCheck className="w-3 h-3 text-emerald-500" />
                            {item}
                          </li>
                        ))}
                      </ul>
                    </motion.button>

                    <motion.button
                      onClick={() => setRole("employer")}
                      className={`relative p-6 rounded-lg text-left transition-all duration-300 ${
                        role === "employer"
                          ? "bg-emerald-500/10 border-2 border-emerald-500/50"
                          : "bg-neutral-800/50 border border-neutral-700/50 hover:border-neutral-600"
                      }`}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      {role === "employer" && (
                        <div className="absolute top-3 right-3 w-6 h-6 rounded-full bg-emerald-500 flex items-center justify-center">
                          <FaCheck className="w-3 h-3 text-white" />
                        </div>
                      )}
                      <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center mb-4">
                        <FaBuilding className="w-6 h-6 text-white" />
                      </div>
                      <h3 className="text-lg font-semibold text-neutral-50 mb-2">
                        I&apos;m hiring
                      </h3>
                      <p className="text-sm text-neutral-400 mb-4">
                        Find qualified candidates with AI matching
                      </p>
                      <ul className="space-y-2">
                        {[
                          "Create job listings",
                          "AI candidate matching",
                          "Review candidates",
                        ].map((item) => (
                          <li
                            key={item}
                            className="flex items-center gap-2 text-sm text-neutral-300"
                          >
                            <FaCheck className="w-3 h-3 text-emerald-500" />
                            {item}
                          </li>
                        ))}
                      </ul>
                    </motion.button>
                  </div>

                  <motion.button
                    onClick={() => role && setStep(2)}
                    disabled={!role}
                    className="btn-primary w-full flex items-center justify-center gap-2 py-3.5 disabled:opacity-50 disabled:cursor-not-allowed"
                    whileHover={{ scale: role ? 1.01 : 1 }}
                    whileTap={{ scale: role ? 0.99 : 1 }}
                  >
                    Continue
                    <FaArrowRight className="w-4 h-4" />
                  </motion.button>

                  <p className="mt-6 text-center text-neutral-400">
                    Already have an account?{" "}
                    <button
                      onClick={() => router.push("/login")}
                      className="text-blue-400 hover:text-blue-300 font-medium transition-colors"
                    >
                      Log in
                    </button>
                  </p>
                </motion.div>
              )}

              {step === 2 && (
                <motion.div
                  key="step2"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.3 }}
                >
                  <button
                    onClick={() => setStep(1)}
                    className="flex items-center gap-2 text-neutral-400 hover:text-neutral-200 mb-6 transition-colors"
                  >
                    <FaArrowLeft className="w-4 h-4" />
                    Change role
                  </button>

                  <div className="text-center mb-8">
                    <h2 className="text-2xl font-bold text-neutral-50 mb-2">
                      Create your account
                    </h2>
                    <p className="text-neutral-400">
                      Role:{" "}
                      <span className="text-blue-400">
                        {role === "job_seeker" ? "Job Seeker" : "Employer"}
                      </span>
                    </p>
                  </div>

                  <form onSubmit={handleRegister} className="space-y-5">
                    <div>
                      <label className="block text-sm font-medium text-neutral-300 mb-2">
                        Full Name
                      </label>
                      <input
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="Your name"
                        className="input-premium"
                        required
                      />
                    </div>

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
                      <label className="block text-sm font-medium text-neutral-300 mb-2">
                        Password
                      </label>
                      <div className="relative">
                        <input
                          type={showPassword ? "text" : "password"}
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          placeholder="At least 10 characters"
                          className="input-premium pr-12"
                          required
                          minLength={PASSWORD_MIN_LENGTH}
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
                      {/* Instant feedback so the policy is not discovered only
                          after submitting the form. */}
                      {passwordHint(password) ? (
                        <p className="mt-2 text-xs text-amber-300">
                          {passwordHint(password)}
                        </p>
                      ) : (
                        password && (
                          <p className="mt-2 text-xs text-emerald-300">
                            Looks good. A memorable phrase beats a short complex
                            password.
                          </p>
                        )
                      )}
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
                          Create Account
                          <FaArrowRight className="w-4 h-4" />
                        </>
                      )}
                    </motion.button>
                  </form>

                  <p className="mt-6 text-center text-neutral-400">
                    Already have an account?{" "}
                    <button
                      onClick={() => router.push("/login")}
                      className="text-blue-400 hover:text-blue-300 font-medium transition-colors"
                    >
                      Log in
                    </button>
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </div>
      </div>

      <MessageDialog
        open={dialog.open}
        onClose={() => setDialog({ ...dialog, open: false })}
        title={dialog.title}
        message={dialog.message}
        type={dialog.type}
      />
    </div>
  );
}
