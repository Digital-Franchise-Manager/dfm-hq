interface Env {
  ASSETS: { fetch(request: Request): Promise<Response> };
  SUPABASE_URL: string;
  SUPABASE_ANON_KEY: string;
  SUPABASE_SERVICE_ROLE_KEY: string;
}

interface ProfileRow {
  drl_player_id: number;
  first_name: string;
  last_name: string;
  appearances: number | null;
  tries: number | null;
  try_assists: number | null;
  points: number | null;
  tackles: number | null;
  tackle_efficiency: number | null;
  metres_gained: number | null;
  line_breaks: number | null;
  errors: number | null;
  penalties_conceded: number | null;
  storage_object_path: string | null;
  photo_alt: string | null;
}

const json = (body: unknown, status = 200): Response =>
  new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "private, no-store, max-age=0",
      "X-Content-Type-Options": "nosniff",
      "Referrer-Policy": "no-referrer",
      "Vary": "Authorization"
    }
  });

function isSameOrigin(request: Request): boolean {
  const origin = request.headers.get("Origin");
  if (!origin) return true;
  try {
    return new URL(origin).origin === new URL(request.url).origin;
  } catch {
    return false;
  }
}

async function handlePlayerProfiles(request: Request, env: Env): Promise<Response> {
  if (request.method !== "GET") {
    return json({ error: "Method not allowed" }, 405);
  }
  if (!isSameOrigin(request)) {
    return json({ error: "Forbidden" }, 403);
  }

  const token = request.headers.get("Authorization")?.match(/^Bearer\s+(.+)$/i)?.[1];
  if (!token || token.length > 8192) {
    return json({ error: "Unauthorized" }, 401);
  }

  const supabaseUrl = env.SUPABASE_URL.replace(/\/$/, "");
  if (!/^https:\/\/[a-z0-9.-]+$/i.test(supabaseUrl) ||
      !env.SUPABASE_ANON_KEY || !env.SUPABASE_SERVICE_ROLE_KEY) {
    return json({ error: "Player service unavailable" }, 503);
  }

  // Validate the bearer token with Supabase Auth; never trust decoded JWT claims.
  let authResponse: Response;
  try {
    authResponse = await fetch(`${supabaseUrl}/auth/v1/user`, {
      headers: {
        apikey: env.SUPABASE_ANON_KEY,
        Authorization: `Bearer ${token}`
      }
    });
  } catch {
    return json({ error: "Authentication service unavailable" }, 503);
  }
  if (!authResponse.ok) return json({ error: "Unauthorized" }, 401);

  const seasonValue = new URL(request.url).searchParams.get("season") ?? "2026";
  if (!/^20[0-9]{2}$/.test(seasonValue) || seasonValue !== "2026") {
    return json({ error: "Season unavailable" }, 400);
  }

  // This narrow RPC is executable only by service_role. Browser roles have no
  // privileges on the private schema or the RPC.
  let dataResponse: Response;
  try {
    dataResponse = await fetch(`${supabaseUrl}/rest/v1/rpc/drl_nrl_player_profiles_read`, {
      method: "POST",
      headers: {
        apikey: env.SUPABASE_SERVICE_ROLE_KEY,
        Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
        "Content-Type": "application/json",
        Accept: "application/json"
      },
      body: JSON.stringify({ p_season: Number(seasonValue) })
    });
  } catch {
    return json({ error: "Player service unavailable" }, 503);
  }
  if (!dataResponse.ok) return json({ error: "Player service unavailable" }, 503);

  const rows = await dataResponse.json() as ProfileRow[];
  if (!Array.isArray(rows) || rows.length > 1000) {
    return json({ error: "Player service unavailable" }, 503);
  }

  const players = await Promise.all(rows.map(async (row) => {
    let photoUrl: string | null = null;
    if (row.storage_object_path) {
      const objectPath = row.storage_object_path.split("/").map(encodeURIComponent).join("/");
      try {
        const signedResponse = await fetch(
          `${supabaseUrl}/storage/v1/object/sign/drl-player-media/${objectPath}`,
          {
            method: "POST",
            headers: {
              apikey: env.SUPABASE_SERVICE_ROLE_KEY,
              Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
              "Content-Type": "application/json"
            },
            body: JSON.stringify({ expiresIn: 300 })
          }
        );
        if (signedResponse.ok) {
          const signed = await signedResponse.json() as { signedURL?: string };
          if (signed.signedURL && signed.signedURL.startsWith("/storage/v1/")) {
            photoUrl = `${supabaseUrl}${signed.signedURL}`;
          }
        }
      } catch {
        // A missing/failed media signature does not prevent the player profile.
      }
    }

    return {
      drl_player_id: row.drl_player_id,
      first_name: row.first_name,
      last_name: row.last_name,
      team_name: null,
      position: null,
      photo_url: photoUrl,
      photo_alt: photoUrl ? row.photo_alt : null,
      stats: {
        appearances: row.appearances,
        tries: row.tries,
        try_assists: row.try_assists,
        points: row.points,
        tackles: row.tackles,
        tackle_efficiency: row.tackle_efficiency,
        metres_gained: row.metres_gained,
        line_breaks: row.line_breaks,
        errors: row.errors,
        penalties_conceded: row.penalties_conceded
      }
    };
  }));

  return json({ season: Number(seasonValue), source_status: "connected", players });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname === "/api/drl/nrl/players") {
      return handlePlayerProfiles(request, env);
    }
    if (url.pathname.startsWith("/api/")) {
      return json({ error: "Not found" }, 404);
    }
    return env.ASSETS.fetch(request);
  }
};
