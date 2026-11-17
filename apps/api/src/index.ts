/**
 * Backend request-handler foundation.
 *
 * The supplied authenticate callback MUST validate the actual Supabase JWT
 * and resolve the principal from verified claims. Never trust client-supplied
 * user IDs or user_metadata for authorization.
 *
 * This scaffold has no application routes and is not deployed.
 */
export interface AuthenticatedPrincipal {
  userId: string;
}

export type AuthenticateRequest = (
  request: Request
) => Promise<AuthenticatedPrincipal | null>;

export function createAuthenticatedApiHandler(
  authenticate: AuthenticateRequest
): (request: Request) => Promise<Response> {
  return async (request: Request): Promise<Response> => {
    let principal: AuthenticatedPrincipal | null = null;

    try {
      principal = await authenticate(request);
    } catch {
      principal = null;
    }

    if (!principal?.userId) {
      return new Response(
        JSON.stringify({ error: "Unauthorized" }),
        {
          status: 401,
          headers: {
            "Content-Type": "application/json",
            "Cache-Control": "no-store"
          }
        }
      );
    }

    return new Response(
      JSON.stringify({ error: "No application routes are enabled." }),
      {
        status: 501,
        headers: {
          "Content-Type": "application/json",
          "Cache-Control": "no-store"
        }
      }
    );
  };
}
