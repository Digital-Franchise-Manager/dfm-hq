# DFM TypeScript Monorepo Foundation

## Objective

Establish a shared TypeScript workspace for the Digital Franchise Manager platform while preserving the existing application until each replacement module passes regression testing.

## Workspace boundaries

- `apps/web`: React and Vite browser application.
- `packages/contracts`: shared domain contracts and DTO types.
- `packages/platform-core`: shared identity, franchise, league and platform-level contracts.
- `packages/fantasy-engine`: sport-neutral scoring, ranking and competition primitives.
- `packages/game-classic`: Classic game-mode rules and contracts.
- `packages/game-draft`: Draft game-mode rules and contracts.
- `packages/sport-drl`: Digital Rugby League domain contracts and sport-specific adapters.
- `supabase/migrations`: versioned database schema and security changes.
- `supabase/tests/database`: database security regression checks.

Authentication, user identity, franchise ownership and league identity remain shared platform concerns. Classic and Draft are separate game-mode modules and must not create duplicate users, franchises or leagues.

## Preservation rule

The existing `frontend/` and `backend/` trees are intentionally retained. No existing route, service, model, identity asset or API implementation is removed or redirected as part of this foundation. Port modules incrementally, with parity tests and an explicit cutover only after the replacement is verified.

## Runtime and package policy

- Node.js 26 LTS is the CI runtime; Node.js 22.12 or newer is required for local development.
- npm is pinned to 12.2.2.
- Direct dependencies are exact-version pinned in workspace manifests.
- The CI workflow generates a lockfile from those exact pins, publishes a short-lived backup artifact, installs from that lockfile, and commits it to the security branch only after typecheck, tests and build succeed.
- No paid services, hosted build products or paid dependencies are introduced.

## Database security sequence

1. `20261117194130_security_baseline_lockdown.sql` removes excess public grants, tightens default privileges and relocates the RLS event-trigger function.
2. `20261117194151_public_franchise_profiles_projection.sql` replaces the writable view with an RLS-protected, read-only public branding projection and a private synchronisation trigger.
3. Run `supabase/tests/database/security_baseline.sql` after migration changes.
4. Run Supabase security advisors after every database security change.

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
