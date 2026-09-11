"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { apiCall, viewFile } from "@/components/api";
import MessageDialog from "@/components/MessageDialog";
import InterviewScheduler from "@/components/InterviewScheduler";

interface Candidate {
  /** CV id — identifies the document, not the person. */
  id: string;
  /** The addressable user. Use this for interviews and messages. */
  user_id: number;
  name: string;
  email: string;
  location?: string;
  headline?: string;
  summary?: string;
  skills: string[];
  experience_level: "entry" | "mid" | "senior" | "expert";
  match_score: number;
  experience?: Array<{
    title: string;
    company: string;
    duration: string;
  }>;
  education?: Array<{
    degree: string;
    institution: string;
    year: string;
  }>;
  cv_url?: string;
}

interface MessageModalProps {
  isOpen: boolean;
  onClose: () => void;
  candidateId: string;
  onSend: (content: string) => void;
}

function MessageModal({ isOpen, onClose, candidateId, onSend }: MessageModalProps) {
  const [content, setContent] = useState("");

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;
    onSend(content);
    setContent("");
  };

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-neutral-800 rounded p-4 max-w-xl w-full mx-2"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-base font-bold mb-2">Send Message</h3>
        <form onSubmit={handleSubmit} className="space-y-2">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Enter your message..."
            rows={3}
            className="input-premium"
            required
          />
          <div className="flex gap-2">
            <button
              type="submit"
              className="btn-primary btn-small"
            >
              Send
            </button>
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary btn-small"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function EmployerCandidateDetailPage() {
  const router = useRouter();
  const params = useParams();
  const candidateId = params.id as string;
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [loading, setLoading] = useState(true);
  const [messageModalOpen, setMessageModalOpen] = useState(false);
  const [schedulerOpen, setSchedulerOpen] = useState(false);
  const [dialog, setDialog] = useState({ open: false, title: '', message: '', type: 'info' as 'info' | 'success' | 'error' | 'warning' });

  useEffect(() => {
    fetchCandidateDetail();
  }, [candidateId]);

  const fetchCandidateDetail = async () => {
    setLoading(true);
    try {
      const response = await apiCall(`/api/candidates/${candidateId}`);
      if (response.ok) {
        const data = await response.json();
        setCandidate(data);
      }
    } catch (err) {
      setDialog({ open: true, title: 'Error', message: "Error loading candidate details", type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  // Scheduling used to post a fixed "seven days from now" with no joining
  // details at all, which produced interviews nobody could actually attend.
  // The form now collects the time and how the two sides will meet.
  const handleInterviewScheduled = () => {
    setDialog({
      open: true,
      title: 'Interview scheduled',
      message: "The candidate can see it under Interviews, with the joining details, and can confirm or decline.",
      type: 'success',
    });
  };

  const handleSendMessage = async (content: string) => {
    try {
      const response = await apiCall("/api/messages", {
        method: "POST",
        body: JSON.stringify({
          recipient_user_id: candidate?.user_id,
          content,
        }),
      });

      if (response.ok) {
        setDialog({ open: true, title: 'Message sent', message: "You'll find the conversation under Messages.", type: 'success' });
      } else {
        const err = await response.json().catch(() => ({}));
        setDialog({ open: true, title: 'Could not send', message: err.detail || "Failed to send message", type: 'error' });
      }
    } catch (err) {
      setDialog({ open: true, title: 'Error', message: "Error sending message", type: 'error' });
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen text-neutral-100">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <p className="text-base text-neutral-500">Loading candidate details...</p>
        </div>
      </div>
    );
  }

  if (!candidate) {
    return (
      <div className="min-h-screen text-neutral-100">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <p className="text-base text-neutral-500">Candidate not found</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen text-neutral-100">
      <div className="max-w-5xl mx-auto px-4 py-6">
        <button
          onClick={() => router.push("/employer/candidates")}
          className="text-base text-blue-600 mb-2"
        >
            Back to Candidates
        </button>

        {/* Header */}
        <div className="card mb-4">
          <div className="flex justify-between">
            <div>
              <h1 className="page-title">{candidate.name}</h1>
              {candidate.headline && (
                <p className="text-base text-neutral-400">{candidate.headline}</p>
              )}
              <p className="text-base text-neutral-500">{candidate.email}</p>
              {candidate.location && (
                <p className="text-base text-neutral-500"> |  {candidate.location}</p>
              )}
            </div>
            <div className="text-right">
              <p className="text-base font-bold text-blue-600">
                {candidate.match_score}%
              </p>
              <p className="text-base text-neutral-400">Match Score</p>
            </div>
          </div>
        </div>

        {/* AI Skills */}
        <div className="card mb-4">
          <h2 className="section-title mb-2">
            AI-Extracted Skills
          </h2>
          <div className="flex flex-wrap gap-1">
            {candidate.skills.map((s) => (
              <span
                key={s}
                className="text-base px-2 py-0.5 bg-neutral-800 text-neutral-200 rounded"
              >
                {s}
              </span>
            ))}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="card mb-4">
          <h2 className="section-title mb-3">Actions</h2>
          <div className="flex gap-2">
            <button
              onClick={() => setSchedulerOpen(true)}
              className="btn-primary"
            >
              Schedule Interview
            </button>
            <button
              onClick={() => setMessageModalOpen(true)}
              className="btn-secondary"
            >
              Send Message
            </button>
            {candidate.id && (
              <button
                onClick={() => viewFile(`/api/cvs/${candidate.id}/download`)}
                className="btn-secondary"
              >
                View CV
              </button>
            )}
          </div>
        </div>

        {/* Experience & Education */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          {candidate.experience && candidate.experience.length > 0 && (
            <div className="card">
              <h2 className="section-title mb-2">
                Experience
              </h2>
              <div className="space-y-2">
                {candidate.experience.map((exp, i) => (
                  <div key={i}>
                    <p className="text-base font-medium">{exp.title}</p>
                    <p className="text-base text-neutral-400">{exp.company}</p>
                    <p className="text-base text-neutral-500">{exp.duration}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {candidate.education && candidate.education.length > 0 && (
            <div className="card">
              <h2 className="section-title mb-2">
                Education
              </h2>
              <div className="space-y-2">
                {candidate.education.map((edu, i) => (
                  <div key={i}>
                    <p className="text-base font-medium">{edu.degree}</p>
                    <p className="text-base text-neutral-400">{edu.institution}</p>
                    <p className="text-base text-neutral-500">{edu.year}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Summary */}
        {candidate.summary && (
          <div className="card">
            <h2 className="section-title mb-2">
              AI Summary
            </h2>
            <p className="text-base text-neutral-300">{candidate.summary}</p>
          </div>
        )}

        {/* Message Modal */}
        <MessageModal
          isOpen={messageModalOpen}
          onClose={() => setMessageModalOpen(false)}
          candidateId={candidateId}
          onSend={handleSendMessage}
        />
        <InterviewScheduler
          open={schedulerOpen}
          onClose={() => setSchedulerOpen(false)}
          onSaved={handleInterviewScheduled}
          candidateName={candidate?.name}
          candidateUserId={candidate?.user_id}
        />
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
