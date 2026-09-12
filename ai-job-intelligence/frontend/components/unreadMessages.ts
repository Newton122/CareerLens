"use client";

import { useEffect, useState } from "react";
import { apiCall } from "@/components/api";

/**
 * The unread-message count shown on the "Messages" link.
 *
 * There is no push channel (such as a WebSocket) yet, so the count is polled:
 * every POLL_MS, and straight away whenever this tab reads messages
 * (MessagesView fires MESSAGES_READ_EVENT). Polling pauses while the browser
 * tab is hidden, so a background tab costs nothing.
 */

export const MESSAGES_READ_EVENT = "careerlens-messages-read";

const POLL_MS = 30_000;

/** Tell badges that messages were just read, so they update immediately. */
export function notifyMessagesRead() {
  window.dispatchEvent(new Event(MESSAGES_READ_EVENT));
}

export function useUnreadMessageCount(enabled: boolean): number {
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (!enabled) return;
    let active = true;
    const refresh = () => {
      if (document.hidden) return;
      apiCall("/api/messages/unread/count")
        .then((res) => (res.ok ? res.json() : null))
        .then((data: { unread: number } | null) => {
          if (active && data) setCount(data.unread);
        })
        .catch(() => {
          // A missed poll is harmless; the next one will try again.
        });
    };
    refresh();
    const timer = window.setInterval(refresh, POLL_MS);
    window.addEventListener(MESSAGES_READ_EVENT, refresh);
    return () => {
      active = false;
      window.clearInterval(timer);
      window.removeEventListener(MESSAGES_READ_EVENT, refresh);
    };
  }, [enabled]);

  return enabled ? count : 0;
}
