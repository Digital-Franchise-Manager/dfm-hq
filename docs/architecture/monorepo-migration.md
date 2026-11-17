# DFM TypeScript Monorepo Foundation

## Objective

Establish a shared TypeScript workspace for the Digital Franchise Manager platform while preserving the existing application until each replacement module passes regression testing.

## Workspace boundaries

- `apps/web`: React and Vite browser application.
- `apps/api`: authenticated TypeScript request-handler boundary. The scaffold requires an injected JWT authenticator and intentionally returns no application routes; it is not deployed.
- `packages/contracts`: shared domain contracts and DTO types.
- `packages/platform-core`: shared identity, franchise, league and platform-level contracts.
- `backend/dfm/drl/classic/core`: Classic-specific backend logic.
- `backend/dfm/drl/classic/packages`: Classic TypeScript package boundary.
- `backend/dfm/drl/classic/manifest.json`: Classic module registration and configuration.
- `backend/dfm/drl/draft/core`: Draft-specific backend logic and integrations.
- `backend/dfm/drl/draft/packages`: Draft TypeScript package boundary.
- `backend/dfm/drl/draft/manifest.json`: Draft module registration and configuration.
- `backend/dfm/drl/core`: shared DRL backend functionality.
- `backend/dfm/drl/packages`: shared DRL-specific packages, including `@dfm/sport-drl` and the Rugby League fantasy engine.
- `backend/dfm/drl/packages/fantasy-engine`: Rugby League scoring, ranking and competition primitives.
- `backend/dfm/assets/drl`: DRL identity and sport assets.

The DRL-specific npm workspaces are discovered from the `packages/` directories inside Classic, Draft and the shared DRL domain. The Fantasy Engine is Rugby League-specific and therefore resides within the DRL domain. Only genuinely sport-neutral contracts and platform services remain in the root `packages/` directory.

Authentication, user identity, franchise ownership and league identity remain shared platform concerns. Classic and Draft are separate game-mode modules and must not create duplicate users, franchises or leagues.

## API security boundary

The API handler accepts an injected authentication function. A production adapter must validate the Supabase JWT and derive the principal from verified claims; never trust a client-supplied user ID or user-editable metadata. No application route is enabled and no API function is deployed by this foundation.

## Preservation rule

The existing `frontend/` and `backend/` trees are intentionally retained. No existing route, service, model, identity asset or API implementation is removed or redirected as part of this foundation. Port modules incrementally, with parity tests and an explicit cutover only after the replacement is verified.

## Runtime and package policy

- Node.js 26 LTS is the CI runtime; Node.js 22.12 or newer is required for local development.
- npm is pinned to 12.2.2.
- Direct dependencies are exact-version pinned in workspace manifests.
- The exact `package-lock.json` is committed. CI installs with `npm ci` against the committed lockfile.
- No paid services, hosted build products or paid dependencies are introduced.

## Database security sequence

1. `20261117194130_security_baseline_lockdown.sql` removes excess public grants, tightens default privileges and relocates the RLS event-trigger function.
2. `20261117194151_public_franchise_profiles_projection.sql` replaces the writable view with an RLS-protected, read-only public branding projection and a private synchronisation trigger.
3. Run `supabase/tests/database/security_baseline.sql` after migration changes.
4. Run `supabase/tests/database/rls_auto_enable.sql` to verify the relocated event trigger and future default grants. Its temporary table is rolled back.
5. Run `supabase/tests/database/franchise_projection_trigger.sql` to verify projection insert/update synchronisation and cascade deletion. Its synthetic account and franchise are rolled back.
6. Run Supabase security advisors after every database security change.

The private `dfm_private` schema is deliberately excluded from the Data API schemas in `supabase/config.toml`.

## Development commands

```sh
npm install
npm run dev
npm run typecheck
npm test
npm run build
npm run check
```

Do not place service-role keys, database passwords, private tokens or privileged endpoint configuration in browser code, committed environment files or build output. Only a publishable key may be used in the browser, and only after the application's authentication and RLS controls are implemented.
