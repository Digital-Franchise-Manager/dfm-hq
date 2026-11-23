-- Add explicit current-club, action-context, uniform and rights-evidence gates.
-- This migration is committed for review only; it has NOT been applied to JARVIS.

alter table dfm_private.drl_nrl_player_media
  add column if not exists current_squad_id bigint,
  add column if not exists current_club_name text,
  add column if not exists action_photo_verified boolean not null default false,
  add column if not exists uniform_verified boolean not null default false,
  add column if not exists source_page_url text,
  add column if not exists rights_evidence_url text;

alter table dfm_private.drl_nrl_player_media
  add constraint drl_nrl_player_media_action_gate_check
  check (
    (action_photo_verified is false or media_kind = 'action_photo') and
    (uniform_verified is false or media_kind = 'action_photo')
  );

alter table dfm_private.drl_nrl_player_media
  add constraint drl_nrl_player_media_source_urls_https_check
  check (
    (source_page_url is null or source_page_url ~ '^https://') and
    (rights_evidence_url is null or rights_evidence_url ~ '^https://')
  );

create index if not exists drl_nrl_player_media_current_club_idx
  on dfm_private.drl_nrl_player_media (season, current_squad_id, rights_status);


-- Replace the read RPC after the media review columns exist. The function
-- exposes only the club label and signed-media input for a fully approved
-- action photo; it never exposes source or rights-evidence URLs.
drop function if exists public.drl_nrl_player_profiles_read(smallint);

create function public.drl_nrl_player_profiles_read(p_season smallint)
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
  photo_alt text,
  current_club_name text,
  current_squad_id bigint
)
language sql
stable
security definer
set search_path = pg_catalog, dfm_private
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
    media.alt_text,
    media.current_club_name,
    media.current_squad_id
  from dfm_private.drl_nrl_player_master as master
  left join dfm_private.drl_nrl_player_season_stats as stats
    on stats.drl_player_id = master.drl_player_id
   and stats.season = p_season
  left join lateral (
    select
      candidate.storage_object_path,
      candidate.alt_text,
      candidate.current_club_name,
      candidate.current_squad_id
    from dfm_private.drl_nrl_player_media as candidate
    where candidate.drl_player_id = master.drl_player_id
      and candidate.season = p_season
      and candidate.media_kind = 'action_photo'
      and candidate.verified_identity is true
      and candidate.action_photo_verified is true
      and candidate.uniform_verified is true
      and candidate.rights_status in ('licensed', 'permission_granted', 'public_domain')
      and candidate.rights_evidence_url is not null
      and candidate.storage_object_path is not null
      and candidate.current_squad_id is not null
      and candidate.current_club_name is not null
    order by candidate.updated_at desc
    limit 1
  ) as media on true
  where master.identity_status = 'verified'
  order by master.last_name, master.first_name, master.drl_player_id;
$function$;

revoke all on function public.drl_nrl_player_profiles_read(smallint) from public;
revoke all on function public.drl_nrl_player_profiles_read(smallint) from anon, authenticated;
grant execute on function public.drl_nrl_player_profiles_read(smallint) to service_role;
