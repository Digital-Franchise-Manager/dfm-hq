# DRL NRL Player Photo Extraction Engine

## Purpose

Discover two photograph categories for the 2026 DRL NRL player archive:

1. NRL Fantasy player profile photographs.
2. Genuine NRL match-action photographs from official NRL and club pages.

The engine reads a local JARVIS player export and writes a local JSON manifest plus eligible image files to private staging. Its optional `player_media.py --sync-jarvis` stage uploads only downloaded, human-verified and rights-cleared images to the private Supabase Storage bucket `drl-player-media`, then registers metadata through a service-role-only database function. It does not deploy Cloudflare or publish images.

## Safety and rights gates

- Only player rows with \`identity_status\` exactly \`verified\` are processed.
- Player identity uses permanent DRL player ID, current squad ID and exact first/last name when resolving the official NRL directory.
- NRL Fantasy pages must be supplied as \`fantasy_profile_url\`; the engine does not guess undocumented Fantasy APIs.
- Club action-photo pages must be supplied as \`action_photo_pages\`.
- Source pages and image URLs must remain on the HTTPS allow-list in \`photo_sources.py\`.
- Redirect destinations are revalidated. Off-domain redirects are rejected.
- Authentication, bot protections, paywalls and access restrictions are never bypassed.
- A publicly viewable image is not proof of reuse rights.
- Automatic downloads occur only when identity, profile/action type and rights evidence are confirmed. Accepted rights statuses are \`licensed\`, \`permission_granted\` and \`public_domain\`.
- Action photographs additionally require human confirmation of genuine match action, current uniform and current-club assignment.
- Keep the local staging directory outside the Git repository and do not sync it publicly.
- Discovery and validation do not write to JARVIS. The separate `--sync-jarvis` command is the only upload path and requires a privileged server-side key supplied through the private Termux environment. The key is never stored in this repository, the manifest or the report.
- The Storage bucket is private. Uploaded objects are not public URLs; the app must retrieve them through an authenticated backend or short-lived signed URLs.
- The metadata table remains in the private `dfm_private` schema. The uploader calls a narrowly scoped `public.drl_register_player_photo_asset(jsonb)` function whose execution is revoked from `anon` and `authenticated` and granted only to `service_role`.

## Android 13 / Termux setup

\`\`\`sh
pkg update
pkg install python
python --version
\`\`\`

No third-party Python package is required.

## Player export format

The private JSON export is an array of objects. Required fields:

- \`drl_player_id\`
- \`first_name\`
- \`last_name\`
- \`squad_id\`
- \`identity_status\`

Optional source/review fields:

- \`fantasy_profile_url\`: one URL or an array on \`fantasy.nrl.com\`
- \`nrl_profile_url\`, \`nrl_profile_image_url\`: official NRL profile references; if omitted, the NRL directory can be checked for supported verified squads
- \`action_photo_pages\`: one URL or an array of official club pages
- \`current_club_name\`, \`current_club_verified\`, \`current_club_source_url\`
- \`identity_confirmed\`, \`profile_photo_confirmed\`
- \`action_photo_confirmed\`, \`current_uniform_confirmed\`
- \`rights_status\`, \`rights_evidence_url\`, \`photographer_credit\`

Missing source URLs are not fabricated. If Fantasy or club page references are absent from the export, those source categories remain undiscovered until valid references are supplied.

## Run the engine

Run from the extractor directory:

\`\`\`sh
python photo_discovery.py \\
  --players /path/to/private-jarvis-player-export.json \\
  --manifest /path/to/private-staging/photo-manifest-2026.json \\
  --staging /path/to/private-staging/images \\
  --delay 1.5
\`\`\`

The default mode downloads only candidates that pass every verification and rights gate. Use \`--no-download\` for discovery-only mode.

## Validate candidates separately

\`\`\`sh
python player_media.py \\
  --players /path/to/private-jarvis-player-export.json \\
  --candidates /path/to/private-staging/photo-manifest-2026.json \\
  --output /path/to/private-staging/photo-validation-report.json
\`\`\`

The validator accepts the complete manifest produced by \`photo_discovery.py\`.

## Upload approved photographs into JARVIS

The Supabase project must already contain the private `drl-player-media` bucket, the private `dfm_private.drl_nrl_player_photo_assets` table, and the restricted `public.drl_register_player_photo_asset(jsonb)` function. The uploader uses the project URL and a privileged server-side key only from environment variables.

Never put a secret/service-role key in GitHub, the player export, a manifest, a report, screenshots, browser code or the app's public environment variables. Do not paste credentials into ChatGPT. Keep the key only in Termux's private environment on your own device.

Set the variables in the current Termux session without echoing the secret:

```sh
read -r -p "Supabase project URL: " SUPABASE_URL
read -r -s -p "Supabase secret/service-role key: " SUPABASE_SECRET_KEY
printf '\\n'
export SUPABASE_URL SUPABASE_SECRET_KEY
```

Run the upload stage only after discovery, human identity review and rights review are complete:

```sh
python player_media.py \\
  --players /path/to/private-jarvis-player-export.json \\
  --candidates /path/to/private-staging/photo-manifest-2026.json \\
  --staging /path/to/private-staging/images \\
  --output /path/to/private-staging/jarvis-photo-upload-report.json \\
  --sync-jarvis
```

Only manifest entries with status `downloaded_private` are considered. Every candidate is revalidated against the full player export and the identity, current-club (for action photos), and reuse-rights gates. The uploader verifies the local file's actual image signature, dimensions, checksum and 10 MB bucket limit before transfer. Object paths are deterministic and contain the permanent DRL player ID and SHA-256 checksum. It records the object path and source/rights metadata in JARVIS; it does not create public URLs.

The upload report records success/failure without printing credentials or full request URLs. A failed metadata registration may leave an unreferenced private object in Storage; review the report before retrying. The upload operation is idempotent for the same player, media type and image checksum.

Profile records are marked primary only when that player does not already have a primary profile image. Action photographs are never marked as the primary profile image.

## Audit downloaded files

\`\`\`sh
python photo_audit.py \\
  --manifest /path/to/private-staging/photo-manifest-2026.json \\
  --players /path/to/private-jarvis-player-export.json \\
  --staging /path/to/private-staging/images \\
  --output /path/to/private-staging/photo-audit-2026.json
\`\`\`

The audit compares downloaded profile and action photos against the supplied player export, and reports missing players, duplicate SHA-256 hashes, image formats and readable dimensions.

## Tests

\`\`\`sh
python -m unittest discover -s tests/unit -p 'test_*.py' -v
\`\`\`

## Current limitations

- The JARVIS export does not guarantee Fantasy player-page URLs or club match-photo page URLs. Supply these in the optional fields; this implementation deliberately does not invent an endpoint or search result.
- NRL directory matching is limited to squad IDs already defined by the existing player-profile extractor.
- Page parsing discovers image candidates; it cannot prove that an image depicts the named player in genuine match action. Human confirmation remains mandatory.
- Rights metadata must be supplied and evidenced. A source domain alone never clears copyright.
- Discovery and validation remain local-only. The separately invoked `--sync-jarvis` mode uploads only approved local files into private JARVIS storage. Publication or delivery changes remain out of scope.
