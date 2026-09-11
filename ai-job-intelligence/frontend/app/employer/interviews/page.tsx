"use client";

import InterviewsView from "@/components/InterviewsView";

export default function EmployerInterviewsPage() {
  return (
    <div className="max-w-5xl mx-auto">
      <header className="mb-6">
        <h1 className="page-title">Interviews</h1>
        <p className="page-subtitle">Interviews you have scheduled with candidates.</p>
      </header>
      <InterviewsView side="employer" />
    </div>
  );
}
