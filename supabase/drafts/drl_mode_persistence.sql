-- DRAFT ONLY — NOT A REGISTERED SUPABASE MIGRATION.
-- Do not apply this file directly. First reconcile the migration-history gap
-- documented in supabase/drafts/README.md, then generate the official file
-- with `supabase migration new drl_mode_persistence`.
--
-- This draft creates private, mode-separated persistence tables only.
-- It deliberately grants no access to anon, authenticated or service_role,
-- and does not expose either mode schema through the Supabase Data API.

BEGIN;

CREATE SCHEMA IF NOT EXISTS dfm_private AUTHORIZATION postgres;

REVOKE ALL ON SCHEMA dfm_private
FROM PUBLIC, anon, authenticated, service_role;

ALTER DEFAULT PRIVILEGES
FOR ROLE postgres IN SCHEMA dfm_private
REVOKE ALL PRIVILEGES ON TABLES
FROM PUBLIC, anon, authenticated, service_role;

ALTER DEFAULT PRIVILEGES
FOR ROLE postgres IN SCHEMA dfm_private
REVOKE ALL PRIVILEGES ON SEQUENCES
FROM PUBLIC, anon, authenticated, service_role;

ALTER DEFAULT PRIVILEGES
FOR ROLE postgres IN SCHEMA dfm_private
REVOKE EXECUTE ON FUNCTIONS
FROM PUBLIC, anon, authenticated, service_role;

-- ---------------------------------------------------------------------------
-- CLASSIC: odds snapshots, outcomes and append-only price movement history.
-- ---------------------------------------------------------------------------

CREATE TABLE dfm_private.drl_classic_odds_market_snapshots (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  league_id text NOT NULL,
  market_id text NOT NULL,
  market_type text NOT NULL CHECK (market_type IN (
    'head_to_head',
    'premiership',
    'finals_qualification',
    'grand_final_qualification',
    'play_of_the_week',
    'man_of_the_match',
    'man_of_the_round',
    'player_of_the_year',
    'coach_of_the_year'
  )),
  revision integer NOT NULL DEFAULT 1 CHECK (revision >= 1),
  source_id text NOT NULL,
  source_category text NOT NULL,
  source_verified boolean NOT NULL,
  source_summary text NOT NULL,
  model_version text NOT NULL,
  official boolean NOT NULL,
  calculated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT drl_classic_odds_source_status_ck
    CHECK (official = source_verified),
  CONSTRAINT drl_classic_odds_snapshot_revision_uq
    UNIQUE (league_id, market_id, revision)
);

CREATE TABLE dfm_private.drl_classic_odds_market_outcomes (
  market_snapshot_id uuid NOT NULL
    REFERENCES dfm_private.drl_classic_odds_market_snapshots(id)
    ON DELETE CASCADE,
  selection_id text NOT NULL,
  label text NOT NULL,
  probability numeric(16,12) NOT NULL
    CHECK (probability > 0 AND probability < 1),
  decimal_price numeric(18,4) NOT NULL
    CHECK (decimal_price >= 1),
  PRIMARY KEY (market_snapshot_id, selection_id)
);

CREATE TABLE dfm_private.drl_classic_odds_price_movements (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  league_id text NOT NULL,
  market_id text NOT NULL,
  selection_id text NOT NULL,
  revision integer NOT NULL CHECK (revision >= 2),
  previous_probability numeric(16,12) NOT NULL
    CHECK (previous_probability > 0 AND previous_probability < 1),
  revised_probability numeric(16,12) NOT NULL
    CHECK (revised_probability > 0 AND revised_probability < 1),
  previous_price numeric(18,4) NOT NULL CHECK (previous_price >= 1),
  revised_price numeric(18,4) NOT NULL CHECK (revised_price >= 1),
  source_id text NOT NULL,
  model_version text NOT NULL,
  idempotency_key text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT drl_classic_odds_movement_idempotency_uq
    UNIQUE (league_id, idempotency_key),
  CONSTRAINT drl_classic_odds_movement_revision_uq
    UNIQUE (league_id, market_id, selection_id, revision)
);

