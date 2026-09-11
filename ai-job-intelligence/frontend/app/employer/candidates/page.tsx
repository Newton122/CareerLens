"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { apiCall } from "@/components/api";
import MessageDialog from "@/components/MessageDialog";

interface Candidate {
  id: string;
  name: string;
  email: string;
  skills: string[];
  experience_level: "entry" | "mid" | "senior" | "expert";
  match_score: number;
  location?: string;
  headline?: string;
}

export default function EmployerCandidatesPage() {
  const router = useRouter();
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchSkills, setSearchSkills] = useState("");
  const [minMatch, setMinMatch] = useState(0);
  const [dialog, setDialog] = useState({ open: false, title: '', message: '', type: 'info' as 'info' | 'success' | 'error' | 'warning' });

  const handleSearch = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchSkills) params.append("skills", searchSkills);
      if (minMatch > 0) params.append("min_match", minMatch.toString());

      const response = await apiCall(`/api/candidates?${params.toString()}`);

      if (response.ok) {
        const data = await response.json();
        let results = Array.isArray(data) ? data : [];
        if (minMatch > 0) {
          results = results.filter(
            (c: Candidate) => c.match_score >= minMatch,
          );
        }
        setCandidates(results);
        if (results.length === 0) {
          setDialog({ open: true, title: 'Info', message: "No candidates found", type: 'info' });
        }
      }
    } catch (err) {
      setDialog({ open: true, title: 'Error', message: "Error searching candidates", type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setSearchSkills("");
    setMinMatch(0);
    setCandidates([]);
  };

  return (
    <div className="min-h-screen text-neutral-100">
      <div className="max-w-5xl mx-auto px-4 py-6">
        <h1 className="page-title mb-2">Candidate Search</h1>
        <p className="text-base text-neutral-400 mb-3">
          Find candidates for your open positions
        </p>

        {/* Filters */}
        <div className="card mb-4">
          <div className="space-y-2">
            <input
              type="text"
              value={searchSkills}
              onChange={(e) => setSearchSkills(e.target.value)}
              placeholder="Skills (comma-separated), e.g. React, TypeScript"
              className="input-premium"
            />
            <div className="flex items-center gap-2">
              <input
                type="range"
                min="0"
                max="100"
                value={minMatch}
                onChange={(e) => setMinMatch(Number(e.target.value))}
                className="flex-1"
              />
              <span className="text-base text-neutral-400 w-8">{minMatch}%</span>
            </div>
          </div>
          <div className="flex gap-2 mt-2">
            <button
              onClick={handleSearch}
              disabled={loading}
              className="btn-primary"
            >
              {loading ? "Searching..." : "Search"}
            </button>
            <button
              onClick={handleClear}
              className="btn-secondary"
            >
              Clear
            </button>
          </div>
        </div>

        {/* Results */}
        {candidates.length > 0 ? (
          <div className="space-y-1">
            {candidates.map((candidate) => (
              <div
                key={candidate.id}
                onClick={() => router.push(`/employer/candidates/${candidate.id}`)}
                className="border border-neutral-700/50 rounded p-2 cursor-pointer hover:bg-neutral-700/50"
              >
                <div className="flex justify-between">
                  <div>
                    <p className="text-base font-medium">{candidate.name}</p>
                    {candidate.headline && (
                      <p className="text-base text-neutral-400">{candidate.headline}</p>
                    )}
                    <p className="text-base text-neutral-500">{candidate.email}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-base font-bold text-blue-600">
                      {candidate.match_score}%
                    </p>
                    <span className={`text-base px-1.5 py-0.5 rounded border ${getExpLevelColor(candidate.experience_level)}`}>
                      {candidate.experience_level}
                    </span>
                  </div>
                </div>
                <div className="flex flex-wrap gap-1 mt-1">
                  {candidate.skills.slice(0, 3).map((s) => (
                    <span
                      key={s}
                      className="text-base px-1.5 py-0.5 bg-neutral-800 text-neutral-200 rounded"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-base text-neutral-500 py-6 text-center">
            {searchSkills || minMatch > 0
              ? "No candidates found. Try adjusting your filters."
              : "Use the search filters above to find candidates."}
          </p>
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

function getExpLevelColor(level: string) {
  switch (level) {
    case "entry":
      return "bg-blue-500/15 text-blue-300 border-blue-500/30";
    case "mid":
      return "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";
    case "senior":
      return "bg-amber-500/15 text-amber-300 border-amber-500/30";
    case "expert":
      return "bg-rose-500/15 text-rose-300 border-rose-500/30";
    default:
      return "bg-neutral-800 text-neutral-100 border-neutral-700/50";
  }
}
