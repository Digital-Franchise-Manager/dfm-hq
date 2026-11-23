#!/usr/bin/env python3
"""Validate manually reviewed 2026 DRL action-photo candidates.

This is a zero-cost, review-first workflow. It does not scrape search engines,
download images, upload media, or write to JARVIS. Candidate URLs must come from
an official NRL/club source page. A human reviewer must confirm the player,
current club uniform, action context, and evidence of image-use rights.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SEASON = 2026
OFFICIAL_SOURCE_HOSTS = {
    "nrl.com", "www.nrl.com",
    "broncos.com.au", "www.broncos.com.au",
    "raiders.com.au", "www.raiders.com.au",
    "canberraraiders.com.au", "www.canberraraiders.com.au",
    "bulldogs.com.au", "www.bulldogs.com.au",
    "cowboys.com.au", "www.cowboys.com.au",
    "dolphinsnrl.com.au", "www.dolphinsnrl.com.au",
    "manlyseaeagles.com.au", "www.manlyseaeagles.com.au",
    "melbournestorm.com.au", "www.melbournestorm.com.au",
    "newcastleknights.com.au", "www.newcastleknights.com.au",
    "parraeels.com.au", "www.parraeels.com.au",
    "panthers.com.au", "www.panthers.com.au",
    "rabbitohs.com.au", "www.rabbitohs.com.au",
    "dragons.com.au", "www.dragons.com.au",
    "titans.com.au", "www.titans.com.au",
    "warriors.kiwi", "www.warriors.kiwi",
    "weststigers.com.au", "www.weststigers.com.au",
    "sharks.com.au", "www.sharks.com.au",
}
CLEARED_RIGHTS = {"licensed", "permission_granted", "public_domain"}


def https_url(value: Any) -> bool:
    if not isinstance(value, str) or len(value) > 2048:
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password


def official_source_page(value: Any) -> bool:
    if not https_url(value):
        return False
    host = (urlparse(value).hostname or "").lower()
    return host in OFFICIAL_SOURCE_HOSTS


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
                        help="Human-reviewed action-photo candidate manifest")
    parser.add_argument("--output", required=True, type=Path,
                        help="Review report JSON; no database writes are performed")
    args = parser.parse_args()

    players = load_array(args.players, "Players")
    candidates = load_array(args.candidates, "Candidates")
    verified: dict[int, dict[str, Any]] = {}
    for player in players:
        try:
            player_id = int(player["drl_player_id"])
            squad_id = int(player["squad_id"])
        except (KeyError, TypeError, ValueError):
            continue
        if str(player.get("identity_status", "")).casefold() == "verified":
            verified[player_id] = {"squad_id": squad_id}

    report: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    for candidate in candidates:
        issues: list[str] = []
        try:
            player_id = int(candidate.get("drl_player_id"))
            season = int(candidate.get("season", SEASON))
            squad_id = int(candidate.get("squad_id"))
        except (TypeError, ValueError):
            report.append({"status": "rejected", "reason": "invalid_player_season_or_squad_id"})
            continue

        identity = verified.get(player_id)
        if identity is None:
            issues.append("player_identity_not_verified_in_JARVIS")
        elif identity["squad_id"] != squad_id:
            issues.append("candidate_squad_does_not_match_verified_current_squad")

        if season != SEASON:
            issues.append("candidate_not_for_2026_season")
        if not str(candidate.get("current_club_name", "")).strip():
            issues.append("current_club_name_missing")
        if not https_url(candidate.get("image_url")):
            issues.append("image_url_must_be_https")
        if not official_source_page(candidate.get("source_page_url")):
            issues.append("source_page_must_be_an_official_nrl_or_club_domain")
        if candidate.get("identity_confirmed") is not True:
            issues.append("human_player_identity_review_not_confirmed")
        if candidate.get("action_photo_confirmed") is not True:
            issues.append("human_match_action_photo_review_not_confirmed")
        if candidate.get("current_uniform_confirmed") is not True:
            issues.append("human_current_club_uniform_review_not_confirmed")
        rights = str(candidate.get("rights_status", "pending_review")).casefold()
        if rights not in CLEARED_RIGHTS:
            issues.append("image_usage_rights_not_cleared")
        if not https_url(candidate.get("rights_evidence_url")):
            issues.append("rights_evidence_url_missing_or_invalid")

        key = (player_id, season)
        if key in seen:
            issues.append("duplicate_player_season_candidate")
        seen.add(key)

        report.append({
            "drl_player_id": player_id,
            "season": season,
            "current_squad_id": squad_id,
            "current_club_name": str(candidate.get("current_club_name", "")).strip() or None,
            "media_kind": "action_photo",
            "source_provider": urlparse(candidate["source_page_url"]).hostname
                if official_source_page(candidate.get("source_page_url")) else None,
            "source_url": candidate.get("image_url"),
            "source_page_url": candidate.get("source_page_url"),
            "photographer_credit": candidate.get("photographer_credit"),
            "rights_status": rights if rights in CLEARED_RIGHTS else "pending_review",
            "rights_evidence_url": candidate.get("rights_evidence_url"),
            "verified_identity": not any(issue.startswith("player_identity") or issue.startswith("candidate_squad") for issue in issues),
            "action_photo_verified": candidate.get("action_photo_confirmed") is True,
            "uniform_verified": candidate.get("current_uniform_confirmed") is True,
            "status": "ready_for_separate_upload_approval" if not issues else "review_required",
            "issues": issues,
            "storage_object_path": None,
            "uploaded": False,
            "published": False,
        })

    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    ready = sum(item["status"] == "ready_for_separate_upload_approval" for item in report)
    print(f"Reviewed {len(report)} candidates; {ready} ready for separate upload approval; {len(report)-ready} require review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
