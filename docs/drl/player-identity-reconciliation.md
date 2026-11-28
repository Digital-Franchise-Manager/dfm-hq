# DRL permanent player identity reconciliation (2019–2026)

This workflow reads the eight annual player archive PDFs and creates a permanent player-ID crosswalk based on the earliest confirmed season. It is review-first and local-only: it does not connect to Supabase, call an API, or write to JARVIS.

## Android 13 / Termux

Install free dependencies:

```sh
pkg update
pkg install python poppler
```

Place the eight PDFs in one folder. Each filename must contain its season year and end in `players.PDF`. Run from the repository root:

```sh
python backend/dfm/sports/drl/nrl/extractor/player_identity.py \
  --input-dir /storage/emulated/0/Download/drl-source-pdfs \
  --output-dir /storage/emulated/0/Download/drl-identity-output
```

## Identity decisions

1. The earliest confirmed season determines the permanent `drl_player_id`.
2. Each source season's original ID remains in `season_player_id`; the permanent ID is a separate crosswalk value.
3. Connelly Lemuelu's 2023–2026 ID `507949` maps to his earliest ID `100003377` from 2020.
4. Sione Katoa `501240` (winger) and Sione Katoa `503922` (hooker) remain separate identities. Names alone are never used to merge them.
5. ID `504325` is one user-confirmed DRL identity with canonical display name **Greg Marzhew**. Historical 2019–2020 source records labelled Greg Leleisiuao are mapped to the same permanent ID. Their original season names remain unchanged in `source-map.csv`, and `player-master.csv` records Greg Leleisiuao as a historical name variant. This is a platform identity-reconciliation instruction; it is not an independent claim about real-world identity.
6. Other spelling variants on stable source IDs are preserved in each season record and listed in the audit output.

## Generated local files

- `player-master.csv` — one row per permanent identity, based on the earliest mapped season.
- `source-map.csv` — season, original source ID and canonical DRL ID.
- `identity-review.csv` — records withheld because their source ID is ambiguous.
- `source-name-variants.csv` — source IDs with more than one recorded name.
- `identity-audit.json` — season counts and applied identity rules.

Do not commit the generated player data or upload it to a public location. The original PDFs and their source records remain unchanged.

## Database integration gate

The live private schema has `dfm_private.drl_nrl_player_master` and `dfm_private.drl_nrl_player_source_map`; both were empty when inspected. Existing season archive tables were also empty. Intended destinations are the legacy archive for 2019 and 2025, the existing season-specific tables for 2020–2024 and 2026, and the source map for permanent-ID links.

Only verified crosswalk rows are eligible for import. The Greg Marzhew / Greg Leleisiuao records carrying source ID `504325` are included under one permanent ID, with original season names preserved in the source map. Database migration-history drift must be reconciled before import. This tool intentionally performs no database writes.
