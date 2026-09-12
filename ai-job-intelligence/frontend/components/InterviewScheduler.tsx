"use client";

/**
 * Book an interview, or correct one already booked.
 *
 * The form is organised around how the two sides will actually meet, because
 * that is the decision the employer is really making. Choosing the mode
 * changes what the form asks for: a video call needs a link, a phone call
 * needs a number, an on-site interview needs an address. Asking for all three
 * at once produced interviews with a location of "Zoom" and no way to join.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import {
  FaVideo,
  FaPhone,
  FaLocationDot,
  FaCircleNotch,
  FaXmark,
} from "react-icons/fa6";

import { apiCall } from "@/components/api";
import { revealFields } from "@/components/motion";

export type InterviewMode = "video" | "phone" | "onsite";

export interface SchedulerValues {
  scheduled_at: string;
  mode: InterviewMode;
  meeting_url: string;
  dial_in: string;
  contact_email: string;
  contact_phone: string;
  duration_minutes: number;
  timezone: string;
  location: string;
  notes: string;
}

const MODES: Array<{
  value: InterviewMode;
  label: string;
  icon: typeof FaVideo;
  hint: string;
}> = [
  { value: "video", label: "Video call", icon: FaVideo, hint: "Send a joining link" },
  { value: "phone", label: "Phone call", icon: FaPhone, hint: "You call, or they do" },
  { value: "onsite", label: "In person", icon: FaLocationDot, hint: "Share the address" },
];

const DURATIONS = [15, 30, 45, 60, 90];

/** The browser's own zone is right far more often than any default we'd pick. */
function localZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "";
  } catch {
    return "";
  }
}

