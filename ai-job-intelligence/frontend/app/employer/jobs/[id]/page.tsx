"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { apiCall } from "@/components/api";
import MessageDialog from "@/components/MessageDialog";

interface Job {
  id: number;
  title: string;
  description: string;
  location: string;
  salary_min?: number;
  salary_max?: number;
  required_skills: string[];
  applications_count: number;
  views: number;
  status: "open" | "closed" | "draft";
  created_at: string;
}

interface Application {
  id: number;
  job_title: string;
  candidate_name: string;
  candidate_email: string;
  status: "applied" | "reviewing" | "shortlisted" | "accepted" | "rejected";
  match_score?: number;
  applied_at: string;
}

export default function EmployerJobDetailPage() {
  const router = useRouter();
  const params = useParams();
  const jobId = params.id as string;
  const [job, setJob] = useState<Job | null>(null);
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("all");
  const [dialog, setDialog] = useState({ open: false, title: '', message: '', type: 'info' as 'info' | 'success' | 'error' | 'warning' });
  const [confirmState, setConfirmState] = useState<{ open: boolean; message: string; onConfirm: () => void }>({
    open: false,
    message: '',
    onConfirm: () => {},
  });

  // Fetches and returns the applicants; used on load and after accept/reject.
  const loadApplications = useCallback(async (): Promise<Application[]> => {
    const response = await apiCall(`/api/jobs/${jobId}/applications`);
    if (!response.ok) return [];
    const data = await response.json();
    return Array.isArray(data) ? data : [];
  }, [jobId]);

  const refreshApplications = async () => {
    try {
      setApplications(await loadApplications());
    } catch {
      setDialog({ open: true, title: 'Error', message: "Error fetching applications", type: 'error' });
    }
  };

  // State is set only after each request returns, and never once the page
  // has moved on (`active`), so a slow response can't overwrite newer data.
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const response = await apiCall(`/api/jobs/${jobId}`);
        if (response.ok) {
          const data = await response.json();
          if (active) setJob(data);
        }
      } catch {
        if (active) setDialog({ open: true, title: 'Error', message: "Error loading job details", type: 'error' });
      } finally {
        if (active) setLoading(false);
      }
    })();
    loadApplications()
      .then((data) => {
        if (active) setApplications(data);
      })
      .catch(() => {
        if (active) setDialog({ open: true, title: 'Error', message: "Error fetching applications", type: 'error' });
      });
    return () => {
      active = false;
    };
  }, [jobId, loadApplications]);

  const handleAccept = async (appId: number) => {
    setConfirmState({
      open: true,
      message: "Are you sure you want to accept this application?",
      onConfirm: async () => {
        try {
          const response = await apiCall(`/api/applications/${appId}/accept`, {
            method: "POST",
          });
          if (response.ok) {
            setDialog({ open: true, title: 'Success', message: "Application accepted!", type: 'success' });
            await refreshApplications();
          }
        } catch {
          setDialog({ open: true, title: 'Error', message: "Error accepting application", type: 'error' });
        }
      },
    });
  };

  const handleReject = async (appId: number) => {
    setConfirmState({
      open: true,
      message: "Are you sure you want to reject this application?",
      onConfirm: async () => {
        try {
          const response = await apiCall(`/api/applications/${appId}/reject`, {
            method: "POST",
          });
          if (response.ok) {
            setDialog({ open: true, title: 'Success', message: "Application rejected", type: 'success' });
            await refreshApplications();
          }
        } catch {
          setDialog({ open: true, title: 'Error', message: "Error rejecting application", type: 'error' });
        }
      },
    });
  };

  const filteredApplications =
    filter === "all"
      ? applications
      : applications.filter((app) => app.status === filter);

  if (loading) {
    return (
      <div className="min-h-screen text-neutral-100">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <p className="text-base text-neutral-500">Loading job details...</p>
        </div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="min-h-screen text-neutral-100">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <p className="text-base text-neutral-500">Job not found</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen text-neutral-100">
      <div className="max-w-5xl mx-auto px-4 py-6">
        {/* Header */}
        <button
          onClick={() => router.push("/employer/jobs")}
          className="text-base text-blue-600 mb-3"
        >
          Back to Jobs
        </button>

        <div className="card mb-4">
          <div className="flex justify-between">
            <div>
              <h1 className="page-title">{job.title}</h1>
              <p className="text-base text-neutral-400">{job.location}</p>
            </div>
            <div className="flex items-start gap-3">
              <span className={`text-base px-2 py-0.5 rounded border ${getStatusTag(job.status)}`}>
                {job.status}
              </span>
              <button
                onClick={() => router.push(`/employer/jobs/${job.id}/edit`)}
                className="text-base px-3 py-0.5 rounded border border-neutral-700 text-neutral-200 hover:bg-neutral-700/50"
              >
                Edit posting
              </button>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-2 mb-3">
          <div className="card p-4 text-center">
            <p className="text-base text-neutral-400">Applications</p>
            <p className="text-base font-bold">{job.applications_count}</p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-base text-neutral-400">Views</p>
            <p className="text-base font-bold">{job.views || 0}</p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-base text-neutral-400">Posted</p>
            <p className="text-base font-bold">
              {new Date(job.created_at).toLocaleDateString()}
            </p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-base text-neutral-400">Status</p>
            <p className="text-base font-bold">{job.status}</p>
          </div>
        </div>

        {/* Description */}
        <div className="card mb-4">
          <h2 className="section-title mb-2">
            Job Description
          </h2>
          <p className="text-base text-neutral-300">{job.description}</p>
        </div>

        {/* Skills */}
        <div className="card mb-4">
          <h2 className="section-title mb-2">
            Required Skills
          </h2>
          <div className="flex flex-wrap gap-1">
            {job.required_skills.map((skill) => (
              <span
                key={skill}
                className="text-base px-2 py-0.5 bg-neutral-800 text-neutral-200 rounded"
              >
                {skill}
              </span>
            ))}
          </div>
        </div>

        {/* Applications */}
        <div className="card">
          <h2 className="section-title mb-3">
            Applications ({filteredApplications.length})
          </h2>

          <div className="flex gap-1 mb-2 flex-wrap">
            {["all", "applied", "reviewing", "shortlisted", "accepted", "rejected"].map(
              (status) => (
                <button
                  key={status}
                  onClick={() => setFilter(status)}
                  className={`text-base px-3 py-2 border rounded ${
                    filter === status
                      ? "bg-blue-600 text-white border-blue-600"
                      : "bg-neutral-800 text-neutral-200 border-neutral-700 hover:bg-neutral-700/50"
                  }`}
                >
                  {status === "all"
                    ? "All"
                    : status.charAt(0).toUpperCase() + status.slice(1)}
                </button>
              ),
            )}
          </div>

          {filteredApplications.length === 0 ? (
            <p className="text-base text-neutral-500 py-3">No applications yet</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-base">
                <thead className="border-b border-neutral-700/50">
                  <tr>
                    <th className="text-left py-1 text-neutral-400">Candidate</th>
                    <th className="text-left py-1 text-neutral-400">Match</th>
                    <th className="text-left py-1 text-neutral-400">Status</th>
                    <th className="text-left py-1 text-neutral-400">Applied</th>
                    <th className="text-left py-1 text-neutral-400">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredApplications.map((app) => (
                    <tr
                      key={app.id}
                      className="border-t border-neutral-700/50"
                    >
                      <td className="py-1">
                        <p className="font-medium">
                          {app.candidate_name || "Anonymous"}
                        </p>
                        <p className="text-neutral-400">{app.candidate_email}</p>
                      </td>
                      <td className="py-1 text-neutral-400">
                        {app.match_score || 0}%
                      </td>
                      <td className="py-1">
                        <span
                          className={`text-base px-2 py-0.5 rounded border ${getAppStatusTag(app.status)}`}
                        >
                          {app.status}
                        </span>
                      </td>
                      <td className="py-1 text-neutral-500">
                        {new Date(app.applied_at).toLocaleDateString()}
                      </td>
                      <td className="py-1">
                        <div className="flex gap-1">
                          {app.status === "applied" && (
                            <>
                              <button
                                onClick={() => handleAccept(app.id)}
                                className="text-base px-1.5 py-0.5 bg-emerald-500/15 text-emerald-300 rounded border border-emerald-500/30"
                              >
                                Accept
                              </button>
                              <button
                                onClick={() => handleReject(app.id)}
                                className="text-base px-1.5 py-0.5 bg-rose-500/15 text-rose-300 rounded border border-rose-500/30"
                              >
                                Reject
                              </button>
                            </>
                          )}
                          {app.status === "shortlisted" && (
                            <button
                              onClick={() => handleAccept(app.id)}
                              className="text-base px-1.5 py-0.5 bg-emerald-500/15 text-emerald-300 rounded border border-emerald-500/30"
                            >
                              Accept
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
        <MessageDialog
          open={dialog.open}
          onClose={() => setDialog({ ...dialog, open: false })}
          title={dialog.title}
          message={dialog.message}
          type={dialog.type}
        />
        <MessageDialog
          open={confirmState.open}
          onClose={() => setConfirmState({ ...confirmState, open: false })}
          title="Confirm"
          message={confirmState.message}
          type="warning"
          confirmText="Yes"
          cancelText="No"
          onConfirm={confirmState.onConfirm}
        />
      </div>
    </div>
  );
}

function getStatusTag(status: string) {
  switch (status) {
    case "open":
      return "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";
    case "closed":
      return "bg-rose-500/15 text-rose-300 border-rose-500/30";
    case "draft":
      return "bg-amber-500/15 text-amber-300 border-amber-500/30";
    default:
      return "bg-neutral-800 text-neutral-100 border-neutral-700/50";
  }
}

function getAppStatusTag(status: string) {
  switch (status) {
    case "shortlisted":
      return "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";
    case "accepted":
      return "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";
    case "rejected":
      return "bg-rose-500/15 text-rose-300 border-rose-500/30";
    case "reviewing":
      return "bg-amber-500/15 text-amber-300 border-amber-500/30";
    default:
      return "bg-blue-500/15 text-blue-300 border-blue-500/30";
  }
}
