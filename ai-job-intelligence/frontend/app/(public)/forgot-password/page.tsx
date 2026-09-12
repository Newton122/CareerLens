"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { FaPaperPlane } from "react-icons/fa";
import AuthCard from "@/components/AuthCard";
import { apiCall } from "@/components/api";
import { describeApiError } from "@/components/format";

/**
 * Ask for a password-reset link.
 *
 * The server answers identically whether or not the address has an account
 * (so this page can't be used to find out who is registered), and this page
 * simply shows that answer.
 */
export default function ForgotPasswordPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState("");
  const [error, setError] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSending(true);
    setError("");
    try {
      const response = await apiCall("/api/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      const data = await response.json();
      if (response.ok) {
        setSent(data.message);
      } else {
        setError(describeApiError(data, "Could not send the reset link."));
      }
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSending(false);
    }
  };

  return (
    <AuthCard
      title="Forgot your password?"
      subtitle="Enter your email and we'll send you a link to choose a new one."
    >
      {sent ? (
        <div className="space-y-6 text-center">
          <p className="text-neutral-300">{sent}</p>
          <p className="text-sm text-neutral-500">
            Nothing arrived? Check your spam folder, or try again in a few minutes.
          </p>
          <button onClick={() => router.push("/login")} className="btn-primary w-full py-3">
            Back to sign in
          </button>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-neutral-300 mb-2">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="input-premium"
              required
            />
          </div>
          {error && <p className="text-sm text-rose-400">{error}</p>}
          <button
            type="submit"
            disabled={sending}
            className="btn-primary w-full flex items-center justify-center gap-2 py-3.5"
          >
            {sending ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                <FaPaperPlane className="w-4 h-4" />
                Send reset link
              </>
            )}
          </button>
          <p className="text-center text-sm text-neutral-400">
            Remembered it?{" "}
            <button
              type="button"
              onClick={() => router.push("/login")}
              className="text-blue-400 hover:text-blue-300 font-medium"
            >
              Sign in
            </button>
          </p>
        </form>
      )}
    </AuthCard>
  );
}
