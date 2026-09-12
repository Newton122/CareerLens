"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiCall } from "@/components/api";
import { useAuth } from "@/components/AuthProvider";
import LoadingSpinner from "@/components/LoadingSpinner";
import { FaSearch, FaFilter, FaArrowLeft } from "react-icons/fa";
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
}

export default function JobsPage() {
  const router = useRouter();
  const { role } = useAuth();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [minMatch, setMinMatch] = useState(0);
  const [dialog, setDialog] = useState({ open: false, title: '', message: '', type: 'info' as 'info' | 'success' | 'error' | 'warning' });
  const isAdmin = role === "admin";

  // State is set only after the request returns, and never once the page
  // has moved on (`active`), so a slow response can't overwrite newer data.
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const response = await apiCall("/api/jobs");
        if (response.ok) {
          const data = await response.json();
          if (active) setJobs(data);
        } else {
          if (active) setDialog({ open: true, title: 'Error', message: "Failed to load jobs", type: 'error' });
        }
      } catch (err) {
        if (active) setDialog({ open: true, title: 'Error', message: err instanceof Error ? err.message : "Error fetching jobs", type: 'error' });
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const filtered = jobs.filter((j) => {
    const matchesSearch =
      search === "" ||
      j.title.toLowerCase().includes(search.toLowerCase()) ||
      j.company.toLowerCase().includes(search.toLowerCase());
    const matchesMatch =
      j.match_score === undefined || j.match_score >= minMatch;
    return matchesSearch && matchesMatch;
  });

  return (
    <div className="min-h-screen text-neutral-100">
      <div className="max-w-5xl mx-auto px-4 py-6">
        {isAdmin && (
          <button
            onClick={() => router.push("/admin/dashboard")}
            className="flex items-center gap-2 text-sm text-rose-600 hover:text-rose-300 mb-3"
          >
            <FaArrowLeft className="w-3 h-3" />
            Back to Admin Panel
          </button>
        )}
        <h1 className="page-title mb-2">
          {isAdmin ? "All Jobs (Admin View)" : "Find Jobs"}
        </h1>
        <p className="page-subtitle mb-6">
          {isAdmin ? "Browse all jobs on the platform" : "Discover opportunities matched to your CV"}
        </p>

        <div className="mb-3">
          <div className="flex items-center gap-1 border border-neutral-700 rounded px-2 mb-2">
            <FaSearch className="w-3 h-3 text-neutral-500" />
            <input
              type="text"
              placeholder="Search by title or company..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full px-2 py-2 text-base border-0 focus:outline-none focus:ring-0"
            />
          </div>
          {!isAdmin && (
            <div className="flex items-center gap-2">
              <FaFilter className="w-3 h-3 text-neutral-500" />
              <span className="text-base text-neutral-400">Min match:</span>
              <input
                type="range"
                min="0"
                max="100"
                value={minMatch}
                onChange={(e) => setMinMatch(Number(e.target.value))}
                className="flex-1"
              />
              <span className="text-base text-neutral-400 w-10">{minMatch}%</span>
            </div>
          )}
        </div>

        {loading ? (
          <LoadingSpinner />
        ) : filtered.length > 0 ? (
          <div className="space-y-2">
            {filtered.map((job) => (
              <div
                key={job.id}
                className="border border-neutral-700/50 rounded p-2 cursor-pointer hover:bg-neutral-700/50"
                onClick={() => router.push(`/jobs/${job.id}`)}
              >
                <div className="flex justify-between">
                  <div>
                    <p className="text-base font-medium">{job.title}</p>
                    <p className="text-base text-neutral-400">{job.company}</p>
                  </div>
                  {job.match_score !== undefined && (
                    <span className="text-base font-bold text-blue-600">
                      {Math.round(job.match_score)}%
                    </span>
                  )}
                </div>
                <div className="flex flex-wrap gap-1 mt-1">
                  {job.required_skills.slice(0, 3).map((s) => (
                    <span
                      key={s}
                      className="text-base px-2 py-0.5 bg-neutral-800 text-neutral-200 rounded"
                    >
                      {s}
                    </span>
                  ))}
                </div>
                <div className="flex gap-3 mt-1 text-base text-neutral-500">
                  <span> |  {job.location}</span>
                  {job.salary_min && job.salary_max && (
                    <span>
                      $ ${job.salary_min.toLocaleString()} - $
                      {job.salary_max.toLocaleString()}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-base text-neutral-500">No jobs found</p>
        )}
      </div>
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
