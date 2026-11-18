-- DRAFT ONLY — append to drl_mode_persistence.sql before generating the
-- official Supabase migration. No hosted database changes are made by this file.
--
-- PostgREST can only call public-schema RPCs. These narrow SECURITY DEFINER
-- wrappers expose no table access and are executable only by service_role.
-- Their fixed search_path and fully-qualified private calls are intentional.

BEGIN;

CREATE OR REPLACE FUNCTION dfm_private.reject_drl_news_mutation()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $function$
BEGIN
  RAISE EXCEPTION 'DRL newsroom history is append-only: %.%',
    TG_TABLE_SCHEMA, TG_TABLE_NAME
    USING ERRCODE = '55000';
END;
$function$;

REVOKE ALL ON FUNCTION dfm_private.reject_drl_news_mutation()
FROM PUBLIC, anon, authenticated, service_role;

CREATE TRIGGER drl_classic_news_immutable
BEFORE UPDATE OR DELETE ON dfm_private.drl_classic_news_articles
FOR EACH ROW EXECUTE FUNCTION dfm_private.reject_drl_news_mutation();

CREATE TRIGGER drl_draft_news_immutable
BEFORE UPDATE OR DELETE ON dfm_private.drl_draft_news_articles
FOR EACH ROW EXECUTE FUNCTION dfm_private.reject_drl_news_mutation();

