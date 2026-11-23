# DRL NRL Player Photo Extraction Engine

## Purpose

Discover two photograph categories for the 2026 DRL NRL player archive:

1. NRL Fantasy player profile photographs.
2. Genuine NRL match-action photographs from official NRL and club pages.

The engine reads a local JARVIS player export and writes a local JSON manifest plus eligible image files to private staging. It does **not** connect to Supabase, modify JARVIS, upload to Storage, deploy Cloudflare or publish images.

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
- No JARVIS writes, uploads or publication occur.

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

## Audit downloaded files

\`\`\`sh
python photo_audit.py \\
  --manifest /path/to/private-staging/photo-manifest-2026.json \\
  --staging /path/to/private-staging/images \\
  --output /path/to/private-staging/photo-audit-2026.json
\`\`\`

The audit reports candidates, downloaded files, missing files, duplicate SHA-256 hashes, image formats and readable dimensions.

## Tests

\`\`\`sh
python -m unittest discover -s tests/unit -p 'test_*.py' -v
\`\`\`

## Current limitations

- The current JARVIS export does not guarantee Fantasy player-page URLs or club match-photo page URLs. Supply these in the optional fields; this implementation deliberately does not invent an endpoint or search result.
- NRL directory matching is limited to squad IDs already defined by the existing player-profile extractor.
- Page parsing discovers image candidates; it cannot prove that an image depicts the named player in genuine match action. Human confirmation remains mandatory.
- Rights metadata must be supplied and evidenced. A source domain alone never clears copyright.
- This stage is local private staging only. Separate approval is required before any upload to JARVIS or publication/delivery change.
