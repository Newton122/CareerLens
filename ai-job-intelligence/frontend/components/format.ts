/** Shared formatting helpers for values the API may legitimately omit. */

/**
 * A match sub-score. `null` means the job posting never stated that
 * requirement, so it was excluded from the overall score — which is different
 * from a score of 0, meaning "asked for and not met".
 */
export type Score = number | null | undefined;

export const NOT_SPECIFIED = "Not specified";

export function formatScore(value: Score): string {
  return value === null || value === undefined ? NOT_SPECIFIED : `${value}%`;
}

/** Bar width for a score, treating "not specified" as empty. */
export function scoreWidth(value: Score): string {
  return value === null || value === undefined ? "0%" : `${value}%`;
}

export function isSpecified(value: Score): value is number {
  return value !== null && value !== undefined;
}

/** Format a salary figure the API returns as a plain integer. */
export function formatSalary(value: number | null | undefined): string | null {
  if (value === null || value === undefined) return null;
  return `$${value.toLocaleString()}`;
}

/**
 * Turn a FastAPI error body into a sentence.
 *
 * `detail` is a plain string for HTTPException, but Pydantic validation
 * failures (422) return an array of error objects. Rendering that array
 * directly produces "[object Object]", which tells the user nothing.
 */
export function describeApiError(data: unknown, fallback = "Something went wrong"): string {
  if (!data || typeof data !== "object") return fallback;

  const detail = (data as { detail?: unknown }).detail;
  if (typeof detail === "string" && detail.trim()) return detail;

  if (Array.isArray(detail)) {
    const messages = detail
      .map((entry) => {
        if (typeof entry === "string") return entry;
        const msg = (entry as { msg?: unknown }).msg;
        return typeof msg === "string" ? msg.replace(/^Value error,\s*/, "") : null;
      })
      .filter((m): m is string => Boolean(m));
    if (messages.length) return messages.join(". ");
  }

  return fallback;
}

/** Mirrors services/password_policy on the server, for instant feedback. */
export const PASSWORD_MIN_LENGTH = 10;

export function passwordHint(password: string): string | null {
  if (!password) return null;
  if (password.length < PASSWORD_MIN_LENGTH) {
    return `At least ${PASSWORD_MIN_LENGTH} characters (${password.length} so far)`;
  }
  if (new Set(password).size <= 2) {
    return "Too repetitive — vary the characters";
  }
  return null;
}
