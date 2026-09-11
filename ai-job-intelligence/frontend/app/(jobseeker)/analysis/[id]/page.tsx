"use client";

import { describeApiError } from "@/components/format";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { apiCall, viewFile } from "@/components/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import { motion, AnimatePresence } from "framer-motion";
import {
  FaCheck,
  FaChevronDown,
  FaChevronRight,
  FaArrowRight,
  FaEye,
  FaDownload,
  FaLightbulb,
  FaRobot,
  FaFileAlt,
  FaRocket,
} from "react-icons/fa";
import MessageDialog from "@/components/MessageDialog";
import LearningResources from "@/components/LearningResources";

interface Skill {
  name: string;
  proficiency: "beginner" | "intermediate" | "advanced" | "expert";
}

interface SkillEvidenceItem {
  skill: string;
  source: string;
  context: string;
}

interface CVAnalysis {
  id: number;
  cv_name: string;
  overall_score: number;
  summary: string;
  strengths: string[];
  weaknesses: string[];
  recommendations: string[];
  skills: Skill[];
  experience_assessment: string;
  education_assessment: string;
  formatting_tips?: string[];
  ats_tips?: string[];
  action_verbs?: string[];
  analyzed_at: string;
  skill_evidence?: SkillEvidenceItem[];
  learn_next?: string[];
}

