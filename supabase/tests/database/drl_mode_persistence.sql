-- Read-only security verification. Run as database owner after migration.
DO $drl_persistence_security$
DECLARE
  table_name text;
  expected_tables text[] := ARRAY[
    'drl_classic_odds_market_snapshots','drl_classic_odds_market_outcomes',
    'drl_classic_odds_price_movements','drl_classic_award_records',
    'drl_classic_coach_award_credits','drl_classic_news_articles',
    'drl_classic_ladder_match_results','drl_draft_odds_market_snapshots',
    'drl_draft_odds_market_outcomes','drl_draft_odds_price_movements',
    'drl_draft_award_records','drl_draft_coach_award_credits',
    'drl_draft_news_articles','drl_draft_ladder_match_results'
  ];
  rpc_name text;
  expected_rpcs text[] := ARRAY[
    'public.dfm_classic_persist_market_snapshot(text,text,text,integer,text,text,boolean,text,text,boolean,jsonb,jsonb)',
    'public.dfm_draft_persist_market_snapshot(text,text,text,integer,text,text,boolean,text,text,boolean,jsonb,jsonb)',
    'public.dfm_classic_persist_award_bundle(text,jsonb,jsonb)',
    'public.dfm_draft_persist_award_bundle(text,jsonb,jsonb)',
    'public.dfm_classic_persist_news_article(text,text,integer,text,text,text,text,boolean)',
    'public.dfm_draft_persist_news_article(text,text,integer,text,text,text,text,boolean)',
    'public.dfm_classic_persist_ladder_result(text,text,uuid,uuid,numeric,numeric,integer,integer)',
    'public.dfm_draft_persist_ladder_result(text,text,uuid,uuid,numeric,numeric,integer,integer)',
    'public.dfm_classic_append_price_movement(text,text,text,integer,numeric,numeric,numeric,numeric,text,text,text)',
    'public.dfm_draft_append_price_movement(text,text,text,integer,numeric,numeric,numeric,numeric,text,text,text)',
    'public.dfm_classic_list_market_movements(text,text)',
    'public.dfm_draft_list_market_movements(text,text)',
    'public.dfm_classic_list_awards(text,integer)',
    'public.dfm_draft_list_awards(text,integer)',
    'public.dfm_classic_list_coach_credits(text,text)',
    'public.dfm_draft_list_coach_credits(text,text)',
    'public.dfm_classic_list_news_articles(text,integer)',
    'public.dfm_draft_list_news_articles(text,integer)',
    'public.dfm_classic_list_ladder_results(text)',
    'public.dfm_draft_list_ladder_results(text)'
  ];
  q text;
  oid_value oid;
