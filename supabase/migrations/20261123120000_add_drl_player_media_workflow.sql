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
