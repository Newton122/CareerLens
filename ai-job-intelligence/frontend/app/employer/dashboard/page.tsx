"use client";
import LoadingSpinner from "@/components/LoadingSpinner";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiCall } from "@/components/api";
import { motion } from "framer-motion";
import { FaBriefcase, FaUsers, FaFileAlt, FaPlus, FaArrowRight, FaEye } from "react-icons/fa";
import type { IconType } from "react-icons";
import MessageDialog from "@/components/MessageDialog";

interface EmployerStats {
  jobs_posted: number;
  applications_received: number;
  candidates_viewed: number;
  profile_views: number;
}

interface Job {
  id: number;
  title: string;
  location: string;
  status: "open" | "closed" | "draft";
  applications_count: number;
  created_at: string;
}

interface Application {
  id: number;
  job_id: number;
  job_title: string;
  candidate_name: string;
  status: string;
  match_score: number;
}

export default function EmployerDashboard() {
  const router = useRouter();
  const [stats, setStats] = useState<EmployerStats>({
    jobs_posted: 0,
    applications_received: 0,
    candidates_viewed: 0,
    profile_views: 0,
  });
  const [jobs, setJobs] = useState<Job[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialog, setDialog] = useState({ open: false, title: '', message: '', type: 'info' as 'info' | 'success' | 'error' | 'warning' });

  // State is set only after the request returns, and never once the page
  // has moved on (`active`), so a slow response can't overwrite newer data.
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const statsRes = await apiCall("/api/user/stats");
        if (statsRes.ok) {
          const data = await statsRes.json();
          if (active) setStats(data);
        }

        const jobsRes = await apiCall("/api/jobs");
        if (jobsRes.ok) {
          const jobsData: Job[] = await jobsRes.json();
          if (active) setJobs(jobsData.slice(0, 3));

          const apps: Application[] = [];
          for (const job of jobsData.slice(0, 3)) {
            const appsRes = await apiCall(
              `/api/jobs/${job.id}/applications`,
            );
            if (appsRes.ok) {
              const jobApps = await appsRes.json();
              jobApps.forEach((app: Application & { match_score: number | null }) => {
                apps.push({
                  id: app.id,
                  job_id: app.job_id,
                  job_title: app.job_title,
                  candidate_name: app.candidate_name,
                  status: app.status,
                  match_score: app.match_score || 0,
                });
              });
            }
          }
          if (active) setApplications(apps.slice(0, 5));
        }
      } catch (err) {
        if (active) setDialog({ open: true, title: 'Error', message: err instanceof Error ? err.message : "Error loading dashboard", type: 'error' });
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="min-h-screen bg-neutral-900">
      <div className="max-w-5xl mx-auto px-4 py-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="border-b border-neutral-700/50 pb-4 mb-6"
        >
          <div className="flex justify-between items-center">
            <div>
              <h1 className="page-title">Employer Dashboard</h1>
              <p className="page-subtitle">
                Manage your job postings and review candidates
              </p>
            </div>
            <motion.button
              onClick={() => router.push("/employer/jobs/new")}
              className="btn-primary flex items-center gap-2"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <FaPlus className="w-4 h-4" />
              Post a Job
            </motion.button>
          </div>
        </motion.div>

        <motion.div
          className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <StatCard label="Jobs Posted" value={stats.jobs_posted} icon={FaBriefcase} color="blue" />
          <StatCard label="Applications" value={stats.applications_received} icon={FaFileAlt} color="emerald" />
          <StatCard label="Candidates" value={stats.candidates_viewed} icon={FaUsers} color="emerald" />
          <StatCard label="Profile Views" value={stats.profile_views} icon={FaEye} color="amber" />
        </motion.div>

        <motion.div
          className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-5 mb-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <h2 className="section-title mb-4">Quick Actions</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <QuickAction
              icon={FaPlus}
              label="Post Job"
              onClick={() => router.push("/employer/jobs/new")}
              color="blue"
            />
            <QuickAction
              icon={FaBriefcase}
              label="View Jobs"
              onClick={() => router.push("/employer/jobs")}
              color="blue"
            />
            <QuickAction
              icon={FaUsers}
              label="Search Candidates"
              onClick={() => router.push("/employer/candidates")}
              color="emerald"
            />
            <QuickAction
              icon={FaFileAlt}
              label="Company"
              onClick={() => router.push("/employer/company")}
              color="emerald"
            />
          </div>
        </motion.div>

        <motion.div
          className="mb-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <div className="flex justify-between items-center mb-4">
            <h2 className="section-title">Your Job Postings</h2>
            <button
              onClick={() => router.push("/employer/jobs")}
              className="text-sm text-blue-400 hover:text-blue-300 flex items-center gap-1"
            >
              View all <FaArrowRight className="w-3 h-3" />
            </button>
          </div>

          {loading ? (
            <LoadingSpinner />
          ) : jobs.length > 0 ? (
            <div className="space-y-3">
              {jobs.map((job, index) => (
                <motion.div
                  key={job.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-4 hover:border-neutral-600/50 transition-colors cursor-pointer"
                  onClick={() => router.push(`/employer/jobs/${job.id}`)}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium text-neutral-200">{job.title}</p>
                      <p className="page-subtitle">
                        {job.location} | {job.applications_count} apps
                      </p>
                    </div>
                    <span className={`text-xs px-2.5 py-1 rounded-lg border ${getStatusTag(job.status)}`}>
                      {job.status}
                    </span>
                  </div>
                </motion.div>
              ))}
            </div>
          ) : (
            <div className="rounded-lg border-2 border-dashed border-neutral-700/50 p-8 text-center">
              <p className="text-neutral-400 mb-3">No jobs posted yet</p>
              <motion.button
                onClick={() => router.push("/employer/jobs/new")}
                className="btn-primary"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                Post Your First Job
              </motion.button>
            </div>
          )}
        </motion.div>

        {applications.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <div className="flex justify-between items-center mb-4">
              <h2 className="section-title">Recent Applications</h2>
              <button
                onClick={() => router.push("/employer/jobs")}
                className="text-sm text-blue-400 hover:text-blue-300 flex items-center gap-1"
              >
                View all <FaArrowRight className="w-3 h-3" />
              </button>
            </div>

            <div className="space-y-3">
              {applications.map((app, index) => (
                <motion.div
                  key={app.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-4 hover:border-neutral-600/50 transition-colors cursor-pointer"
                  onClick={() => router.push(`/employer/candidates/${app.id}`)}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium text-neutral-200">
                        {app.candidate_name || "Anonymous"}
                      </p>
                      <p className="page-subtitle">
                        {app.job_title} | {Math.round(app.match_score)}% match
                      </p>
                    </div>
                    <span
                      className={`text-xs px-2.5 py-1 rounded-lg border ${getAppStatusTag(app.status)}`}
                    >
                      {app.status}
                    </span>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
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

function StatCard({ label, value, icon: Icon, color }: { label: string; value: number; icon: IconType; color: string }) {
  const colorClasses: Record<string, string> = {
    blue: "from-blue-500/20 to-blue-500/5 border-blue-500/20 text-blue-400",
    emerald: "from-emerald-500/20 to-emerald-500/5 border-emerald-500/20 text-emerald-400",
    amber: "from-amber-500/20 to-amber-500/5 border-amber-500/20 text-amber-400",
  };

  return (
    <div className={`rounded-lg bg-gradient-to-br ${colorClasses[color]} border p-4 text-center`}>
      <Icon className="w-5 h-5 mx-auto mb-2 opacity-80" />
      <p className="text-sm text-neutral-400">{label}</p>
      <p className="text-2xl font-bold text-neutral-200 mt-1">{value}</p>
    </div>
  );
}

function QuickAction({ icon: Icon, label, onClick, color }: { icon: IconType; label: string; onClick: () => void; color: string }) {
  const colorClasses: Record<string, string> = {
    blue: "text-blue-400 bg-blue-500/10 border-blue-500/20 hover:bg-blue-500/20",
    emerald: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20 hover:bg-emerald-500/20",
    amber: "text-amber-400 bg-amber-500/10 border-amber-500/20 hover:bg-amber-500/20",
  };

  return (
    <motion.button
      onClick={onClick}
      className={`flex flex-col items-center gap-2 p-4 rounded-lg border ${colorClasses[color]} transition-colors`}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
    >
      <Icon className="w-5 h-5" />
      <span className="text-sm font-medium">{label}</span>
    </motion.button>
  );
}

function getStatusTag(status: string) {
  switch (status) {
    case "open":
      return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
    case "closed":
      return "bg-rose-500/10 text-rose-400 border-rose-500/20";
    case "draft":
      return "bg-amber-500/10 text-amber-400 border-amber-500/20";
    default:
      return "bg-neutral-500/10 text-neutral-400 border-neutral-500/20";
  }
}

function getAppStatusTag(status: string) {
  switch (status) {
    case "shortlisted":
      return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
    case "accepted":
      return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
    case "rejected":
      return "bg-rose-500/10 text-rose-400 border-rose-500/20";
    case "reviewing":
      return "bg-amber-500/10 text-amber-400 border-amber-500/20";
    default:
      return "bg-blue-500/10 text-blue-400 border-blue-500/20";
  }
}
