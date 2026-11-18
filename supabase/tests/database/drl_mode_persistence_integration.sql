-- Integration smoke tests for a disposable local Supabase/Postgres database.
-- All synthetic writes are rolled back. Do not run against production.
BEGIN;

SET LOCAL ROLE service_role;

SELECT public.dfm_classic_persist_market_snapshot(
  'test-classic-league','test-classic-market','head_to_head',1,
  'test-source','official',true,'synthetic verified source','0.2.0',true,
  '[{"selection_id":"home","label":"Home","probability":0.55,"decimal_price":1.8182},
    {"selection_id":"away","label":"Away","probability":0.45,"decimal_price":2.2222}]'::jsonb,
  '[]'::jsonb
);

-- Exact retries are idempotent and do not duplicate snapshot/outcome rows.
SELECT public.dfm_classic_persist_market_snapshot(
  'test-classic-league','test-classic-market','head_to_head',1,
  'test-source','official',true,'synthetic verified source','0.2.0',true,
  '[{"selection_id":"home","label":"Home","probability":0.55,"decimal_price":1.8182},
    {"selection_id":"away","label":"Away","probability":0.45,"decimal_price":2.2222}]'::jsonb,
  '[]'::jsonb
);

-- Persist a revision and its price movement as one atomic market operation.
SELECT public.dfm_classic_persist_market_snapshot(
  'test-classic-league','test-classic-market','head_to_head',2,
  'test-source-2','official',true,'revised synthetic source','0.2.0',true,
  '[{"selection_id":"home","label":"Home","probability":0.60,"decimal_price":1.6667},
    {"selection_id":"away","label":"Away","probability":0.40,"decimal_price":2.5000}]'::jsonb,
  '[{"selection_id":"home","revision":2,"previous_probability":0.55,
     "revised_probability":0.60,"previous_price":1.8182,"revised_price":1.6667,
     "source_id":"test-source-2","model_version":"0.2.0",
     "idempotency_key":"classic-home-revision-2"}]'::jsonb
);

SELECT public.dfm_draft_persist_market_snapshot(
  'test-draft-league','test-draft-market','team_of_the_week',1,
  'test-source','official',true,'synthetic verified source','0.2.0',true,
  '[{"selection_id":"team-a","label":"Team A","probability":0.60,"decimal_price":1.6667},
    {"selection_id":"team-b","label":"Team B","probability":0.40,"decimal_price":2.5000}]'::jsonb,
  '[]'::jsonb
);

-- Replaying the same award/credit bundle is idempotent.
SELECT public.dfm_classic_persist_award_bundle(
  'test-classic-league',
  '[{"award_id":"classic-award-1","category":"man_of_the_match","round_number":1,
     "player_id":"player-1","player_name":"Test Player",
     "franchise_id":"00000000-0000-0000-0000-000000000011",
     "coach_id":"coach-at-award-time","base_score":88,"points":2,
     "position":"HLF","achievement_only":false}]'::jsonb,
  '[{"coach_id":"coach-at-award-time",
     "franchise_id":"00000000-0000-0000-0000-000000000011",
     "player_id":"player-1","category":"man_of_the_match",
     "round_number":1,"points":2}]'::jsonb
);

SELECT public.dfm_classic_persist_award_bundle(
  'test-classic-league',
  '[{"award_id":"classic-award-1","category":"man_of_the_match","round_number":1,
     "player_id":"player-1","player_name":"Test Player",
     "franchise_id":"00000000-0000-0000-0000-000000000011",
     "coach_id":"coach-at-award-time","base_score":88,"points":2,
     "position":"HLF","achievement_only":false}]'::jsonb,
  '[{"coach_id":"coach-at-award-time",
     "franchise_id":"00000000-0000-0000-0000-000000000011",
     "player_id":"player-1","category":"man_of_the_match",
     "round_number":1,"points":2}]'::jsonb
);

