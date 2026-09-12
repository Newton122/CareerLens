"use client";

import { useEffect, useState } from "react";
import { FaEnvelopeOpenText, FaTimes } from "react-icons/fa";
import { apiCall } from "@/components/api";
import { describeApiError } from "@/components/format";

/**
 * A reminder, shown at the top of the signed-in pages, until the user has
 * clicked the link in their verification email. Nothing is blocked by an
 * unconfirmed address; this only asks.
 */
export default function VerifyEmailBanner() {
  const [email, setEmail] = useState<string | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const [sending, setSending] = useState(false);
  const [note, setNote] = useState("");

  // Only unverified accounts get an email address set, which is what makes
  // the banner appear. State is set only after the request returns.
  useEffect(() => {
    let active = true;
    apiCall("/api/profile")
      .then((res) => (res.ok ? res.json() : null))
      .then((profile: { email: string; email_verified: boolean } | null) => {
        if (active && profile && !profile.email_verified) setEmail(profile.email);
      })
      .catch(() => {
        // Not worth an error message: the banner simply doesn't show.
      });
    return () => {
      active = false;
    };
  }, []);

  if (!email || dismissed) return null;

  const resend = async () => {
    setSending(true);
    try {
      const res = await apiCall("/api/auth/resend-verification", { method: "POST" });
      const data = await res.json();
      setNote(res.ok ? data.message : describeApiError(data, "Could not send the link."));
    } catch {
      setNote("Network error. Please try again.");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="mb-4 flex items-start gap-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
      <FaEnvelopeOpenText className="w-4 h-4 mt-0.5 shrink-0" />
      <div className="flex-1">
        {note || (
          <>
            Please confirm your email address. We sent a link to <strong>{email}</strong>.{" "}
            <button
              onClick={resend}
              disabled={sending}
              className="font-medium text-amber-100 underline underline-offset-2 hover:text-white disabled:opacity-50"
            >
              {sending ? "Sending…" : "Resend link"}
            </button>
          </>
        )}
      </div>
      <button
        onClick={() => setDismissed(true)}
        aria-label="Dismiss"
        className="text-amber-300/70 hover:text-amber-100"
      >
        <FaTimes className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
