# DRL 2026 NRL player profiles — ingestion and rights workflow

## Action-photo completion requirement

The target is one genuine match-action photograph for every player in the 2026 player archive, showing the player in their current club's playing uniform. A headshot, training image, generic team image, or former-club uniform does not satisfy the requirement.

The archive currently contains 588 player rows. Identity verification and current-club verification are separate gates: do not infer the current club from a name, an old squad assignment, or a photograph caption. Use the current 2026 squad assignment and a verified permanent `drl_player_id`. Unresolved identity/current-club records remain flagged for review and must not receive an attached photo.

## Source and review policy

- Prefer official NRL match reports, official NRL media, and official club match-report/media pages.
- Candidate discovery is free/manual and source-page based; no paid scraping, stock-photo service, or image API is used.
- The action-photo candidate manifest must identify the exact player, current squad ID and club, original image URL, official source page, photographer credit, rights status and evidence URL.
- A human reviewer must confirm all three visual facts: correct player, genuine match action, and current club uniform.
- A discoverable image is not a licence. Only `licensed`, `permission_granted`, or `public_domain` with a recorded HTTPS evidence URL can progress to upload review.
- Candidates remain private and unpublished. The validator never downloads, uploads, writes to JARVIS, or publishes images.

## Candidate validation

Run `backend/dfm/drl/nrl/extractor/player_media.py` on Android Termux or another Python 3 environment with the two JSON inputs exported locally:

```sh
python player_media.py --players jarvis-verified-players-2026.json --candidates action-photo-candidates-2026.json --output action-photo-review-2026.json
```

The player export must contain `drl_player_id`, `squad_id`, and `identity_status`. Candidate rows must contain:

- `drl_player_id`, `season` (2026), `squad_id`, `current_club_name`
- `image_url`, `source_page_url`, `photographer_credit`
- `rights_status`, `rights_evidence_url`
- `identity_confirmed: true`, `action_photo_confirmed: true`, `current_uniform_confirmed: true`

The validator rejects unverified player identities, mismatched squad IDs, non-HTTPS URLs, non-official source pages, missing visual confirmations, uncleared rights, and duplicate player-season candidates. A result marked `ready_for_separate_upload_approval` is only a reviewed candidate; it is not uploaded or published.

## Private media record and publication gate

The migration `20261123120000_add_drl_player_media_workflow.sql` adds current-club, current-squad, action-photo verification, uniform verification, source-page and rights-evidence fields to the existing private media table. It is committed for review only and has NOT been applied.

The authenticated read function must return an action image only when all of these are true:
- permanent player identity is verified;
- action-photo and current-uniform review flags are true;
- rights status is cleared;
- a private Storage object path exists.

The Cloudflare Worker signs only that private stored object. It never returns original source URLs, rights evidence, or private Storage paths to the browser. Images are not served from candidate URLs.

## Frontend behaviour

The DRL player list and profile show only media explicitly marked `verified_action_photo`. Otherwise, the UI displays `PHOTO PENDING`; it does not substitute a headshot or an unverified image.

## Operational boundaries

This PR changes GitHub source files only. It does not apply migrations, write to JARVIS, export player data, download/upload photographs, configure Cloudflare secrets, deploy a Worker, or merge itself. Each of those actions requires separate approval.
