interface WorkerEnv {
  ASSETS: { fetch(request: Request): Promise<Response> };
  SUPABASE_URL?: string;
  SUPABASE_ANON_KEY?: string;
}

const ACCESS_COOKIE = "dfm_session";
const REFRESH_COOKIE = "dfm_refresh";
const ACCESS_MAX_AGE = 60 * 60;
const REFRESH_MAX_AGE = 60 * 60 * 24 * 30;

function json(data: unknown, status = 200, headers: HeadersInit = {}): Response {
  const responseHeaders = new Headers(headers);
  responseHeaders.set("Content-Type", "application/json; charset=utf-8");
  responseHeaders.set("Cache-Control", "no-store");
  responseHeaders.set("X-Content-Type-Options", "nosniff");
  responseHeaders.set("Referrer-Policy", "same-origin");
  return new Response(JSON.stringify(data), { status, headers: responseHeaders });
}

function cookie(request: Request, name: string): string | null {
  const raw = request.headers.get("Cookie") ?? "";
  for (const part of raw.split(";")) {
    const [key, ...value] = part.trim().split("=");
    if (key === name) return value.join("=") || null;
  }
  return null;
}

function cookieHeader(name: string, value: string, maxAge: number): string {
  return `${name}=${value}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${maxAge}`;
}

function clearCookie(name: string): string {
  return `${name}=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0`;
}

function authConfig(env: WorkerEnv): { url: string; key: string } | null {
  const url = env.SUPABASE_URL?.replace(/\/$/, "");
  const key = env.SUPABASE_ANON_KEY;
  return url && key ? { url, key } : null;
}

async function authRequest(
  config: { url: string; key: string },
  path: string,
  method: string,
  body?: unknown,
  accessToken?: string
): Promise<Response> {
  const headers = new Headers({
    apikey: config.key,
    "Content-Type": "application/json"
  });
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  const init: RequestInit = { method, headers };
  if (body !== undefined) init.body = JSON.stringify(body);
  return fetch(`${config.url}/auth/v1/${path}`, init);
}

function safeAuthError(payload: Record<string, unknown>, status: number): Response {
  const message = typeof payload.msg === "string" ? payload.msg
    : typeof payload.message === "string" ? payload.message
    : typeof payload.error_description === "string" ? payload.error_description
    : status === 429 ? "Too many attempts. Please try again shortly."
    : "Authentication could not be completed.";
  return json({ error: message }, status);
}

