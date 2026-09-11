"use client";

import { formatScore } from "@/components/format";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { apiCall } from "@/components/api";
import { describeApiError } from "@/components/format";
import { motion, AnimatePresence } from "framer-motion";
import {
  FaBriefcase,
  FaChartLine,
  FaGraduationCap,
  FaProjectDiagram,
  FaCertificate,
  FaSearch,
  FaRobot,
  FaArrowRight,
  FaBolt,
} from "react-icons/fa";
import MessageDialog from "@/components/MessageDialog";

interface AnalysisData {
  id: number;
  cv_name: string;
  overall_score: number;
  summary: string;
  strengths: string[];
  weaknesses: string[];
  recommendations: string[];
  skills: Array<{ name: string; proficiency: string }>;
  experience: string[];
  education: string[];
  projects: string[];
  certifications: string[];
  experience_assessment: string;
  education_assessment: string;
  formatting_tips: string[];
  ats_tips: string[];
  action_verbs: string[];
  analyzed_at: string;
}

interface JobRecommendation {
  job_id: number;
  job_title: string;
  company: string;
  match_score: number;
  matched_skills: string[];
  missing_skills: string[];
  location: string;
  salary_min?: number;
  salary_max?: number;
  employment_type: string;
  required_skills: string[];
  experience_required?: string;
  education_required?: string;
  match_breakdown: {
    skills_match: number;
    experience_match: number | null;
    education_match: number | null;
  };
}

