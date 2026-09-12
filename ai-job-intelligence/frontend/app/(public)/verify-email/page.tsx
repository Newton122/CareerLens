"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { FaCheckCircle, FaExclamationCircle } from "react-icons/fa";
import AuthCard from "@/components/AuthCard";
import { apiCall } from "@/components/api";
import { useAuth } from "@/components/AuthProvider";
import { describeApiError } from "@/components/format";

type Outcome = { ok: true } | { ok: false; message: string };

/**
 * Confirms the address from the link in the welcome email
 * (/verify-email?token=...) as soon as the page opens.
 */
function VerifyEmail() {
  const router = useRouter();
  const { token: session } = useAuth();
  const token = useSearchParams().get("token") ?? "";
  const [outcome, setOutcome] = useState<Outcome | null>(null);

  useEffect(() => {
    if (!token) return;
    let active = true;
    (async () => {
      try {
        const response = await apiCall("/api/auth/verify-email", {
          method: "POST",
          body: JSON.stringify({ token }),
        });
        const data = await response.json();
        if (!active) return;
        setOutcome(
          response.ok
            ? { ok: true }
            : { ok: false, message: describeApiError(data, "This link could not be used.") }
        );
      } catch {
        if (active) setOutcome({ ok: false, message: "Network error. Please try again." });
      }
    })();
    return () => {
      active = false;
    };
  }, [token]);

  const next = session ? "/dashboard" : "/login";
  const nextLabel = session ? "Go to your dashboard" : "Sign in";

  if (!token) {
    return (
      <AuthCard title="This link is incomplete">
        <p className="text-center text-neutral-400">
          Open the link from your email again. You can ask for a new one from your profile page.
        </p>
      </AuthCard>
    );
  }

  if (outcome === null) {
    return (
      <AuthCard title="Confirming your email…">
        <div className="flex justify-center">
          <div className="w-8 h-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
        </div>
      </AuthCard>
    );
  }

  return (
    <AuthCard title={outcome.ok ? "Email confirmed" : "We couldn't confirm your email"}>
      <div className="space-y-6 text-center">
        {outcome.ok ? (
          <FaCheckCircle className="w-12 h-12 text-emerald-400 mx-auto" />
        ) : (
          <>
            <FaExclamationCircle className="w-12 h-12 text-rose-400 mx-auto" />
            <p className="text-neutral-400">
              {outcome.message} You can send yourself a new link from your profile page.
            </p>
          </>
        )}
        <button onClick={() => router.push(next)} className="btn-primary w-full py-3">
          {nextLabel}
        </button>
      </div>
    </AuthCard>
  );
}

// useSearchParams needs a Suspense boundary so Next.js can pre-render the rest.
export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<AuthCard title="Confirming your email…">{null}</AuthCard>}>
      <VerifyEmail />
    </Suspense>
  );
}
