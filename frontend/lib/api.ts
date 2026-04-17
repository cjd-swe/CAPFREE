// Base URL for the SharpWatch backend. Override in frontend/.env.local via
// NEXT_PUBLIC_API_URL (must be prefixed with NEXT_PUBLIC_ to be exposed to the
// browser). Default points at the local uvicorn server.
export const API_URL =
    process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000"

/** Build an API URL from a path like "/api/picks/" or "api/picks". */
export function apiUrl(path: string): string {
    const normalized = path.startsWith("/") ? path : `/${path}`
    return `${API_URL}${normalized}`
}

/** Fetch wrapper that includes credentials (auth cookie) automatically. */
export function apiFetch(path: string, init?: RequestInit): Promise<Response> {
    return fetch(apiUrl(path), { credentials: "include", ...init })
}

/**
 * Parse a date/datetime string returned by the backend into a Date.
 *
 * The backend emits naive datetimes (e.g. "2026-04-17T01:57:00") that represent
 * UTC but carry no timezone suffix. Native `new Date(...)` would interpret them
 * as *local* time, which silently skips the conversion and pushes upload times
 * into the next UTC day when displayed with toLocaleDateString. This helper
 * appends 'Z' when no timezone marker is present so the browser converts
 * correctly.
 *
 * Date-only strings ("YYYY-MM-DD") are already parsed as UTC midnight by the
 * ES spec, so they're passed through untouched.
 */
export function parseApiDate(s: string): Date {
    if (/Z$|[+-]\d\d:?\d\d$/.test(s)) return new Date(s)
    if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return new Date(s)
    return new Date(s + "Z")
}
