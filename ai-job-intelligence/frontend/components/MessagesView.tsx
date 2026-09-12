"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { FaPaperPlane, FaInbox, FaArrowLeft } from "react-icons/fa";
import { apiCall } from "@/components/api";

interface Conversation {
  user_id: number;
  name: string;
  email: string;
  role: string;
  last_message: string;
  last_message_at: string | null;
  last_sender_id: number | null;
  unread_count: number;
}

interface Message {
  id: number;
  sender_id: number;
  sender_name: string;
  recipient_id: number;
  recipient_name: string;
  body: string;
  job_id: number | null;
  read_at: string | null;
  created_at: string;
}

function initials(name: string, email: string): string {
  const source = name?.trim() || email || "?";
  return source
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function MessagesView() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [thread, setThread] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  const loadConversations = useCallback(async () => {
    try {
      const res = await apiCall("/api/messages");
      if (res.ok) setConversations(await res.json());
    } catch {
      setError("Could not load your conversations.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  const openThread = useCallback(
    async (userId: number) => {
      setActiveId(userId);
      try {
        const res = await apiCall(`/api/messages/${userId}`);
        if (res.ok) {
          setThread(await res.json());
          // Opening a thread marks it read server-side; reflect that here.
          setConversations((prev) =>
            prev.map((c) => (c.user_id === userId ? { ...c, unread_count: 0 } : c))
          );
        }
      } catch {
        setError("Could not open that conversation.");
      }
    },
    []
  );

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [thread]);

  const send = async () => {
    const body = draft.trim();
    if (!body || activeId === null) return;
    setSending(true);
    try {
      const res = await apiCall("/api/messages", {
        method: "POST",
        body: JSON.stringify({ recipient_user_id: activeId, content: body }),
      });
      if (res.ok) {
        const created: Message = await res.json();
        setThread((prev) => [...prev, created]);
        setDraft("");
        loadConversations();
      } else {
        const err = await res.json().catch(() => ({}));
        setError(err.detail || "Could not send that message.");
      }
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return <p className="text-sm text-neutral-500">Loading messages…</p>;
  }

  if (conversations.length === 0) {
    return (
      <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-10 text-center">
        <FaInbox className="w-6 h-6 text-neutral-600 mx-auto mb-3" />
        <p className="text-neutral-300 font-medium">No messages yet</p>
        <p className="text-sm text-neutral-500 mt-1">
          Conversations you start or receive will appear here.
        </p>
      </div>
    );
  }

  const active = conversations.find((c) => c.user_id === activeId);

  return (
    <div className="grid lg:grid-cols-3 gap-4 min-h-[32rem]">
      {/* Conversation list — hidden on mobile once a thread is open. */}
      <aside
        className={`lg:col-span-1 rounded-lg border border-neutral-800 bg-neutral-900 overflow-hidden ${
          activeId !== null ? "hidden lg:block" : ""
        }`}
      >
        <ul className="divide-y divide-neutral-800">
          {conversations.map((c) => (
            <li key={c.user_id}>
              <button
                onClick={() => openThread(c.user_id)}
                className={`w-full text-left px-4 py-3 transition-colors ${
                  c.user_id === activeId
                    ? "bg-neutral-800"
                    : "hover:bg-neutral-800/60"
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="w-9 h-9 rounded-md bg-neutral-800 border border-neutral-700 flex items-center justify-center text-xs font-semibold text-neutral-300 shrink-0">
                    {initials(c.name, c.email)}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center justify-between gap-2">
                      <span className="font-medium text-neutral-100 truncate">
                        {c.name || c.email}
                      </span>
                      {c.unread_count > 0 && (
                        <span className="shrink-0 min-w-5 h-5 px-1.5 rounded-full bg-white text-neutral-950 text-xs font-semibold flex items-center justify-center">
                          {c.unread_count}
                        </span>
                      )}
                    </span>
                    <span className="block text-sm text-neutral-500 truncate">
                      {c.last_message}
                    </span>
                  </span>
                </div>
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <section
        className={`lg:col-span-2 rounded-lg border border-neutral-800 bg-neutral-900 flex flex-col ${
          activeId === null ? "hidden lg:flex" : ""
        }`}
      >
        {active ? (
          <>
            <header className="px-4 py-3 border-b border-neutral-800 flex items-center gap-3">
              <button
                onClick={() => setActiveId(null)}
                className="lg:hidden btn-ghost btn-small"
                aria-label="Back to conversations"
              >
                <FaArrowLeft className="w-3 h-3" />
              </button>
              <div className="min-w-0">
                <p className="font-medium text-neutral-100 truncate">
                  {active.name || active.email}
                </p>
                <p className="text-xs text-neutral-500 capitalize">
                  {active.role.replace("_", " ")}
                </p>
              </div>
            </header>

            <div className="flex-1 overflow-y-auto p-4 space-y-3 max-h-[26rem]">
              {thread.map((m) => {
                const mine = m.sender_id !== active.user_id;
                return (
                  <div
                    key={m.id}
                    className={`flex ${mine ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[75%] rounded-lg px-3.5 py-2.5 ${
                        mine
                          ? "bg-white text-neutral-950"
                          : "bg-neutral-800 text-neutral-100 border border-neutral-700"
                      }`}
                    >
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">
                        {m.body}
                      </p>
                      <p
                        className={`text-[11px] mt-1 ${
                          mine ? "text-neutral-500" : "text-neutral-500"
                        }`}
                      >
                        {formatTime(m.created_at)}
                      </p>
                    </div>
                  </div>
                );
              })}
              <div ref={endRef} />
            </div>

            <footer className="p-3 border-t border-neutral-800 flex gap-2">
              <input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    send();
                  }
                }}
                placeholder="Write a message…"
                className="input-premium flex-1"
              />
              <button
                onClick={send}
                disabled={sending || !draft.trim()}
                className="btn-primary"
              >
                <FaPaperPlane className="w-3.5 h-3.5" />
                Send
              </button>
            </footer>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center p-10 text-center">
            <p className="text-sm text-neutral-500">
              Select a conversation to read it.
            </p>
          </div>
        )}
      </section>

      {error && (
        <p className="lg:col-span-3 text-sm text-rose-300 bg-rose-500/10 border border-rose-500/30 rounded-md px-4 py-3">
          {error}
        </p>
      )}
    </div>
  );
}
