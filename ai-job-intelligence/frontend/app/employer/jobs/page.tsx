"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiCall } from "@/components/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import { FaSearch, FaFilter } from "react-icons/fa";
import MessageDialog from "@/components/MessageDialog";

interface Job {
  id: number;
  title: string;
  location: string;
  status: "open" | "closed" | "draft";
  applications_count: number;
  created_at: string;
  views: number;
}

export default function EmployerJobsPage() {
  const router = useRouter();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [dialog, setDialog] = useState({ open: false, title: '', message: '', type: 'info' as 'info' | 'success' | 'error' | 'warning' });

  useEffect(() => {
    fetchJobs();
  }, []);

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const response = await apiCall("/api/jobs");
      if (response.ok) {
        const data = await response.json();
        setJobs(data);
      } else {
        setDialog({ open: true, title: 'Error', message: "Failed to load jobs", type: 'error' });
      }
    } catch (err) {
      setDialog({ open: true, title: 'Error', message: err instanceof Error ? err.message : "Error fetching jobs", type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const filteredJobs = jobs.filter((job) => {
    const matchesSearch =
      job.title.toLowerCase().includes(search.toLowerCase()) ||
      job.location.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === "" || job.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const getStatusTag = (status: string) => {
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
  };

  return (
    <div className="min-h-screen text-neutral-100">
      <div className="max-w-5xl mx-auto px-4 py-6">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h1 className="page-title mb-2">My Job Postings</h1>
            <p className="text-base text-neutral-400">
              Track and manage your job postings
            </p>
          </div>
          <button
            onClick={() => router.push("/employer/jobs/new")}
            className="btn-primary"
          >
            Post New Job
          </button>
        </div>

        <div className="mb-3">
          <div className="flex items-center gap-1 border border-neutral-700 rounded px-2">
            <FaSearch className="w-3 h-3 text-neutral-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by title or location..."
              className="w-full px-2 py-2 text-base border-0 focus:outline-none focus:ring-0"
            />
          </div>
        </div>

        <div className="flex gap-1 mb-3 flex-wrap items-center">
          <FaFilter className="w-3 h-3 text-neutral-500" />
          <span className="text-base text-neutral-400 mr-1">Status:</span>
          <button
            onClick={() => setStatusFilter("")}
            className={`text-base px-3 py-1 border rounded ${
              statusFilter === ""
                ? "bg-blue-600 text-white border-blue-600"
                : "bg-neutral-800 text-neutral-200 border-neutral-700 hover:bg-neutral-700/50"
            }`}
          >
            All
          </button>
          <button
            onClick={() => setStatusFilter("open")}
            className={`text-base px-3 py-1 border rounded ${
              statusFilter === "open"
                ? "bg-green-600 text-white border-green-600"
                : "bg-neutral-800 text-neutral-200 border-neutral-700 hover:bg-neutral-700/50"
            }`}
          >
            Open
          </button>
          <button
            onClick={() => setStatusFilter("closed")}
            className={`text-base px-3 py-1 border rounded ${
              statusFilter === "closed"
                ? "bg-red-600 text-white border-red-600"
                : "bg-neutral-800 text-neutral-200 border-neutral-700 hover:bg-neutral-700/50"
            }`}
          >
            Closed
          </button>
          <button
            onClick={() => setStatusFilter("draft")}
            className={`text-base px-3 py-1 border rounded ${
              statusFilter === "draft"
                ? "bg-yellow-600 text-white border-yellow-600"
                : "bg-neutral-800 text-neutral-200 border-neutral-700 hover:bg-neutral-700/50"
            }`}
          >
            Draft
          </button>
        </div>

        {loading ? (
          <LoadingSpinner />
        ) : filteredJobs.length > 0 ? (
          <div className="border border-neutral-700/50 rounded overflow-hidden">
            <table className="w-full text-base">
              <thead className="bg-neutral-800/50 border-b border-neutral-700/50">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-neutral-200">
                    Title
                  </th>
                  <th className="px-3 py-2 text-left font-medium text-neutral-200">
                    Location
                  </th>
                  <th className="px-3 py-2 text-left font-medium text-neutral-200">
                    Apps
                  </th>
                  <th className="px-3 py-2 text-left font-medium text-neutral-200">
                    Views
                  </th>
                  <th className="px-3 py-2 text-left font-medium text-neutral-200">
                    Status
                  </th>
                  <th className="px-3 py-2 text-left font-medium text-neutral-200">
                    Posted
                  </th>
                  <th className="px-3 py-2 text-left font-medium text-neutral-200">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredJobs.map((job) => (
                  <tr
                    key={job.id}
                    className="border-t border-neutral-700/50 hover:bg-neutral-700/50"
                  >
                    <td className="px-3 py-2 font-medium">{job.title}</td>
                    <td className="px-3 py-2 text-neutral-400">
                      {job.location}
                    </td>
                    <td className="px-3 py-2 text-neutral-400">
                      {job.applications_count}
                    </td>
                    <td className="px-3 py-2 text-neutral-400">{job.views}</td>
                    <td className="px-3 py-2">
                      <span
                        className={`text-base px-2 py-0.5 rounded border ${getStatusTag(job.status)}`}
                      >
                        {job.status}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-neutral-500">
                      {new Date(job.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-3">
                        <button
                          onClick={() => router.push(`/employer/jobs/${job.id}`)}
                          className="text-base text-blue-600 hover:text-blue-300 font-medium"
                        >
                          View
                        </button>
                        <button
                          onClick={() =>
                            router.push(`/employer/jobs/${job.id}/edit`)
                          }
                          className="text-base text-neutral-400 hover:text-neutral-100 font-medium"
                        >
                          Edit
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="border border-dashed border-neutral-700 rounded p-6 text-center">
            <p className="text-base text-neutral-500 mb-3">No jobs found</p>
            <button
              onClick={() => router.push("/employer/jobs/new")}
              className="btn-primary btn-small"
            >
              Post Your First Job
            </button>
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
    </div>
  );
}