-- Internal dispatcher. The mode is strictly whitelisted and every dynamic
-- identifier is generated from that whitelist; all values use bind parameters.
CREATE OR REPLACE FUNCTION dfm_private.persist_market_snapshot(
  p_mode text,
  p_league_id text,
  p_market_id text,
  p_market_type text,
  p_revision integer,
  p_source_id text,
  p_source_category text,
  p_source_verified boolean,
  p_source_summary text,
  p_model_version text,
  p_official boolean,
  p_outcomes jsonb,
  p_movements jsonb
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $function$
DECLARE
  v_prefix text;
  v_snapshot_table text;
  v_outcomes_table text;
  v_movements_table text;
  v_snapshot_id uuid;
  v_bad boolean;
  v_total numeric;
  v_count integer;
BEGIN
  v_prefix := CASE p_mode
    WHEN 'classic' THEN 'drl_classic'
    WHEN 'draft' THEN 'drl_draft'
    ELSE NULL
  END;
  IF v_prefix IS NULL THEN RAISE EXCEPTION 'Unsupported DRL mode'; END IF;
  IF p_league_id IS NULL OR btrim(p_league_id) = ''
     OR p_market_id IS NULL OR btrim(p_market_id) = ''
     OR p_revision < 1
     OR p_official IS DISTINCT FROM p_source_verified
     OR jsonb_typeof(p_outcomes) IS DISTINCT FROM 'array'
     OR jsonb_array_length(p_outcomes) < 2
     OR jsonb_typeof(p_movements) IS DISTINCT FROM 'array' THEN
    RAISE EXCEPTION 'Invalid market snapshot payload' USING ERRCODE = '22023';
  END IF;

  SELECT count(*), sum((x->>'probability')::numeric)
    INTO v_count, v_total
  FROM jsonb_array_elements(p_outcomes) AS x;
  IF v_count <> (SELECT count(DISTINCT x->>'selection_id') FROM jsonb_array_elements(p_outcomes) AS x)
     OR abs(v_total - 1::numeric) > 0.00000001 THEN
    RAISE EXCEPTION 'Market outcomes must have unique selections and probabilities summing to one'
      USING ERRCODE = '22023';
  END IF;

  v_snapshot_table := v_prefix || '_odds_market_snapshots';
  v_outcomes_table := v_prefix || '_odds_market_outcomes';
  v_movements_table := v_prefix || '_odds_price_movements';

  EXECUTE format(
    'INSERT INTO dfm_private.%I
      (league_id, market_id, market_type, revision, source_id, source_category,
       source_verified, source_summary, model_version, official)
     VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
     ON CONFLICT (league_id, market_id, revision) DO NOTHING
     RETURNING id',
    v_snapshot_table
  ) INTO v_snapshot_id
  USING p_league_id,p_market_id,p_market_type,p_revision,p_source_id,
        p_source_category,p_source_verified,p_source_summary,p_model_version,p_official;

  IF v_snapshot_id IS NULL THEN
    EXECUTE format(
      'SELECT id FROM dfm_private.%I
       WHERE league_id=$1 AND market_id=$2 AND revision=$3
         AND market_type=$4 AND source_id=$5 AND source_category=$6
         AND source_verified=$7 AND source_summary=$8
         AND model_version=$9 AND official=$10',
      v_snapshot_table
    ) INTO v_snapshot_id
    USING p_league_id,p_market_id,p_revision,p_market_type,p_source_id,
          p_source_category,p_source_verified,p_source_summary,p_model_version,p_official;
    IF v_snapshot_id IS NULL THEN
      RAISE EXCEPTION 'Market revision already exists with different content'
        USING ERRCODE = '23505';
    END IF;
  END IF;

  EXECUTE format(
    'INSERT INTO dfm_private.%I
       (market_snapshot_id, selection_id, label, probability, decimal_price)
     SELECT $1,x.selection_id,x.label,x.probability,x.decimal_price
     FROM jsonb_to_recordset($2) AS x(
       selection_id text,label text,probability numeric,decimal_price numeric
     )
     ON CONFLICT (market_snapshot_id,selection_id) DO NOTHING',
    v_outcomes_table
  ) USING v_snapshot_id,p_outcomes;

  EXECUTE format(
    'SELECT EXISTS (
       SELECT 1 FROM jsonb_to_recordset($1) AS x(
         selection_id text,label text,probability numeric,decimal_price numeric
       )
       LEFT JOIN dfm_private.%I t
         ON t.market_snapshot_id=$2 AND t.selection_id=x.selection_id
       WHERE t.selection_id IS NULL
          OR ROW(t.label,t.probability,t.decimal_price)
             IS DISTINCT FROM ROW(x.label,x.probability,x.decimal_price)
     )',
    v_outcomes_table
  ) INTO v_bad USING p_outcomes,v_snapshot_id;
  IF v_bad THEN RAISE EXCEPTION 'Market outcome idempotency conflict' USING ERRCODE = '23505'; END IF;

  IF jsonb_array_length(p_movements) > 0 THEN
    EXECUTE format(
      'INSERT INTO dfm_private.%I
        (league_id,market_id,selection_id,revision,previous_probability,
         revised_probability,previous_price,revised_price,source_id,
         model_version,idempotency_key)
       SELECT $1,$2,x.selection_id,x.revision,x.previous_probability,
              x.revised_probability,x.previous_price,x.revised_price,
              x.source_id,x.model_version,x.idempotency_key
       FROM jsonb_to_recordset($3) AS x(
         selection_id text,revision integer,previous_probability numeric,
         revised_probability numeric,previous_price numeric,revised_price numeric,
         source_id text,model_version text,idempotency_key text
       )
       ON CONFLICT DO NOTHING',
      v_movements_table
    ) USING p_league_id,p_market_id,p_movements;

    EXECUTE format(
      'SELECT EXISTS (
         SELECT 1 FROM jsonb_to_recordset($1) AS x(
           selection_id text,revision integer,previous_probability numeric,
           revised_probability numeric,previous_price numeric,revised_price numeric,
           source_id text,model_version text,idempotency_key text
         )
         LEFT JOIN dfm_private.%I t
           ON t.league_id=$2 AND t.idempotency_key=x.idempotency_key
         WHERE x.revision <> $3 OR t.id IS NULL
            OR ROW(t.market_id,t.selection_id,t.revision,t.previous_probability,
                   t.revised_probability,t.previous_price,t.revised_price,
                   t.source_id,t.model_version)
               IS DISTINCT FROM
               ROW($4,x.selection_id,x.revision,x.previous_probability,
                   x.revised_probability,x.previous_price,x.revised_price,
                   x.source_id,x.model_version)
       )',
      v_movements_table
    ) INTO v_bad USING p_movements,p_league_id,p_revision,p_market_id;
    IF v_bad THEN RAISE EXCEPTION 'Market movement revision or idempotency conflict' USING ERRCODE = '23505'; END IF;
  END IF;

  RETURN v_snapshot_id;
