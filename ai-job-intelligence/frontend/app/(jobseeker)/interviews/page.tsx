"use client";

import InterviewsView from "@/components/InterviewsView";

export default function CandidateInterviewsPage() {
  return (
    <div className="max-w-5xl mx-auto">
      <header className="mb-6">
        <h1 className="page-title">Interviews</h1>
        <p className="page-subtitle">Interviews employers have booked with you. Confirm or decline below.</p>
      </header>
      <InterviewsView side="candidate" />
    </div>
  );
}
