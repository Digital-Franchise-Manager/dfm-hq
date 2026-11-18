-- Run only after the reviewed DRL persistence migration has been applied.
-- Execute as the database owner. This script is read-only.

DO $drl_persistence_security$
DECLARE
  table_name text;
  expected_tables text[] := ARRAY[
    'drl_classic_odds_market_snapshots',
    'drl_classic_odds_market_outcomes',
    'drl_classic_odds_price_movements',
    'drl_classic_award_records',
    'drl_classic_coach_award_credits',
    'drl_classic_news_articles',
    'drl_classic_ladder_match_results',
    'drl_draft_odds_market_snapshots',
    'drl_draft_odds_market_outcomes',
    'drl_draft_odds_price_movements',
    'drl_draft_award_records',
    'drl_draft_coach_award_credits',
    'drl_draft_news_articles',
    'drl_draft_ladder_match_results'
  ];
  qualified_name text;
  relation_oid oid;
BEGIN
  IF to_regnamespace('dfm_private') IS NULL THEN
    RAISE EXCEPTION 'dfm_private schema is missing';
  END IF;

  IF has_schema_privilege('anon', 'dfm_private', 'USAGE')
     OR has_schema_privilege('authenticated', 'dfm_private', 'USAGE')
     OR has_schema_privilege('service_role', 'dfm_private', 'USAGE') THEN
    RAISE EXCEPTION 'DRL persistence schema must remain unavailable to API roles';
  END IF;

  FOREACH table_name IN ARRAY expected_tables LOOP
    qualified_name := format('dfm_private.%I', table_name);
    relation_oid := to_regclass(qualified_name);

    IF relation_oid IS NULL THEN
      RAISE EXCEPTION 'Required DRL persistence table is missing: %', qualified_name;
    END IF;

    IF NOT EXISTS (
      SELECT 1 FROM pg_class
      WHERE oid = relation_oid AND relrowsecurity
    ) THEN
      RAISE EXCEPTION 'RLS is not enabled on %', qualified_name;
    END IF;

    IF has_table_privilege('anon', qualified_name, 'SELECT')
       OR has_table_privilege('anon', qualified_name, 'INSERT')
       OR has_table_privilege('anon', qualified_name, 'UPDATE')
       OR has_table_privilege('anon', qualified_name, 'DELETE')
       OR has_table_privilege('authenticated', qualified_name, 'SELECT')
       OR has_table_privilege('authenticated', qualified_name, 'INSERT')
       OR has_table_privilege('authenticated', qualified_name, 'UPDATE')
       OR has_table_privilege('authenticated', qualified_name, 'DELETE')
       OR has_table_privilege('service_role', qualified_name, 'SELECT')
       OR has_table_privilege('service_role', qualified_name, 'INSERT')
       OR has_table_privilege('service_role', qualified_name, 'UPDATE')
       OR has_table_privilege('service_role', qualified_name, 'DELETE') THEN
      RAISE EXCEPTION 'An API role has direct table privileges on %', qualified_name;
    END IF;

    IF EXISTS (
      SELECT 1 FROM pg_policies AS policy
      WHERE policy.schemaname = 'dfm_private'
        AND policy.tablename = table_name
    ) THEN
      RAISE EXCEPTION 'Unexpected API policy exists on private table %', qualified_name;
    END IF;
  END LOOP;

  IF EXISTS (
    SELECT 1 FROM pg_tables
    WHERE schemaname = 'public'
      AND tablename LIKE 'drl\_%' ESCAPE '\'
  ) THEN
    RAISE EXCEPTION 'DRL engine persistence must not be created in exposed public schema';
  END IF;
END;
$drl_persistence_security$;

SELECT 'drl_persistence_security: PASS' AS result;