CREATE INDEX drl_classic_odds_snapshots_market_idx
  ON dfm_private.drl_classic_odds_market_snapshots
  (league_id, market_id, revision DESC);

CREATE INDEX drl_classic_odds_movements_market_idx
  ON dfm_private.drl_classic_odds_price_movements
  (league_id, market_id, revision DESC);

-- ---------------------------------------------------------------------------
-- CLASSIC: award events and immutable coach credits at award time.
-- ---------------------------------------------------------------------------

CREATE TABLE dfm_private.drl_classic_award_records (
  league_id text NOT NULL,
  award_id text NOT NULL,
  category text NOT NULL CHECK (category IN (
    'man_of_the_match',
    'man_of_the_round',
    'play_of_the_week',
    'player_of_the_year',
    'coach_of_the_year'
  )),
  round_number integer NOT NULL CHECK (round_number >= 1),
  player_id text NOT NULL,
  player_name text NOT NULL,
  franchise_id uuid NOT NULL,
  coach_id uuid NOT NULL,
  base_score numeric(18,6) NOT NULL CHECK (base_score >= 0),
  points integer NOT NULL CHECK (points >= 0),
  position text CHECK (position IS NULL OR position IN (
    'WFB', 'CTR', 'HLF', 'EDG', 'MID', 'HOK'
  )),
  achievement_only boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (league_id, award_id),
  CONSTRAINT drl_classic_award_event_uq
    UNIQUE (league_id, round_number, category, player_id, franchise_id)
);

CREATE TABLE dfm_private.drl_classic_coach_award_credits (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  league_id text NOT NULL,
  coach_id uuid NOT NULL,
  franchise_id uuid NOT NULL,
  player_id text NOT NULL,
  category text NOT NULL CHECK (category IN (
    'man_of_the_match',
    'man_of_the_round',
    'play_of_the_week',
    'player_of_the_year',
    'coach_of_the_year'
  )),
  round_number integer NOT NULL CHECK (round_number >= 1),
  points integer NOT NULL CHECK (points > 0),
  credited_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT drl_classic_coach_credit_event_uq
    UNIQUE (league_id, coach_id, franchise_id, player_id, category, round_number)
);

CREATE INDEX drl_classic_awards_player_idx
  ON dfm_private.drl_classic_award_records
  (league_id, player_id, round_number);

CREATE INDEX drl_classic_awards_round_idx
  ON dfm_private.drl_classic_award_records
  (league_id, round_number, category);

CREATE INDEX drl_classic_coach_credits_ladder_idx
  ON dfm_private.drl_classic_coach_award_credits
  (league_id, coach_id, category);

-- ---------------------------------------------------------------------------
-- CLASSIC: newsroom articles and source fixture results for ladder derivation.
-- ---------------------------------------------------------------------------

CREATE TABLE dfm_private.drl_classic_news_articles (
  league_id text NOT NULL,
  article_id text NOT NULL,
  round_number integer NOT NULL CHECK (round_number >= 1),
  category text NOT NULL CHECK (category IN (
    'preview',
    'match_report',
    'round_awards',
    'odds_update',
    'injury',
    'transfer',
    'finals_race'
  )),
  title text NOT NULL,
  summary text NOT NULL,
  content text NOT NULL,
  published boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (league_id, article_id)
);

CREATE INDEX drl_classic_news_feed_idx
  ON dfm_private.drl_classic_news_articles
  (league_id, published, created_at DESC);