SELECT public.dfm_draft_persist_award_bundle(
  'test-draft-league',
  '[{"award_id":"draft-award-1","category":"team_of_the_week","round_number":1,
     "player_id":"player-2","player_name":"Draft Player",
     "franchise_id":"00000000-0000-0000-0000-000000000022",
     "coach_id":"draft-coach","base_score":90,"points":1,
     "position":"WFB","achievement_only":false}]'::jsonb,
  '[{"coach_id":"draft-coach",
     "franchise_id":"00000000-0000-0000-0000-000000000022",
     "player_id":"player-2","category":"team_of_the_week",
     "round_number":1,"points":1}]'::jsonb
);

SELECT public.dfm_classic_persist_news_article(
  'test-classic-league','shared-test-article-id',1,'preview',
  'Classic preview','Classic summary','Classic body',true
);
SELECT public.dfm_classic_persist_news_article(
  'test-classic-league','shared-test-article-id',1,'preview',
  'Classic preview','Classic summary','Classic body',true
);
SELECT public.dfm_draft_persist_news_article(
  'test-draft-league','shared-test-article-id',1,'preview',
  'Draft preview','Draft summary','Draft body',true
);

SELECT public.dfm_classic_persist_ladder_result(
  'test-classic-league','test-fixture-1',
  '00000000-0000-0000-0000-000000000011',
  '00000000-0000-0000-0000-000000000012',
  44.5,39.0,2,0
);
SELECT public.dfm_classic_persist_ladder_result(
  'test-classic-league','test-fixture-1',
  '00000000-0000-0000-0000-000000000011',
  '00000000-0000-0000-0000-000000000012',
  44.5,39.0,2,0
);
SELECT public.dfm_draft_persist_ladder_result(
  'test-draft-league','test-fixture-1',
  '00000000-0000-0000-0000-000000000021',
  '00000000-0000-0000-0000-000000000022',
  61.0,61.0,1,1
);

RESET ROLE;

DO $assertions$
BEGIN
  IF (SELECT count(*) FROM dfm_private.drl_classic_odds_market_snapshots
      WHERE league_id='test-classic-league' AND market_id='test-classic-market') <> 1
     OR (SELECT count(*) FROM dfm_private.drl_classic_odds_market_outcomes o
         JOIN dfm_private.drl_classic_odds_market_snapshots s
           ON s.id=o.market_snapshot_id
         WHERE s.league_id='test-classic-league' AND s.market_id='test-classic-market') <> 2 THEN
    RAISE EXCEPTION 'Market snapshot replay was not idempotent';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM dfm_private.drl_classic_odds_price_movements
    WHERE league_id='test-classic-league'
      AND idempotency_key='classic-home-revision-2'
      AND revised_probability=0.60
  ) THEN RAISE EXCEPTION 'Classic price movement persistence failed'; END IF;

  IF NOT EXISTS (
    SELECT 1 FROM dfm_private.drl_classic_award_records
    WHERE league_id='test-classic-league' AND award_id='classic-award-1'
      AND coach_id='coach-at-award-time'
  ) THEN RAISE EXCEPTION 'Classic award persistence failed'; END IF;

  IF NOT EXISTS (
    SELECT 1 FROM dfm_private.drl_draft_award_records
    WHERE league_id='test-draft-league' AND category='team_of_the_week'
  ) THEN RAISE EXCEPTION 'Draft-only award persistence failed'; END IF;

  IF EXISTS (
    SELECT 1 FROM dfm_private.drl_draft_award_records
    WHERE league_id='test-classic-league'
  ) OR EXISTS (
    SELECT 1 FROM dfm_private.drl_classic_award_records
    WHERE league_id='test-draft-league'
  ) THEN RAISE EXCEPTION 'Classic/Draft award data crossed mode boundaries'; END IF;

  IF NOT EXISTS (
    SELECT 1 FROM dfm_private.drl_classic_news_articles
    WHERE article_id='shared-test-article-id' AND title='Classic preview'
  ) OR NOT EXISTS (
    SELECT 1 FROM dfm_private.drl_draft_news_articles
    WHERE article_id='shared-test-article-id' AND title='Draft preview'
  ) THEN RAISE EXCEPTION 'Classic/Draft newsroom isolation failed'; END IF;

  IF NOT EXISTS (
    SELECT 1 FROM dfm_private.drl_classic_ladder_match_results
    WHERE fixture_id='test-fixture-1' AND finalised
  ) OR NOT EXISTS (
    SELECT 1 FROM dfm_private.drl_draft_ladder_match_results
    WHERE fixture_id='test-fixture-1' AND finalised
  ) THEN RAISE EXCEPTION 'Ladder result persistence failed'; END IF;
