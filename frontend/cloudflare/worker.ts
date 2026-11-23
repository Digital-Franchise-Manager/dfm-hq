interface Env {
  ASSETS: { fetch(request: Request): Promise<Response> };
  SUPABASE_URL: string;
  SUPABASE_ANON_KEY: string;
  SUPABASE_SERVICE_ROLE_KEY: string;
}
interface ProfileRow {
  drl_player_id: number; first_name: string; last_name: string;
  appearances: number | null; tries: number | null; try_assists: number | null;
  points: number | null; tackles: number | null; tackle_efficiency: number | null;
  metres_gained: number | null; line_breaks: number | null; errors: number | null;
  penalties_conceded: number | null; storage_object_path: string | null; photo_alt: string | null;
  current_club_name: string | null; current_squad_id: number | null;
}
const json = (body: unknown, status = 200): Response => new Response(JSON.stringify(body), {
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
  try { return new URL(origin).origin === new URL(request.url).origin; }
  catch { return false; }
}
function isSafeStoragePath(path: string): boolean {
  const segments = path.split("/");
  return segments.length > 0 && segments.every((segment) =>
    segment.length > 0 && segment !== "." && segment !== ".." &&
    !segment.includes(String.fromCharCode(92)) && !/[\u0000-\u001f]/.test(segment)
  );
}
async function handlePlayerProfiles(request: Request, env: Env): Promise<Response> {
  if (request.method !== "GET") return json({ error: "Method not allowed" }, 405);
  if (!isSameOrigin(request)) return json({ error: "Forbidden" }, 403);
  const token = request.headers.get("Authorization")?.match(/^Bearer\s+(.+)$/i)?.[1];
  if (!token || token.length > 8192) return json({ error: "Unauthorized" }, 401);
  const supabaseUrl = env.SUPABASE_URL.replace(/\/$/, "");
  if (!/^https:\/\/[a-z0-9.-]+$/i.test(supabaseUrl) || !env.SUPABASE_ANON_KEY || !env.SUPABASE_SERVICE_ROLE_KEY) {
    return json({ error: "Player service unavailable" }, 503);
  }
  let authResponse: Response;
  try {
    authResponse = await fetch(supabaseUrl + "/auth/v1/user", {
      headers: { apikey: env.SUPABASE_ANON_KEY, Authorization: "Bearer " + token }
    });
  } catch { return json({ error: "Authentication service unavailable" }, 503); }
  if (!authResponse.ok) return json({ error: "Unauthorized" }, 401);
  const seasonValue = new URL(request.url).searchParams.get("season") ?? "2026";
  if (seasonValue !== "2026") return json({ error: "Season unavailable" }, 400);
  let dataResponse: Response;
  try {
    dataResponse = await fetch(supabaseUrl + "/rest/v1/rpc/drl_nrl_player_profiles_read", {
      method: "POST",
      headers: {
        apikey: env.SUPABASE_SERVICE_ROLE_KEY,
        Authorization: "Bearer " + env.SUPABASE_SERVICE_ROLE_KEY,
        "Content-Type": "application/json",
        Accept: "application/json"
      },
      body: JSON.stringify({ p_season: 2026 })
    });
  } catch { return json({ error: "Player service unavailable" }, 503); }
  if (!dataResponse.ok) return json({ error: "Player service unavailable" }, 503);
  const rows = await dataResponse.json() as ProfileRow[];
  if (!Array.isArray(rows) || rows.length > 1000) return json({ error: "Player service unavailable" }, 503);
  const players = await Promise.all(rows.map(async (row) => {
    let photoUrl: string | null = null;
    const storagePath = row.storage_object_path;
    if (storagePath && isSafeStoragePath(storagePath)) {
      const objectPath = storagePath.split("/").map(encodeURIComponent).join("/");
      try {
        const signedResponse = await fetch(
          supabaseUrl + "/storage/v1/object/sign/drl-player-media/" + objectPath,
          {
            method: "POST",
            headers: {
              apikey: env.SUPABASE_SERVICE_ROLE_KEY,
              Authorization: "Bearer " + env.SUPABASE_SERVICE_ROLE_KEY,
              "Content-Type": "application/json"
            },
            body: JSON.stringify({ expiresIn: 300 })
          }
        );
        if (signedResponse.ok) {
          const signed = await signedResponse.json() as { signedURL?: string };
          if (signed.signedURL?.startsWith("/storage/v1/")) photoUrl = supabaseUrl + signed.signedURL;
        }
      } catch { /* A missing media signature never blocks a player profile. */ }
    }
    return {
      drl_player_id: row.drl_player_id, first_name: row.first_name, last_name: row.last_name,
      team_name: row.current_club_name, position: row.primary_fantasy_position, photo_url: photoUrl,
      photo_alt: photoUrl ? row.photo_alt : null,
      photo_kind: photoUrl ? "verified_action_photo" : null,
      fantasy_points: row.fantasy_points,
      primary_fantasy_position: row.primary_fantasy_position,
      eligible_fantasy_positions: Array.isArray(row.eligible_fantasy_positions) ? row.eligible_fantasy_positions : [],
      stats: {
        appearances: row.appearances, tries: row.tries, try_assists: row.try_assists,
        points: row.points, tackles: row.tackles, tackle_efficiency: row.tackle_efficiency,
        metres_gained: row.metres_gained, line_breaks: row.line_breaks, errors: row.errors,
        penalties_conceded: row.penalties_conceded
      }
    };
  }));
  return json({ season: 2026, source_status: "connected", players });
}
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname === "/api/drl/nrl/players") return handlePlayerProfiles(request, env);
    if (url.pathname.startsWith("/api/")) return json({ error: "Not found" }, 404);
    return env.ASSETS.fetch(request);
  }
};