END;
$function$;

CREATE OR REPLACE FUNCTION dfm_private.persist_award_bundle(
  p_mode text, p_league_id text, p_awards jsonb, p_credits jsonb
)
RETURNS integer
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $function$
DECLARE
  v_prefix text;
  v_awards_table text;
  v_credits_table text;
  v_bad boolean;
  v_count integer;
BEGIN
  v_prefix := CASE p_mode WHEN 'classic' THEN 'drl_classic'
                          WHEN 'draft' THEN 'drl_draft' ELSE NULL END;
  IF v_prefix IS NULL THEN RAISE EXCEPTION 'Unsupported DRL mode'; END IF;
  IF p_league_id IS NULL OR btrim(p_league_id) = ''
     OR jsonb_typeof(p_awards) IS DISTINCT FROM 'array'
     OR jsonb_typeof(p_credits) IS DISTINCT FROM 'array' THEN
    RAISE EXCEPTION 'Invalid award bundle payload' USING ERRCODE = '22023';
  END IF;

  v_awards_table := v_prefix || '_award_records';
  v_credits_table := v_prefix || '_coach_award_credits';

  EXECUTE format(
    'INSERT INTO dfm_private.%I
      (league_id,award_id,category,round_number,player_id,player_name,
       franchise_id,coach_id,base_score,points,position,achievement_only)
     SELECT $1,x.award_id,x.category,x.round_number,x.player_id,x.player_name,
            x.franchise_id,x.coach_id,x.base_score,x.points,x.position,
            coalesce(x.achievement_only,false)
     FROM jsonb_to_recordset($2) AS x(
       award_id text,category text,round_number integer,player_id text,
       player_name text,franchise_id uuid,coach_id text,base_score numeric,
       points integer,position text,achievement_only boolean
     )
     ON CONFLICT DO NOTHING',
    v_awards_table
  ) USING p_league_id,p_awards;

  EXECUTE format(
    'SELECT EXISTS (
       SELECT 1 FROM jsonb_to_recordset($1) AS x(
         award_id text,category text,round_number integer,player_id text,
         player_name text,franchise_id uuid,coach_id text,base_score numeric,
         points integer,position text,achievement_only boolean
       )
       LEFT JOIN dfm_private.%I t
         ON t.league_id=$2 AND t.award_id=x.award_id
       WHERE t.award_id IS NULL
          OR ROW(t.category,t.round_number,t.player_id,t.player_name,
                 t.franchise_id,t.coach_id,t.base_score,t.points,t.position,
                 t.achievement_only)
             IS DISTINCT FROM
             ROW(x.category,x.round_number,x.player_id,x.player_name,
                 x.franchise_id,x.coach_id,x.base_score,x.points,x.position,
                 coalesce(x.achievement_only,false))
     )',
    v_awards_table
  ) INTO v_bad USING p_awards,p_league_id;
  IF v_bad THEN RAISE EXCEPTION 'Award idempotency conflict' USING ERRCODE = '23505'; END IF;

  EXECUTE format(
    'INSERT INTO dfm_private.%I
      (league_id,coach_id,franchise_id,player_id,category,round_number,points)
     SELECT $1,x.coach_id,x.franchise_id,x.player_id,x.category,x.round_number,x.points
     FROM jsonb_to_recordset($2) AS x(
       coach_id text,franchise_id uuid,player_id text,category text,
       round_number integer,points integer
     )
     ON CONFLICT DO NOTHING',
    v_credits_table
  ) USING p_league_id,p_credits;

  EXECUTE format(
    'SELECT EXISTS (
       SELECT 1 FROM jsonb_to_recordset($1) AS x(
         coach_id text,franchise_id uuid,player_id text,category text,
         round_number integer,points integer
       )
       LEFT JOIN dfm_private.%I t
         ON t.league_id=$2 AND t.coach_id=x.coach_id
        AND t.franchise_id=x.franchise_id AND t.player_id=x.player_id
        AND t.category=x.category AND t.round_number=x.round_number
       WHERE t.id IS NULL OR t.points IS DISTINCT FROM x.points
     )',
    v_credits_table
  ) INTO v_bad USING p_credits,p_league_id;
  IF v_bad THEN RAISE EXCEPTION 'Coach credit idempotency conflict' USING ERRCODE = '23505'; END IF;

  v_count := jsonb_array_length(p_awards);
  RETURN v_count;
