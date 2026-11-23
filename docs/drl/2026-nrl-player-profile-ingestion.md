# DRL 2026 NRL player profiles — ingestion and rights workflow

## Current source-of-truth position

- JARVIS currently contains 588 rows in `dfm_private.drl_nrl_players_2026`.
- All 588 rows have a `drl_player_id` foreign-key link, but only 416 seasonal identity mappings are marked verified. Do not treat the remaining 172 as verified.
- Existing fantasy fields in `stats` and the original `source_record` must remain untouched.
- NRL's official player pages expose a 2026 season-by-round table. The page structure observed includes tries, points, try assists, line breaks, tackles made, missed tackles and total running metres. Some requested fields (errors and penalties conceded) were not present in the inspected public profile table and must remain NULL until a verified source supplies them.
- NRL player pages also link to Stats Perform profile headshots. These are not action photographs. The preferred image order is licensed in-action photograph, permission-cleared club/photographer action photograph, then NRL/Stats Perform profile image where its usage rights are cleared.

## Data model

The migration adds two private tables:

- `dfm_private.drl_nrl_player_season_stats`: normalized NRL season totals, keyed by season and permanent DRL player ID, with source URL, import time and raw source evidence.
- `dfm_private.drl_nrl_player_media`: media source, storage path, identity verification, photographer credit and rights status.

A private Storage bucket named `drl-player-media` is created. No public bucket or browser-role Storage policy is created. Media remains unavailable to the public until an authenticated server-side delivery route is implemented and rights are cleared.

## Identity matching

1. Use the existing season source map and its source player ID / squad ID.
2. Require a verified permanent `drl_player_id` before attaching statistics or a photograph to the master player.
3. Never merge on name alone. Names are not unique and can change.
4. Store unresolved candidate records separately for review; do not silently attach them to a different player.

## Requested 2026 fields

| Field | Official profile table mapping |
|---|---|
| Appearances | Count of played round rows |
| Tries | Sum of Tries |
| Try assists | Sum of Try Assists |
| Points | Sum of Points |
| Tackles | Sum of Tackles Made |
| Tackle efficiency | Official profile Defence summary, when supplied |
| Metres gained | Sum of Total Running Metres |
| Line breaks | Sum of Linebreaks |
| Errors | NULL unless a verified source supplies it |
| Penalties conceded | NULL unless a verified source supplies it |

A dash or missing column is not converted to a fabricated zero. The raw source table and profile URL must be retained for auditability.

## Rights and publication gate

A discoverable image URL is not proof of permission to copy or republish. Record the original source, photographer credit and rights status. Keep all candidate media at `pending_review`; only `licensed`, `permission_granted`, or `public_domain` assets with verified player identity can be published. Rejected or unverified assets must never be served.

## Deployment sequence

1. Reconcile the four already-applied database migration IDs that are absent from the Git repository before applying this migration.
2. Review and apply the migration through the normal migration process.
3. Build the authenticated Cloudflare API route to read private schema data server-side and issue short-lived signed media URLs.
4. Run a 588-player NRL profile extraction batch, with identity verification before import.
5. Complete media rights review and upload only cleared images.
6. Connect the DRL roster/profile UI to the authenticated API; do not query `dfm_private` directly from the browser.

No live database schema changes or public media publication are performed by this PR.

## Authenticated frontend response contract

The DRL roster UI expects the same-origin authenticated route:

`GET /api/drl/nrl/players?season=2026`

Response shape:

```json
{
  "season": 2026,
  "source_status": "connected",
  "players": [{
    "drl_player_id": 12345,
    "first_name": "Verified first name",
    "last_name": "Verified last name",
    "team_name": "Verified club",
    "position": "Verified position",
    "photo_url": "short-lived signed URL or null",
    "photo_alt": "Accessible image description",
    "stats": {
      "appearances": null,
      "tries": null,
      "try_assists": null,
      "points": null,
      "tackles": null,
      "tackle_efficiency": null,
      "metres_gained": null,
      "line_breaks": null,
      "errors": null,
      "penalties_conceded": null
    }
  }]
}
```

The API must authenticate the session, read `dfm_private` server-side only, filter out unverified identity mappings, and return a signed URL only for media whose player identity is verified and whose rights status is cleared. Never return the private Storage object path, source-only image URL, database credentials, or raw source payload to the browser.

The frontend calls the authenticated same-origin Cloudflare API route. The implementation and required secret bindings are described in the Cloudflare authenticated profile API section below. The Worker is committed for review but has not been deployed.

## Authenticated frontend response contract

The DRL roster UI expects the same-origin authenticated route:

`GET /api/drl/nrl/players?season=2026`

Response shape:

```json
{
  "season": 2026,
  "source_status": "connected",
  "players": [{
    "drl_player_id": 12345,
    "first_name": "Verified first name",
    "last_name": "Verified last name",
    "team_name": "Verified club",
    "position": "Verified position",
    "photo_url": "short-lived signed URL or null",
    "photo_alt": "Accessible image description",
    "stats": {
      "appearances": null, "tries": null, "try_assists": null, "points": null,
      "tackles": null, "tackle_efficiency": null, "metres_gained": null,
      "line_breaks": null, "errors": null, "penalties_conceded": null
    }
  }]
}
```