CREATE TABLE dfm_private.drl_classic_ladder_match_results (
  league_id text NOT NULL,
  fixture_id text NOT NULL,
  home_franchise_id uuid NOT NULL,
  away_franchise_id uuid NOT NULL,
  home_score numeric(18,6) NOT NULL
    CHECK (home_score >= 0 AND home_score < 'Infinity'::numeric),
  away_score numeric(18,6) NOT NULL
    CHECK (away_score >= 0 AND away_score < 'Infinity'::numeric),
  home_competition_points integer NOT NULL CHECK (home_competition_points >= 0),
  away_competition_points integer NOT NULL CHECK (away_competition_points >= 0),
  finalised boolean NOT NULL DEFAULT false,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (league_id, fixture_id),
  CONSTRAINT drl_classic_ladder_distinct_franchises_ck
    CHECK (home_franchise_id <> away_franchise_id)
);

CREATE INDEX drl_classic_ladder_results_league_idx
  ON dfm_private.drl_classic_ladder_match_results
  (league_id, finalised, fixture_id);

-- ---------------------------------------------------------------------------
-- DRAFT: independent odds snapshots, outcomes and price movement history.
-- ---------------------------------------------------------------------------

CREATE TABLE dfm_private.drl_draft_odds_market_snapshots (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  league_id text NOT NULL,
  market_id text NOT NULL,
  market_type text NOT NULL CHECK (market_type IN (
    'head_to_head',
    'premiership',
    'finals_qualification',
    'grand_final_qualification',
    'play_of_the_week',
    'man_of_the_match',
    'man_of_the_round',
    'player_of_the_year',
    'coach_of_the_year',
    'team_of_the_week',
    'team_of_the_year'
  )),
  revision integer NOT NULL DEFAULT 1 CHECK (revision >= 1),
  source_id text NOT NULL,
  source_category text NOT NULL,
  source_verified boolean NOT NULL,
  source_summary text NOT NULL,
  model_version text NOT NULL,
  official boolean NOT NULL,
  calculated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT drl_draft_odds_source_status_ck
    CHECK (official = source_verified),
  CONSTRAINT drl_draft_odds_snapshot_revision_uq
    UNIQUE (league_id, market_id, revision)
);

CREATE TABLE dfm_private.drl_draft_odds_market_outcomes (
  market_snapshot_id uuid NOT NULL
    REFERENCES dfm_private.drl_draft_odds_market_snapshots(id)
    ON DELETE CASCADE,
  selection_id text NOT NULL,
  label text NOT NULL,
  probability numeric(16,12) NOT NULL
    CHECK (probability > 0 AND probability < 1),
  decimal_price numeric(18,4) NOT NULL
    CHECK (decimal_price >= 1),
  PRIMARY KEY (market_snapshot_id, selection_id)
);

CREATE TABLE dfm_private.drl_draft_odds_price_movements (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  league_id text NOT NULL,
  market_id text NOT NULL,
  selection_id text NOT NULL,
  revision integer NOT NULL CHECK (revision >= 2),
  previous_probability numeric(16,12) NOT NULL
    CHECK (previous_probability > 0 AND previous_probability < 1),
  revised_probability numeric(16,12) NOT NULL
    CHECK (revised_probability > 0 AND revised_probability < 1),
  previous_price numeric(18,4) NOT NULL CHECK (previous_price >= 1),
  revised_price numeric(18,4) NOT NULL CHECK (revised_price >= 1),
  source_id text NOT NULL,
  model_version text NOT NULL,
  idempotency_key text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT drl_draft_odds_movement_idempotency_uq
    UNIQUE (league_id, idempotency_key),
  CONSTRAINT drl_draft_odds_movement_revision_uq
    UNIQUE (league_id, market_id, selection_id, revision)
);

CREATE INDEX drl_draft_odds_snapshots_market_idx
  ON dfm_private.drl_draft_odds_market_snapshots
  (league_id, market_id, revision DESC);

CREATE INDEX drl_draft_odds_movements_market_idx
  ON dfm_private.drl_draft_odds_price_movements
  (league_id, market_id, revision DESC);

