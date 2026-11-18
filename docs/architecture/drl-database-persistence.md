# DRL persistence reconciliation

## Reconciliation result

The live JARVIS project was re-inspected on 2026-11-18 (PostgreSQL 17.12).
Its application schema still contains only \`public.franchises\` and
\`public.franchise_public_profiles\`; both have RLS enabled. The live migration
history contains three applied migrations:
- \`20261117024400_create_franchises_and_public_profiles\`
- \`20261117194130_security_baseline_lockdown\`
- \`20261117194151_public_franchise_profiles_projection\`

No league, fixture, player, Classic or Draft persistence tables are present.
The latest Supabase security and performance advisor checks returned no lints.
The \`dfm_private\` schema has no USAGE or CREATE privilege for anon,
authenticated or service_role. No live database objects were changed during
this reconciliation.

## Engine contract alignment

The adapter accepts league/fixture context as explicit arguments because the
current Python engine value objects do not contain those identifiers in every
write model. It preserves:
- Market mode, type, market ID, source verification, model version, outcome
  probabilities/fair prices, revision and movement idempotency key.
- Award ID/category/round, player identity, franchise and coach-at-award-time,
  base score, points, position and achievement-only flag.
- Coach credit events using the coach/franchise ownership captured at award time.
- Newsroom article ID, mode, league, round, category, content and publication flag.
- Ladder scores and the competition points already calculated by the relevant
  mode's Ladder Engine. The database does not recalculate engine rules.

## Persistence and security design

The 14 Classic/Draft tables remain in the non-exposed \`dfm_private\` schema.
No API role receives direct schema USAGE or table privileges. RLS remains
enabled as defence in depth.

PostgREST cannot call functions in a schema that is not exposed. The server
adapter therefore calls twenty narrowly scoped \`public.dfm_*_persist_*\` RPC
wrappers. Each wrapper:
- Is SECURITY DEFINER with an empty search_path and fully qualified private call.
- Has EXECUTE revoked from PUBLIC, anon and authenticated.
- Grants EXECUTE only to service_role.
- Does not grant service_role direct access to \`dfm_private\` or its tables.

The service-role client must be constructed only in a trusted server runtime
using a runtime secret. The credential must never enter browser code, Git,
logs, error responses or client-visible environment variables.

Because `service_role` bypasses RLS, the adapter is an internal persistence
service, not an authorization layer. No user-facing route is added in this
change. Before a route can call it, the API must validate the Supabase JWT and
verify the caller's league/franchise membership using a canonical membership
model. The live schema currently has no league or membership tables, so that
authorization layer remains intentionally unimplemented rather than guessed.

Each RPC is one PostgreSQL transaction:
- Market snapshot, outcomes and price movements commit together.
- Award records and award-time coach-credit events commit together.
- Newsroom append is idempotent.
- Finalised ladder results are immutable and idempotent.
- Conflicting replays with the same identity but different payload are rejected.

History triggers protect odds snapshots/outcomes/movements, award records,
coach credits and newsroom articles from UPDATE/DELETE. Finalised ladder
results reject UPDATE/DELETE. Classic and Draft have separate table families
and separate RPC entry points; the caller cannot choose the mode dynamically.

## Corrected implementation files

- \`supabase/drafts/drl_mode_persistence.sql\` — private schema tables and
  immutable history triggers.
- \`supabase/drafts/drl_mode_persistence_rpc.sql\` — trusted transactional RPCs.
- \`apps/api/src/drl-persistence.ts\` — server-side adapter with no embedded
  credentials or browser dependency.
- \`apps/api/src/drl-persistence.test.ts\` — adapter contract and mode-routing tests.
- \`supabase/tests/database/drl_mode_persistence.sql\` — read-only security checks.
- \`supabase/tests/database/drl_mode_persistence_integration.sql\` — disposable
  database integration tests, transaction rollback included.

## Validation status and limitations

- Live schema, migrations, schema grants, and advisors were checked read-only.
- PR #4 model files and PR #5 persistence draft were inspected.
- Adapter unit tests are authored but have not yet been run in CI.
- SQL is statically reconciled but has not been executed against local Postgres.
- The official timestamped migration has not been generated because the
  Supabase CLI is not available in this environment. Do not invent a migration
  filename; generate it with \`supabase migration new drl_mode_persistence\`
  after SQL validation.
- No hosted migration, Edge Function deployment, Cloudflare change, PR merge or
  production data mutation was performed.
