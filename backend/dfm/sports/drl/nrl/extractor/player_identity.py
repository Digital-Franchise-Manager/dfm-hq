#!/usr/bin/env python3
"""Build a review-first permanent player-ID crosswalk from annual DRL PDFs.

Requires Python 3 and pdftotext (Poppler). Writes local CSV/JSON only; it
never connects to Supabase or writes to JARVIS.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

# User-confirmed identity decisions.
SOURCE_ID_ALIASES = {507949: 100003377}  # Connelly Lemuelu: earliest ID from 2020.
DISPLAY_NAME_OVERRIDES = {504325: ("Greg", "Marzhew")}
SIONE_IDENTITIES = {(501240): "winger", (503922): "hooker"}


def parse_pdf(path: Path) -> list[dict[str, Any]]:
    result = subprocess.run(
        ["pdftotext", "-raw", str(path), "-"],
        check=True, capture_output=True, text=True,
    )
    compact = re.sub(r"\s+", "", result.stdout).replace("Prettyprint", "")
    payload = json.loads(compact.replace(",}", "}").replace(",]", "]"))
    if not isinstance(payload, list) or any(not isinstance(row, dict) for row in payload):
        raise ValueError(f"{path.name}: expected a JSON array of player records")
    return payload


def name_key(row: dict[str, Any]) -> str:
    return " ".join(f"{row.get('first_name', '')} {row.get('last_name', '')}".split()).casefold()


def position_codes(row: dict[str, Any]) -> str:
    return ";".join(str(value) for value in (row.get("positions") or row.get("original_positions") or []))


def read_seasons(input_dir: Path) -> dict[int, list[dict[str, Any]]]:
    seasons: dict[int, list[dict[str, Any]]] = {}
    for path in sorted(input_dir.glob("20??*players.PDF")):
        match = re.search(r"(20\d{2})", path.name)
        if not match:
            continue
        season = int(match.group(1))
        if season in seasons:
            raise ValueError(f"Multiple source PDFs found for season {season}")
        records = parse_pdf(path)
        seen: set[int] = set()
        for number, row in enumerate(records, 1):
            try:
                player_id = int(row["id"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"{path.name} record {number}: invalid player ID") from exc
            if player_id <= 0 or not row.get("first_name") or not row.get("last_name"):
                raise ValueError(f"{path.name} record {number}: missing identity fields")
            if player_id in seen:
                raise ValueError(f"{path.name}: duplicate source ID {player_id}")
            seen.add(player_id)
            row["_source_file"] = path.name
        seasons[season] = records
    if sorted(seasons) != list(range(2019, 2027)):
        raise ValueError("Expected exactly one source PDF for every season 2019 through 2026.")
    return seasons


def resolve(row: dict[str, Any]) -> tuple[int | None, str, str | None]:
    source_id = int(row["id"])
    target = SOURCE_ID_ALIASES.get(source_id, source_id)
    method = "explicit_earliest_id_alias" if target != source_id else "earliest_season_source_id"
    return target, method, None


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_outputs(seasons: dict[int, list[dict[str, Any]]], output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    observations: dict[int, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    source_map: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []

    for season in sorted(seasons):
        for row in seasons[season]:
            source_id = int(row["id"])
            observations[source_id].append((season, row))
            canonical_id, method, issue = resolve(row)
            mapped = {
                "season": season,
                "season_player_id": source_id,
                "drl_player_id": canonical_id,
                "identity_status": "verified" if canonical_id is not None else "review_required",
                "match_method": method,
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "squad_id": row.get("squad_id"),
                "positions": position_codes(row),
                "source_file": row["_source_file"],
            }
            source_map.append(mapped)
            if issue:
                review.append({**mapped, "issue": issue})

    first_seen = {pid: min(season for season, _ in rows) for pid, rows in observations.items()}
    for alias_id, original_id in SOURCE_ID_ALIASES.items():
        if alias_id not in first_seen or original_id not in first_seen:
            raise ValueError(f"ID alias {alias_id}->{original_id} is missing from the supplied seasons")
        if first_seen[original_id] > first_seen[alias_id]:
            raise ValueError(f"ID alias target {original_id} is not from an earlier season")
        if {name_key(row) for _, row in observations[alias_id]} != {
            name_key(row) for _, row in observations[original_id]
        }:
            raise ValueError(f"ID alias {alias_id}->{original_id} has inconsistent names")

    master: dict[int, dict[str, Any]] = {}
    for item in sorted(source_map, key=lambda value: (value["season"], value["season_player_id"])):
        canonical = item["drl_player_id"]
        if canonical is None or canonical in master:
            continue
        first, last = item["first_name"], item["last_name"]
        if canonical in DISPLAY_NAME_OVERRIDES:
            first, last = DISPLAY_NAME_OVERRIDES[canonical]
        master[canonical] = {
            "drl_player_id": canonical,
            "first_name": first,
            "last_name": last,
            "source_season": item["season"],
            "source_player_id": item["season_player_id"],
            "first_seen_squad_id": item["squad_id"],
            "first_seen_positions": item["positions"],
            "historical_name_variants": "; ".join(sorted({
                " ".join(f"{r['first_name']} {r['last_name']}".split())
                for _, r in observations[canonical]
                if " ".join(f"{r['first_name']} {r['last_name']}".split()).casefold()
                != f"{first} {last}".casefold()
            })),
            "identity_status": "verified",
        }

    for player in master.values():
        if player["drl_player_id"] in SIONE_IDENTITIES:
            player["identity_note"] = SIONE_IDENTITIES[player["drl_player_id"]]

    variants = []
    for source_id, rows in sorted(observations.items()):
        names = sorted({" ".join(f"{r['first_name']} {r['last_name']}".split()) for _, r in rows})
        if len(names) > 1:
            variants.append({
                "source_player_id": source_id,
                "first_seen_season": first_seen[source_id],
                "names_observed": "; ".join(names),
                "seasons": ";".join(str(y) for y in sorted({y for y, _ in rows})),
            })

    # Do not allow two different players to share a canonical ID within one season.
    for season in sorted(seasons):
        seen: dict[int, str] = {}
        for item in (row for row in source_map if row["season"] == season and row["drl_player_id"] is not None):
            label = f"{item['first_name']} {item['last_name']}"
            prior = seen.get(item["drl_player_id"])
            if prior and prior != label:
                raise ValueError(f"Season {season}: canonical ID collision {item['drl_player_id']}: {prior} / {label}")
            seen[item["drl_player_id"]] = label

    write_csv(output_dir / "source-map.csv", source_map)
    write_csv(output_dir / "player-master.csv", list(master.values()))
    write_csv(output_dir / "identity-review.csv", review)
    write_csv(output_dir / "source-name-variants.csv", variants)
    summary = {
        "seasons": {str(year): len(rows) for year, rows in sorted(seasons.items())},
        "total_source_records": sum(map(len, seasons.values())),
        "distinct_source_player_ids": len(observations),
        "canonical_master_players_excluding_unresolved": len(master),
        "source_map_verified_rows": sum(row["drl_player_id"] is not None for row in source_map),
        "source_map_review_required_rows": len(review),
        "explicit_id_aliases": {str(k): v for k, v in SOURCE_ID_ALIASES.items()},
        "source_ids_with_name_variants": len(variants),
        "user_confirmed_identity_rules": {
            "sione_katoa_501240": "winger; separate identity",
            "sione_katoa_503922": "hooker; separate identity",
            "greg_504325": "canonical Greg Marzhew; historical Greg Leleisiuao records retained under the same source identity",
            "connelly_507949": "canonical ID 100003377 from earliest 2020 appearance",
        },
        "database_write_performed": False,
    }
    (output_dir / "identity-audit.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    summary = build_outputs(read_seasons(args.input_dir), args.output_dir)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
