"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { FaKey } from "react-icons/fa";
import AuthCard from "@/components/AuthCard";
import { apiCall } from "@/components/api";
import { describeApiError, passwordHint } from "@/components/format";

/**
 * Choose a new password, from the link in the reset email
 * (/reset-password?token=...). Resetting signs the account out on every
 * device, so the next step is always "sign in".
 */
function ResetPasswordForm() {
  const router = useRouter();
  const token = useSearchParams().get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  if (!token) {
    return (
      <AuthCard title="This link is incomplete">
        <div className="space-y-6 text-center">
          <p className="text-neutral-400">
            Open the link from your email again, or ask for a new one.
          </p>
          <button onClick={() => router.push("/forgot-password")} className="btn-primary w-full py-3">
            Request a new link
          </button>
        </div>
      </AuthCard>
    );
  }

  if (done) {
    return (
      <AuthCard title="Password changed" subtitle="You've been signed out everywhere, for safety.">
        <button onClick={() => router.push("/login")} className="btn-primary w-full py-3">
          Sign in with your new password
        </button>
      </AuthCard>
    );
  }

  const hint = passwordHint(password);
  const mismatch = confirm.length > 0 && confirm !== password;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirm) {
      setError("The two passwords don't match.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const response = await apiCall("/api/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ token, password }),
      });
      const data = await response.json();
      if (response.ok) {
        setDone(true);
      } else {
        setError(describeApiError(data, "Could not change your password."));
      }
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <AuthCard title="Choose a new password" subtitle="At least 10 characters. A short phrase works well.">
      <form onSubmit={submit} className="space-y-5">
        <div>
          <label className="block text-sm font-medium text-neutral-300 mb-2">New password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input-premium"
            autoComplete="new-password"
            required
          />
          {hint && <p className="text-xs text-amber-400 mt-2">{hint}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-neutral-300 mb-2">Repeat it</label>
          <input
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            className="input-premium"
            autoComplete="new-password"
            required
          />
          {mismatch && <p className="text-xs text-amber-400 mt-2">The two passwords don&apos;t match yet.</p>}
        </div>
        {error && (
          <div className="text-sm text-rose-400 space-y-2">
            <p>{error}</p>
            {/expired|invalid/i.test(error) && (
              <button
                type="button"
                onClick={() => router.push("/forgot-password")}
                className="text-blue-400 hover:text-blue-300 font-medium"
              >
                Request a new link
              </button>
            )}
          </div>
        )}
        <button
          type="submit"
          disabled={saving}
          className="btn-primary w-full flex items-center justify-center gap-2 py-3.5"
        >
          {saving ? (
            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <>
              <FaKey className="w-4 h-4" />
              Change password
            </>
          )}
        </button>
      </form>
    </AuthCard>
  );
}

// useSearchParams needs a Suspense boundary so Next.js can pre-render the rest.
export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<AuthCard title="Choose a new password">{null}</AuthCard>}>
      <ResetPasswordForm />
    </Suspense>
  );
}
