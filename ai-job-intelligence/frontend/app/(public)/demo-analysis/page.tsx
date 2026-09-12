"use client";

import { describeApiError, formatScore } from "@/components/format";

import { useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FaCheck,
  FaArrowRight,
  FaBrain,
  FaStar,
  FaRocket,
  FaShieldAlt,
  FaUpload,
  FaTimes,
  FaPlay,
  FaFileAlt,
  FaRobot,
} from "react-icons/fa";
import MessageDialog from "@/components/MessageDialog";
import { API_BASE } from "@/components/api";

interface AnalysisResult {
  job_title: string;
  filename: string;
  match_score: number;
  matched_skills: string[];
  missing_skills: string[];
  /** null when the posting lists no technical requirements. */
  skills_match: number | null;
  /** null means the posting never stated this, so it was not scored. */
  experience_match: number | null;
  education_match: number | null;
  recommendations: string[];
  summary: string;
  detected_skills: string[];
  sources: string[];
}

const JOB_DESC_GUIDE = `Tips for a good job description:
• Paste the full job posting, not just a summary.
• Include required skills, experience level, and education.
• Mention tools, frameworks, and responsibilities.
• The more detail you provide, the more accurate the match score.`;

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.05 },
  },
};

const item = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0 },
};

export default function DemoAnalysisPage() {
  const [file, setFile] = useState<File | null>(null);
  const [jobTitle, setJobTitle] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [showGuide, setShowGuide] = useState(false);
  const [dialog, setDialog] = useState({ open: false, title: "", message: "", type: "info" as "info" | "success" | "error" | "warning" });
  // The demo limit is enforced by the server (per IP, per hour) and reported
  // via 429. There was previously a sessionStorage counter that disabled the
  // submit button after two runs -- a disabled button fires no submit event,
  // so the page silently did nothing when clicked. It was also read during
  // render, which produced a hydration mismatch because sessionStorage does
  // not exist on the server.
  const [limitMessage, setLimitMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (selected: File | null) => {
    if (!selected) return;
    const allowed = [".pdf", ".txt", ".png", ".jpg", ".jpeg"];
    const ext = "." + selected.name.split(".").pop()?.toLowerCase();
    if (!allowed.includes(ext)) {
      setDialog({ open: true, title: "Error", message: "Only PDF, TXT, PNG, JPG, JPEG files are allowed", type: "error" });
      return;
    }
    setFile(selected);
    setResult(null);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files[0]) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !jobTitle.trim() || !jobDescription.trim()) {
      setDialog({ open: true, title: "Error", message: "Please upload a CV and fill in all fields", type: "error" });
      return;
    }
    setAnalyzing(true);
    setResult(null);
    setLimitMessage(null);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("job_title", jobTitle);
      formData.append("job_description", jobDescription);

      // FormData must not carry the JSON content-type apiCall sets, so this
      // uses fetch directly -- but still against the shared API base.
      const response = await fetch(`${API_BASE}/api/demo/analyze`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      if (!response.ok) {
        if (response.status === 429) {
          // The server owns the quota, so show exactly what it said.
          setLimitMessage(describeApiError(data, "Demo limit reached."));
          return;
        }
        throw new Error(describeApiError(data, "Analysis failed"));
      }

      setResult(data);
    } catch (err) {
      setDialog({ open: true, title: "Error", message: err instanceof Error ? err.message : "Analysis failed", type: "error" });
    } finally {
      setAnalyzing(false);
    }
  };

  const resetDemo = () => {
    setFile(null);
    setJobTitle("");
    setJobDescription("");
    setResult(null);
  };

  const getScoreColor = (score: number) => {
    if (score >= 75) return "text-emerald-400";
    if (score >= 50) return "text-amber-400";
    if (score >= 30) return "text-orange-400";
    return "text-rose-400";
  };

  return (
    <div className="min-h-screen bg-neutral-900 text-neutral-50">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 lg:py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center mb-8"
        >
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-600/10 border border-blue-500/20 text-sm text-blue-400 mb-4">
            <FaBrain className="w-4 h-4" />
            Free Demo
          </span>
          <h1 className="text-3xl sm:text-4xl font-bold mb-2">
            Try CV{" "}
            <span className="gradient-text">Analysis</span>
          </h1>
          <p className="text-neutral-400 max-w-xl mx-auto">
            Upload your CV and a job description to see how the matching engine
            evaluates your fit. Free to try, no account needed.
          </p>
          <div className="mt-3 inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-neutral-800/50 border border-neutral-700/50 text-sm text-neutral-300">
            <FaShieldAlt className="w-4 h-4 text-blue-400" />
            Your file is analysed then deleted — nothing is stored.
          </div>
        </motion.div>

        <AnimatePresence mode="wait">
          {!result ? (
            <motion.form
              key="form"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.4 }}
              onSubmit={handleAnalyze}
              className="space-y-5"
            >
              {/* CV Upload */}
              <div className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-5">
                <h3 className="text-lg font-semibold text-neutral-200 mb-3 flex items-center gap-2">
                  <FaUpload className="w-5 h-5 text-blue-400" />
                  Upload CV
                </h3>
                <div
                  onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`relative rounded-lg border-2 border-dashed p-8 text-center cursor-pointer transition-colors ${
                    dragOver ? "border-blue-500 bg-blue-600/10" : "border-neutral-600 hover:border-neutral-500"
                  }`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.txt,.png,.jpg,.jpeg"
                    className="hidden"
                    onChange={(e) => handleFileChange(e.target.files?.[0] || null)}
                  />
                  {file ? (
                    <div className="flex items-center justify-center gap-3">
                      <FaFileAlt className="w-8 h-8 text-blue-400" />
                      <div className="text-left">
                        <p className="text-sm font-medium text-neutral-200">{file.name}</p>
                        <p className="text-xs text-neutral-400">{(file.size / 1024).toFixed(1)} KB</p>
                      </div>
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); setFile(null); }}
                        className="p-1 text-neutral-400 hover:text-rose-400"
                      >
                        <FaTimes className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <>
                      <FaUpload className="w-10 h-10 text-neutral-500 mx-auto mb-3" />
                      <p className="text-sm text-neutral-300 mb-1">Drag and drop your CV here, or click to browse</p>
                      <p className="text-xs text-neutral-500">PDF, TXT, PNG, JPG up to 10MB</p>
                    </>
                  )}
                </div>
              </div>

              {/* Job Details */}
              <div className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-5">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-semibold text-neutral-200 flex items-center gap-2">
                    <FaRobot className="w-5 h-5 text-emerald-400" />
                    Job Details
                  </h3>
                  <button
                    type="button"
                    onClick={() => setShowGuide(!showGuide)}
                    className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
                  >
                    {showGuide ? "Hide guide" : "Writing guide"}
                  </button>
                </div>

                <AnimatePresence>
                  {showGuide && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      className="overflow-hidden mb-4 rounded-lg bg-neutral-700/30 border border-neutral-600/30 p-4"
                    >
                      <p className="text-sm text-neutral-300 whitespace-pre-line">{JOB_DESC_GUIDE}</p>
                    </motion.div>
                  )}
                </AnimatePresence>

                <div className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-neutral-300 mb-1.5">Job Title</label>
                    <input
                      type="text"
                      value={jobTitle}
                      onChange={(e) => setJobTitle(e.target.value)}
                      placeholder="e.g. Senior Data Engineer"
                      className="w-full px-4 py-3 bg-neutral-800 border border-neutral-700 rounded-lg text-neutral-100 placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-neutral-300 mb-1.5">Job Description</label>
                    <textarea
                      value={jobDescription}
                      onChange={(e) => setJobDescription(e.target.value)}
                      placeholder="Paste the full job description here..."
                      rows={8}
                      className="w-full px-4 py-3 bg-neutral-800 border border-neutral-700 rounded-lg text-neutral-100 placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all resize-y"
                      required
                    />
                    <p className="text-xs text-neutral-500 mt-1.5">
                      Tip: include required skills, experience level, and education requirements for best results.
                    </p>
                  </div>
                </div>
              </div>

              {limitMessage && (
                <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3">
                  <p className="text-sm text-amber-200">{limitMessage}</p>
                  <a
                    href="/register"
                    className="inline-block mt-2 text-sm text-amber-100 underline underline-offset-4"
                  >
                    Create a free account for unlimited analyses
                  </a>
                </div>
              )}

              <motion.button
                type="submit"
                disabled={analyzing}
                className="btn-primary w-full flex items-center justify-center gap-2 py-3.5 disabled:opacity-50 disabled:cursor-not-allowed"
                whileHover={{ scale: analyzing ? 1 : 1.01 }}
                whileTap={{ scale: analyzing ? 1 : 0.99 }}
              >
                {analyzing ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <FaPlay className="w-4 h-4" />
                    Analyze CV
                  </>
                )}
              </motion.button>

              {analyzing && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="space-y-2 text-sm text-neutral-400"
                >
                  <div className="flex items-center gap-2">
                    <FaCheck className="w-4 h-4 text-emerald-500" />
                    <span>Extracting text from CV...</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <FaCheck className="w-4 h-4 text-emerald-500" />
                    <span>Analyzing job requirements with AI...</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <FaPlay className="w-4 h-4 text-blue-400" />
                    <span>Calculating match score and recommendations...</span>
                  </div>
                </motion.div>
              )}
            </motion.form>
          ) : (
            <motion.div
              key="result"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="space-y-5"
            >
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-neutral-200">Analysis Result</h2>
                <button
                  onClick={resetDemo}
                  className="text-sm text-blue-400 hover:text-blue-300 flex items-center gap-1"
                >
                  <FaArrowRight className="w-3 h-3" />
                  New analysis
                </button>
              </div>

              {/* Score Card */}
              <div className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-6">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                  <div>
                    <h3 className="text-lg font-semibold text-neutral-200">{jobTitle}</h3>
                    <p className="page-subtitle">{result.summary}</p>
                  </div>
                  <div className="text-center md:text-right">
                    <div className={`text-4xl font-bold ${getScoreColor(result.match_score)}`}>
                      {result.match_score}%
                    </div>
                    <p className="text-sm text-neutral-400">Match Score</p>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-3 mt-5">
                  <div className="rounded-lg bg-neutral-800/60 border border-neutral-700 p-3 text-center">
                    <p className="text-xs text-neutral-400 mb-1">Skills</p>
                    <p className="text-lg font-bold text-neutral-100">
                      {formatScore(result.skills_match)}
                    </p>
                  </div>
                  <div className="rounded-lg bg-neutral-800/60 border border-neutral-700 p-3 text-center">
                    <p className="text-xs text-neutral-400 mb-1">Experience</p>
                    <p className="text-lg font-bold text-neutral-100">{formatScore(result.experience_match)}</p>
                  </div>
                  <div className="rounded-lg bg-neutral-800/60 border border-neutral-700 p-3 text-center">
                    <p className="text-xs text-neutral-400 mb-1">Education</p>
                    <p className="text-lg font-bold text-neutral-100">{formatScore(result.education_match)}</p>
                  </div>
                </div>
              </div>

              {/* Matched & Missing Skills */}
              <div className="grid md:grid-cols-2 gap-4">
                <div className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-5">
                  <h4 className="text-sm font-semibold text-emerald-400 mb-3 flex items-center gap-2">
                    <FaCheck className="w-4 h-4" />
                    Matched Skills
                  </h4>
                  <div className="flex flex-wrap gap-1.5">
                    {result.matched_skills.map((s) => (
                      <span key={s} className="text-xs px-2 py-1 rounded-lg bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                        {s}
                      </span>
                    ))}
                    {result.matched_skills.length === 0 && (
                      <span className="text-xs text-neutral-500">No skills matched</span>
                    )}
                  </div>
                </div>
                <div className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-5">
                  <h4 className="text-sm font-semibold text-amber-400 mb-3 flex items-center gap-2">
                    <FaStar className="w-4 h-4" />
                    Missing Skills
                  </h4>
                  <div className="flex flex-wrap gap-1.5">
                    {result.missing_skills.map((s) => (
                      <span key={s} className="text-xs px-2 py-1 rounded-lg bg-amber-500/10 text-amber-300 border border-amber-500/20">
                        {s}
                      </span>
                    ))}
                    {result.missing_skills.length === 0 && (
                      <span className="text-xs text-neutral-500">No missing skills identified</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Recommendations */}
              <div className="rounded-lg bg-neutral-800/50 border border-neutral-700/50 p-5">
                <h4 className="text-lg font-semibold text-neutral-200 mb-4 flex items-center gap-2">
                  <FaRocket className="w-5 h-5 text-emerald-400" />
                  Recommendations
                </h4>
                <motion.div className="space-y-2" variants={container} initial="hidden" animate="show">
                  {result.recommendations.map((rec, i) => (
                    <motion.div key={i} variants={item} className="flex items-start gap-2 text-sm text-neutral-300">
                      <FaArrowRight className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
                      {rec}
                    </motion.div>
                  ))}
                </motion.div>
              </div>

              {/* Provenance — the same "show your working" panel the signed-in
                  insights page uses, so the demo does not look like a black box. */}
              {result.sources && result.sources.length > 0 && (
                <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-5">
                  <h4 className="eyebrow mb-3">How this score was calculated</h4>
                  <ul className="space-y-2">
                    {result.sources.map((src, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-neutral-400">
                        <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-neutral-600" />
                        {src}
                      </li>
                    ))}
                  </ul>
                  {result.detected_skills.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-neutral-800">
                      <p className="eyebrow mb-2">Skills detected in your CV</p>
                      <div className="flex flex-wrap gap-1.5">
                        {result.detected_skills.map((skill) => (
                          <span key={skill} className="chip">
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* CTA */}
              <div className="rounded-lg bg-gradient-to-r from-blue-500/10 to-emerald-500/10 border border-blue-500/20 p-6 text-center">
                <FaShieldAlt className="w-10 h-10 text-blue-400 mx-auto mb-3" />
                <h3 className="text-xl font-bold text-neutral-50 mb-2">
                  Ready for Full Access?
                </h3>
                <p className="text-neutral-400 mb-5 max-w-lg mx-auto text-sm">
                  Sign up to save analyses, track progress, and get unlimited AI-powered career insights.
                </p>
                <a
                  href="/register"
                  className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-emerald-500 text-white font-medium rounded-lg hover:shadow-lg hover:shadow-blue-500/25 transition-all duration-300"
                >
                  <FaRocket className="w-4 h-4" />
                  Create Free Account
                </a>
              </div>
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
