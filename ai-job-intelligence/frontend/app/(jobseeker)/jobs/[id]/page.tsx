"use client";

import { formatScore } from "@/components/format";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { apiCall } from "@/components/api";
import { describeApiError } from "@/components/format";
import { useAuth } from "@/components/AuthProvider";
import { FaArrowLeft } from "react-icons/fa";
import MessageDialog from "@/components/MessageDialog";

interface Job {
  id: number;
  title: string;
  company: string;
  location: string;
  salary_min?: number;
  salary_max?: number;
  description: string;
  required_skills: string[];
  match_score?: number;
  skill_gaps?: string[];
  match_breakdown?: {
    skills_match: number;
    experience_match: number | null;
    education_match: number | null;
  };
}

export default function JobDetailPage() {
  const router = useRouter();
  const params = useParams();
  const jobId = params.id as string;
  const { role } = useAuth();
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState(false);
  const [saved, setSaved] = useState(false);
  const [dialog, setDialog] = useState({ open: false, title: '', message: '', type: 'info' as 'info' | 'success' | 'error' | 'warning' });
  const isAdmin = role === "admin";

  useEffect(() => {
    fetchJob();
  }, [jobId]);

  const fetchJob = async () => {
    setLoading(true);
    try {
      const response = await apiCall(`/api/jobs/${jobId}`);
      if (response.ok) {
        const data = await response.json();
        setJob(data);
      }
      // Seed the toggle so an already-saved job offers "Unsave" rather than
      // failing with "Job already saved".
      const savedRes = await apiCall("/api/saved-jobs");
      if (savedRes.ok) {
        const savedJobs: { job_id: number }[] = await savedRes.json();
        setSaved(savedJobs.some((s) => s.job_id === parseInt(jobId)));
      }
    } catch (err) {
      setDialog({ open: true, title: 'Error', message: err instanceof Error ? err.message : "Error loading job", type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleApply = async () => {
    setApplying(true);
    try {
      const response = await apiCall("/api/applications", {
        method: "POST",
        body: JSON.stringify({ job_id: parseInt(jobId) }),
      });
      const data = await response.json();
      if (response.ok) {
        setDialog({ open: true, title: 'Success', message: "Application submitted!", type: 'success' });
        setTimeout(() => router.push("/applications"), 1500);
      } else {
        setDialog({ open: true, title: 'Error', message: describeApiError(data, "Failed to apply"), type: 'error' });
      }
    } catch (err) {
      setDialog({ open: true, title: 'Error', message: "Error submitting application", type: 'error' });
    } finally {
      setApplying(false);
    }
  };

  const handleSave = async () => {
    try {
      // The backend saves via POST /api/saved-jobs (job_id in the body) and
      // unsaves via DELETE /api/saved-jobs/{job_id}.
      const response = saved
        ? await apiCall(`/api/saved-jobs/${jobId}`, { method: "DELETE" })
        : await apiCall("/api/saved-jobs", {
            method: "POST",
            body: JSON.stringify({ job_id: parseInt(jobId) }),
          });
      const data = await response.json();
      if (response.ok) {
        setSaved(!saved);
        setDialog({ open: true, title: 'Success', message: saved ? "Job removed" : "Job saved!", type: 'success' });
      } else {
        setDialog({ open: true, title: 'Error', message: describeApiError(data, "Error saving job"), type: 'error' });
      }
    } catch (err) {
      setDialog({ open: true, title: 'Error', message: "Error saving job", type: 'error' });
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen text-neutral-100">
        <div className="max-w-3xl mx-auto px-4 py-6">
          <p className="text-base text-neutral-400">Loading job...</p>
        </div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="min-h-screen text-neutral-100">
        <div className="max-w-3xl mx-auto px-4 py-6">
          <p className="text-base text-neutral-400">Job not found</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen text-neutral-100">
      <div className="max-w-3xl mx-auto px-4 py-6">
        {isAdmin && (
          <button
            onClick={() => router.push("/admin/dashboard")}
            className="flex items-center gap-2 text-sm text-rose-600 hover:text-rose-300 mb-3"
          >
            <FaArrowLeft className="w-3 h-3" />
            Back to Admin Panel
          </button>
        )}

        {/* Header */}
        <div className="border border-neutral-700/50 rounded p-4 mb-4">
          <div className="flex justify-between">
            <div>
              <h1 className="page-title">{job.title}</h1>
              <p className="text-base text-neutral-400">{job.company}</p>
            </div>
            {!isAdmin && (
              <button
                onClick={handleSave}
                className={`text-base px-3 py-1 border rounded ${
                  saved
                    ? "border-yellow-300 bg-amber-500/10 text-amber-300"
                    : "border-neutral-700 hover:bg-neutral-700/50"
                }`}
              >
                {saved ? "[OK] Saved" : "Save"}
              </button>
            )}
          </div>
          <div className="flex gap-3 mt-1 text-base text-neutral-400">
            <span> |  {job.location}</span>
            {job.salary_min && job.salary_max && (
              <span>
                $ ${job.salary_min.toLocaleString()} - ${job.salary_max.toLocaleString()}
              </span>
            )}
          </div>
        </div>

        {!isAdmin && (
          <>
            {/* Match Info */}
            {job.match_score !== undefined && (
              <div className="grid grid-cols-4 gap-2 mb-4">
                <div className="card p-4 text-center">
                  <p className="text-base text-neutral-400">Match</p>
                  <p
                    className={`text-base font-bold ${
                      job.match_score >= 75
                        ? "text-green-600"
                        : job.match_score >= 50
                          ? "text-yellow-600"
                          : "text-red-600"
                    }`}
                  >
                    {Math.round(job.match_score)}%
                  </p>
                </div>
                <div className="card p-4 text-center">
                  <p className="text-base text-neutral-400">Experience</p>
                  <p className="text-base font-bold">
                    {formatScore(job.match_breakdown?.experience_match)}
                  </p>
                </div>
                <div className="card p-4 text-center">
                  <p className="text-base text-neutral-400">Skills</p>
                  <p className="text-base font-bold">
                    {job.match_breakdown?.skills_match ?? 0}%
                  </p>
                </div>
                <div className="card p-4 text-center">
                  <p className="text-base text-neutral-400">Education</p>
                  <p className="text-base font-bold">
                    {formatScore(job.match_breakdown?.education_match)}
                  </p>
                </div>
              </div>
            )}

            {/* Skill Gaps */}
            {job.skill_gaps && job.skill_gaps.length > 0 && (
              <div className="card mb-4">
                <h2 className="section-title mb-2">
                  Skill Gaps (AI Recommendation)
                </h2>
                <div className="flex flex-wrap gap-1">
                  {job.skill_gaps.slice(0, 5).map((s) => (
                    <span
                      key={s}
                      className="text-base px-2 py-0.5 bg-rose-500/10 text-rose-300 rounded border border-rose-500/30"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* Description */}
        <div className="card mb-4">
          <h2 className="section-title mb-2">
            About This Role
          </h2>
          <p className="text-base text-neutral-300 leading-relaxed">
            {job.description}
          </p>
        </div>

        {/* Skills */}
        <div className="card mb-4">
          <h2 className="section-title mb-2">
            Required Skills (AI Extracted)
          </h2>
          <div className="flex flex-wrap gap-1">
            {job.required_skills.map((s) => (
              <span
                key={s}
                className="text-base px-2 py-0.5 bg-neutral-800 text-neutral-200 rounded"
              >
                {s}
              </span>
            ))}
          </div>
        </div>

        {/* Apply */}
        {!isAdmin && (
          <div className="flex gap-2">
            <button
              onClick={handleApply}
              disabled={applying}
              className="btn-primary"
            >
              {applying ? "Applying..." : "Apply Now"}
            </button>
          </div>
        )}
        <MessageDialog
          open={dialog.open}
          onClose={() => setDialog({ ...dialog, open: false })}
          title={dialog.title}
          message={dialog.message}
          type={dialog.type}
        />
      </div>
    </div>
  );
}
