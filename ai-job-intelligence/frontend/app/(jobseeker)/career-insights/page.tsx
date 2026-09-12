"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiCall } from "@/components/api";
import { motion } from "framer-motion";
import {
  FaArrowRight,
  FaTrash,
  FaChartLine,
  FaBrain,
  FaRocket,
  FaShieldAlt,
} from "react-icons/fa";
import MessageDialog from "@/components/MessageDialog";

interface CareerInsight {
  profile_strength: number;
  skill_gaps: string[];
  market_value: string;
  recommended_roles: string[];
  in_demand_skills: Array<{ skill: string; demand: number }>;
  salary_trends?: {
    min: number;
    max: number;
    average: number;
  };
  action_items: string[];
  sources?: string[];
}

export default function CareerInsightsPage() {
  const router = useRouter();
  const [insights, setInsights] = useState<CareerInsight | null>(null);
  const [loading, setLoading] = useState(true);
  const [resetting, setResetting] = useState(false);
  const [dialog, setDialog] = useState({ open: false, title: '', message: '', type: 'info' as 'info' | 'success' | 'error' | 'warning' });

  // Fetches and returns the insights; callers decide what to do with them.
  const loadInsights = useCallback(async (): Promise<CareerInsight> => {
    const response = await apiCall("/api/career-insights");
    if (!response.ok) throw new Error("Failed to load insights");
    return response.json();
  }, []);

  // State is set only in the promise callbacks, and never after the page
  // has moved on (`active`), so a slow response can't overwrite newer data.
  useEffect(() => {
    let active = true;
    loadInsights()
      .then((data) => {
        if (active) setInsights(data);
      })
      .catch((err) => {
        if (active) setDialog({ open: true, title: 'Error', message: err instanceof Error ? err.message : "Error loading insights", type: 'error' });
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [loadInsights]);

  const handleReset = async () => {
    setResetting(true);
    try {
      const response = await apiCall("/api/reset-data", { method: "POST" });
      if (response.ok) {
        setDialog({ open: true, title: 'Success', message: "All data has been reset", type: 'success' });
        setInsights(await loadInsights());
      } else {
        setDialog({ open: true, title: 'Error', message: "Failed to reset data", type: 'error' });
      }
    } catch (err) {
      setDialog({ open: true, title: 'Error', message: err instanceof Error ? err.message : "Error resetting data", type: 'error' });
    } finally {
      setResetting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-900 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-neutral-400">Loading career insights...</p>
        </div>
      </div>
    );
  }

  if (!insights) {
    return (
      <div className="min-h-screen bg-neutral-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-neutral-400 mb-4">Failed to load insights</p>
          <button
            onClick={() => router.push("/dashboard")}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neutral-900 text-neutral-50">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8"
        >
          <div>
            <h1 className="text-3xl font-bold text-neutral-50">Career Insights</h1>
            <p className="text-neutral-400 mt-1">
              AI-powered insights to advance your career
            </p>
          </div>
          <motion.button
            onClick={handleReset}
            disabled={resetting}
            className="btn-secondary flex items-center gap-2 text-rose-400 border-rose-500/30 hover:bg-rose-500/10 disabled:opacity-50"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <FaTrash className="w-4 h-4" />
            {resetting ? "Resetting..." : "Reset All Data"}
          </motion.button>
        </motion.div>

        {/* Overview Stats */}
        <motion.div
          className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
        >
          <div className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-5 text-center">
            <FaChartLine className="w-6 h-6 text-blue-400 mx-auto mb-2" />
            <p className="text-sm text-neutral-400">Profile Strength</p>
            <p className="text-3xl font-bold text-neutral-200 mt-1">{insights.profile_strength}%</p>
          </div>
          <div className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-5 text-center">
            <FaBrain className="w-6 h-6 text-amber-400 mx-auto mb-2" />
            <p className="text-sm text-neutral-400">Skill Gaps</p>
            <p className="text-3xl font-bold text-neutral-200 mt-1">{insights.skill_gaps.length}</p>
          </div>
          <div className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-5 text-center">
            <FaRocket className="w-6 h-6 text-emerald-400 mx-auto mb-2" />
            <p className="text-sm text-neutral-400">Market Value</p>
            <p className="text-2xl font-bold text-neutral-200 mt-1">{insights.market_value}</p>
          </div>
          <div className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-5 text-center">
            <FaShieldAlt className="w-6 h-6 text-emerald-400 mx-auto mb-2" />
            <p className="text-sm text-neutral-400">Recommended Roles</p>
            <p className="text-3xl font-bold text-neutral-200 mt-1">{insights.recommended_roles.length}</p>
          </div>
        </motion.div>

        {/* Skill Gaps & Recommended Roles */}
        <div className="grid md:grid-cols-2 gap-4 mb-6">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-5"
          >
            <h3 className="text-lg font-semibold text-amber-400 mb-3 flex items-center gap-2">
              <FaBrain className="w-5 h-5" />
              Skill Gap Analysis
            </h3>
            {insights.skill_gaps.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {insights.skill_gaps.map((s) => (
                  <span
                    key={s}
                    className="text-sm px-3 py-1.5 rounded-lg bg-amber-500/10 text-amber-300 border border-amber-500/20"
                  >
                    {s}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-neutral-500">
                {insights.recommended_roles.length > 0
                  ? "You already cover the skills these roles ask for."
                  : "No open role currently matches your field, so there is nothing to compare against yet."}
              </p>
            )}
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-5"
          >
            <h3 className="text-lg font-semibold text-emerald-400 mb-3 flex items-center gap-2">
              <FaRocket className="w-5 h-5" />
              Recommended Career Paths
            </h3>
            {insights.recommended_roles.length > 0 ? (
              <div className="space-y-2">
                {insights.recommended_roles.map((role, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.1 * i }}
                    className="flex items-center gap-2 text-sm text-neutral-300"
                  >
                    <FaArrowRight className="w-3 h-3 text-emerald-500 flex-shrink-0" />
                    {role}
                  </motion.div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-neutral-500">
                No open posting is close enough to your profile to recommend.
                Check back as new roles are added.
              </p>
            )}
          </motion.div>
        </div>

        {/* In-Demand Skills */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-5 mb-6"
        >
          <div className="flex items-baseline justify-between mb-4">
            <h3 className="text-lg font-semibold text-neutral-200">Skills In Demand</h3>
            <span className="text-xs text-neutral-500">
              share of roles matching your profile
            </span>
          </div>
          {insights.in_demand_skills.length === 0 && (
            <p className="text-sm text-neutral-500">
              {insights.recommended_roles.length > 0
                ? "The roles matching your profile ask for nothing you are missing."
                : "No matching roles yet, so there is no demand data to show."}
            </p>
          )}
          <div className="space-y-3">
            {insights.in_demand_skills.map((item) => (
              <div key={item.skill}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-neutral-300">{item.skill}</span>
                  <span className="text-neutral-400">{item.demand}% demand</span>
                </div>
                <div className="w-full bg-neutral-800 rounded-full h-1.5">
                  <div
                    className="h-1.5 rounded-full bg-neutral-100"
                    style={{ width: `${item.demand}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Salary Trends */}
        {insights.salary_trends && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.5 }}
            className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-5 mb-6"
          >
            <h3 className="text-lg font-semibold text-neutral-200 mb-4">Salary Insights</h3>
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center">
                <p className="text-sm text-neutral-400">Min</p>
                <p className="text-xl font-bold text-neutral-200">${insights.salary_trends.min.toLocaleString()}</p>
              </div>
              <div className="text-center">
                <p className="text-sm text-neutral-400">Average</p>
                <p className="text-xl font-bold text-blue-400">${insights.salary_trends.average.toLocaleString()}</p>
              </div>
              <div className="text-center">
                <p className="text-sm text-neutral-400">Max</p>
                <p className="text-xl font-bold text-neutral-200">${insights.salary_trends.max.toLocaleString()}</p>
              </div>
            </div>
          </motion.div>
        )}

        {!insights.salary_trends && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.5 }}
            className="rounded-lg bg-neutral-900 border border-neutral-800 p-5 mb-6"
          >
            <h3 className="text-lg font-semibold text-neutral-200 mb-2">
              Salary Insights
            </h3>
            <p className="text-sm text-neutral-400">
              {insights.market_value}. Salary figures are only shown when open
              roles matching your profile publish pay ranges — we do not
              estimate them.
            </p>
          </motion.div>
        )}

        {/* Action Items */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.6 }}
          className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-5 mb-6"
        >
          <h3 className="text-lg font-semibold text-neutral-200 mb-4 flex items-center gap-2">
            <FaRocket className="w-5 h-5 text-emerald-400" />
            Action Items
          </h3>
          <div className="space-y-3">
            {insights.action_items.map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.05 * i }}
                className="flex items-start gap-3 p-3 rounded-lg bg-neutral-700/30 border border-neutral-600/30"
              >
                <div className="w-6 h-6 rounded-full bg-blue-600/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <FaArrowRight className="w-3 h-3 text-blue-400" />
                </div>
                <span className="text-sm text-neutral-300">{item}</span>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Where these numbers come from */}
        {insights.sources && insights.sources.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.7 }}
            className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-5 mb-6"
          >
            <h3 className="eyebrow mb-3">How these figures were calculated</h3>
            <ul className="space-y-2">
              {insights.sources.map((src, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 text-sm text-neutral-400"
                >
                  <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-neutral-600" />
                  {src}
                </li>
              ))}
            </ul>
          </motion.div>
        )}

        {/* Next steps */}
        <div className="flex flex-wrap gap-3 mb-6">
          <button onClick={() => router.push("/jobs")} className="btn-primary">
            Browse matching jobs
            <FaArrowRight className="w-3.5 h-3.5" />
          </button>
          <button onClick={() => router.push("/cv")} className="btn-secondary">
            Update my CV
          </button>
          <button
            onClick={() => router.push("/career-lens")}
            className="btn-secondary"
          >
            Ask the assistant
          </button>
        </div>

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
