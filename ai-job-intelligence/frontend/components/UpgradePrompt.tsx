"use client";

import { useRouter } from "next/navigation";
import { FaCrown, FaCheck } from "react-icons/fa";
import MessageDialog from "@/components/MessageDialog";

/**
 * Shown where the API answered 402: the user is signed in, but their plan
 * doesn't include this. The server has already refused; this only explains
 * why and offers the way forward.
 */
export default function UpgradePrompt({
  title,
  message,
  perks = [],
  badge = "Pro feature",
}: {
  title: string;
  message: string;
  perks?: string[];
  badge?: string;
}) {
  const router = useRouter();
  return (
    <div className="card border-indigo-500/30 bg-gradient-to-br from-indigo-500/10 via-neutral-900 to-neutral-900">
      <div className="flex items-start gap-4">
        <div className="w-11 h-11 shrink-0 rounded-lg bg-gradient-to-br from-blue-600 to-emerald-500 flex items-center justify-center">
          <FaCrown className="w-5 h-5 text-white" />
        </div>
        <div className="min-w-0">
          <span className="chip-accent mb-2">{badge}</span>
          <h2 className="section-title mt-2">{title}</h2>
          <p className="body-text mt-1">{message}</p>
          {perks.length > 0 && (
            <ul className="mt-4 space-y-2">
              {perks.map((perk) => (
                <li key={perk} className="flex items-center gap-2 text-sm text-neutral-300">
                  <FaCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  {perk}
                </li>
              ))}
            </ul>
          )}
          <div className="flex flex-wrap gap-3 mt-5">
            <button onClick={() => router.push("/pricing")} className="btn-primary">
              See Pro plans
            </button>
            <button onClick={() => router.push("/billing")} className="btn-ghost">
              View my usage
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/** The same message as a dialog, for actions (upload, analyse) that hit a limit. */
export function UpgradeDialog({
  message,
  onClose,
}: {
  message: string | null;
  onClose: () => void;
}) {
  const router = useRouter();
  return (
    <MessageDialog
      open={message !== null}
      onClose={onClose}
      title="Plan limit reached"
      message={message ?? ""}
      type="info"
      confirmText="See Pro plans"
      cancelText="Not now"
      onConfirm={() => router.push("/pricing")}
    />
  );
}
