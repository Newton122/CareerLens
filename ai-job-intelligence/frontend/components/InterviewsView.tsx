"use client";

/**
 * The interviews list, for either side of the conversation.
 *
 * A card here has one job: let the person attend the interview. So the
 * joining details lead, shaped by how the meeting actually happens -- a video
 * call puts a Join button first, a phone call puts the number first, an
 * on-site interview puts the address first. Everything else is secondary to
 * getting the two people into the same room.
 */

import { useEffect, useRef, useState } from "react";
import {
  FaCalendarPlus,
  FaCheck,
  FaXmark,
  FaBan,
  FaClipboardCheck,
  FaLocationDot,
  FaVideo,
  FaPhone,
  FaClock,
  FaEnvelope,
  FaPen,
  FaRegCalendar,
} from "react-icons/fa6";

import { apiCall } from "@/components/api";
import { attachTilt } from "@/components/motion";
import InterviewScheduler, {
  type InterviewMode,
} from "@/components/InterviewScheduler";

export interface Interview {
  id: number;
  employer_id: number;
  employer_name: string;
  company: string;
  candidate_user_id: number;
  candidate_name: string;
  candidate_email: string;
  cv_id: number | null;
  job_id: number | null;
  job_title: string | null;
  scheduled_at: string;
  status: "scheduled" | "confirmed" | "declined" | "cancelled" | "completed";
  mode: InterviewMode;
  meeting_url: string | null;
  dial_in: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  duration_minutes: number;
  timezone: string | null;
  location: string | null;
  notes: string | null;
  created_at: string;
}

const STATUS_STYLE: Record<Interview["status"], string> = {
  scheduled: "chip-accent",
  confirmed: "chip-positive",
  declined: "chip-negative",
  cancelled: "chip-negative",
  completed: "chip",
};

const MODE_ICON: Record<InterviewMode, typeof FaVideo> = {
  video: FaVideo,
  phone: FaPhone,
  onsite: FaLocationDot,
};

const MODE_LABEL: Record<InterviewMode, string> = {
  video: "Video call",
  phone: "Phone call",
  onsite: "In person",
};

/** Which transitions each side is allowed to make, mirroring the API. */
const ACTIONS: Record<
  "employer" | "candidate",
  Array<{ status: string; label: string; icon: typeof FaCheck; danger?: boolean }>
> = {
  candidate: [
    { status: "confirmed", label: "Confirm", icon: FaCheck },
    { status: "declined", label: "Decline", icon: FaXmark, danger: true },
  ],
  employer: [
    { status: "completed", label: "Mark complete", icon: FaClipboardCheck },
    { status: "cancelled", label: "Cancel", icon: FaBan, danger: true },
  ],
};

const CLOSED = new Set(["cancelled", "declined", "completed"]);

