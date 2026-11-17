import { describe, expect, it } from "vitest";
import { createAuthenticatedApiHandler } from "../../apps/api/src/index";

describe("authenticated API foundation", () => {
  it("rejects requests when the JWT authenticator returns no principal", async () => {
    const handler = createAuthenticatedApiHandler(async () => null);
    const response = await handler(new Request("https://dfm.invalid/api"));

    expect(response.status).toBe(401);
    expect(await response.json()).toEqual({ error: "Unauthorized" });
  });

  it("does not expose an application route before one is implemented", async () => {
    const handler = createAuthenticatedApiHandler(async () => ({
      userId: "synthetic-test-user"
    }));
    const response = await handler(new Request("https://dfm.invalid/api"));

    expect(response.status).toBe(501);
    expect(await response.json()).toEqual({
      error: "No application routes are enabled."
    });
  });
});