END;
$function$;

CREATE OR REPLACE FUNCTION dfm_private.persist_news_article(
  p_mode text,p_league_id text,p_article_id text,p_round_number integer,
  p_category text,p_title text,p_summary text,p_content text,p_published boolean
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $function$
DECLARE
  v_prefix text;
  v_table text;
  v_bad boolean;
BEGIN
  v_prefix := CASE p_mode WHEN 'classic' THEN 'drl_classic'
                          WHEN 'draft' THEN 'drl_draft' ELSE NULL END;
  IF v_prefix IS NULL THEN RAISE EXCEPTION 'Unsupported DRL mode'; END IF;
  IF p_league_id IS NULL OR btrim(p_league_id)=''
     OR p_article_id IS NULL OR btrim(p_article_id)=''
     OR p_round_number < 1 THEN
    RAISE EXCEPTION 'Invalid newsroom article identity' USING ERRCODE = '22023';
  END IF;
  v_table := v_prefix || '_news_articles';

  EXECUTE format(
    'INSERT INTO dfm_private.%I
      (league_id,article_id,round_number,category,title,summary,content,published)
     VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
     ON CONFLICT (league_id,article_id) DO NOTHING',
    v_table
  ) USING p_league_id,p_article_id,p_round_number,p_category,p_title,p_summary,p_content,p_published;

  EXECUTE format(
    'SELECT EXISTS (
       SELECT 1 FROM dfm_private.%I
       WHERE league_id=$1 AND article_id=$2
         AND ROW(round_number,category,title,summary,content,published)
             IS DISTINCT FROM ROW($3,$4,$5,$6,$7,$8)
     )',
    v_table
  ) INTO v_bad USING p_league_id,p_article_id,p_round_number,p_category,p_title,p_summary,p_content,p_published;
  IF v_bad THEN RAISE EXCEPTION 'News article idempotency conflict' USING ERRCODE = '23505'; END IF;
  RETURN true;
END;
$function$;