export default function CVAnalysisDetailPage() {
  const router = useRouter();
  const params = useParams();
  const cvId = params.id as string;
  const [analysis, setAnalysis] = useState<CVAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [showAiPipeline, setShowAiPipeline] = useState(false);
  const [openSection, setOpenSection] = useState<string | null>(null);
  const [dialog, setDialog] = useState({ open: false, title: '', message: '', type: 'info' as 'info' | 'success' | 'error' | 'warning' });

  useEffect(() => {
    fetchAnalysis();
  }, [cvId]);

  const handleViewCV = async () => {
    try {
      await viewFile(`/api/cvs/${cvId}/download`);
    } catch {
      setDialog({ open: true, title: 'Error', message: "Failed to open CV", type: 'error' });
    }
  };

  useEffect(() => {
    fetchAnalysis();
  }, [cvId]);

  const fetchAnalysis = async () => {
    setLoading(true);
    try {
      const response = await apiCall(`/api/cvs/${cvId}/analysis`);
      if (response.ok) {
        setAnalysis(await response.json());
      } else {
        const data = await response.json();
        setDialog({ open: true, title: 'Error', message: describeApiError(data, "Analysis not found"), type: 'error' });
      }
    } catch (err) {
      setDialog({ open: true, title: 'Error', message: err instanceof Error ? err.message : "Error loading analysis", type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 75) return "text-emerald-600";
    if (score >= 50) return "text-yellow-600";
    if (score >= 30) return "text-orange-600";
    return "text-red-600";
  };

  const getProficiencyColor = (level: string) => {
    switch (level) {
      case "expert":
        return "bg-emerald-500";
      case "advanced":
        return "bg-blue-500";
      case "intermediate":
        return "bg-amber-500";
      default:
        return "bg-rose-500";
    }
  };

  const getProficiencyWidth = (level: string) => {
    switch (level) {
      case "expert":
        return "100%";
      case "advanced":
        return "75%";
      case "intermediate":
        return "50%";
      default:
        return "25%";
    }
  };

  const toggleSection = (section: string) => {
    setOpenSection(openSection === section ? null : section);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-900 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-neutral-400">Analyzing your CV with AI...</p>
        </div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="min-h-screen bg-neutral-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-neutral-400 mb-4">Analysis not found</p>
          <button
            onClick={() => router.push("/cv")}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Back to CV
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neutral-900 text-neutral-50">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-6 mb-6"
        >
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h1 className="page-title">{analysis.cv_name}</h1>
              <p className="page-subtitle">
                General CV profile analysis — not tied to any specific job
              </p>
              <p className="text-xs text-neutral-500 mt-1">
                Analyzed: {new Date(analysis.analyzed_at).toLocaleDateString()}
              </p>
            </div>
            <div className="text-center md:text-right">
              <span className={`text-4xl font-bold ${getScoreColor(analysis.overall_score)}`}>
                {analysis.overall_score}%
              </span>
              <p className="text-sm text-neutral-400">Profile Strength</p>
            </div>
          </div>

          {/* AI Pipeline Toggle */}
          <div className="mt-4 pt-4 border-t border-neutral-700/50">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <button
                onClick={() => setShowAiPipeline(!showAiPipeline)}
                className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300 font-medium"
              >
                {showAiPipeline ? (
                  <FaChevronDown className="w-4 h-4" />
                ) : (
                  <FaChevronRight className="w-4 h-4" />
                )}
                {showAiPipeline ? "Hide AI Process" : "Show AI Analysis Process"}
              </button>
              <div className="flex gap-2">
                <button
                  onClick={handleViewCV}
                  className="flex items-center gap-2 text-sm px-4 py-2 border border-neutral-600/50 rounded-lg hover:bg-neutral-700/50 text-neutral-300"
                >
                  <FaEye className="w-4 h-4" />
                  View CV
                </button>
              </div>
            </div>

            {showAiPipeline && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                className="mt-3 space-y-2 text-sm text-neutral-400"
              >
                <div className="flex items-center gap-2">
                  <FaCheck className="w-4 h-4 text-emerald-500" />
                  <span>PDF text extraction (PyMuPDF)</span>
                </div>
                <div className="flex items-center gap-2">
                  <FaCheck className="w-4 h-4 text-emerald-500" />
                  <span>Skill & experience extraction (AI / local NLP fallback)</span>
                </div>
                <div className="flex items-center gap-2">
                  <FaCheck className="w-4 h-4 text-emerald-500" />
                  <span>Profile scoring & gap analysis</span>
                </div>
              </motion.div>
            )}

            <p className="mt-3 text-sm text-neutral-400 leading-relaxed">
              {analysis.summary}
            </p>
          </div>
        </motion.div>

        {/* Strengths & Weaknesses */}
        <div className="grid md:grid-cols-2 gap-4 mb-6">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-5"
          >
            <h3 className="text-lg font-semibold text-emerald-400 mb-3 flex items-center gap-2">
              <FaCheck className="w-5 h-5" />
              Strengths
            </h3>
            <ul className="space-y-2">
              {analysis.strengths.map((strength, i) => (
                <motion.li
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 * i }}
                  className="flex items-start gap-2 text-sm text-neutral-300"
                >
                  <FaCheck className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                  {strength}
                </motion.li>
              ))}
            </ul>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-5"
          >
            <h3 className="text-lg font-semibold text-amber-400 mb-3 flex items-center gap-2">
              <FaLightbulb className="w-5 h-5" />
              Areas for Improvement
            </h3>
            <ul className="space-y-2">
              {analysis.weaknesses.map((weakness, i) => (
                <motion.li
                  key={i}
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 * i }}
                  className="flex items-start gap-2 text-sm text-neutral-300"
                >
                  <span className="text-amber-500 mt-0.5 font-bold">!</span>
                  {weakness}
                </motion.li>
              ))}
            </ul>
          </motion.div>
        </div>

        {/* Skills */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-5 mb-6"
        >
          <h3 className="text-lg font-semibold text-neutral-200 mb-4 flex items-center gap-2">
            <FaRobot className="w-5 h-5 text-blue-400" />
            AI-Extracted Skills
          </h3>
          <div className="space-y-3">
            {analysis.skills.map((skill, i) => (
              <motion.div
                key={skill.name}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.05 * i }}
              >
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-neutral-300">{skill.name}</span>
                  <span className="text-neutral-400 capitalize">{skill.proficiency}</span>
                </div>
                <div className="w-full bg-neutral-700/50 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${getProficiencyColor(skill.proficiency)} transition-all duration-500`}
                    style={{ width: getProficiencyWidth(skill.proficiency) }}
                  />
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Experience & Education */}
        <div className="grid md:grid-cols-2 gap-4 mb-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-5"
          >
            <h3 className="text-lg font-semibold text-neutral-200 mb-2">Experience</h3>
            <p className="text-sm text-neutral-400 leading-relaxed">
              {analysis.experience_assessment}
            </p>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.5 }}
            className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-5"
          >
            <h3 className="text-lg font-semibold text-neutral-200 mb-2">Education</h3>
            <p className="text-sm text-neutral-400 leading-relaxed">
              {analysis.education_assessment}
            </p>
          </motion.div>
        </div>

        {/* Recommendations */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.6 }}
          className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-5 mb-6"
        >
          <h3 className="text-lg font-semibold text-neutral-200 mb-4 flex items-center gap-2">
            <FaRocket className="w-5 h-5 text-emerald-400" />
            AI Recommendations
          </h3>
          <div className="space-y-3">
            {analysis.recommendations.map((rec, i) => (
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
                <span className="text-sm text-neutral-300">{rec}</span>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Where each skill was found.

            This is the answer to "that skill IS in my CV, why was it not
            picked up?": a skill evidenced by a described project shows the
            sentence that earned it, and one merely listed says so plainly. */}
        {analysis.skill_evidence && analysis.skill_evidence.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.65 }}
            className="card mb-6"
          >
            <h2 className="section-title">Where we found your skills</h2>
            <p className="meta mt-1">
              A skill you described doing is stronger evidence than one in a
              list. Anything missing here was not visible to the parser.
            </p>
            <div className="mt-5 space-y-2">
              {analysis.skill_evidence.map((e) => {
                const shown =
                  e.source === "experience" || e.source === "projects" ||
                  e.source === "certifications";
                return (
                  <div
                    key={`${e.skill}-${e.source}`}
                    className="rounded-md border border-neutral-800 p-3.5"
                  >
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="item-title">{e.skill}</span>
                      <span className={shown ? "chip-positive" : "chip"}>
                        {shown ? `shown in your ${e.source}` : "listed only"}
                      </span>
                    </div>
                    {e.context && (
                      <p className="text-[0.8125rem] text-neutral-400 mt-2 border-l border-neutral-800 pl-3">
                        {e.context}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}

        {/* Real places to close the gaps that current postings ask for. */}
        {analysis.learn_next && analysis.learn_next.length > 0 && (
          <div className="mb-6">
            <LearningResources skills={analysis.learn_next} />
          </div>
        )}

        {/* Formatting Tips */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.7 }}
          className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-5 mb-6"
        >
          <button
            onClick={() => toggleSection("formatting")}
            className="w-full flex items-center justify-between text-left"
          >
            <h3 className="text-lg font-semibold text-neutral-200 flex items-center gap-2">
              <FaFileAlt className="w-5 h-5 text-blue-400" />
              CV Formatting Tips
            </h3>
            {openSection === "formatting" ? (
              <FaChevronDown className="w-4 h-4 text-neutral-400" />
            ) : (
              <FaChevronRight className="w-4 h-4 text-neutral-400" />
            )}
          </button>
          <AnimatePresence>
            {openSection === "formatting" && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
                className="overflow-hidden"
              >
                <ul className="mt-4 space-y-2">
                  {(analysis.formatting_tips || []).map((tip, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-neutral-300">
                      <FaCheck className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
                      {tip}
                    </li>
                  ))}
                </ul>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* ATS Tips */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.8 }}
          className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-5 mb-6"
        >
          <button
            onClick={() => toggleSection("ats")}
            className="w-full flex items-center justify-between text-left"
          >
            <h3 className="text-lg font-semibold text-neutral-200 flex items-center gap-2">
              <FaRobot className="w-5 h-5 text-emerald-400" />
              ATS Optimization Guide
            </h3>
            {openSection === "ats" ? (
              <FaChevronDown className="w-4 h-4 text-neutral-400" />
            ) : (
              <FaChevronRight className="w-4 h-4 text-neutral-400" />
            )}
          </button>
          <AnimatePresence>
            {openSection === "ats" && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
                className="overflow-hidden"
              >
                <ul className="mt-4 space-y-2">
                  {(analysis.ats_tips || []).map((tip, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-neutral-300">
                      <FaCheck className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                      {tip}
                    </li>
                  ))}
                </ul>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Action Verbs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.9 }}
          className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-5 mb-8"
        >
          <button
            onClick={() => toggleSection("verbs")}
            className="w-full flex items-center justify-between text-left"
          >
            <h3 className="text-lg font-semibold text-neutral-200 flex items-center gap-2">
              <FaRocket className="w-5 h-5 text-amber-400" />
              Writing Better Bullet Points
            </h3>
            {openSection === "verbs" ? (
              <FaChevronDown className="w-4 h-4 text-neutral-400" />
            ) : (
              <FaChevronRight className="w-4 h-4 text-neutral-400" />
            )}
          </button>
          <AnimatePresence>
            {openSection === "verbs" && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
                className="overflow-hidden"
              >
                <ul className="mt-4 space-y-2">
                  {(analysis.action_verbs || []).map((tip, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-neutral-300">
                      <FaArrowRight className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
                      {tip}
                    </li>
                  ))}
                </ul>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 1.0 }}
          className="text-center"
        >
          <div className="rounded-lg bg-gradient-to-r from-blue-500/10 to-emerald-500/10 border border-blue-500/20 p-8">
            <h3 className="text-2xl font-bold text-neutral-50 mb-2">
              Ready to Find Matching Jobs?
            </h3>
            <p className="text-neutral-400 mb-6 max-w-xl mx-auto">
              Use your analysis to discover roles that match your skills and get
              personalized recommendations.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <button
                onClick={() => router.push("/jobs")}
                className="px-6 py-3 bg-gradient-to-r from-blue-600 to-emerald-500 text-white font-medium rounded-lg hover:shadow-lg hover:shadow-blue-500/25 transition-all duration-300"
              >
                Find Matching Jobs
              </button>
              <button
                onClick={() => router.push("/career-insights")}
                className="px-6 py-3 border border-neutral-600/50 text-neutral-200 font-medium rounded-lg hover:bg-neutral-700/50 transition-all duration-300"
              >
                Career Insights
              </button>
            </div>
          </div>
        </motion.div>
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
