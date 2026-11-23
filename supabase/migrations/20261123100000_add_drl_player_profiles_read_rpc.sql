-- Narrow PostgREST entry point for the Cloudflare Worker.
-- The function is callable only by service_role. It exposes no private table
-- privileges to anon/authenticated and returns only verified player identities,
-- season statistics, and rights-cleared media object paths for server signing.

create or replace function public.drl_nrl_player_profiles_read(p_season smallint)
returns table (
  drl_player_id bigint,
  first_name text,
  last_name text,
  appearances smallint,
  tries smallint,
  try_assists smallint,
  points smallint,
  tackles smallint,
  tackle_efficiency numeric,
  metres_gained integer,
  line_breaks smallint,
  errors smallint,
  penalties_conceded smallint,
  storage_object_path text,
  photo_alt text
)
language sql
stable
security definer
set search_path = pg_catalog, public, dfm_private
as $function$
  select
    master.drl_player_id,
    master.first_name,
    master.last_name,
    stats.appearances,
    stats.tries,
    stats.try_assists,
    stats.points,
    stats.tackles,
    stats.tackle_efficiency,
    stats.metres_gained,
    stats.line_breaks,
    stats.errors,
    stats.penalties_conceded,
    media.storage_object_path,
    media.alt_text
  from dfm_private.drl_nrl_player_master as master
  left join dfm_private.drl_nrl_player_season_stats as stats
    on stats.drl_player_id = master.drl_player_id
   and stats.season = p_season
  left join lateral (
    select candidate.storage_object_path, candidate.alt_text
    from dfm_private.drl_nrl_player_media as candidate
    where candidate.drl_player_id = master.drl_player_id
      and candidate.season = p_season
      and candidate.verified_identity is true
      and candidate.rights_status in ('licensed', 'permission_granted', 'public_domain')
      and candidate.storage_object_path is not null
    order by case candidate.media_kind when 'action_photo' then 0 else 1 end
    limit 1
  ) as media on true
  where master.identity_status = 'verified'
  order by master.last_name, master.first_name, master.drl_player_id;
$function$;

revoke all on function public.drl_nrl_player_profiles_read(smallint) from public;
revoke all on function public.drl_nrl_player_profiles_read(smallint) from anon, authenticated;
grant execute on function public.drl_nrl_player_profiles_read(smallint) to service_role;