CREATE OR REPLACE FUNCTION dfm_private.persist_ladder_result(
  p_mode text,p_league_id text,p_fixture_id text,p_home_franchise_id uuid,
  p_away_franchise_id uuid,p_home_score numeric,p_away_score numeric,
  p_home_competition_points integer,p_away_competition_points integer
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $function$
DECLARE
  v_prefix text;
  v_table text;
  v_bad boolean;
BEGIN
  v_prefix := CASE p_mode WHEN 'classic' THEN 'drl_classic'
                          WHEN 'draft' THEN 'drl_draft' ELSE NULL END;
  IF v_prefix IS NULL THEN RAISE EXCEPTION 'Unsupported DRL mode'; END IF;
  IF p_league_id IS NULL OR btrim(p_league_id)=''
     OR p_fixture_id IS NULL OR btrim(p_fixture_id)=''
     OR p_home_franchise_id IS NULL OR p_away_franchise_id IS NULL
     OR p_home_franchise_id = p_away_franchise_id
     OR p_home_score < 0 OR p_away_score < 0
     OR p_home_competition_points < 0 OR p_away_competition_points < 0 THEN
    RAISE EXCEPTION 'Invalid finalised ladder result' USING ERRCODE = '22023';
  END IF;
  v_table := v_prefix || '_ladder_match_results';

  EXECUTE format(
    'INSERT INTO dfm_private.%I
      (league_id,fixture_id,home_franchise_id,away_franchise_id,
       home_score,away_score,home_competition_points,away_competition_points,finalised)
     VALUES ($1,$2,$3,$4,$5,$6,$7,$8,true)
     ON CONFLICT (league_id,fixture_id) DO NOTHING',
    v_table
  ) USING p_league_id,p_fixture_id,p_home_franchise_id,p_away_franchise_id,
          p_home_score,p_away_score,p_home_competition_points,p_away_competition_points;

  EXECUTE format(
    'SELECT EXISTS (
       SELECT 1 FROM dfm_private.%I
       WHERE league_id=$1 AND fixture_id=$2
         AND ROW(home_franchise_id,away_franchise_id,home_score,away_score,
                 home_competition_points,away_competition_points,finalised)
             IS DISTINCT FROM ROW($3,$4,$5,$6,$7,$8,true)
     )',
    v_table
  ) INTO v_bad USING p_league_id,p_fixture_id,p_home_franchise_id,p_away_franchise_id,
                     p_home_score,p_away_score,p_home_competition_points,p_away_competition_points;
  IF v_bad THEN RAISE EXCEPTION 'Finalised match idempotency conflict' USING ERRCODE = '23505'; END IF;
  RETURN true;
END;
$function$;

-- Public RPC facade: the only callable route for the trusted server adapter.
-- No direct table grants, private schema USAGE or user-facing execute grants.
CREATE OR REPLACE FUNCTION public.dfm_classic_persist_market_snapshot(
  p_league_id text,p_market_id text,p_market_type text,p_revision integer,
  p_source_id text,p_source_category text,p_source_verified boolean,
  p_source_summary text,p_model_version text,p_official boolean,
  p_outcomes jsonb,p_movements jsonb
) RETURNS uuid LANGUAGE sql SECURITY DEFINER SET search_path = ''
AS $$ SELECT dfm_private.persist_market_snapshot(
  'classic',$1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12
) $$;

CREATE OR REPLACE FUNCTION public.dfm_draft_persist_market_snapshot(
  p_league_id text,p_market_id text,p_market_type text,p_revision integer,
  p_source_id text,p_source_category text,p_source_verified boolean,
  p_source_summary text,p_model_version text,p_official boolean,
  p_outcomes jsonb,p_movements jsonb
) RETURNS uuid LANGUAGE sql SECURITY DEFINER SET search_path = ''
AS $$ SELECT dfm_private.persist_market_snapshot(
  'draft',$1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12
) $$;

CREATE OR REPLACE FUNCTION public.dfm_classic_persist_award_bundle(
  p_league_id text,p_awards jsonb,p_credits jsonb
) RETURNS integer LANGUAGE sql SECURITY DEFINER SET search_path = ''
AS $$ SELECT dfm_private.persist_award_bundle('classic',$1,$2,$3) $$;

CREATE OR REPLACE FUNCTION public.dfm_draft_persist_award_bundle(
  p_league_id text,p_awards jsonb,p_credits jsonb
) RETURNS integer LANGUAGE sql SECURITY DEFINER SET search_path = ''
AS $$ SELECT dfm_private.persist_award_bundle('draft',$1,$2,$3) $$;

CREATE OR REPLACE FUNCTION public.dfm_classic_persist_news_article(
  p_league_id text,p_article_id text,p_round_number integer,p_category text,
  p_title text,p_summary text,p_content text,p_published boolean
) RETURNS boolean LANGUAGE sql SECURITY DEFINER SET search_path = ''
AS $$ SELECT dfm_private.persist_news_article('classic',$1,$2,$3,$4,$5,$6,$7,$8) $$;

