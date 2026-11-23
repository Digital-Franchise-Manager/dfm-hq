-- Private NRL player profiles: official season statistics and rights-tracked media metadata.
-- This migration is intentionally private. No Data API grants or public Storage policies are created.

create table if not exists dfm_private.drl_nrl_player_season_stats (
  season smallint not null,
  drl_player_id bigint not null references dfm_private.drl_nrl_player_master(drl_player_id) on update cascade on delete restrict,
  appearances smallint,
  tries smallint,
  try_assists smallint,
  points smallint,
  tackles smallint,
  tackle_efficiency numeric(5,2),
  metres_gained integer,
  line_breaks smallint,
  errors smallint,
  penalties_conceded smallint,
  source_provider text not null default 'nrl.com',
  source_profile_url text,
  source_updated_at timestamptz,
  imported_at timestamptz not null default now(),
  raw_source jsonb not null default '{}'::jsonb,
  primary key (season, drl_player_id),
  constraint drl_nrl_player_season_stats_season_check check (season between 1998 and 2100),
  constraint drl_nrl_player_season_stats_nonnegative check (
    (appearances is null or appearances >= 0) and
    (tries is null or tries >= 0) and
    (try_assists is null or try_assists >= 0) and
    (points is null or points >= 0) and
    (tackles is null or tackles >= 0) and
    (metres_gained is null or metres_gained >= 0) and
    (line_breaks is null or line_breaks >= 0) and
    (errors is null or errors >= 0) and
    (penalties_conceded is null or penalties_conceded >= 0)
  ),
  constraint drl_nrl_player_season_stats_efficiency_check check (
    tackle_efficiency is null or (tackle_efficiency >= 0 and tackle_efficiency <= 100)
  )
);

create index if not exists drl_nrl_player_season_stats_season_rank_idx
  on dfm_private.drl_nrl_player_season_stats (season, points desc nulls last);
create index if not exists drl_nrl_player_season_stats_player_idx
  on dfm_private.drl_nrl_player_season_stats (drl_player_id, season desc);

create table if not exists dfm_private.drl_nrl_player_media (
  drl_player_id bigint not null references dfm_private.drl_nrl_player_master(drl_player_id) on update cascade on delete restrict,
  season smallint not null,
  media_kind text not null default 'action_photo',
  storage_object_path text,
  source_url text not null,
  source_provider text not null,
  photographer_credit text,
  rights_status text not null default 'pending_review',
  verified_identity boolean not null default false,
  verified_by text,
  verified_at timestamptz,
  alt_text text,
  width_px integer,
  height_px integer,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (drl_player_id, season, media_kind),
  constraint drl_nrl_player_media_kind_check check (media_kind in ('action_photo', 'profile_photo')),
  constraint drl_nrl_player_media_rights_check check (
    rights_status in ('pending_review', 'licensed', 'permission_granted', 'public_domain', 'rejected')
  ),
  constraint drl_nrl_player_media_dimensions_check check (
    (width_px is null or width_px > 0) and (height_px is null or height_px > 0)
  )
);

create index if not exists drl_nrl_player_media_rights_idx
  on dfm_private.drl_nrl_player_media (rights_status, verified_identity);

alter table dfm_private.drl_nrl_player_season_stats enable row level security;
alter table dfm_private.drl_nrl_player_media enable row level security;

-- Defense in depth: the schema is not exposed in Supabase Data API config,
-- and browser roles receive no direct table privileges.
revoke all on table dfm_private.drl_nrl_player_season_stats from anon, authenticated;
revoke all on table dfm_private.drl_nrl_player_media from anon, authenticated;

-- A private bucket is used for reviewed/licensed copies only. No public URL access.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'drl-player-media',
  'drl-player-media',
  false,
  5242880,
  array['image/jpeg', 'image/png', 'image/webp']
)
on conflict (id) do update
set public = false,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

-- No storage.objects policies are added for anon/authenticated.
-- Server-side privileged ingestion and authorized signed-URL delivery must be
-- implemented behind the authenticated Cloudflare API before media is served.
