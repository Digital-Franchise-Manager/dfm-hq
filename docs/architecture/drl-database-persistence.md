# DRL database persistence boundary

## Scope

This document defines the database shape corresponding to the independent DRL
Classic and Draft engine models. It is a persistence-schema preparation stage,
not a claim that the engines are already connected to JARVIS.

The SQL design is held in `supabase/drafts/drl_mode_persistence.sql`. It is not
registered as a Supabase migration because the repository's migration history
does not currently reconcile with the live project's applied migration list.

## Mode-specific persistence map

| Capability | Classic tables | Draft tables |
|---|---|---|
| Odds calculation snapshots | `drl_classic_odds_market_snapshots` | `drl_draft_odds_market_snapshots` |
| Odds outcomes | `drl_classic_odds_market_outcomes` | `drl_draft_odds_market_outcomes` |
| Price movement history | `drl_classic_odds_price_movements` | `drl_draft_odds_price_movements` |
| Award events | `drl_classic_award_records` | `drl_draft_award_records` |
| Coach award credits | `drl_classic_coach_award_credits` | `drl_draft_coach_award_credits` |
| Newsroom | `drl_classic_news_articles` | `drl_draft_news_articles` |
| Ladder source results | `drl_classic_ladder_match_results` | `drl_draft_ladder_match_results` |

All tables are proposed for the existing non-exposed `dfm_private` schema.
No Classic table references a Draft table, and no Draft table references a
Classic table.

## Model alignment

- Odds snapshots preserve market identity, market type, source provenance,
  verification state, model version and calculation revision.
- Outcomes preserve selection ID, label, probability and fair decimal price.
- Price movements preserve previous/revised probabilities and prices, revision,
  source ID, model version and the engine-generated idempotency key.
- Award events preserve the deterministic award ID, category, round, player,
  franchise, coach-at-award-time, base score, points, position and
  achievement-only status.
- Coach credits preserve the coach and franchise that held the player when the
  award was earned. Transfers do not rewrite prior credits. Database triggers
  reject updates/deletes to award and coach-credit history.
- Newsroom records preserve the engine's article ID, league, round, category,
  title, summary, content and publication state.
- Ladder source records preserve finalised fixture scores and the competition
  points already supplied to the Ladder Engine. W/L/D, PF, PA and PD remain
  derived values, not separately mutable facts. A trigger prevents changes to
  a result after it has been finalised.

## Verified live-schema boundaries

The live project currently has the two application tables
`public.franchises` and `public.franchise_public_profiles`. Both have RLS
enabled. There is no verified league, fixture, player or competition table in
the inspected application schema.

Accordingly:

- `league_id` and `fixture_id` remain text context identifiers with no
  invented foreign keys.
- Franchise and coach IDs are represented as UUIDs, consistent with the
  existing franchise and Auth identity types.
- Player IDs remain text until a canonical player identity schema is verified.
- Historical award and ladder rows do not cascade-delete when a franchise or
  account is deleted.

## Security boundary

- `dfm_private` is not included in the Data API schemas in
  `supabase/config.toml`.
- The proposed tables explicitly enable RLS.
- No `anon`, `authenticated` or `service_role` table grants or policies are
  created at this stage.
- No service-role key, database password or privileged endpoint is added to
  source code.
- A later authenticated server adapter must be designed and reviewed before
  access is granted. Direct client access is not part of this design.

## Outstanding integration work

1. Reconcile the missing repository copy of live migration
   `20261117024400_create_franchises_and_public_profiles`.
2. Generate the official migration filename using the installed Supabase CLI.
3. Validate the draft against a local Postgres/Supabase stack.
4. Review constraints and security tests.
5. Obtain separate approval before applying any migration to the hosted project.
6. Implement server-side repositories and authenticated API routes after the
   persistence schema is approved.
