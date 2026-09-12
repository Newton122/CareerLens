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
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
      ...options.headers,
    },
  });
  return response;
}

export async function viewFile(endpoint: string): Promise<void> {
  const response = await apiCall(endpoint);
  if (!response.ok) {
    throw new Error("Failed to load file");
  }
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  window.open(url, "_blank");
  setTimeout(() => window.URL.revokeObjectURL(url), 60000);
}
