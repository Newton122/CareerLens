"use client";

/**
 * Edit a posting that is already live.
 *
 * The screen is built around one idea: this listing is public, and candidates
 * are reading it right now. So the thing given the most room is not the form
 * -- it is the revision ledger, a running old -> new diff of everything you
 * have changed but not yet published. The comparison card carries the same
 * idea spatially: its two faces are the published posting and your draft.
 *
 * Only changed fields are sent, which is why the API accepts a partial
 * update: an employer correcting a salary should not risk overwriting a
 * description they never opened.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  FaArrowLeft,
  FaCircleNotch,
  FaEye,
  FaRotateLeft,
  FaCheck,
} from "react-icons/fa6";

import { apiCall } from "@/components/api";
import { describeApiError } from "@/components/format";
import MessageDialog from "@/components/MessageDialog";
import {
  flipCard,
  playPublishSequence,
  revealFields,
  revealLedgerRow,
} from "@/components/motion";

interface Job {
  id: number;
  title: string;
  description: string;
  location: string;
  salary_min: number | null;
  salary_max: number | null;
  employment_type: string;
  required_skills: string[];
  experience_required: string | null;
  education_required: string | null;
  responsibilities: string | null;
  benefits: string[];
  status: "open" | "closed" | "draft";
  applications_count: number;
  views: number;
}

/** The shape the form edits: every value a string, so inputs stay controlled. */
type Draft = {
  title: string;
  description: string;
  location: string;
  salary_min: string;
  salary_max: string;
  employment_type: string;
  required_skills: string;
  experience_required: string;
  education_required: string;
  responsibilities: string;
  benefits: string;
  status: string;
};

const FIELD_LABELS: Record<keyof Draft, string> = {
  title: "Title",
  description: "Description",
  location: "Location",
  salary_min: "Minimum salary",
  salary_max: "Maximum salary",
  employment_type: "Employment type",
  required_skills: "Required skills",
  experience_required: "Experience",
  education_required: "Education",
  responsibilities: "Responsibilities",
  benefits: "Benefits",
  status: "Status",
};

const EMPLOYMENT_TYPES = ["full-time", "part-time", "contract", "freelance"];
const STATUSES: Array<{ value: string; label: string; hint: string }> = [
  { value: "open", label: "Open", hint: "Visible to candidates, accepting applications" },
  { value: "closed", label: "Closed", hint: "No new applications; existing ones stay" },
  { value: "draft", label: "Draft", hint: "Hidden from candidates entirely" },
];

function jobToDraft(job: Job): Draft {
  return {
    title: job.title ?? "",
    description: job.description ?? "",
    location: job.location ?? "",
    salary_min: job.salary_min == null ? "" : String(job.salary_min),
    salary_max: job.salary_max == null ? "" : String(job.salary_max),
    employment_type: job.employment_type ?? "full-time",
    required_skills: (job.required_skills ?? []).join(", "),
    experience_required: job.experience_required ?? "",
    education_required: job.education_required ?? "",
    responsibilities: job.responsibilities ?? "",
    benefits: (job.benefits ?? []).join(", "),
    status: job.status ?? "open",
  };
}

/** Empty values read better as an explicit absence than as a blank gap. */
function display(value: string): string {
  return value.trim() === "" ? "— not set —" : value;
}