/** `datetime-local` wants "YYYY-MM-DDTHH:mm" in local time, not an ISO UTC string. */
function toLocalInput(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}`
  );
}

function defaultValues(): SchedulerValues {
  const when = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);
  when.setMinutes(0, 0, 0);
  return {
    scheduled_at: toLocalInput(when),
    mode: "video",
    meeting_url: "",
    dial_in: "",
    contact_email: "",
    contact_phone: "",
    duration_minutes: 45,
    timezone: localZone(),
    location: "",
    notes: "",
  };
}

interface SchedulerProps {
  open: boolean;
  onClose: () => void;
  onSaved: (interview: unknown) => void;
  candidateName?: string;
  /** Required when booking; ignored when editing an existing interview. */
  candidateUserId?: number;
  jobId?: number | null;
  /** Present means "edit this interview" rather than "book a new one". */
  interviewId?: number;
  initial?: Partial<SchedulerValues>;
}

/**
 * Mount the form only while it is open.
 *
 * Doing the open/closed check here rather than inside the form means the
 * form's state can be seeded from props at mount, instead of an effect
 * copying props into state every time it reopens.
 */
export default function InterviewScheduler(props: SchedulerProps) {
  if (!props.open) return null;
  return <SchedulerForm {...props} />;
}

function SchedulerForm({
  onClose,
  onSaved,
  candidateName,
  candidateUserId,
  jobId,
  interviewId,
  initial,
}: SchedulerProps) {
  const [values, setValues] = useState<SchedulerValues>(() => ({
    ...defaultValues(),
    ...initial,
  }));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const panelRef = useRef<HTMLDivElement>(null);

  const editing = interviewId !== undefined;

  // Let the panel paint before the fields travel in.
  useEffect(() => {
    const id = requestAnimationFrame(() => revealFields(".scheduler-field"));
    return () => cancelAnimationFrame(id);
  }, []);

  // Escape closes, matching every other dismissible surface in the app.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const set = <K extends keyof SchedulerValues>(
    key: K,
    value: SchedulerValues[K],
  ) => setValues((prev) => ({ ...prev, [key]: value }));

  /** Say what is missing before the request, not after a 422. */
  const localProblem = useMemo(() => {
    if (!values.scheduled_at) return "Pick a date and time.";
    if (values.mode === "video" && values.meeting_url.trim()) {
      if (!/^https?:\/\//i.test(values.meeting_url.trim())) {
        return "The meeting link must start with http:// or https://";
      }
    }
    if (values.mode === "onsite" && !values.location.trim()) {
      return "Add the address so the candidate knows where to go.";
    }
    if (values.mode === "phone" && !values.dial_in.trim()) {
      return "Add the number that will be called.";
    }
    return "";
  }, [values]);

  const submit = async () => {
    if (localProblem) {
      setError(localProblem);
      return;
    }
    setSaving(true);
    setError("");

    // datetime-local has no zone; the Date constructor reads it as local time
    // and toISOString converts to the UTC the API stores.
    const scheduledIso = new Date(values.scheduled_at).toISOString();

    const details = {
      scheduled_at: scheduledIso,
      mode: values.mode,
      meeting_url: values.meeting_url.trim() || null,
      dial_in: values.dial_in.trim() || null,
      contact_email: values.contact_email.trim() || null,
      contact_phone: values.contact_phone.trim() || null,
      duration_minutes: values.duration_minutes,
      timezone: values.timezone || null,
      location: values.location.trim() || null,
      notes: values.notes.trim() || null,
    };

    try {
      const res = editing
        ? await apiCall(`/api/interviews/${interviewId}/details`, {
            method: "PATCH",
            body: JSON.stringify(details),
          })
        : await apiCall("/api/interviews", {
            method: "POST",
            body: JSON.stringify({
              candidate_user_id: candidateUserId,
              job_id: jobId ?? null,
              ...details,
            }),
          });

      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = body?.detail;
        setError(
          typeof detail === "string"
            ? detail
            : Array.isArray(detail) && detail[0]?.msg
              ? String(detail[0].msg).replace(/^Value error, /, "")
              : "The interview could not be saved.",
        );
        return;
      }
      onSaved(body);
      onClose();
    } catch {
      setError("The server did not respond. Nothing was saved.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70"
      role="dialog"
      aria-modal="true"
      aria-label={editing ? "Edit interview" : "Schedule interview"}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={panelRef}
        className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-lg border border-neutral-800 bg-neutral-900 p-6"
      >
        <div className="flex items-start justify-between mb-5">
          <div>
            <p className="eyebrow">
              {editing ? "Edit interview" : "Schedule an interview"}
            </p>
            <h2 className="text-lg font-semibold text-neutral-50 mt-1">
              {candidateName || "Candidate"}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="text-neutral-500 hover:text-neutral-200 transition-colors"
          >
            <FaXmark className="w-4 h-4" />
          </button>
        </div>

        {/* Mode first: it decides what the rest of the form asks for. */}
        <div className="scheduler-field mb-5">
          <label className="label">How will you meet?</label>
          <div className="grid grid-cols-3 gap-2">
            {MODES.map((m) => {
              const active = values.mode === m.value;
              return (
                <button
                  key={m.value}
                  type="button"
                  onClick={() => set("mode", m.value)}
                  aria-pressed={active}
                  className={`rounded-md border p-3 text-left transition-colors ${
                    active
                      ? "border-indigo-500/50 bg-indigo-500/10"
                      : "border-neutral-800 hover:border-neutral-700"
                  }`}
                >
                  <m.icon
                    className={`w-3.5 h-3.5 mb-2 ${active ? "text-indigo-300" : "text-neutral-500"}`}
                  />
                  <span className="block text-xs font-medium text-neutral-100">
                    {m.label}
                  </span>
                  <span className="block text-[11px] text-neutral-500 mt-0.5">
                    {m.hint}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="scheduler-field grid grid-cols-2 gap-3 mb-4">
          <div>
            <label className="label" htmlFor="when">
              When
            </label>
            <input
              id="when"
              type="datetime-local"
              value={values.scheduled_at}
              onChange={(e) => set("scheduled_at", e.target.value)}
              className="input-premium"
            />
          </div>
          <div>
            <label className="label" htmlFor="duration">
              For how long
            </label>
            <select
              id="duration"
              value={values.duration_minutes}
              onChange={(e) => set("duration_minutes", Number(e.target.value))}
              className="input-premium"
            >
              {DURATIONS.map((d) => (
                <option key={d} value={d}>
                  {d} minutes
                </option>
              ))}
            </select>
          </div>
        </div>

        {values.timezone && (
          <p className="text-xs text-neutral-500 -mt-2 mb-4">
            Times are in {values.timezone}. The candidate sees them in their own
            zone.
          </p>
        )}

        {/* Only what this mode actually needs. */}
        {values.mode === "video" && (
          <div className="scheduler-field mb-4">
            <label className="label" htmlFor="link">
              Joining link
            </label>
            <input
              id="link"
              type="url"
              inputMode="url"
              value={values.meeting_url}
              onChange={(e) => set("meeting_url", e.target.value)}
              placeholder="https://meet.example.com/your-room"
              className="input-premium"
            />
            <p className="text-xs text-neutral-500 mt-2">
              Paste the link from Meet, Zoom or Teams. The candidate gets a Join
              button.
            </p>
          </div>
        )}

        {values.mode === "onsite" && (
          <div className="scheduler-field mb-4">
            <label className="label" htmlFor="address">
              Address
            </label>
            <input
              id="address"
              type="text"
              value={values.location}
              onChange={(e) => set("location", e.target.value)}
              placeholder="Floor 4, Westlands Square, Nairobi"
              className="input-premium"
            />
          </div>
        )}

        <div className="scheduler-field mb-4">
          <label className="label" htmlFor="dial">
            {values.mode === "phone" ? "Number to call" : "Backup number"}
          </label>
          <input
            id="dial"
            type="tel"
            value={values.dial_in}
            onChange={(e) => set("dial_in", e.target.value)}
            placeholder="+254 20 000 0000"
            className="input-premium"
          />
          {values.mode === "video" && (
            <p className="text-xs text-neutral-500 mt-2">
              Optional, for when the link will not connect.
            </p>
          )}
          {values.mode === "onsite" && (
            <p className="text-xs text-neutral-500 mt-2">
              Optional, for when they cannot find the building.
            </p>
          )}
        </div>

        <div className="scheduler-field grid grid-cols-2 gap-3 mb-4">
          <div>
            <label className="label" htmlFor="cemail">
              Contact email
            </label>
            <input
              id="cemail"
              type="email"
              value={values.contact_email}
              onChange={(e) => set("contact_email", e.target.value)}
              placeholder="Defaults to your account"
              className="input-premium"
            />
          </div>
          <div>
            <label className="label" htmlFor="cphone">
              Contact phone
            </label>
            <input
              id="cphone"
              type="tel"
              value={values.contact_phone}
              onChange={(e) => set("contact_phone", e.target.value)}
              placeholder="Optional"
              className="input-premium"
            />
          </div>
        </div>

        <div className="scheduler-field mb-5">
          <label className="label" htmlFor="notes">
            Anything they should prepare
          </label>
          <textarea
            id="notes"
            rows={3}
            value={values.notes}
            onChange={(e) => set("notes", e.target.value)}
            placeholder="Who they'll meet, what to bring, how the time is split"
            className="input-premium"
          />
        </div>

        {error && (
          <p className="mb-4 text-sm text-rose-300 bg-rose-500/10 border border-rose-500/30 rounded-md px-4 py-3">
            {error}
          </p>
        )}

        <div className="flex gap-2 justify-end">
          <button type="button" onClick={onClose} className="btn-secondary">
            Cancel
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={saving}
            className="btn-primary"
          >
            {saving ? (
              <>
                <FaCircleNotch className="w-3.5 h-3.5 animate-spin" />
                Saving…
              </>
            ) : editing ? (
              "Save changes"
            ) : (
              "Schedule interview"
            )}
          </button>
        </div>

        {editing && (
          <p className="text-xs text-neutral-500 mt-4">
            Moving a confirmed interview to a new time asks the candidate to
            confirm again.
          </p>
        )}
      </div>
    </div>
  );
}
