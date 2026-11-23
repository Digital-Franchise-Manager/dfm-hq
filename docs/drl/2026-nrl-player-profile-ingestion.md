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

The frontend intentionally shows a disconnected state until this authenticated Cloudflare API route is implemented. This PR does not change Cloudflare Worker routing because that is a separate infrastructure change requiring its own approval.

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
