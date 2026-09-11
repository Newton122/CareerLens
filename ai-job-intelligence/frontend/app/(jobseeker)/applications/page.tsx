"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { apiCall } from "@/components/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import { FaSearch } from "react-icons/fa";
import MessageDialog from "@/components/MessageDialog";

interface Application {
  id: number;
  job_id: number;
  job_title: string;
  company: string;
  status: "applied" | "reviewing" | "shortlisted" | "accepted" | "rejected";
  match_score: number;
  applied_at: string;
}

export default function ApplicationsPage() {
  const router = useRouter();
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("");
  const [search, setSearch] = useState("");
  const [dialog, setDialog] = useState({ open: false, title: '', message: '', type: 'info' as 'info' | 'success' | 'error' | 'warning' });

  useEffect(() => {
    fetchApplications();
  }, []);

  const fetchApplications = async () => {
    setLoading(true);
    try {
      const response = await apiCall("/api/applications");
      if (response.ok) {
        const data = await response.json();
        setApplications(data);
      } else {
        setDialog({ open: true, title: 'Error', message: "Failed to load applications", type: 'error' });
      }
    } catch (err) {
      setDialog({ open: true, title: 'Error', message: err instanceof Error ? err.message : "Error fetching applications", type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const filtered = applications.filter((a) => {
    const matchesSearch =
      a.job_title.toLowerCase().includes(search.toLowerCase()) ||
      a.company.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = filter === "" || a.status === filter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="min-h-screen text-neutral-100">
      <div className="max-w-5xl mx-auto px-4 py-6">
        <h1 className="page-title mb-2">My Applications</h1>
        <p className="page-subtitle mb-6">
          Track your job application status
        </p>

        {/* Search */}
        <div className="mb-3">
          <div className="flex items-center gap-1 border border-neutral-700 rounded px-2">
            <FaSearch className="w-3 h-3 text-neutral-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by job title or company..."
              className="w-full px-2 py-2 text-base border-0 focus:outline-none focus:ring-0"
            />
          </div>
        </div>

        {/* Filter */}
        <div className="flex gap-1 mb-3 flex-wrap">
          {[
            "",
            "applied",
            "reviewing",
            "shortlisted",
            "accepted",
            "rejected",
          ].map((status) => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={`text-base px-3 py-2 border rounded ${
                filter === status
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-neutral-800 text-neutral-200 border-neutral-700 hover:bg-neutral-700/50"
              }}`}
            >
              {status === "" ? "All" : status.charAt(0).toUpperCase() + status.slice(1)}
            </button>
          ))}
        </div>

        {loading ? (
          <LoadingSpinner />
        ) : filtered.length > 0 ? (
          <div className="space-y-1">
            {filtered.map((app) => (
              <div
                key={app.id}
                className="border border-neutral-700/50 rounded p-2"
              >
                <div className="flex justify-between">
                  <div>
                    <p className="text-base font-medium">{app.job_title}</p>
                    <p className="text-base text-neutral-400">
                      {app.company}  |  {new Date(app.applied_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="text-right">
                    <span
                      className={`text-base px-2 py-0.5 rounded border ${
                        getStatusClass(app.status)
                      }`}
                    >
                      {app.status}
                    </span>
                    <p className="text-base text-neutral-400 mt-1">
                      {Math.round(app.match_score)}% match
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-base text-neutral-500">No applications found</p>
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

function getStatusClass(status: string) {
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
