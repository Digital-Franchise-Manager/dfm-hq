#!/usr/bin/env python3
"""Validate DRL 2026 NRL photo candidates before private staging.

A source URL is not permission. Candidate files must be sourced from approved
official NRL/club/NRL Fantasy pages, linked to a verified permanent DRL player
ID, and pass the applicable human identity and rights checks. This validator
does not write to JARVIS, upload media or publish photographs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SEASON = 2026
OFFICIAL_SOURCE_HOSTS = {
    "nrl.com", "www.nrl.com", "fantasy.nrl.com",
    "broncos.com.au", "www.broncos.com.au", "raiders.com.au", "www.raiders.com.au",
    "canberraraiders.com.au", "www.canberraraiders.com.au",
    "bulldogs.com.au", "www.bulldogs.com.au", "cowboys.com.au", "www.cowboys.com.au",
    "dolphinsnrl.com.au", "www.dolphinsnrl.com.au",
    "manlyseaeagles.com.au", "www.manlyseaeagles.com.au",
    "melbournestorm.com.au", "www.melbournestorm.com.au",
    "newcastleknights.com.au", "www.newcastleknights.com.au",
    "parraeels.com.au", "www.parraeels.com.au", "panthers.com.au", "www.panthers.com.au",
    "rabbitohs.com.au", "www.rabbitohs.com.au", "dragons.com.au", "www.dragons.com.au",
    "titans.com.au", "www.titans.com.au", "warriors.kiwi", "www.warriors.kiwi",
    "weststigers.com.au", "www.weststigers.com.au", "sharks.com.au", "www.sharks.com.au",
}
CLEARED_RIGHTS = {"licensed", "permission_granted", "public_domain"}


def https_url(value: Any) -> bool:
    if not isinstance(value, str) or len(value) > 2048:
        return False
    parsed = urlparse(value)
    try:
        port_ok = parsed.port in (None, 443)
    except ValueError:
        return False
    return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password and port_ok


def official_source_page(value: Any) -> bool:
    return https_url(value) and (urlparse(str(value)).hostname or "").lower() in OFFICIAL_SOURCE_HOSTS


def validate_candidate(player: dict[str, Any], candidate: dict[str, Any]) -> list[str]:
    """Return reasons a candidate must not be downloaded or progressed."""
    issues: list[str] = []
    try:
        player_id, candidate_id = int(player.get("drl_player_id")), int(candidate.get("drl_player_id"))
        player_squad, candidate_squad = int(player.get("squad_id")), int(candidate.get("squad_id"))
        season = int(candidate.get("season", SEASON))
    except (TypeError, ValueError):
        return ["invalid_player_or_squad_identifier"]
    if player_id != candidate_id:
        issues.append("candidate_drl_player_id_mismatch")
    if str(player.get("identity_status", "")).casefold() != "verified":
        issues.append("player_identity_not_verified_in_JARVIS")
    if player_squad != candidate_squad:
        issues.append("candidate_squad_does_not_match_verified_current_squad")
    if season != SEASON:
        issues.append("candidate_not_for_2026_season")
    if not official_source_page(candidate.get("source_page_url")):
        issues.append("source_page_must_be_an_official_nrl_fantasy_nrl_or_club_domain")
    if not https_url(candidate.get("image_url")):
        issues.append("image_url_must_be_https")
    else:
        page_host = (urlparse(str(candidate.get("source_page_url") or "")).hostname or "").lower()
        image_host = (urlparse(str(candidate.get("image_url"))).hostname or "").lower()
        if image_host not in OFFICIAL_SOURCE_HOSTS or not (
            image_host == page_host or image_host.endswith("." + page_host)
            or page_host.endswith("." + image_host)
        ):
            issues.append("image_host_must_be_on_the_official_source_domain")
    if candidate.get("identity_confirmed") is not True:
        issues.append("human_player_identity_review_not_confirmed")
    media_kind = str(candidate.get("media_kind", "action_photo")).casefold()
    if media_kind == "action_photo":
        if candidate.get("action_photo_confirmed") is not True:
            issues.append("human_match_action_photo_review_not_confirmed")
        if candidate.get("current_uniform_confirmed") is not True:
            issues.append("human_current_club_uniform_review_not_confirmed")
        if candidate.get("current_club_verified") is not True:
            issues.append("current_club_not_human_verified_against_2026_squad")
        if not str(candidate.get("current_club_name", "")).strip():
            issues.append("current_club_name_missing")
        if not official_source_page(candidate.get("current_club_source_url")):
            issues.append("current_club_source_must_be_official")
    elif media_kind == "profile_photo":
        if candidate.get("profile_photo_confirmed") is not True:
            issues.append("human_profile_photo_review_not_confirmed")
    else:
        issues.append("unsupported_media_kind")
    if str(candidate.get("rights_status", "pending_review")).casefold() not in CLEARED_RIGHTS:
        issues.append("image_usage_rights_not_cleared")
    if not https_url(candidate.get("rights_evidence_url")):
        issues.append("rights_evidence_url_missing_or_invalid")
    return issues


def load_array(path: Path, label: str) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise SystemExit(f"{label} must be a JSON array of objects.")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--players", required=True, type=Path,
                        help="Private JARVIS export: drl_player_id, squad_id, identity_status")
    parser.add_argument("--candidates", required=True, type=Path,
                        help="Candidate manifest containing profile_photo and/or action_photo rows")
    parser.add_argument("--output", required=True, type=Path,
                        help="Review report JSON; no database writes are performed")
    args = parser.parse_args()

    players = load_array(args.players, "Players")
    candidates = load_array(args.candidates, "Candidates")
    verified = {}
    for player in players:
        try:
            player_id = int(player["drl_player_id"])
        except (KeyError, TypeError, ValueError):
            continue
        verified[player_id] = player

    report = []
    seen: set[tuple[int, int, str]] = set()
    for candidate in candidates:
        try:
            player_id = int(candidate.get("drl_player_id"))
            season = int(candidate.get("season", SEASON))
        except (TypeError, ValueError):
            report.append({"status": "rejected", "reason": "invalid_player_or_season_id"})
            continue
        player = verified.get(player_id)
        issues = ["player_not_found_in_player_export"] if player is None else validate_candidate(player, candidate)
        key = (player_id, season, str(candidate.get("media_kind", "action_photo")))
        if key in seen:
            issues.append("duplicate_player_season_media_kind_candidate")
        seen.add(key)
        report.append({
            **candidate,
            "status": "ready_for_private_download" if not issues else "review_required",
            "issues": sorted(set(issues)), "downloaded": False, "uploaded": False, "published": False,
        })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    ready = sum(item["status"] == "ready_for_private_download" for item in report)
    print(f"Reviewed {len(report)} candidates; {ready} eligible for private download; {len(report)-ready} require review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
