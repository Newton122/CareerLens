"use client";
import LoadingSpinner from "@/components/LoadingSpinner";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiCall } from "@/components/api";
import { motion } from "framer-motion";
import { FaUpload, FaSearch, FaChartLine, FaBookmark, FaUser, FaArrowRight } from "react-icons/fa";
import type { IconType } from "react-icons";
import MessageDialog from "@/components/MessageDialog";

interface UserStats {
  cvs_uploaded: number;
  analyses_completed: number;
  applications: number;
  saved_jobs: number;
}

interface Job {
  id: number;
  title: string;
  company: string;
  match_score?: number;
}

export default function JobSeekerDashboard() {
  const router = useRouter();
  const [stats, setStats] = useState<UserStats>({
    cvs_uploaded: 0,
    analyses_completed: 0,
    applications: 0,
    saved_jobs: 0,
  });
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialog, setDialog] = useState({ open: false, title: '', message: '', type: 'info' as 'info' | 'success' | 'error' | 'warning' });

  // State is set only in the promise callbacks, and never after the page
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
          if (active) setJobs(jobsData.slice(0, 4));
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
          className="flex justify-between items-center mb-6"
        >
          <div>
            <h1 className="page-title">Your Dashboard</h1>
            <p className="page-subtitle">
              Your career intelligence overview
            </p>
          </div>
          <motion.button
            onClick={() => router.push("/profile")}
            className="btn-secondary flex items-center gap-2"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <FaUser className="w-4 h-4" />
            Profile
          </motion.button>
        </motion.div>

        <motion.div
          className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <StatCard label="CVs" value={stats.cvs_uploaded} icon={FaUpload} color="blue" />
          <StatCard label="Analyses" value={stats.analyses_completed} icon={FaChartLine} color="emerald" />
          <StatCard label="Applications" value={stats.applications} icon={FaSearch} color="emerald" />
          <StatCard label="Saved" value={stats.saved_jobs} icon={FaBookmark} color="amber" />
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
              icon={FaUpload}
              label="Upload CV"
              onClick={() => router.push("/cv")}
              color="blue"
            />
            <QuickAction
              icon={FaSearch}
              label="Find Jobs"
              onClick={() => router.push("/jobs")}
              color="emerald"
            />
            <QuickAction
              icon={FaBookmark}
              label="Saved Jobs"
              onClick={() => router.push("/saved-jobs")}
              color="amber"
            />
            <QuickAction
              icon={FaChartLine}
              label="Insights"
              onClick={() => router.push("/career-insights")}
              color="emerald"
            />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <div className="flex justify-between items-center mb-4">
            <h2 className="section-title">Recommended Jobs for You</h2>
            <button
              onClick={() => router.push("/jobs")}
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
                  className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-4 hover:border-blue-500/30 transition-colors cursor-pointer"
                  onClick={() => router.push(`/jobs/${job.id}`)}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium text-neutral-200">{job.title}</p>
                      <p className="page-subtitle">
                        {job.company || "Confidential"}
                      </p>
                    </div>
                    {job.match_score !== undefined && (
                      <span className="px-3 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-sm font-medium">
                        {Math.round(job.match_score)}%
                      </span>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          ) : (
            <div className="rounded-lg border-2 border-dashed border-neutral-700/50 p-8 text-center">
              <p className="text-neutral-400">Upload your CV to get matched with jobs</p>
            </div>
          )}
        </motion.div>
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
    blue: "text-blue-400 bg-blue-600/10 border-blue-500/20 hover:bg-blue-600/20",
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
