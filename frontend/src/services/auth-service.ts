export interface DfmUser {
  id: string;
  email: string | null;
}

export interface DfmSession {
  authenticated: boolean;
  user?: DfmUser | null;
}

async function request<T>(path: string, body?: Record<string, string>): Promise<T> {
  const response = await fetch(path, {
    method: body ? "POST" : "GET",
    credentials: "same-origin",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined
  });
  const payload = await response.json().catch(() => ({})) as T & { error?: string };
  if (!response.ok) throw new Error(payload.error || "The request could not be completed.");
  return payload;
}

export const authService = {
  getSession: () => request<DfmSession>("/api/auth/session"),
  login: (email: string, password: string) =>
    request<{ authenticated: boolean }>("/api/auth/login", { email, password }),
  signup: (email: string, password: string) =>
    request<{ authenticated: boolean; confirmationRequired: boolean }>("/api/auth/signup", { email, password }),
  logout: () => request<{ authenticated: false }>("/api/auth/logout", {})
};
