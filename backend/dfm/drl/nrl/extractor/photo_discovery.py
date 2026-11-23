#!/usr/bin/env python3
"""Discover, rights-gate and privately download DRL NRL player photographs.

The engine reads a local JSON export; it never connects to JARVIS or writes to
Supabase. Only public pages on the allow-listed official domains are fetched.
A download is automatic only after identity, image type and reuse rights are
explicitly confirmed in the input record.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

try:
    from .photo_manifest import load_manifest, merge_candidates, write_manifest
    from .photo_sources import ClubActionSource, NRLFantasySource, OfficialNRLSource, download_image
    from .player_media import validate_candidate
except ImportError:
    from photo_manifest import load_manifest, merge_candidates, write_manifest
    from photo_sources import ClubActionSource, NRLFantasySource, OfficialNRLSource, download_image
    from player_media import validate_candidate

SEASON = 2026
CLEARED_RIGHTS = {"licensed", "permission_granted", "public_domain"}


def load_players(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise ValueError("--players must contain a JSON array of objects.")
    return value


def safe_file_name(player_id: Any, media_kind: str, image_url: str) -> str:
    digest = hashlib.sha256(image_url.encode("utf-8")).hexdigest()[:12]
    kind = "action" if media_kind == "action_photo" else "profile"
    return f"player-{int(player_id)}-{kind}-{digest}"


def candidate_is_downloadable(candidate: dict[str, Any], player: dict[str, Any]) -> tuple[bool, list[str]]:
    issues = validate_candidate(player, candidate)
    if str(candidate.get("rights_status", "pending_review")).casefold() not in CLEARED_RIGHTS:
        issues.append("image_usage_rights_not_cleared")
    if not candidate.get("rights_evidence_url"):
        issues.append("rights_evidence_missing")
    return not issues, sorted(set(issues))


def discover(players: list[dict[str, Any]], delay: float = 1.5) -> list[dict[str, Any]]:
    fantasy, nrl, clubs = NRLFantasySource(), OfficialNRLSource(), ClubActionSource()
    candidates: list[dict[str, Any]] = []
    for index, player in enumerate(players, start=1):
        try:
            player_id = int(player["drl_player_id"])
        except (KeyError, TypeError, ValueError):
            candidates.append({"status": "review_required", "reason": "missing_or_invalid_drl_player_id"})
            continue
        if str(player.get("identity_status", "")).casefold() != "verified":
            candidates.append({
                "drl_player_id": player_id, "status": "review_required",
                "issues": ["player_identity_not_verified_in_JARVIS"],
            })
            continue
        discovered: list[dict[str, Any]] = []
        for source_name, operation, kind in (
            ("nrl_fantasy", lambda: fantasy.discover(player), "profile_photo"),
            ("official_nrl", lambda: nrl.discover(player, delay=delay), "profile_photo"),
            ("official_club", lambda: clubs.discover(player), "action_photo"),
        ):
            try:
                discovered.extend(operation())
            except Exception as error:
                candidates.append({
                    "drl_player_id": player_id, "media_kind": kind,
                    "source_provider": source_name, "status": "discovery_failed",
                    "issues": [type(error).__name__],
                })
        for candidate in discovered:
            candidate["drl_player_id"] = player_id
            candidate["season"] = int(player.get("season", SEASON))
            candidate["download_path"] = None
            eligible, issues = candidate_is_downloadable(candidate, player)
            candidate["issues"] = issues
            candidate["status"] = "eligible_for_private_download" if eligible else "awaiting_human_review"
            candidates.append(candidate)
        if delay and index < len(players):
            time.sleep(max(0, delay))
        print(f"Processed player {player_id} ({index}/{len(players)})", file=sys.stderr)
    return candidates


def run_downloads(candidates: list[dict[str, Any]], staging: Path) -> None:
    staging.mkdir(parents=True, exist_ok=True)
    for candidate in candidates:
        if candidate.get("status") != "eligible_for_private_download":
            continue
        name = safe_file_name(candidate["drl_player_id"], candidate["media_kind"], candidate["image_url"])
        try:
            result = download_image(candidate["image_url"], candidate["source_page_url"], staging / name)
            candidate["download_path"] = Path(result["path"]).name
            candidate["download_bytes"] = result["bytes"]
            candidate["download_content_type"] = result["content_type"]
            candidate["status"] = "downloaded_private"
        except Exception as error:
            candidate["status"] = "download_failed"
            candidate["issues"] = list(candidate.get("issues", [])) + [f"download_failed:{type(error).__name__}"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--players", required=True, type=Path,
                        help="Local JSON export with verified player identities and permitted source page fields")
    parser.add_argument("--manifest", required=True, type=Path,
                        help="Output manifest JSON; existing candidates are preserved")
    parser.add_argument("--staging", required=True, type=Path,
                        help="Private local image staging directory; keep outside the Git repository")
    parser.add_argument("--delay", type=float, default=1.5,
                        help="Minimum delay between player source lookups")
    parser.add_argument("--no-download", action="store_true",
                        help="Discovery-only run; do not download images")
    args = parser.parse_args()

    players = load_players(args.players)
    discovered = discover(players, delay=args.delay)
    current = load_manifest(args.manifest)
    combined = merge_candidates(current.get("candidates", []), discovered)
    if not args.no_download:
        run_downloads(combined, args.staging)
    write_manifest(args.manifest, combined, season=SEASON)
    counts: dict[str, int] = {}
    for item in combined:
        status = str(item.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    print(json.dumps({
        "players_received": len(players),
        "players_with_verified_identity": sum(
            str(row.get("identity_status", "")).casefold() == "verified" for row in players
        ),
        "candidate_count": len(combined), "status_counts": counts,
        "download_mode": "disabled" if args.no_download else "eligible_only",
        "manifest": str(args.manifest), "staging_directory": str(args.staging),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
