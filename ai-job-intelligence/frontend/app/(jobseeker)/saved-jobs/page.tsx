"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { apiCall } from "@/components/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import { FaSearch } from "react-icons/fa";
import MessageDialog from "@/components/MessageDialog";

interface SavedJob {
  id: number;
  job_id: number;
  title: string;
  company: string;
  location: string;
  salary_min?: number;
  salary_max?: number;
  saved_at: string;
  match_score?: number;
  required_skills: string[];
}

export default function SavedJobsPage() {
  const router = useRouter();
  const [savedJobs, setSavedJobs] = useState<SavedJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [dialog, setDialog] = useState({ open: false, title: '', message: '', type: 'info' as 'info' | 'success' | 'error' | 'warning' });
  const [confirmState, setConfirmState] = useState<{ open: boolean; message: string; onConfirm: () => void }>({
    open: false,
    message: '',
    onConfirm: () => {},
  });

  useEffect(() => {
    fetchSavedJobs();
  }, []);

  const fetchSavedJobs = async () => {
    setLoading(true);
    try {
      const response = await apiCall("/api/saved-jobs");
      if (response.ok) {
        const data = await response.json();
        setSavedJobs(data);
      }
    } catch (err) {
      setDialog({ open: true, title: 'Error', message: err instanceof Error ? err.message : "Error fetching saved jobs", type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const removeSaved = async (jobId: number) => {
    setConfirmState({
      open: true,
      message: "Are you sure you want to remove this saved job?",
      onConfirm: async () => {
        try {
          const response = await apiCall(`/api/saved-jobs/${jobId}`, {
            method: "DELETE",
          });
          if (response.ok) {
            setSavedJobs(savedJobs.filter((j) => j.job_id !== jobId));
            setDialog({ open: true, title: 'Success', message: "Job removed", type: 'success' });
          }
        } catch (err) {
          setDialog({ open: true, title: 'Error', message: "Error removing job", type: 'error' });
        }
      },
    });
  };

  const filteredJobs = search
    ? savedJobs.filter(
        (j) =>
          j.title.toLowerCase().includes(search.toLowerCase()) ||
          j.company.toLowerCase().includes(search.toLowerCase()),
      )
    : savedJobs;

  return (
    <div className="min-h-screen text-neutral-100">
      <div className="max-w-5xl mx-auto px-4 py-6">
        <h1 className="page-title mb-2">Saved Jobs</h1>
        <p className="page-subtitle mb-6">
          Your bookmarked job opportunities
        </p>

        <div className="mb-3">
          <div className="flex items-center gap-1 border border-neutral-700 rounded px-2">
            <FaSearch className="w-3 h-3 text-neutral-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search saved jobs..."
              className="w-full px-2 py-2 text-base border-0 focus:outline-none focus:ring-0"
            />
          </div>
        </div>

        {loading ? (
          <LoadingSpinner />
        ) : savedJobs.length > 0 ? (
          <div className="space-y-2">
            {filteredJobs.map((job) => (
              <div
                key={job.id}
                className="border border-neutral-700/50 rounded p-2"
              >
                <div className="flex justify-between">
                  <div>
                    <p
                      className="text-base font-medium cursor-pointer hover:text-blue-600"
                      onClick={() => router.push(`/jobs/${job.job_id}`)}
                    >
                      {job.title}
                    </p>
                    <p className="text-base text-neutral-400">{job.company}</p>
                  </div>
                  {job.match_score !== undefined && (
                    <span className="text-base font-bold text-blue-600">
                      {Math.round(job.match_score)}%
                    </span>
                  )}
                </div>
                <div className="flex gap-1 mt-1 text-base text-neutral-500">
                  <span> |  {job.location}</span>
                </div>
                <div className="flex gap-2 mt-1">
                  <button
                    onClick={() => router.push(`/jobs/${job.job_id}`)}
                    className="btn-secondary"
                  >
                    View
                  </button>
                  <button
                    onClick={() => removeSaved(job.job_id)}
                    className="text-base px-3 py-2 border border-neutral-700 text-red-600 rounded hover:bg-neutral-700/50"
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="border border-dashed border-neutral-700 rounded p-6 text-center">
            <p className="text-base text-neutral-400 mb-2">No saved jobs</p>
            <button
              onClick={() => router.push("/jobs")}
              className="btn-primary btn-small"
            >
              Browse Jobs
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
