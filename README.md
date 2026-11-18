# Digital Franchise Manager HQ

Digital Franchise Manager (DFM) is a multi-sport fantasy platform. Digital Rugby League (DRL) is the first sport domain.

## Repository structure

- `apps/web/` — React and Vite TypeScript application foundation.
- `apps/api/` — authenticated TypeScript request-handler foundation; no application routes are enabled or deployed.
- `packages/contracts/` — shared domain contracts and DTO types.
- `packages/platform-core/` — shared identity, franchise and league boundaries.
- `backend/dfm/drl/classic/core/` — independent Classic Odds, Awards, Newsroom and Ladder engines.
- `backend/dfm/drl/draft/core/` — independent Draft Odds, Awards, Newsroom and Ladder engines.
- `backend/dfm/drl/classic/packages/` and `backend/dfm/drl/draft/packages/` — mode-specific TypeScript package boundaries.
- `backend/dfm/drl/core/` — shared DRL foundations only; no Classic or Draft competition engines.
- `backend/dfm/drl/packages/` — DRL sport-specific packages, including the Rugby League fantasy engine.
- `supabase/migrations/` — versioned JARVIS database migrations.

Classic and Draft engine implementations, calculations, histories, publication feeds and standings are deliberately isolated. Neither mode imports or reads the other's engine package.

## Database security

Any future engine persistence adapter must use verified live schema, least-privilege grants and Row Level Security. This engine foundation does not invent database tables or apply migrations. Never commit credentials, service-role keys, tokens or private user data. Browser code may use only publishable keys; privileged operations belong server-side. Maintain the $0 AUD operating constraint.

## Development

Requirements: Node.js 24 LTS (Node.js 22.17 or newer is accepted by the package engine), npm 12.2.2 and Python 3.12 for DRL tests.

```sh
npm install
npm run dev
npm run typecheck
npm test
npm run build
npm run check
python -m unittest discover -s backend/dfm/drl/tests -t . -p "test_*.py"
```