-- ---------------------------------------------------------------------------
-- DRAFT: award events include Draft-only TOTW and TOTY categories.
-- ---------------------------------------------------------------------------

CREATE TABLE dfm_private.drl_draft_award_records (
  league_id text NOT NULL,
  award_id text NOT NULL,
  category text NOT NULL CHECK (category IN (
    'man_of_the_match',
    'man_of_the_round',
    'play_of_the_week',
    'team_of_the_week',
    'team_of_the_year',
    'player_of_the_year',
    'coach_of_the_year'
  )),
  round_number integer NOT NULL CHECK (round_number >= 1),
  player_id text NOT NULL,
  player_name text NOT NULL,
  franchise_id uuid NOT NULL,
  coach_id uuid NOT NULL,
  base_score numeric(18,6) NOT NULL CHECK (base_score >= 0),
  points integer NOT NULL CHECK (points >= 0),
  position text CHECK (position IS NULL OR position IN (
    'WFB', 'CTR', 'HLF', 'EDG', 'MID', 'HOK'
  )),
  achievement_only boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (league_id, award_id),
  CONSTRAINT drl_draft_award_event_uq
    UNIQUE (league_id, round_number, category, player_id, franchise_id)
);

CREATE TABLE dfm_private.drl_draft_coach_award_credits (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  league_id text NOT NULL,
  coach_id uuid NOT NULL,
  franchise_id uuid NOT NULL,
  player_id text NOT NULL,
  category text NOT NULL CHECK (category IN (
    'man_of_the_match',
    'man_of_the_round',
    'play_of_the_week',
    'team_of_the_week',
    'team_of_the_year',
    'player_of_the_year',
    'coach_of_the_year'
  )),
  round_number integer NOT NULL CHECK (round_number >= 1),
  points integer NOT NULL CHECK (points > 0),
  credited_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT drl_draft_coach_credit_event_uq
    UNIQUE (league_id, coach_id, franchise_id, player_id, category, round_number)
);

CREATE INDEX drl_draft_awards_player_idx
  ON dfm_private.drl_draft_award_records
  (league_id, player_id, round_number);

CREATE INDEX drl_draft_awards_round_idx
  ON dfm_private.drl_draft_award_records
  (league_id, round_number, category);

CREATE INDEX drl_draft_coach_credits_ladder_idx
  ON dfm_private.drl_draft_coach_award_credits
  (league_id, coach_id, category);

-- ---------------------------------------------------------------------------
-- DRAFT: newsroom and source fixture results for ladder derivation.
-- ---------------------------------------------------------------------------

CREATE TABLE dfm_private.drl_draft_news_articles (
  league_id text NOT NULL,
  article_id text NOT NULL,
  round_number integer NOT NULL CHECK (round_number >= 1),
  category text NOT NULL CHECK (category IN (
    'preview',
    'match_report',
    'round_awards',
    'odds_update',
    'injury',
    'transfer',
    'finals_race'
  )),
  title text NOT NULL,
  summary text NOT NULL,
  content text NOT NULL,
  published boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (league_id, article_id)
);

CREATE INDEX drl_draft_news_feed_idx
  ON dfm_private.drl_draft_news_articles
  (league_id, published, created_at DESC);

CREATE TABLE dfm_private.drl_draft_ladder_match_results (
  league_id text NOT NULL,
  fixture_id text NOT NULL,
  home_franchise_id uuid NOT NULL,
  away_franchise_id uuid NOT NULL,
  home_score numeric(18,6) NOT NULL
    CHECK (home_score >= 0 AND home_score < 'Infinity'::numeric),
  away_score numeric(18,6) NOT NULL
    CHECK (away_score >= 0 AND away_score < 'Infinity'::numeric),
  home_competition_points integer NOT NULL CHECK (home_competition_points >= 0),
  away_competition_points integer NOT NULL CHECK (away_competition_points >= 0),
  finalised boolean NOT NULL DEFAULT false,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (league_id, fixture_id),
  CONSTRAINT drl_draft_ladder_distinct_franchises_ck
    CHECK (home_franchise_id <> away_franchise_id)
);

