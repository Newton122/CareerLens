"use client";

/**
 * Backend origin.
 *
 * Configurable so end-to-end tests can point the app at an isolated API on
 * another port, and so a deployment is not hardwired to localhost. Falls back
 * to the local dev server when unset.
 *
 * Must be NEXT_PUBLIC_* to be readable from the browser bundle. It is inlined
 * at build time, so changing it on Vercel needs a redeploy. A trailing slash is
 * dropped so "https://api.example.com/" cannot produce "//api/..." paths.
 */
export const API_BASE = (
  process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

// ─── The login session, kept in localStorage ──────────────────────────────

export const SESSION_KEYS = ["access_token", "user_id", "careerLens_role", "user_email"] as const;

/** Fired in this tab when the session changes (other tabs get "storage"). */
export const AUTH_CHANGED_EVENT = "careerlens-auth-changed";

/** Fired when the API says the session is no longer valid. */
export const SESSION_EXPIRED_EVENT = "careerlens-session-expired";

export function notifySessionChanged() {
  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
}

/** Forget the session in this browser; every open tab updates. */
export function clearStoredSession() {
  SESSION_KEYS.forEach((key) => localStorage.removeItem(key));
  notifySessionChanged();
}

export function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem("access_token");
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

export async function apiCall(
  endpoint: string,
  options: RequestInit = {},
): Promise<Response> {
  const authHeaders = getAuthHeaders();
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...options.headers,
    },
  });
  // A signed-in request refused as unauthenticated means the session is
  // over: the token expired (after 24 hours) or was revoked by a password
  // reset. Sign this browser out; the layouts then send the user to /login.
  if (response.status === 401 && authHeaders.Authorization) {
    clearStoredSession();
    window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
  }
  return response;
}

/**
 * Open a protected file (a CV) in a new tab.
 *
 * A plain link can't send the Authorization header, so the file is downloaded
 * with the token and shown from a temporary blob: URL.
 *
 * The tab is opened *first*, while the click is still happening, and filled in
 * once the download finishes. Browsers only let a page open a tab as a direct
 * result of a click; opening it after waiting for a slow download can be
 * silently blocked as a pop-up.
 *
 * On failure it throws an Error carrying the server's own reason (for example
 * "The original file for this CV is no longer stored on the server…"), so the
 * page can show it instead of a vague "failed".
 */
export async function viewFile(endpoint: string): Promise<void> {
  const tab = window.open("", "_blank");
  try {
    const response = await apiCall(endpoint);
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      const detail = (data as { detail?: unknown }).detail;
      throw new Error(
        typeof detail === "string" && detail.trim()
          ? detail
          : `Could not open the file (error ${response.status}).`,
      );
    }
    const url = window.URL.createObjectURL(await response.blob());
    if (tab) {
      tab.location.href = url;
    } else {
      window.open(url, "_blank"); // the browser refused the early tab; try now
    }
    setTimeout(() => window.URL.revokeObjectURL(url), 60000);
  } catch (err) {
    tab?.close(); // don't leave an empty tab behind
    throw err;
  }
}
