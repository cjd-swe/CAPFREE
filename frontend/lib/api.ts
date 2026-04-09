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