CREATE INDEX drl_draft_ladder_results_league_idx
  ON dfm_private.drl_draft_ladder_match_results
  (league_id, finalised, fixture_id);

-- ---------------------------------------------------------------------------
-- Explicitly keep all mode tables private and RLS-protected.
-- No policies or API-role grants are created in this stage.
-- ---------------------------------------------------------------------------

ALTER TABLE dfm_private.drl_classic_odds_market_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE dfm_private.drl_classic_odds_market_outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE dfm_private.drl_classic_odds_price_movements ENABLE ROW LEVEL SECURITY;
ALTER TABLE dfm_private.drl_classic_award_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE dfm_private.drl_classic_coach_award_credits ENABLE ROW LEVEL SECURITY;
ALTER TABLE dfm_private.drl_classic_news_articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE dfm_private.drl_classic_ladder_match_results ENABLE ROW LEVEL SECURITY;

ALTER TABLE dfm_private.drl_draft_odds_market_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE dfm_private.drl_draft_odds_market_outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE dfm_private.drl_draft_odds_price_movements ENABLE ROW LEVEL SECURITY;
ALTER TABLE dfm_private.drl_draft_award_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE dfm_private.drl_draft_coach_award_credits ENABLE ROW LEVEL SECURITY;
ALTER TABLE dfm_private.drl_draft_news_articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE dfm_private.drl_draft_ladder_match_results ENABLE ROW LEVEL SECURITY;

REVOKE ALL PRIVILEGES ON TABLE
  dfm_private.drl_classic_odds_market_snapshots,
  dfm_private.drl_classic_odds_market_outcomes,
  dfm_private.drl_classic_odds_price_movements,
  dfm_private.drl_classic_award_records,
  dfm_private.drl_classic_coach_award_credits,
  dfm_private.drl_classic_news_articles,
  dfm_private.drl_classic_ladder_match_results,
  dfm_private.drl_draft_odds_market_snapshots,
  dfm_private.drl_draft_odds_market_outcomes,
  dfm_private.drl_draft_odds_price_movements,
  dfm_private.drl_draft_award_records,
  dfm_private.drl_draft_coach_award_credits,
  dfm_private.drl_draft_news_articles,
  dfm_private.drl_draft_ladder_match_results
FROM PUBLIC, anon, authenticated, service_role;

COMMENT ON TABLE dfm_private.drl_classic_odds_market_snapshots IS
  'Private Classic-only DRL odds calculation snapshots.';
COMMENT ON TABLE dfm_private.drl_classic_award_records IS
  'Private Classic-only award events; league-scoped IDs preserve shared-player ownership history.';
COMMENT ON TABLE dfm_private.drl_classic_coach_award_credits IS
  'Private Classic-only coach credits captured at award time; never rewritten after transfers.';
COMMENT ON TABLE dfm_private.drl_classic_news_articles IS
  'Private Classic-only newsroom articles.';
COMMENT ON TABLE dfm_private.drl_classic_ladder_match_results IS
  'Private Classic-only source match results used to derive competition standings.';

COMMENT ON TABLE dfm_private.drl_draft_odds_market_snapshots IS
  'Private Draft-only DRL odds calculation snapshots, including Draft award markets.';
COMMENT ON TABLE dfm_private.drl_draft_award_records IS
  'Private Draft-only award events, including positional TOTW and TOTY selections.';
COMMENT ON TABLE dfm_private.drl_draft_coach_award_credits IS
  'Private Draft-only coach credits captured at award time.';
COMMENT ON TABLE dfm_private.drl_draft_news_articles IS
  'Private Draft-only newsroom articles.';
COMMENT ON TABLE dfm_private.drl_draft_ladder_match_results IS
  'Private Draft-only source match results used to derive competition standings.';

COMMIT;
