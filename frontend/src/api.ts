const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function handleUnauthorized() {
  localStorage.removeItem("intelliflow_token");
  window.dispatchEvent(new Event("intelliflow:unauthorized"));
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("intelliflow_token");
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (Array.isArray(body.detail)) {
        detail = body.detail
          .map((issue: { loc?: unknown; msg?: unknown }) => {
            const message = typeof issue.msg === "string" ? issue.msg : "";
            const location = Array.isArray(issue.loc)
              ? issue.loc
                  .filter((part): part is string | number => typeof part === "string" || typeof part === "number")
                  .slice(1)
                  .join(".")
              : "";
            return message && location ? `${location}: ${message}` : message;
          })
          .filter(Boolean)
          .join("; ") || detail;
      }
    } catch {}
    if (response.status === 401 && !path.startsWith("/api/auth/")) {
      handleUnauthorized();
    }
    throw new Error(detail);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

