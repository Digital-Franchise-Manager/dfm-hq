# DRL persistence migration draft

**Status: DRAFT ONLY — not an executable or registered Supabase migration.**

The schema design is prepared from the current Classic and Draft engine models on
`feature/drl-independent-odds-engine`. The SQL is stored here so it cannot be
picked up accidentally by Supabase migration commands.

## Why this is not under `supabase/migrations/` yet

The live Supabase project reports these applied migration versions:

- `20261117024400` — `create_franchises_and_public_profiles`
- `20261117194130` — `security_baseline_lockdown`
- `20261117194151` — `public_franchise_profiles_projection`

The GitHub repository contains the latter two SQL files, but the first migration
file could not be found in the inspected repository branch. That is migration
history drift. Do not create a new official migration until the missing baseline
is recovered or the discrepancy is reconciled.

The Supabase CLI is not available in the current execution environment. The
official migration filename must be generated with the CLI, not guessed:

```sh
supabase migration new drl_mode_persistence
```

Then copy the reviewed SQL from `supabase/drafts/drl_mode_persistence.sql`
into the generated file. Review the diff and validate locally before any hosted
migration is considered. No hosted migration has been applied.

## Design decisions

- Classic and Draft persistence are separate table families in the existing
  private `dfm_private` schema.
- The schema remains outside the Data API schemas in `supabase/config.toml`.
- All 14 tables explicitly enable RLS.
- No API-role grants or RLS policies are created. The tables remain inaccessible
  to `anon`, `authenticated` and `service_role` until a separately reviewed
  server-side access design is implemented.
- `league_id` and `fixture_id` are text identifiers because the live database
  currently has no verified league or fixture tables. No guessed foreign keys
  are added.
- Franchise identifiers are stored as UUID values, matching the verified
  `public.franchises.id` type. Coach identifiers remain text until a canonical
  coach identity schema is verified. Historical
  references intentionally do not cascade-delete with an account or franchise.
- Player identifiers remain text because the current engine contracts do not
  define a verified player identity table.
- Ladder standings are derived from persisted finalised match results and award
  events; no redundant calculated leaderboard table is introduced.
- Classic and Draft award categories are constrained independently. Draft alone
  supports TOTW and TOTY.
- Price movement records include the engine's idempotency key and revision.
- Database triggers reject updates/deletes to odds snapshots, outcomes, price movements, award records and coach credits. Finalised ladder match results cannot be changed or deleted.

## Validation

After the official migration has been reviewed and applied in an explicitly
authorised environment, run:

```sh
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f supabase/tests/database/drl_mode_persistence.sql
```

The test checks table existence, RLS, API-role isolation and that DRL persistence
has not been placed in the exposed `public` schema.

This draft does not add adapters, API routes, public grants, credentials,
Cloudflare configuration or production data changes.
