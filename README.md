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

Run the security regression script after database changes:

```sql
supabase/tests/database/security_baseline.sql
```

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

CI resolves and validates a lockfile, uploads a short-lived backup artifact, and commits the exact generated `package-lock.json` to the security branch after typecheck, tests and build pass.

## Security rules

- Never commit database passwords, service-role keys, secret API keys or access tokens.
- Browser code may use only a publishable key; privileged operations belong on trusted server-side code.
- Keep private database schemas outside the exposed Data API schemas.
- Enforce ownership and authorization in PostgreSQL RLS, not in client-supplied identifiers.
- Do not assume API URLs can be hidden from browser users; secure every operation through authentication, authorization and least-privilege grants.
- Maintain the project's $0 AUD operating constraint.
