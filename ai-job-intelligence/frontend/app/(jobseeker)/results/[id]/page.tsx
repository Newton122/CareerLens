"use client";

/**
 * What the analysis actually means, and what to do about it.
 *
 * The page is ordered by what a candidate needs in the order they need it:
 * the verdict, then the evidence behind it, then the actions, then the
 * resources for carrying those actions out. The score is stated once, large,
 * with the sub-scores that produced it directly beneath — previously it was a
 * 16px number in a bordered box indistinguishable from every other box.
 */

import { useCallback, useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import {
  FaArrowLeft,
  FaCheck,
  FaMinus,
  FaCircleExclamation,
} from "react-icons/fa6";

import { apiCall } from "@/components/api";
import { describeApiError, NOT_SPECIFIED, type Score } from "@/components/format";
import MessageDialog from "@/components/MessageDialog";
import LearningResources from "@/components/LearningResources";

interface Action {
  title: string;
  detail: string;
  group: "gap" | "cv" | "experience" | "positioning";
  priority: number;
  skills: string[];
  effort: string;
}

interface AnalysisResult {
  id: number;
  job_title: string;
  company?: string;
  match_score: number;
  matched_skills: string[];
  missing_skills: string[];
  experience_match: number | null;
  education_match: number | null;
  recommendations: string[];
  guidance?: Action[];
  summary: string;
  created_at: string;
}

const GROUP_LABEL: Record<Action["group"], string> = {
  gap: "Close the gap",
  cv: "Strengthen your CV",
  experience: "Frame your experience",
  positioning: "Position yourself",
};

/** The score's meaning, stated in words rather than left to a colour. */
function verdict(score: number): { label: string; tone: string } {
  if (score >= 75) return { label: "Strong match", tone: "text-emerald-300" };
  if (score >= 50) return { label: "Worth applying", tone: "text-amber-300" };
  if (score >= 30) return { label: "Reach role", tone: "text-orange-300" };
  return { label: "Large gap", tone: "text-rose-300" };
}

function ScoreBar({ label, value }: { label: string; value: Score }) {
  const unset = value === null || value === undefined;
  return (
    <div>
      <div className="flex items-baseline justify-between mb-2">
        <span className="stat-label">{label}</span>
        <span
          className={
            unset
              ? "text-[0.8125rem] text-neutral-600"
              : "text-[0.9375rem] font-medium text-neutral-100 tabular-nums"
          }
        >
          {unset ? NOT_SPECIFIED : `${value}%`}
        </span>
      </div>
      <div className="h-1 rounded-full bg-neutral-800 overflow-hidden">
        <div
          className="h-full rounded-full bg-neutral-300 transition-[width] duration-700"
          style={{ width: unset ? "0%" : `${value}%` }}
        />
      </div>
    </div>
  );
}

export default function ResultsPage() {
  const router = useRouter();
  const params = useParams();
  const analysisId = params.id as string;

  // The id comes from the route and cannot change while this page is
  // mounted, so an invalid one is known before the first render rather than
  // discovered in an effect afterwards.
  const validId = Boolean(analysisId) && analysisId !== "undefined";

  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(validId);
  const [dialog, setDialog] = useState(() => ({
    open: !validId,
    title: validId ? "" : "Could not load this analysis",
    message: validId ? "" : "That analysis link is not valid.",
    type: "info" as "info" | "success" | "error" | "warning",
  }));

  const fetchAnalysis = useCallback(async () => {
    try {
      const response = await apiCall(`/api/analyses/${analysisId}`);
      const data = await response.json();
      if (response.ok) {
        setResult(data);
      } else {
        setDialog({
          open: true,
          title: "Could not load this analysis",
          message: describeApiError(data, "Analysis not found"),
          type: "error",
        });
      }
    } catch (err) {
      setDialog({
        open: true,
        title: "Could not load this analysis",
        message: err instanceof Error ? err.message : "Something went wrong.",
        type: "error",
      });
    } finally {
      setLoading(false);
    }
  }, [analysisId]);

  useEffect(() => {
    if (!validId) return;
    fetchAnalysis();
  }, [validId, fetchAnalysis]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-10">
        <p className="meta">Loading your analysis…</p>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-10">
        <p className="body-text">This analysis could not be opened.</p>
        <Link href="/analyze" className="btn-secondary mt-5">
          Run a new analysis
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

  const v = verdict(result.match_score);
  // Fall back to the flat list for an analysis stored before guidance existed.
  const actions: Action[] =
    result.guidance && result.guidance.length > 0
      ? result.guidance
      : (result.recommendations ?? []).map((r) => ({
          title: r,
          detail: "",
          group: "cv" as const,
          priority: 2,
          skills: [],
          effort: "",
        }));

  const grouped = actions.reduce<Record<string, Action[]>>((acc, a) => {
    (acc[a.group] ||= []).push(a);
    return acc;
  }, {});

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <Link
        href="/analyze"
        className="inline-flex items-center gap-2 meta hover:text-neutral-200 transition-colors"
      >
        <FaArrowLeft className="w-3 h-3" />
        Analyse another posting
      </Link>

      <header className="page-header mt-4">
        <div>
          <p className="eyebrow">Analysis</p>
          <h1 className="page-title mt-1.5">{result.job_title}</h1>
          {result.company && <p className="page-subtitle">at {result.company}</p>}
        </div>
      </header>

      {/* The verdict, stated once and large. */}
      <section className="card mb-5">
        <div className="grid sm:grid-cols-[auto_1fr] gap-7 items-center">
          <div>
            <div className="flex items-baseline gap-2">
              <span className="text-[3.5rem] font-semibold leading-none tabular-nums text-neutral-50">
                {result.match_score}
              </span>
              <span className="text-xl text-neutral-500">%</span>
            </div>
            <p className={`text-[0.9375rem] font-medium mt-2 ${v.tone}`}>
              {v.label}
            </p>
          </div>

          <div className="space-y-4 sm:border-l sm:border-neutral-800 sm:pl-7">
            <ScoreBar
              label="Skills"
              value={
                result.matched_skills.length + result.missing_skills.length > 0
                  ? Math.round(
                      (result.matched_skills.length /
                        (result.matched_skills.length +
                          result.missing_skills.length)) *
                        100,
                    )
                  : null
              }
            />
            <ScoreBar label="Experience" value={result.experience_match} />
            <ScoreBar label="Education" value={result.education_match} />
          </div>
        </div>

        <div className="rule my-6" />
        <p className="body-text">{result.summary}</p>
      </section>

      {/* The evidence. */}
      <section className="grid sm:grid-cols-2 gap-4 mb-5">
        <div className="card">
          <div className="flex items-center gap-2">
            <FaCheck className="w-3 h-3 text-emerald-400" />
            <h2 className="section-title">
              You have {result.matched_skills.length}
            </h2>
          </div>
          <p className="meta mt-1">Requirements your CV already evidences</p>
          <div className="flex flex-wrap gap-1.5 mt-4">
            {result.matched_skills.length > 0 ? (
              result.matched_skills.map((s) => (
                <span key={s} className="chip-positive">
                  {s}
                </span>
              ))
            ) : (
              <p className="body-text">
                None of the stated requirements appear in your CV.
              </p>
            )}
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-2">
            <FaMinus className="w-3 h-3 text-rose-400" />
            <h2 className="section-title">
              You are missing {result.missing_skills.length}
            </h2>
          </div>
          <p className="meta mt-1">Asked for, not found in your CV</p>
          <div className="flex flex-wrap gap-1.5 mt-4">
            {result.missing_skills.length > 0 ? (
              result.missing_skills.map((s) => (
                <span key={s} className="chip-negative">
                  {s}
                </span>
              ))
            ) : (
              <p className="body-text">Nothing stated is missing. </p>
            )}
          </div>
        </div>
      </section>

      {/* What to do, in the order to do it. */}
      <section className="card mb-5">
        <h2 className="section-title">What to do next</h2>
        <p className="meta mt-1">
          Ordered by what costs you the most interviews.
        </p>

        <div className="mt-6 space-y-7">
          {Object.entries(grouped).map(([group, items]) => (
            <div key={group}>
              <h3 className="eyebrow mb-3">
                {GROUP_LABEL[group as Action["group"]] ?? group}
              </h3>
              <div className="space-y-3">
                {items.map((a, i) => (
                  <div
                    key={`${group}-${i}`}
                    className="rounded-md border border-neutral-800 p-4"
                  >
                    <div className="flex items-start justify-between gap-3 flex-wrap">
                      <p className="item-title flex items-center gap-2">
                        {a.priority === 1 && (
                          <FaCircleExclamation
                            className="w-3 h-3 text-amber-400 shrink-0"
                            aria-label="Do this first"
                          />
                        )}
                        {a.title}
                      </p>
                      {a.effort && <span className="chip shrink-0">{a.effort}</span>}
                    </div>
                    {a.detail && (
                      <p className="text-[0.875rem] leading-relaxed text-neutral-400 mt-2">
                        {a.detail}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Where to go and learn it. */}
      {result.missing_skills.length > 0 && (
        <div className="mb-5">
          <LearningResources skills={result.missing_skills} />
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <Link href="/jobs" className="btn-primary">
          Find matching jobs
        </Link>
        <Link href="/analyze" className="btn-secondary">
          Analyse another posting
        </Link>
      </div>

      <MessageDialog
        open={dialog.open}
        onClose={() => {
          setDialog({ ...dialog, open: false });
          if (!result) router.push("/analyze");
        }}
        title={dialog.title}
        message={dialog.message}
        type={dialog.type}
      />
    </div>
  );
}
