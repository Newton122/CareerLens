"use client";

import MessagesView from "@/components/MessagesView";

export default function CandidateMessagesPage() {
  return (
    <div className="max-w-5xl mx-auto">
      <header className="mb-6">
        <h1 className="page-title">Messages</h1>
        <p className="page-subtitle">Your conversations with employers.</p>
      </header>
      <MessagesView />
    </div>
  );
}
