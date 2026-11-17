# Digital Franchise Manager HQ

Digital Franchise Manager (DFM) is a multi-sport fantasy platform. Digital Rugby League (DRL) is the first sport domain.

## Repository structure

- `apps/web/` — React and Vite TypeScript application foundation.
- `packages/contracts/` — shared domain contracts and DTO types.
- `packages/platform-core/` — shared identity, franchise and league boundaries.
- `packages/fantasy-engine/` — sport-neutral fantasy engine primitives.
- `packages/game-classic/` — Classic game-mode rules.
- `packages/game-draft/` — Draft game-mode rules.
- `packages/sport-drl/` — Digital Rugby League domain.
- `supabase/migrations/` — versioned JARVIS database migrations.
- `supabase/tests/database/` — database security regression checks.

The existing `frontend/` and `backend/` directories are preserved during the transition. They are not removed or silently redirected by this foundation. Migration into the TypeScript workspace is incremental and requires regression checks before any cutover.

## Database security baseline

The P0 and P1 migrations lock down franchise privileges, move privileged database functions into a non-exposed schema, and expose franchise branding through a read-only projection. The exact SQL is stored under `supabase/migrations/`.

Run the database checks as the database owner in the Supabase SQL Editor after migration changes:

- `supabase/tests/database/security_baseline.sql` — privilege, RLS and private-schema assertions.
- `supabase/tests/database/rls_auto_enable.sql` — verifies automatic RLS enforcement and default grants for newly created public tables.
- `supabase/tests/database/franchise_projection_trigger.sql` — rollback-safe insert, update and cascade-delete test for the branding projection.

## Development

Requirements: Node.js 24 LTS (Node.js 22.17 or newer is accepted by the package engine) and npm 12.2.2.

```sh
npm install
npm run dev
npm run typecheck
npm test
npm run build
npm run check
```

The exact `package-lock.json` is committed. CI uses `npm ci` against that lockfile and runs typecheck, unit tests and the production build.

## Security rules

- Never commit database passwords, service-role keys, secret API keys or access tokens.
- Browser code may use only a publishable key; privileged operations belong on trusted server-side code.
- Keep private database schemas outside the exposed Data API schemas.
- Enforce ownership and authorization in PostgreSQL RLS, not in client-supplied identifiers.
- Do not assume API URLs can be hidden from browser users; secure every operation through authentication, authorization and least-privilege grants.
- Maintain the project's $0 AUD operating constraint.
