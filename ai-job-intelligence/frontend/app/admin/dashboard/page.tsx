"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiCall } from "@/components/api";
import { motion } from "framer-motion";
import { FaUsers, FaBriefcase, FaFileAlt, FaChartLine, FaUpload, FaArrowRight } from "react-icons/fa";
import MessageDialog from "@/components/MessageDialog";

interface AdminStats {
  total_users: number;
  total_jobs: number;
  total_applications: number;
  total_cvs: number;
  total_analyses: number;
  employers: number;
  job_seekers: number;
}

interface User {
  id: number;
  email: string;
  role: string;
  cv_count: number;
  jobs_posted: number;
  applications: number;
  created_at: string;
}

export default function AdminDashboard() {
  const router = useRouter();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [recentUsers, setRecentUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialog, setDialog] = useState({ open: false, title: '', message: '', type: 'info' as 'info' | 'success' | 'error' | 'warning' });

  useEffect(() => {
    fetchStats();
    fetchUsers();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await apiCall("/api/admin/stats");
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (err) {
      setDialog({ open: true, title: 'Error', message: "Error loading stats", type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const fetchUsers = async () => {
    try {
      const response = await apiCall("/api/admin/users");
      if (response.ok) {
        const data = await response.json();
        setRecentUsers(data.slice(0, 8));
      }
    } catch (err) {
      setDialog({ open: true, title: 'Error', message: "Error loading users", type: 'error' });
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-900 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-rose-500/30 border-t-rose-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neutral-900">
      <div className="max-w-5xl mx-auto px-4 py-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6"
        >
          <h1 className="page-title">System Dashboard</h1>
          <p className="page-subtitle">
            Monitor the entire CareerLens platform
          </p>
        </motion.div>

        {stats && (
          <>
            <motion.div
              className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <StatCard label="Total Users" value={stats.total_users} icon={FaUsers} color="rose" />
              <StatCard label="Total Jobs" value={stats.total_jobs} icon={FaBriefcase} color="blue" />
              <StatCard label="Applications" value={stats.total_applications} icon={FaFileAlt} color="emerald" />
              <StatCard label="CVs Uploaded" value={stats.total_cvs} icon={FaUpload} color="emerald" />
            </motion.div>

            <motion.div
              className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <StatCard label="Employers" value={stats.employers} icon={FaBriefcase} color="amber" />
              <StatCard label="Job Seekers" value={stats.job_seekers} icon={FaUsers} color="blue" />
              <StatCard label="Analyses" value={stats.total_analyses} icon={FaChartLine} color="emerald" />
              <StatCard label="CVs" value={stats.total_cvs} icon={FaUpload} color="emerald" />
            </motion.div>
          </>
        )}

        <motion.div
          className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-5 mb-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <h2 className="section-title mb-4">System Actions</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <QuickAction
              icon={FaUsers}
              label="Manage Users"
              onClick={() => router.push("/admin/users")}
              color="rose"
            />
            <QuickAction
              icon={FaChartLine}
              label="System Stats"
              onClick={() => router.push("/admin/dashboard")}
              color="blue"
            />
            <QuickAction
              icon={FaUsers}
              label="Manage Users"
              onClick={() => router.push("/admin/users")}
              color="rose"
            />
            <QuickAction
              icon={FaBriefcase}
              label="View Jobs"
              onClick={() => router.push("/jobs")}
              color="blue"
            />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <div className="flex justify-between items-center mb-4">
            <h2 className="section-title">Recent Users</h2>
            <button
              onClick={() => router.push("/admin/users")}
              className="text-sm text-rose-400 hover:text-rose-300 flex items-center gap-1"
            >
              View all <FaArrowRight className="w-3 h-3" />
            </button>
          </div>

          {recentUsers.length > 0 ? (
            <div className="space-y-2">
              {recentUsers.map((user, index) => (
                <motion.div
                  key={user.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-4 flex justify-between items-center hover:border-neutral-600/50 transition-colors"
                >
                  <div>
                    <p className="font-medium text-neutral-200">{user.email}</p>
                    <p className="page-subtitle">
                      Role: {user.role} | CVs: {user.cv_count} | Jobs: {user.jobs_posted}
                    </p>
                  </div>
                  <span className={`text-xs px-2.5 py-1 rounded-lg border ${getRoleTag(user.role)}`}>
                    {user.role}
                  </span>
                </motion.div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-neutral-500">No users found</p>
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

function StatCard({ label, value, icon: Icon, color }: { label: string; value: number; icon: any; color: string }) {
  const colorClasses: Record<string, string> = {
    rose: "from-rose-500/20 to-rose-500/5 border-rose-500/20 text-rose-400",
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

function QuickAction({ icon: Icon, label, onClick, color }: { icon: any; label: string; onClick: () => void; color: string }) {
  const colorClasses: Record<string, string> = {
    rose: "text-rose-400 bg-rose-500/10 border-rose-500/20 hover:bg-rose-500/20",
    blue: "text-blue-400 bg-blue-500/10 border-blue-500/20 hover:bg-blue-500/20",
    emerald: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20 hover:bg-emerald-500/20",
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

function getRoleTag(role: string) {
  switch (role) {
    case "admin":
      return "bg-rose-500/10 text-rose-400 border-rose-500/20";
    case "employer":
      return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
    default:
      return "bg-blue-500/10 text-blue-400 border-blue-500/20";
  }
}