The API must authenticate the session, read `dfm_private` server-side only, filter out unverified identity mappings, and return a signed URL only for media whose player identity is verified and whose rights status is cleared. Never return the private Storage object path, source-only image URL, database credentials, or raw source payload to the browser.

The frontend intentionally shows a disconnected state until this authenticated Cloudflare API route is implemented. This PR does not change Cloudflare Worker routing because that is a separate infrastructure change requiring its own approval.

## Cloudflare authenticated profile API (implementation branch)

The Worker entry point is `frontend/cloudflare/worker.ts`; Wrangler serves the built frontend through the `ASSETS` binding and runs the Worker first for `/api/*`. The only player API handler currently accepted is the same-origin GET route documented above.

Required Cloudflare Worker secret bindings (configure through the Cloudflare secret manager; never commit values):
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`

The browser uses the existing pinned `@supabase/supabase-js` dependency and public build-time settings `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`. These are client configuration values, not privileged credentials. The browser sends the current access token in the Authorization header. The Worker validates it by calling Supabase Auth's user endpoint; it does not trust decoded claims or client-supplied user IDs.

After successful authentication, the Worker calls `public.drl_nrl_player_profiles_read` using its server-only service-role binding. The function is a fixed-search-path SECURITY DEFINER function, with EXECUTE revoked from PUBLIC, anon and authenticated and granted only to service_role. It returns verified master identities and season statistics, and only media paths with verified identity plus cleared rights status. The Worker uses any returned media path internally to request a five-minute signed URL; the storage path and original source URL are never returned to the browser.

The current master schema does not provide team or playing-position columns in the verified player master record, and the new season statistics table does not add them. The API therefore returns null for team and position rather than inventing values. The API returns only the 2026 season until additional season data and identity mapping are verified.

This branch does not configure live Worker secrets, apply the SQL migration, deploy the Worker, or publish any media. Those operations require their own operational approval and migration-history reconciliation.


## 2026 action-photo completion requirement

The target is one genuine match-action photograph for every player in the 2026 player archive, showing the player in their current club's playing uniform. A headshot, training image, generic team image, or former-club uniform does not satisfy the requirement.

The archive contains 588 player rows, but only 416 seasonal identity mappings were previously confirmed as verified; 172 remain unresolved. The unresolved identities must be reconciled before any image is attached to those permanent DRL player IDs. Do not infer identity from name alone. Current-club verification is a separate gate and must use the current 2026 squad assignment, not an old club assignment.

### Source and review policy

- Prefer official NRL match reports, official NRL media, and official club match-report/media pages.
- Candidate discovery is free/manual and source-page based; no paid scraping, stock-photo service, or image API is used.
- Each candidate must identify the exact player, current squad ID and club, original image URL, official source page, photographer credit, rights status and evidence URL.
- A human reviewer must confirm the correct player, genuine match action, and current club uniform.
- A discoverable image is not a licence. Only `licensed`, `permission_granted`, or `public_domain` with a recorded HTTPS evidence URL can progress to upload review.
- Candidates remain private and unpublished. The validator never downloads, uploads, writes to JARVIS, or publishes images.

### Candidate validation

Run `backend/dfm/drl/nrl/extractor/player_media.py` on Android Termux or another Python 3 environment with the two JSON inputs exported locally:

```sh
python player_media.py --players jarvis-verified-players-2026.json --candidates action-photo-candidates-2026.json --output action-photo-review-2026.json
```

The player export must contain `drl_player_id`, `squad_id`, and `identity_status`. Candidate rows must contain:

- `drl_player_id`, `season` (2026), `squad_id`, `current_club_name`
- `current_club_verified: true`, `current_club_source_url` (official NRL/club squad evidence)
- `image_url`, `source_page_url`, `photographer_credit`
- `rights_status`, `rights_evidence_url`
- `identity_confirmed: true`, `action_photo_confirmed: true`, `current_uniform_confirmed: true`

The validator rejects unverified player identities, mismatched squad IDs, unverified current-club assignments, missing official club evidence, non-HTTPS URLs, non-official source pages, missing visual confirmations, uncleared rights, and duplicate player-season candidates. A result marked `ready_for_separate_upload_approval` is only a reviewed candidate; it is not uploaded or published.

### Private media record and publication gate

The migration `20261123120000_add_drl_player_media_workflow.sql` adds current-club, current-squad, action-photo verification, uniform verification, source-page and rights-evidence fields to the existing private media table. It is committed for review only and has NOT been applied.

The authenticated read function returns an action image only when permanent player identity is verified, action-photo and current-uniform review flags are true, rights status is cleared with evidence, and a private Storage object path exists. The Cloudflare Worker signs only that private stored object. It never returns original source URLs, rights evidence, or private Storage paths to the browser.

### Frontend behaviour

The DRL player list and profile show only media explicitly marked `verified_action_photo`. Otherwise, the UI displays `PHOTO PENDING`; it does not substitute a headshot or an unverified image.

### Operational boundaries

This PR changes GitHub source files only. It does not apply migrations, write to JARVIS, export player data, download/upload photographs, configure Cloudflare secrets, deploy a Worker, or merge itself. Each of those actions requires separate approval.