export default function AnalyzePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [jobs, setJobs] = useState<JobRecommendation[]>([]);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [showJobs, setShowJobs] = useState(false);
  const [dialog, setDialog] = useState({ open: false, title: '', message: '', type: 'info' as 'info' | 'success' | 'error' | 'warning' });

  useEffect(() => {
    const cvId = searchParams.get("cv_id");
    if (cvId) {
      fetchAnalysis(cvId);
    } else {
      setLoading(false);
    }
  }, [searchParams]);

  const fetchAnalysis = async (cvId: string) => {
    setLoading(true);
    try {
      const response = await apiCall(`/api/cvs/${cvId}/analysis`);
      if (response.ok) {
        const data = await response.json();
        setAnalysis({
          ...data,
          skills: data.skills || [],
          experience: data.experience || [],
          education: data.education || [],
          projects: data.projects || [],
          certifications: data.certifications || [],
          strengths: data.strengths || [],
          weaknesses: data.weaknesses || [],
          recommendations: data.recommendations || [],
        } as AnalysisData);
      } else {
        setDialog({ open: true, title: 'Error', message: "Failed to load profile", type: 'error' });
      }
    } catch (err) {
      setDialog({ open: true, title: 'Error', message: err instanceof Error ? err.message : "Error loading profile", type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleFindJobs = async () => {
    const cvId = searchParams.get("cv_id");
    if (!cvId) {
      setDialog({ open: true, title: 'Error', message: "No CV selected", type: 'error' });
      return;
    }

    setJobsLoading(true);
    setShowJobs(true);
    try {
      const response = await apiCall(`/api/job-recommendations?cv_id=${cvId}`);
      if (response.ok) {
        const data = await response.json();
        setJobs(data.jobs || []);
      } else {
        setDialog({ open: true, title: 'Error', message: "Failed to load job recommendations", type: 'error' });
      }
    } catch (err) {
      setDialog({ open: true, title: 'Error', message: err instanceof Error ? err.message : "Error loading recommendations", type: 'error' });
    } finally {
      setJobsLoading(false);
    }
  };

  const handleAnalyzeJob = async (jobId: number) => {
    const cvId = searchParams.get("cv_id");
    if (!cvId) return;

    setAnalyzing(true);
    try {
      const jobResponse = await apiCall(`/api/jobs/${jobId}`);
      if (!jobResponse.ok) {
        setDialog({ open: true, title: 'Error', message: "Failed to load job details", type: 'error' });
        return;
      }
      const jobData = await jobResponse.json();

      const response = await apiCall(`/api/analyze`, {
        method: "POST",
        body: JSON.stringify({
          cv_id: parseInt(cvId),
          job_title: jobData.title,
          company: jobData.company,
          job_description: jobData.description,
        }),
      });
      const data = await response.json();
      if (response.ok && data.analysis_id) {
        router.push(`/results/${data.analysis_id}`);
      } else {
        setDialog({ open: true, title: 'Error', message: describeApiError(data, "Analysis failed"), type: 'error' });
      }
    } catch (err) {
      setDialog({ open: true, title: 'Error', message: err instanceof Error ? err.message : "Analysis failed", type: 'error' });
    } finally {
      setAnalyzing(false);
    }
  };

  const getProficiencyColor = (proficiency: string) => {
    switch (proficiency) {
      case "advanced": return "from-blue-600 to-emerald-500";
      case "intermediate": return "from-blue-500 to-cyan-600";
      default: return "from-neutral-500 to-neutral-600";
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 75) return "text-emerald-400";
    if (score >= 50) return "text-amber-400";
    return "text-rose-400";
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-900 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-neutral-400">Loading your profile...</p>
        </div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="min-h-screen bg-neutral-900 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto px-4">
          <FaChartLine className="w-16 h-16 text-neutral-600 mx-auto mb-4" />
          <h1 className="page-title mb-2">No CV Selected</h1>
          <p className="text-neutral-400 mb-6">Upload a CV to see your AI-powered profile analysis.</p>
          <button
            onClick={() => router.push("/cv")}
            className="btn-primary flex items-center gap-2"
          >
            <FaSearch className="w-4 h-4" />
            Upload CV
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neutral-900 text-neutral-50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8"
        >
          <div>
            <h1 className="text-3xl font-bold text-neutral-50">Your Profile</h1>
            <p className="text-neutral-400 mt-1">AI-powered analysis of {analysis.cv_name}</p>
          </div>
          <div className="flex gap-3">
            <motion.button
              onClick={() => router.push(`/career-lens?cv_id=${analysis.id}`)}
              className="btn-secondary flex items-center gap-2"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <FaRobot className="w-4 h-4" />
              CareerLens Chat
            </motion.button>
            <motion.button
              onClick={handleFindJobs}
              disabled={jobsLoading}
              className="btn-primary flex items-center gap-2"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <FaBriefcase className="w-4 h-4" />
              {jobsLoading ? "Finding Jobs..." : "Find Matching Jobs"}
            </motion.button>
          </div>
        </motion.div>

        {/* Profile Score Overview */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-6 mb-6"
        >
          <div className="flex flex-col sm:flex-row items-center gap-6">
            <div className="relative w-32 h-32">
              <svg className="w-32 h-32 transform -rotate-90">
                <circle cx="64" cy="64" r="56" stroke="currentColor" strokeWidth="8" fill="none" className="text-neutral-700" />
                <circle
                  cx="64" cy="64" r="56"
                  stroke="currentColor" strokeWidth="8" fill="none"
                  className="text-blue-500"
                  strokeDasharray={`${analysis.overall_score * 3.52} 352`}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-3xl font-bold text-neutral-50">{analysis.overall_score}%</span>
              </div>
            </div>
            <div className="flex-1 text-center sm:text-left">
              <h2 className="text-xl font-semibold text-neutral-200 mb-2">Profile Completeness</h2>
              <p className="text-neutral-400 mb-4">
                Your profile has been analyzed based on {analysis.skills.length} skills, {analysis.experience.length} experience entries, and {analysis.education.length} education items.
              </p>
              <div className="flex flex-wrap justify-center sm:justify-start gap-2">
                {analysis.strengths.slice(0, 3).map((strength, i) => (
                  <span key={i} className="text-sm px-3 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    {strength}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </motion.div>

        {/* Skills Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-6 mb-6"
        >
          <h3 className="text-lg font-semibold text-neutral-200 mb-4 flex items-center gap-2">
            <FaChartLine className="w-5 h-5 text-blue-400" />
            Skills & Proficiency
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {analysis.skills.map((skill, i) => (
              <div key={i} className="flex items-center gap-3">
                <span className="text-sm text-neutral-300 w-40 truncate">{skill.name}</span>
                <div className="flex-1 h-2 bg-neutral-700/50 rounded-full overflow-hidden">
                  <div
                    className={`h-2 rounded-full bg-gradient-to-r ${getProficiencyColor(skill.proficiency)}`}
                    style={{
                      width: skill.proficiency === "advanced" ? "90%" : skill.proficiency === "intermediate" ? "60%" : "30%",
                    }}
                  />
                </div>
                <span className="text-xs text-neutral-500 w-20 capitalize">{skill.proficiency}</span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Experience, Education, Projects, Certifications Grid */}
        <div className="grid md:grid-cols-2 gap-6 mb-6">
          {/* Experience */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
            className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-6"
          >
            <h3 className="text-lg font-semibold text-neutral-200 mb-4 flex items-center gap-2">
              <FaBriefcase className="w-5 h-5 text-emerald-400" />
              Experience
            </h3>
            {analysis.experience.length > 0 ? (
              <div className="space-y-2">
                {analysis.experience.map((exp, i) => (
                  <div key={i} className="p-3 rounded-lg bg-neutral-700/30 border border-neutral-600/30">
                    <p className="text-sm text-neutral-300">{exp}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-neutral-500">No experience details extracted</p>
            )}
          </motion.div>

          {/* Education */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4 }}
            className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-6"
          >
            <h3 className="text-lg font-semibold text-neutral-200 mb-4 flex items-center gap-2">
              <FaGraduationCap className="w-5 h-5 text-emerald-400" />
              Education
            </h3>
            {analysis.education.length > 0 ? (
              <div className="space-y-2">
                {analysis.education.map((edu, i) => (
                  <div key={i} className="p-3 rounded-lg bg-neutral-700/30 border border-neutral-600/30">
                    <p className="text-sm text-neutral-300">{edu}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-neutral-500">No education details extracted</p>
            )}
          </motion.div>

          {/* Projects */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.5 }}
            className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-6"
          >
            <h3 className="text-lg font-semibold text-neutral-200 mb-4 flex items-center gap-2">
              <FaProjectDiagram className="w-5 h-5 text-amber-400" />
              Projects
            </h3>
            {analysis.projects.length > 0 ? (
              <div className="space-y-2">
                {analysis.projects.map((project, i) => (
                  <div key={i} className="p-3 rounded-lg bg-neutral-700/30 border border-neutral-600/30">
                    <p className="text-sm text-neutral-300">{project}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-neutral-500">No projects extracted</p>
            )}
          </motion.div>

          {/* Certifications */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.6 }}
            className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-6"
          >
            <h3 className="text-lg font-semibold text-neutral-200 mb-4 flex items-center gap-2">
              <FaCertificate className="w-5 h-5 text-cyan-400" />
              Certifications
            </h3>
            {analysis.certifications.length > 0 ? (
              <div className="space-y-2">
                {analysis.certifications.map((cert, i) => (
                  <div key={i} className="p-3 rounded-lg bg-neutral-700/30 border border-neutral-600/30">
                    <p className="text-sm text-neutral-300">{cert}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-neutral-500">No certifications extracted</p>
            )}
          </motion.div>
        </div>

        {/* Recommendations */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-6 mb-6"
        >
          <h3 className="text-lg font-semibold text-neutral-200 mb-4 flex items-center gap-2">
            <FaBolt className="w-5 h-5 text-amber-400" />
            Recommendations
          </h3>
          <div className="space-y-2">
            {analysis.recommendations.map((rec, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.05 * i }}
                className="flex items-start gap-3 p-3 rounded-lg bg-neutral-700/30 border border-neutral-600/30"
              >
                <FaArrowRight className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
                <span className="text-sm text-neutral-300">{rec}</span>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Job Recommendations */}
        <AnimatePresence>
          {showJobs && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-6"
            >
              <h3 className="text-lg font-semibold text-neutral-200 mb-4 flex items-center gap-2">
                <FaBriefcase className="w-5 h-5 text-blue-400" />
                Recommended Jobs
              </h3>
              {jobsLoading ? (
                <div className="text-center py-8">
                  <div className="w-8 h-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mx-auto mb-4" />
                  <p className="text-neutral-400">Finding best matches for you...</p>
                </div>
              ) : jobs.length > 0 ? (
                <div className="space-y-4">
                  {jobs.map((job, index) => (
                    <motion.div
                      key={job.job_id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className="p-5 rounded-lg bg-neutral-700/30 border border-neutral-600/30 hover:border-blue-500/30 transition-colors"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-3">
                        <div>
                          <h4 className="text-lg font-semibold text-neutral-200">{job.job_title}</h4>
                          <p className="text-sm text-neutral-400">{job.company} | {job.location}</p>
                          <p className="text-xs text-neutral-500 mt-1">{job.employment_type} | {job.salary_min && job.salary_max ? `$${job.salary_min.toLocaleString()} - $${job.salary_max.toLocaleString()}` : "Salary not specified"}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`text-2xl font-bold ${getScoreColor(job.match_score)}`}>
                            {Math.round(job.match_score)}%
                          </span>
                          <span className="text-xs text-neutral-500">match</span>
                        </div>
                      </div>

                      {/* Match Breakdown */}
                      <div className="grid grid-cols-3 gap-2 mb-3">
                        <div className="text-center p-2 rounded-lg bg-neutral-800/50">
                          <p className="text-xs text-neutral-500">Skills</p>
                          <p className="text-sm font-medium text-neutral-200">{job.match_breakdown.skills_match}%</p>
                        </div>
                        <div className="text-center p-2 rounded-lg bg-neutral-800/50">
                          <p className="text-xs text-neutral-500">Experience</p>
                          <p className="text-sm font-medium text-neutral-200">{formatScore(job.match_breakdown.experience_match)}</p>
                        </div>
                        <div className="text-center p-2 rounded-lg bg-neutral-800/50">
                          <p className="text-xs text-neutral-500">Education</p>
                          <p className="text-sm font-medium text-neutral-200">{formatScore(job.match_breakdown.education_match)}</p>
                        </div>
                      </div>

                      {/* Matched Skills */}
                      {job.matched_skills.length > 0 && (
                        <div className="mb-3">
                          <p className="text-xs text-neutral-500 mb-1">Matched Skills</p>
                          <div className="flex flex-wrap gap-1">
                            {job.matched_skills.slice(0, 5).map((skill, i) => (
                              <span key={i} className="text-xs px-2 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                {skill}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Missing Skills */}
                      {job.missing_skills.length > 0 && (
                        <div className="mb-3">
                          <p className="text-xs text-neutral-500 mb-1">Skill Gaps</p>
                          <div className="flex flex-wrap gap-1">
                            {job.missing_skills.slice(0, 5).map((skill, i) => (
                              <span key={i} className="text-xs px-2 py-1 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
                                {skill}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="flex gap-2">
                        <motion.button
                          onClick={() => router.push(`/jobs/${job.job_id}`)}
                          className="text-sm px-4 py-2 bg-neutral-700 text-neutral-200 rounded-lg hover:bg-neutral-600 flex items-center gap-2"
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                        >
                          View Job
                        </motion.button>
                        <motion.button
                          onClick={() => handleAnalyzeJob(job.job_id)}
                          disabled={analyzing}
                          className="text-sm px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                        >
                          <FaSearch className="w-3 h-3" />
                          {analyzing ? "Analyzing..." : "Analyze This Job"}
                        </motion.button>
                      </div>
                    </motion.div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-neutral-400">No matching jobs found. Try updating your CV with more skills.</p>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

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