async function handleAuth(request: Request, env: WorkerEnv): Promise<Response> {
  const config = authConfig(env);
  if (!config) return json({ error: "Authentication service is not configured." }, 503);

  const url = new URL(request.url);
  if (request.method === "POST" && url.pathname === "/api/auth/signup") {
    const body = await request.json().catch(() => null) as { email?: string; password?: string } | null;
    if (!body || typeof body.email !== "string" || typeof body.password !== "string" ||
        !body.email.trim() || body.password.length < 8) {
      return json({ error: "Enter a valid email address and a password of at least 8 characters." }, 400);
    }
    const response = await authRequest(config, "signup", "POST", {
      email: body.email.trim().toLowerCase(),
      password: body.password
    });
    const payload = await response.json().catch(() => ({})) as Record<string, unknown>;
    if (!response.ok) return safeAuthError(payload, response.status);
    const session = payload.access_token && payload.refresh_token;
    const headers = new Headers();
    if (session) {
      headers.append("Set-Cookie", cookieHeader(ACCESS_COOKIE, String(payload.access_token), ACCESS_MAX_AGE));
      headers.append("Set-Cookie", cookieHeader(REFRESH_COOKIE, String(payload.refresh_token), REFRESH_MAX_AGE));
    }
    return json({ authenticated: Boolean(session), confirmationRequired: !session }, 200, headers);
  }

  if (request.method === "POST" && url.pathname === "/api/auth/login") {
    const body = await request.json().catch(() => null) as { email?: string; password?: string } | null;
    if (!body || typeof body.email !== "string" || typeof body.password !== "string" ||
        !body.email.trim() || !body.password) {
      return json({ error: "Enter your email address and password." }, 400);
    }
    const response = await authRequest(config, "token?grant_type=password", "POST", {
      email: body.email.trim().toLowerCase(),
      password: body.password
    });
    const payload = await response.json().catch(() => ({})) as Record<string, unknown>;
    if (!response.ok) return safeAuthError(payload, response.status);
    if (typeof payload.access_token !== "string" || typeof payload.refresh_token !== "string") {
      return json({ error: "The authentication service returned an incomplete session." }, 502);
    }
    const headers = new Headers();
    headers.append("Set-Cookie", cookieHeader(ACCESS_COOKIE, payload.access_token, ACCESS_MAX_AGE));
    headers.append("Set-Cookie", cookieHeader(REFRESH_COOKIE, payload.refresh_token, REFRESH_MAX_AGE));
    return json({ authenticated: true }, 200, headers);
  }

  if (request.method === "POST" && url.pathname === "/api/auth/logout") {
    const access = cookie(request, ACCESS_COOKIE);
    if (access) await authRequest(config, "logout", "POST", undefined, access).catch(() => undefined);
    const headers = new Headers();
    headers.append("Set-Cookie", clearCookie(ACCESS_COOKIE));
    headers.append("Set-Cookie", clearCookie(REFRESH_COOKIE));
    return json({ authenticated: false }, 200, headers);
  }

  if (request.method === "GET" && url.pathname === "/api/auth/session") {
    const access = cookie(request, ACCESS_COOKIE);
    if (!access) return json({ authenticated: false }, 200);
    const response = await authRequest(config, "user", "GET", undefined, access);
    if (response.ok) {
      const user = await response.json().catch(() => null);
      return json({ authenticated: true, user: user && typeof user === "object" ? {
        id: (user as Record<string, unknown>).id,
        email: (user as Record<string, unknown>).email
      } : null });
    }

    const refresh = cookie(request, REFRESH_COOKIE);
    if (refresh && (response.status === 401 || response.status === 403)) {
      const refreshed = await authRequest(config, "token?grant_type=refresh_token", "POST", {
        refresh_token: refresh
      });
      const payload = await refreshed.json().catch(() => ({})) as Record<string, unknown>;
      if (refreshed.ok && typeof payload.access_token === "string" && typeof payload.refresh_token === "string") {
        const headers = new Headers();
        headers.append("Set-Cookie", cookieHeader(ACCESS_COOKIE, payload.access_token, ACCESS_MAX_AGE));
        headers.append("Set-Cookie", cookieHeader(REFRESH_COOKIE, payload.refresh_token, REFRESH_MAX_AGE));
        const user = payload.user as Record<string, unknown> | undefined;
        return json({ authenticated: true, user: user ? { id: user.id, email: user.email } : null }, 200, headers);
      }
    }
    const headers = new Headers();
    headers.append("Set-Cookie", clearCookie(ACCESS_COOKIE));
    headers.append("Set-Cookie", clearCookie(REFRESH_COOKIE));
    return json({ authenticated: false }, 200, headers);
  }

  return json({ error: "Not found." }, 404);
}

export default {
  async fetch(request: Request, env: WorkerEnv): Promise<Response> {
    const url = new URL(request.url);
    if (request.method === "POST") {
      const origin = request.headers.get("Origin");
      if (origin) {
        try {
          if (new URL(origin).origin !== url.origin) return json({ error: "Cross-origin request rejected." }, 403);
        } catch {
          return json({ error: "Invalid request origin." }, 403);
        }
      }
    }
    if (url.pathname.startsWith("/api/")) {
      if (request.method !== "GET" && request.method !== "POST") {
        return json({ error: "Method not allowed." }, 405, { Allow: "GET, POST" });
      }
      return handleAuth(request, env);
    }
    return env.ASSETS.fetch(request);
  }
};