END;
$assertions$;

-- Verify award + credit bundle atomicity: invalid credits must roll back the award.
SET LOCAL ROLE service_role;
DO $atomicity$
BEGIN
  BEGIN
    PERFORM public.dfm_classic_persist_award_bundle(
      'test-classic-league',
      '[{"award_id":"must-rollback","category":"man_of_the_match","round_number":2,
         "player_id":"player-rollback","player_name":"Rollback Player",
         "franchise_id":"00000000-0000-0000-0000-000000000011",
         "coach_id":"coach-at-award-time","base_score":10,"points":2,
         "position":"HLF","achievement_only":false}]'::jsonb,
      '[{"coach_id":"coach-at-award-time",
         "franchise_id":"00000000-0000-0000-0000-000000000011",
         "player_id":"player-rollback","category":"man_of_the_match",
         "round_number":2,"points":0}]'::jsonb
    );
    RAISE EXCEPTION 'Expected invalid coach credit to fail';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$atomicity$;
RESET ROLE;

DO $rollback_assertion$
BEGIN
  IF EXISTS (
    SELECT 1 FROM dfm_private.drl_classic_award_records
    WHERE award_id='must-rollback'
  ) THEN RAISE EXCEPTION 'Award row survived failed atomic bundle'; END IF;
END;
$rollback_assertion$;

-- Immutability must reject updates to persisted award and newsroom history.
DO $immutability$
BEGIN
  BEGIN
    UPDATE dfm_private.drl_classic_award_records
      SET player_name='Tampered'
      WHERE award_id='classic-award-1';
    RAISE EXCEPTION 'Expected award history mutation to fail';
  EXCEPTION WHEN SQLSTATE '55000' THEN NULL;
  END;
  BEGIN
    UPDATE dfm_private.drl_classic_odds_market_snapshots
      SET source_summary='Tampered'
      WHERE league_id='test-classic-league' AND market_id='test-classic-market'
        AND revision=1;
    RAISE EXCEPTION 'Expected odds snapshot history mutation to fail';
  EXCEPTION WHEN SQLSTATE '55000' THEN NULL;
  END;
  BEGIN
    UPDATE dfm_private.drl_classic_odds_price_movements
      SET revised_price=1.25
      WHERE league_id='test-classic-league'
        AND idempotency_key='classic-home-revision-2';
    RAISE EXCEPTION 'Expected price movement history mutation to fail';
  EXCEPTION WHEN SQLSTATE '55000' THEN NULL;
  END;
  BEGIN
    UPDATE dfm_private.drl_classic_coach_award_credits
      SET points=99
      WHERE league_id='test-classic-league' AND coach_id='coach-at-award-time';
    RAISE EXCEPTION 'Expected coach credit history mutation to fail';
  EXCEPTION WHEN SQLSTATE '55000' THEN NULL;
  END;
  BEGIN
    UPDATE dfm_private.drl_classic_news_articles
      SET title='Tampered'
      WHERE article_id='shared-test-article-id';
    RAISE EXCEPTION 'Expected newsroom history mutation to fail';
  EXCEPTION WHEN SQLSTATE '55000' THEN NULL;
  END;
  BEGIN
    DELETE FROM dfm_private.drl_classic_ladder_match_results
      WHERE fixture_id='test-fixture-1';
    RAISE EXCEPTION 'Expected finalised match deletion to fail';
  EXCEPTION WHEN SQLSTATE '55000' THEN NULL;
  END;
END;
$immutability$;

ROLLBACK;