BEGIN
  IF to_regnamespace('dfm_private') IS NULL THEN
    RAISE EXCEPTION 'dfm_private schema is missing';
  END IF;
  IF has_schema_privilege('anon','dfm_private','USAGE')
     OR has_schema_privilege('authenticated','dfm_private','USAGE')
     OR has_schema_privilege('service_role','dfm_private','USAGE')
     OR has_schema_privilege('anon','dfm_private','CREATE')
     OR has_schema_privilege('authenticated','dfm_private','CREATE')
     OR has_schema_privilege('service_role','dfm_private','CREATE') THEN
    RAISE EXCEPTION 'API roles must not have dfm_private schema USAGE';
  END IF;

  FOREACH table_name IN ARRAY expected_tables LOOP
    q := format('dfm_private.%I',table_name);
    oid_value := to_regclass(q);
    IF oid_value IS NULL THEN RAISE EXCEPTION 'Missing table: %',q; END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE oid=oid_value AND relrowsecurity) THEN
      RAISE EXCEPTION 'RLS disabled: %',q;
    END IF;
    IF has_table_privilege('anon',q,'SELECT')
       OR has_table_privilege('anon',q,'INSERT')
       OR has_table_privilege('anon',q,'UPDATE')
       OR has_table_privilege('anon',q,'DELETE')
       OR has_table_privilege('authenticated',q,'SELECT')
       OR has_table_privilege('authenticated',q,'INSERT')
       OR has_table_privilege('authenticated',q,'UPDATE')
       OR has_table_privilege('authenticated',q,'DELETE')
       OR has_table_privilege('service_role',q,'SELECT')
       OR has_table_privilege('service_role',q,'INSERT')
       OR has_table_privilege('service_role',q,'UPDATE')
       OR has_table_privilege('service_role',q,'DELETE')
       OR has_table_privilege('anon',q,'TRUNCATE')
       OR has_table_privilege('authenticated',q,'TRUNCATE')
       OR has_table_privilege('service_role',q,'TRUNCATE')
       OR has_table_privilege('anon',q,'REFERENCES')
       OR has_table_privilege('authenticated',q,'REFERENCES')
       OR has_table_privilege('service_role',q,'REFERENCES')
       OR has_table_privilege('anon',q,'TRIGGER')
       OR has_table_privilege('authenticated',q,'TRIGGER')
       OR has_table_privilege('service_role',q,'TRIGGER') THEN
      RAISE EXCEPTION 'Unexpected direct API table privilege: %',q;
    END IF;
  END LOOP;

  FOREACH rpc_name IN ARRAY expected_rpcs LOOP
    oid_value := to_regprocedure(rpc_name);
    IF oid_value IS NULL THEN RAISE EXCEPTION 'Missing RPC: %',rpc_name; END IF;
    IF has_function_privilege('anon',oid_value,'EXECUTE')
       OR has_function_privilege('authenticated',oid_value,'EXECUTE')
       OR NOT has_function_privilege('service_role',oid_value,'EXECUTE') THEN
      RAISE EXCEPTION 'RPC execute grants are incorrect: %',rpc_name;
    END IF;
    IF NOT (SELECT p.prosecdef
                    AND coalesce(p.proconfig @> ARRAY['search_path=""'],false)
            FROM pg_proc p WHERE p.oid=oid_value) THEN
      RAISE EXCEPTION 'RPC must be SECURITY DEFINER with an empty search_path: %',rpc_name;
    END IF;
  END LOOP;

  IF EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname='dfm_private'
      AND tablename::text = ANY(expected_tables)
  ) THEN
    RAISE EXCEPTION 'Unexpected row policy exists on private persistence tables';
  END IF;

  IF EXISTS (
    SELECT 1 FROM pg_tables
    WHERE schemaname='public' AND left(tablename,4)='drl_'
  ) THEN
    RAISE EXCEPTION 'DRL persistence tables must not be in public';
  END IF;

  IF has_function_privilege('service_role',
       'dfm_private.persist_market_snapshot(text,text,text,text,integer,text,text,boolean,text,text,boolean,jsonb,jsonb)',
       'EXECUTE')
     OR has_function_privilege('service_role',
       'dfm_private.persist_award_bundle(text,text,jsonb,jsonb)','EXECUTE')
     OR has_function_privilege('service_role',
       'dfm_private.persist_news_article(text,text,text,integer,text,text,text,text,boolean)','EXECUTE')
     OR has_function_privilege('service_role',
       'dfm_private.persist_ladder_result(text,text,text,uuid,uuid,numeric,numeric,integer,integer)','EXECUTE')
     OR has_function_privilege('service_role',
       'dfm_private.append_price_movement(text,text,text,text,integer,numeric,numeric,numeric,numeric,text,text,text)','EXECUTE')
     OR has_function_privilege('service_role',
       'dfm_private.list_market_movements(text,text,text)','EXECUTE')
     OR has_function_privilege('service_role',
       'dfm_private.list_awards(text,text,integer)','EXECUTE')
     OR has_function_privilege('service_role',
       'dfm_private.list_coach_credits(text,text,text)','EXECUTE')
     OR has_function_privilege('service_role',
       'dfm_private.list_news_articles(text,text,integer)','EXECUTE')
     OR has_function_privilege('service_role',
       'dfm_private.list_ladder_results(text,text)','EXECUTE')
     OR has_function_privilege('service_role',
       'dfm_private.reject_drl_history_mutation()','EXECUTE')
     OR has_function_privilege('service_role',
       'dfm_private.reject_finalised_drl_match_mutation()','EXECUTE')
     OR has_function_privilege('service_role',
       'dfm_private.reject_drl_news_mutation()','EXECUTE') THEN
    RAISE EXCEPTION 'Service role must not execute private implementation functions directly';
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='drl_classic_odds_snapshot_immutable')
     OR NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='drl_classic_odds_outcome_immutable')
     OR NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='drl_classic_odds_movement_immutable')
     OR NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='drl_classic_award_immutable')
     OR NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='drl_classic_coach_credit_immutable')
     OR NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='drl_draft_odds_snapshot_immutable')
     OR NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='drl_draft_odds_outcome_immutable')
     OR NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='drl_draft_odds_movement_immutable')
     OR NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='drl_draft_award_immutable')
     OR NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='drl_draft_coach_credit_immutable')
     OR NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='drl_classic_news_immutable')
     OR NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='drl_draft_news_immutable')
     OR NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='drl_classic_finalised_match_immutable')
     OR NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='drl_draft_finalised_match_immutable') THEN
    RAISE EXCEPTION 'One or more immutable-history triggers are missing';
  END IF;
END;
$drl_persistence_security$;

SELECT 'drl_persistence_security: PASS' AS result;