export default function EditJobPage() {
  const router = useRouter();
  const params = useParams();
  const jobId = params.id as string;

  const [job, setJob] = useState<Job | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [published, setPublished] = useState<Draft | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showDraftFace, setShowDraftFace] = useState(false);
  const [dialog, setDialog] = useState({
    open: false,
    title: "",
    message: "",
    type: "info" as "info" | "success" | "error" | "warning",
  });

  const cardRef = useRef<HTMLDivElement>(null);
  const ledgerRef = useRef<HTMLDivElement>(null);
  const badgeRef = useRef<HTMLSpanElement>(null);
  const seenRows = useRef<Set<string>>(new Set());

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await apiCall(`/api/jobs/${jobId}`);
        if (!res.ok) {
          setDialog({
            open: true,
            title: "Could not open this posting",
            message:
              res.status === 404
                ? "That posting does not exist, or it is not yours to edit."
                : "Something went wrong loading the posting.",
            type: "error",
          });
          return;
        }
        const data: Job = await res.json();
        if (cancelled) return;
        setJob(data);
        setDraft(jobToDraft(data));
        setPublished(jobToDraft(data));
      } catch {
        if (!cancelled) {
          setDialog({
            open: true,
            title: "Could not open this posting",
            message: "The server did not respond. Is the backend running?",
            type: "error",
          });
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [jobId]);

  // Fields arrive once the form has something to show.
  useEffect(() => {
    if (!loading && draft) revealFields(".field-stagger");
  }, [loading, draft]);

  /** Which fields differ from what is published right now. */
  const changes = useMemo(() => {
    if (!draft || !published) return [] as Array<keyof Draft>;
    return (Object.keys(draft) as Array<keyof Draft>).filter(
      (k) => draft[k].trim() !== published[k].trim(),
    );
  }, [draft, published]);

  // Animate only rows that are new to the ledger, so existing rows do not
  // re-run their entrance on every keystroke.
  useEffect(() => {
    const current = new Set(changes.map(String));
    for (const key of current) {
      if (!seenRows.current.has(key)) {
        const el = ledgerRef.current?.querySelector(`[data-row="${key}"]`);
        if (el) revealLedgerRow(el);
      }
    }
    seenRows.current = current;
  }, [changes]);

  const set = useCallback((key: keyof Draft, value: string) => {
    setDraft((prev) => (prev ? { ...prev, [key]: value } : prev));
  }, []);

  const toggleFace = () => {
    const next = !showDraftFace;
    setShowDraftFace(next);
    if (cardRef.current) flipCard(cardRef.current, next);
  };

  const revertField = (key: keyof Draft) => {
    if (!published) return;
    set(key, published[key]);
  };

  const revertAll = () => {
    if (published) setDraft({ ...published });
  };

  /** Only what actually changed, in the types the API expects. */
  const buildPayload = () => {
    if (!draft || !published) return {};
    const payload: Record<string, unknown> = {};
    for (const key of changes) {
      const value = draft[key];
      if (key === "salary_min" || key === "salary_max") {
        payload[key] = value.trim() === "" ? null : Number(value);
      } else if (key === "required_skills" || key === "benefits") {
        payload[key] = value
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
      } else if (
        key === "experience_required" ||
        key === "education_required" ||
        key === "responsibilities"
      ) {
        // These columns are nullable: an emptied box means "remove this".
        payload[key] = value.trim() === "" ? null : value.trim();
      } else {
        payload[key] = value.trim();
      }
    }
    return payload;
  };

  const publish = async () => {
    if (changes.length === 0 || !draft) return;
    setSaving(true);
    try {
      const res = await apiCall(`/api/jobs/${jobId}`, {
        method: "PATCH",
        body: JSON.stringify(buildPayload()),
      });
      const body = await res.json().catch(() => ({}));

      if (!res.ok) {
        setDialog({
          open: true,
          title: "Changes not published",
          message: describeApiError(body, "The posting could not be updated."),
          type: "error",
        });
        return;
      }

      const updated: Job = body;
      setJob(updated);
      const next = jobToDraft(updated);
      setDraft(next);
      setPublished(next);
      setShowDraftFace(false);
      seenRows.current = new Set();

      await playPublishSequence({
        ledger: ledgerRef.current,
        card: cardRef.current,
        badge: badgeRef.current,
      });

      setDialog({
        open: true,
        title: "Changes published",
        message: "Candidates now see the updated posting.",
        type: "success",
      });
    } catch {
      setDialog({
        open: true,
        title: "Changes not published",
        message: "The server did not respond. Your edits are still here.",
        type: "error",
      });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-10">
        <p className="text-sm text-neutral-500">Opening the posting…</p>
      </div>
    );
  }

  if (!job || !draft || !published) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-10">
        <p className="text-neutral-300">This posting could not be opened.</p>
        <Link href="/employer/jobs" className="btn-secondary mt-4">
          Back to postings
        </Link>
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

  const dirty = changes.length > 0;

  const textField = (
    key: keyof Draft,
    props: { placeholder?: string; type?: string; rows?: number } = {},
  ) => {
    const changed = changes.includes(key);
    const common = {
      value: draft[key],
      onChange: (
        e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
      ) => set(key, e.target.value),
      placeholder: props.placeholder,
      className: `input-premium ${changed ? "border-[color:var(--draft-border)]" : ""}`,
    };
    return (
      <div className="field-stagger">
        <div className="flex items-baseline justify-between">
          <label className="label">{FIELD_LABELS[key]}</label>
          {changed && (
            <button
              type="button"
              onClick={() => revertField(key)}
              className="text-xs text-neutral-500 hover:text-neutral-200 transition-colors mb-2"
            >
              Revert
            </button>
          )}
        </div>
        {props.rows ? (
          <textarea {...common} rows={props.rows} />
        ) : (
          <input {...common} type={props.type ?? "text"} />
        )}
      </div>
    );
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <Link
        href={`/employer/jobs/${job.id}`}
        className="inline-flex items-center gap-2 text-sm text-neutral-500 hover:text-neutral-200 transition-colors"
      >
        <FaArrowLeft className="w-3 h-3" />
        Back to posting
      </Link>

      <header className="mt-4 mb-8">
        <p className="eyebrow">Editing a live posting</p>
        <div className="flex flex-wrap items-center gap-3 mt-2">
          <h1 className="page-title">{published.title}</h1>
          <span ref={badgeRef} className={job.status === "open" ? "chip-positive" : "chip"}>
            {job.status}
          </span>
          {dirty && (
            <span className="chip-draft">
              {changes.length} unpublished {changes.length === 1 ? "change" : "changes"}
            </span>
          )}
        </div>
        <p className="text-sm text-neutral-400 mt-2">
          {job.applications_count} application
          {job.applications_count === 1 ? "" : "s"} · {job.views} view
          {job.views === 1 ? "" : "s"} so far. Changes go live the moment you publish them.
        </p>
      </header>

      <div className="grid lg:grid-cols-[1fr_20rem] gap-8 items-start">
        {/* ── The form ─────────────────────────────────────────────── */}
        <div className="space-y-8">
          {/* Comparison card: two faces of one posting. */}
          <div className="flip-scene">
            <div ref={cardRef} className="flip-card">
              <div className="flip-face card">
                <div className="flex items-center justify-between mb-3">
                  <p className="eyebrow">What candidates see now</p>
                  <button
                    type="button"
                    onClick={toggleFace}
                    className="text-xs text-neutral-400 hover:text-neutral-100 inline-flex items-center gap-1.5 transition-colors"
                  >
                    <FaEye className="w-3 h-3" />
                    Compare with your draft
                  </button>
                </div>
                <h2 className="section-title">
                  {published.title}
                </h2>
                <p className="page-subtitle">
                  {published.location} · {published.employment_type}
                </p>
                <p className="text-sm text-neutral-300 mt-3 line-clamp-3">
                  {display(published.description)}
                </p>
              </div>

              <div className="flip-face flip-face-back card border-[color:var(--draft-border)]">
                <div className="flex items-center justify-between mb-3">
                  <p className="eyebrow" style={{ color: "var(--draft)" }}>
                    Your draft
                  </p>
                  <button
                    type="button"
                    onClick={toggleFace}
                    className="text-xs text-neutral-400 hover:text-neutral-100 inline-flex items-center gap-1.5 transition-colors"
                  >
                    <FaEye className="w-3 h-3" />
                    Back to published
                  </button>
                </div>
                <h2 className="section-title">
                  {display(draft.title)}
                </h2>
                <p className="page-subtitle">
                  {display(draft.location)} · {draft.employment_type}
                </p>
                <p className="text-sm text-neutral-300 mt-3 line-clamp-3">
                  {display(draft.description)}
                </p>
              </div>
            </div>
          </div>

          <section className="space-y-4">
            <h2 className="eyebrow">The role</h2>
            {textField("title", { placeholder: "Job title" })}
            {textField("location", { placeholder: "Where the work happens" })}

            <div className="field-stagger">
              <label className="label">{FIELD_LABELS.employment_type}</label>
              <select
                value={draft.employment_type}
                onChange={(e) => set("employment_type", e.target.value)}
                className="input-premium"
              >
                {EMPLOYMENT_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>

            <div className="field-stagger grid grid-cols-2 gap-3">
              <div>
                <label className="label">{FIELD_LABELS.salary_min}</label>
                <input
                  type="number"
                  value={draft.salary_min}
                  onChange={(e) => set("salary_min", e.target.value)}
                  placeholder="Leave blank to hide"
                  className="input-premium"
                />
              </div>
              <div>
                <label className="label">{FIELD_LABELS.salary_max}</label>
                <input
                  type="number"
                  value={draft.salary_max}
                  onChange={(e) => set("salary_max", e.target.value)}
                  placeholder="Leave blank to hide"
                  className="input-premium"
                />
              </div>
            </div>
          </section>

          <section className="space-y-4">
            <h2 className="eyebrow">What the job involves</h2>
            {textField("description", {
              rows: 5,
              placeholder: "Describe the role",
            })}
            {textField("responsibilities", {
              rows: 3,
              placeholder: "Key responsibilities",
            })}
          </section>

          <section className="space-y-4">
            <h2 className="eyebrow">Who it suits</h2>
            {textField("required_skills", {
              placeholder: "Skills, separated by commas",
            })}
            {textField("experience_required", {
              placeholder: "e.g. 3–5 years",
            })}
            {textField("education_required", {
              placeholder: "e.g. BSc Computer Science",
            })}
            {textField("benefits", {
              placeholder: "Benefits, separated by commas",
            })}
          </section>

          <section className="space-y-3">
            <h2 className="eyebrow">Visibility</h2>
            <div className="field-stagger grid sm:grid-cols-3 gap-3">
              {STATUSES.map((s) => {
                const active = draft.status === s.value;
                return (
                  <button
                    key={s.value}
                    type="button"
                    onClick={() => set("status", s.value)}
                    aria-pressed={active}
                    className={`text-left rounded-lg border p-3 transition-colors ${
                      active
                        ? "border-neutral-500 bg-neutral-900"
                        : "border-neutral-800 hover:border-neutral-700"
                    }`}
                  >
                    <span className="text-sm font-medium text-neutral-100">
                      {s.label}
                    </span>
                    <span className="block text-xs text-neutral-500 mt-1">
                      {s.hint}
                    </span>
                  </button>
                );
              })}
            </div>
          </section>
        </div>

        {/* ── The revision ledger ──────────────────────────────────── */}
        <aside className="lg:sticky lg:top-8">
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <p className="eyebrow">Unpublished changes</p>
              {dirty && (
                <button
                  type="button"
                  onClick={revertAll}
                  className="text-xs text-neutral-500 hover:text-neutral-200 inline-flex items-center gap-1.5 transition-colors"
                >
                  <FaRotateLeft className="w-3 h-3" />
                  Revert all
                </button>
              )}
            </div>

            <div ref={ledgerRef} className="ledger space-y-3">
              {!dirty && (
                <p className="text-sm text-neutral-500 font-sans">
                  Nothing changed yet. Edits you make appear here before they
                  go live.
                </p>
              )}
              {changes.map((key) => (
                <div key={key} data-row={key}>
                  <p className="ledger-field">{FIELD_LABELS[key]}</p>
                  <p className="ledger-old break-words">
                    {display(published[key])}
                  </p>
                  <p className="ledger-new break-words">{display(draft[key])}</p>
                </div>
              ))}
            </div>

            <div className="rule my-5" />

            <button
              type="button"
              onClick={publish}
              disabled={!dirty || saving}
              className="btn-primary w-full"
            >
              {saving ? (
                <>
                  <FaCircleNotch className="w-3.5 h-3.5 animate-spin" />
                  Publishing…
                </>
              ) : (
                <>
                  <FaCheck className="w-3.5 h-3.5" />
                  Publish changes
                </>
              )}
            </button>
            <p className="text-xs text-neutral-500 mt-3 text-center font-sans">
              {dirty
                ? "Only the fields listed above are sent."
                : "Edit a field to enable publishing."}
            </p>
          </div>
        </aside>
      </div>

      <MessageDialog
        open={dialog.open}
        onClose={() => {
          setDialog({ ...dialog, open: false });
          if (dialog.type === "error" && !job) router.push("/employer/jobs");
        }}
        title={dialog.title}
        message={dialog.message}
        type={dialog.type}
      />
    </div>
  );
}