CREATE OR REPLACE FUNCTION public.dfm_draft_persist_news_article(
  p_league_id text,p_article_id text,p_round_number integer,p_category text,
  p_title text,p_summary text,p_content text,p_published boolean
) RETURNS boolean LANGUAGE sql SECURITY DEFINER SET search_path = ''
AS $$ SELECT dfm_private.persist_news_article('draft',$1,$2,$3,$4,$5,$6,$7,$8) $$;

CREATE OR REPLACE FUNCTION public.dfm_classic_persist_ladder_result(
  p_league_id text,p_fixture_id text,p_home_franchise_id uuid,p_away_franchise_id uuid,
  p_home_score numeric,p_away_score numeric,p_home_competition_points integer,
  p_away_competition_points integer
) RETURNS boolean LANGUAGE sql SECURITY DEFINER SET search_path = ''
AS $$ SELECT dfm_private.persist_ladder_result(
  'classic',$1,$2,$3,$4,$5,$6,$7,$8
) $$;

CREATE OR REPLACE FUNCTION public.dfm_draft_persist_ladder_result(
  p_league_id text,p_fixture_id text,p_home_franchise_id uuid,p_away_franchise_id uuid,
  p_home_score numeric,p_away_score numeric,p_home_competition_points integer,
  p_away_competition_points integer
) RETURNS boolean LANGUAGE sql SECURITY DEFINER SET search_path = ''
AS $$ SELECT dfm_private.persist_ladder_result(
  'draft',$1,$2,$3,$4,$5,$6,$7,$8
) $$;

REVOKE ALL ON FUNCTION public.dfm_classic_persist_market_snapshot(text,text,text,integer,text,text,boolean,text,text,boolean,jsonb,jsonb) FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.dfm_draft_persist_market_snapshot(text,text,text,integer,text,text,boolean,text,text,boolean,jsonb,jsonb) FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.dfm_classic_persist_award_bundle(text,jsonb,jsonb) FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.dfm_draft_persist_award_bundle(text,jsonb,jsonb) FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.dfm_classic_persist_news_article(text,text,integer,text,text,text,text,boolean) FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.dfm_draft_persist_news_article(text,text,integer,text,text,text,text,boolean) FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.dfm_classic_persist_ladder_result(text,text,uuid,uuid,numeric,numeric,integer,integer) FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.dfm_draft_persist_ladder_result(text,text,uuid,uuid,numeric,numeric,integer,integer) FROM PUBLIC, anon, authenticated, service_role;

GRANT EXECUTE ON FUNCTION public.dfm_classic_persist_market_snapshot(text,text,text,integer,text,text,boolean,text,text,boolean,jsonb,jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION public.dfm_draft_persist_market_snapshot(text,text,text,integer,text,text,boolean,text,text,boolean,jsonb,jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION public.dfm_classic_persist_award_bundle(text,jsonb,jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION public.dfm_draft_persist_award_bundle(text,jsonb,jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION public.dfm_classic_persist_news_article(text,text,integer,text,text,text,text,boolean) TO service_role;
GRANT EXECUTE ON FUNCTION public.dfm_draft_persist_news_article(text,text,integer,text,text,text,text,boolean) TO service_role;
GRANT EXECUTE ON FUNCTION public.dfm_classic_persist_ladder_result(text,text,uuid,uuid,numeric,numeric,integer,integer) TO service_role;
GRANT EXECUTE ON FUNCTION public.dfm_draft_persist_ladder_result(text,text,uuid,uuid,numeric,numeric,integer,integer) TO service_role;

REVOKE ALL ON FUNCTION dfm_private.persist_market_snapshot(text,text,text,text,integer,text,text,boolean,text,text,boolean,jsonb,jsonb) FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION dfm_private.persist_award_bundle(text,text,jsonb,jsonb) FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION dfm_private.persist_news_article(text,text,text,integer,text,text,text,text,boolean) FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION dfm_private.persist_ladder_result(text,text,text,uuid,uuid,numeric,numeric,integer,integer) FROM PUBLIC, anon, authenticated, service_role;

COMMIT;
