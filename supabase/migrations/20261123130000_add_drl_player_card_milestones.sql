-- DRL player card milestones and verified achievement cards.
-- GitHub migration only: do not apply to JARVIS without the normal migration approval.

create table if not exists dfm_private.drl_nrl_player_career_totals (
  drl_player_id bigint primary key
    references dfm_private.drl_nrl_player_master(drl_player_id)
    on update cascade on delete restrict,
  career_appearances integer not null check (career_appearances >= 0),
  source_provider text not null default 'nrl.com',
  source_profile_url text not null check (source_profile_url ~ '^https://'),
  source_updated_at timestamptz,
  verified boolean not null default false,
  verified_by text,
  verified_at timestamptz,
  raw_source jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint drl_nrl_player_career_verified_audit_check check (
    verified is false or (verified_by is not null and verified_at is not null)
  )
);

create table if not exists dfm_private.drl_nrl_player_achievement_cards (
  achievement_id bigint generated always as identity primary key,
  drl_player_id bigint not null
    references dfm_private.drl_nrl_player_master(drl_player_id)
    on update cascade on delete restrict,
  card_code text not null check (card_code in (
    'state_of_origin_blue',
    'state_of_origin_burgundy',
    'gold',
    'silver',
    'bronze'
  )),
  award_season smallint not null check (award_season between 1908 and 2100),
  evidence_url text not null check (evidence_url ~ '^https://'),
  verified boolean not null default false,
  verified_by text,
  verified_at timestamptz,
  created_at timestamptz not null default now(),
  unique (drl_player_id, card_code, award_season),
  constraint drl_nrl_player_achievement_verified_audit_check check (
    verified is false or (verified_by is not null and verified_at is not null)
  )
);

create index if not exists drl_nrl_player_achievement_cards_player_idx
  on dfm_private.drl_nrl_player_achievement_cards (drl_player_id, card_code)
  where verified is true;

alter table dfm_private.drl_nrl_player_career_totals enable row level security;
alter table dfm_private.drl_nrl_player_achievement_cards enable row level security;

revoke all on table dfm_private.drl_nrl_player_career_totals from public, anon, authenticated;
revoke all on table dfm_private.drl_nrl_player_achievement_cards from public, anon, authenticated;

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
  current_squad_id bigint,
  career_appearances integer,
  achievement_cards jsonb
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
    media.current_squad_id,
    career.career_appearances,
    coalesce((
      select jsonb_agg(distinct achievement.card_code)
      from dfm_private.drl_nrl_player_achievement_cards as achievement
      where achievement.drl_player_id = master.drl_player_id
        and achievement.verified is true
    ), '[]'::jsonb) as achievement_cards
  from dfm_private.drl_nrl_player_master as master
  left join dfm_private.drl_nrl_player_season_stats as stats
    on stats.drl_player_id = master.drl_player_id
   and stats.season = p_season
  left join dfm_private.drl_nrl_player_career_totals as career
    on career.drl_player_id = master.drl_player_id
   and career.verified is true
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