function formatWhen(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Only http(s) links are ever rendered as a Join button. The API rejects
 *  anything else on the way in; this is the second line of that defence. */
function safeHref(url: string | null): string | null {
  if (!url) return null;
  return /^https?:\/\//i.test(url.trim()) ? url.trim() : null;
}

/**
 * A .ics file the browser downloads, so the interview lands in whatever
 * calendar the person actually uses rather than one we picked for them.
 */
function downloadIcs(it: Interview, side: "employer" | "candidate") {
  const start = new Date(it.scheduled_at);
  const end = new Date(start.getTime() + (it.duration_minutes || 45) * 60000);
  const stamp = (d: Date) => d.toISOString().replace(/[-:]/g, "").split(".")[0] + "Z";

  const who =
    side === "employer"
      ? it.candidate_name || it.candidate_email || "candidate"
      : it.company || it.employer_name || "employer";
  const title = it.job_title
    ? `Interview: ${it.job_title}`
    : `Interview with ${who}`;

  const where = it.mode === "onsite" ? it.location || "" : safeHref(it.meeting_url) || it.dial_in || "";
  const description = [
    `Mode: ${MODE_LABEL[it.mode] ?? it.mode}`,
    safeHref(it.meeting_url) ? `Join: ${it.meeting_url}` : "",
    it.dial_in ? `Dial-in: ${it.dial_in}` : "",
    it.contact_email ? `Contact: ${it.contact_email}` : "",
    it.contact_phone ? `Phone: ${it.contact_phone}` : "",
    it.notes ? `Notes: ${it.notes}` : "",
  ]
    .filter(Boolean)
    .join("\\n");

  // Commas and semicolons are field separators in iCalendar and must be escaped.
  const esc = (s: string) => s.replace(/([,;\\])/g, "\\$1").replace(/\n/g, "\\n");

  const ics = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//CareerLens//Interviews//EN",
    "BEGIN:VEVENT",
    `UID:careerlens-interview-${it.id}@careerlens`,
    `DTSTAMP:${stamp(new Date())}`,
    `DTSTART:${stamp(start)}`,
    `DTEND:${stamp(end)}`,
    `SUMMARY:${esc(title)}`,
    where ? `LOCATION:${esc(where)}` : "",
    `DESCRIPTION:${esc(description)}`,
    "END:VEVENT",
    "END:VCALENDAR",
  ]
    .filter(Boolean)
    .join("\r\n");

  const blob = new Blob([ics], { type: "text/calendar;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `interview-${it.id}.ics`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

/** One interview. Split out so each card can own its tilt listener. */
function InterviewCard({
  it,
  side,
  busy,
  onAction,
  onEdit,
}: {
  it: Interview;
  side: "employer" | "candidate";
  busy: boolean;
  onAction: (id: number, status: string) => void;
  onEdit: (it: Interview) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const open = !CLOSED.has(it.status);

  useEffect(() => {
    if (!ref.current || !open) return;
    return attachTilt(ref.current, 3);
  }, [open]);

  const ModeIcon = MODE_ICON[it.mode] ?? FaVideo;
  const join = safeHref(it.meeting_url);

  return (
    <div
      ref={ref}
      className="rounded-lg border border-neutral-800 bg-neutral-900 p-5"
      style={{ transformStyle: "preserve-3d" }}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold text-neutral-100">
              {side === "employer"
                ? it.candidate_name || it.candidate_email || "Candidate"
                : it.company || it.employer_name || "Employer"}
            </h3>
            <span className={STATUS_STYLE[it.status]}>{it.status}</span>
            <span className="chip">
              <ModeIcon className="w-3 h-3" />
              {MODE_LABEL[it.mode] ?? it.mode}
            </span>
          </div>

          {it.job_title && (
            <p className="text-sm text-neutral-400 mt-1">For {it.job_title}</p>
          )}

          <p className="text-sm text-neutral-300 mt-2 flex items-center gap-2">
            <FaClock className="w-3.5 h-3.5 text-neutral-500" />
            {formatWhen(it.scheduled_at)} · {it.duration_minutes || 45} min
          </p>

          {it.mode === "onsite" && it.location && (
            <p className="text-sm text-neutral-400 mt-1 flex items-center gap-2">
              <FaLocationDot className="w-3.5 h-3.5 text-neutral-500" />
              {it.location}
            </p>
          )}

          {it.dial_in && (
            <p className="text-sm text-neutral-400 mt-1 flex items-center gap-2">
              <FaPhone className="w-3.5 h-3.5 text-neutral-500" />
              <a href={`tel:${it.dial_in}`} className="hover:text-neutral-200">
                {it.dial_in}
              </a>
            </p>
          )}

          {it.contact_email && (
            <p className="text-sm text-neutral-400 mt-1 flex items-center gap-2">
              <FaEnvelope className="w-3.5 h-3.5 text-neutral-500" />
              <a
                href={`mailto:${it.contact_email}`}
                className="hover:text-neutral-200"
              >
                {it.contact_email}
              </a>
            </p>
          )}

          {it.notes && (
            <p className="text-sm text-neutral-400 mt-3 border-l border-neutral-800 pl-3">
              {it.notes}
            </p>
          )}
        </div>

        <div className="flex flex-col items-stretch gap-2 shrink-0">
          {open && join && (
            <a
              href={join}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-primary btn-small"
            >
              <FaVideo className="w-3 h-3" />
              Join interview
            </a>
          )}
          {open && (
            <button
              type="button"
              onClick={() => downloadIcs(it, side)}
              className="btn-secondary btn-small"
            >
              <FaRegCalendar className="w-3 h-3" />
              Add to calendar
            </button>
          )}
          {open && side === "employer" && (
            <button
              type="button"
              onClick={() => onEdit(it)}
              className="btn-secondary btn-small"
            >
              <FaPen className="w-3 h-3" />
              Edit details
            </button>
          )}
        </div>
      </div>

      {open && (
        <div className="flex gap-2 mt-4 pt-4 border-t border-neutral-800">
          {ACTIONS[side].map((action) => (
            <button
              key={action.status}
              type="button"
              onClick={() => onAction(it.id, action.status)}
              disabled={busy}
              className={
                action.danger ? "btn-danger btn-small" : "btn-secondary btn-small"
              }
            >
              <action.icon className="w-3 h-3" />
              {action.label}
            </button>
          ))}
        </div>
      )}

      {open && !join && it.mode === "video" && (
        <p className="text-xs mt-3" style={{ color: "var(--draft)" }}>
          {side === "employer"
            ? "No joining link yet — add one so the candidate can attend."
            : "The employer has not added a joining link yet."}
        </p>
      )}
    </div>
  );
}

export default function InterviewsView({
  side,
}: {
  side: "employer" | "candidate";
}) {
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState<Interview | null>(null);

  // State is set only after the request returns, and never once the view
  // has gone (`active`), so a slow response can't overwrite newer data.
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const res = await apiCall("/api/interviews");
        if (!active) return;
        if (res.ok) {
          const data: Interview[] = await res.json();
          if (active) setInterviews(data);
        } else {
          setError("Could not load interviews.");
        }
      } catch {
        if (active) setError("Could not load interviews.");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const update = async (id: number, status: string) => {
    setBusyId(id);
    try {
      const res = await apiCall(`/api/interviews/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      if (res.ok) {
        const updated: Interview = await res.json();
        setInterviews((prev) => prev.map((i) => (i.id === id ? updated : i)));
      } else {
        const body = await res.json().catch(() => ({}));
        setError(body.detail || "Could not update this interview.");
      }
    } finally {
      setBusyId(null);
    }
  };

  if (loading) {
    return <p className="text-sm text-neutral-500">Loading interviews…</p>;
  }

  if (interviews.length === 0) {
    return (
      <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-10 text-center">
        <FaCalendarPlus className="w-6 h-6 text-neutral-600 mx-auto mb-3" />
        <p className="text-neutral-300 font-medium">No interviews yet</p>
        <p className="text-sm text-neutral-500 mt-1">
          {side === "employer"
            ? "Schedule one from a candidate's profile."
            : "When an employer books a time with you, it appears here."}
        </p>
      </div>
    );
  }

  const upcoming = interviews.filter((i) => !CLOSED.has(i.status));
  const past = interviews.filter((i) => CLOSED.has(i.status));

  const renderGroup = (title: string, rows: Interview[]) =>
    rows.length > 0 && (
      <section className="mb-8">
        <h2 className="eyebrow mb-3">{title}</h2>
        <div className="space-y-3">
          {rows.map((it) => (
            <InterviewCard
              key={it.id}
              it={it}
              side={side}
              busy={busyId === it.id}
              onAction={update}
              onEdit={setEditing}
            />
          ))}
        </div>
      </section>
    );

  return (
    <>
      {error && (
        <p className="mb-4 text-sm text-rose-300 bg-rose-500/10 border border-rose-500/30 rounded-md px-4 py-3">
          {error}
        </p>
      )}
      {renderGroup("Upcoming", upcoming)}
      {renderGroup("Past", past)}

      {editing && (
        <InterviewScheduler
          open
          interviewId={editing.id}
          candidateName={editing.candidate_name || editing.candidate_email}
          onClose={() => setEditing(null)}
          onSaved={(updated) => {
            const u = updated as Interview;
            setInterviews((prev) => prev.map((i) => (i.id === u.id ? u : i)));
          }}
          initial={{
            // datetime-local needs local wall-clock, not the stored UTC.
            scheduled_at: (() => {
              const d = new Date(editing.scheduled_at);
              const pad = (n: number) => String(n).padStart(2, "0");
              return (
                `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
                `T${pad(d.getHours())}:${pad(d.getMinutes())}`
              );
            })(),
            mode: editing.mode,
            meeting_url: editing.meeting_url ?? "",
            dial_in: editing.dial_in ?? "",
            contact_email: editing.contact_email ?? "",
            contact_phone: editing.contact_phone ?? "",
            duration_minutes: editing.duration_minutes || 45,
            timezone: editing.timezone ?? "",
            location: editing.location ?? "",
            notes: editing.notes ?? "",
          }}
        />
      )}
    </>
  );
}
