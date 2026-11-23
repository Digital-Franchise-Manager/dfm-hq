#!/usr/bin/env python3
"""Validate DRL 2026 NRL photo candidates and optionally sync approved files to private JARVIS.

A source URL is not permission. Uploads require an approved official source,
a verified permanent DRL player ID, human identity/type review and documented
reuse rights. The default validation mode is read-only; JARVIS sync is explicit.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

try:
    from .photo_audit import image_info
except ImportError:
    from photo_audit import image_info

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



def _privileged_supabase_key(value: str) -> bool:
    """Accept only a Supabase secret key or legacy service_role JWT."""
    if value.startswith("sb_secret_"):
        return True
    parts = value.split(".")
    if len(parts) != 3:
        return False
    try:
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload.encode("ascii")))
        return claims.get("role") == "service_role"
    except (ValueError, UnicodeError, binascii.Error):
        return False


def _jarvis_request(base_url: str, secret: str, path: str, method: str,
                    body: bytes | None = None, content_type: str = "application/json",
                    extra_headers: dict[str, str] | None = None) -> bytes:
    url = base_url.rstrip("/") + path
    headers = {
        "apikey": secret,
        "Authorization": "Bearer " + secret,
        "Content-Type": content_type,
        "Accept": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=60) as response:
            return response.read(1024 * 1024)
    except HTTPError as error:
        # Never echo response bodies or request headers: they may contain private details.
        raise RuntimeError(f"JARVIS request failed with HTTP {error.code}") from None
    except (URLError, TimeoutError, OSError):
        raise RuntimeError("JARVIS request could not be completed") from None


def sync_approved_photos_to_jarvis(players: list[dict[str, Any]],
                                   candidates: list[dict[str, Any]],
                                   staging: Path) -> list[dict[str, Any]]:
    """Upload only fully approved, downloaded photographs to private JARVIS storage."""
    base_url = os.environ.get("SUPABASE_URL", "").strip()
    secret = (os.environ.get("SUPABASE_SECRET_KEY")
              or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise SystemExit("Set SUPABASE_URL to the HTTPS project URL in the private Termux environment.")
    if not _privileged_supabase_key(secret):
        raise SystemExit("Set SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY to a privileged server-side key.")
    if not staging.exists() or not staging.is_dir():
        raise SystemExit("--staging must point to the existing private image staging directory.")

    root = staging.resolve()
    player_index: dict[int, dict[str, Any]] = {}
    for player in players:
        try:
            player_index[int(player["drl_player_id"])] = player
        except (KeyError, TypeError, ValueError):
            continue

    report: list[dict[str, Any]] = []
    for candidate in candidates:
        if candidate.get("status") != "downloaded_private" or not candidate.get("download_path"):
            continue
        try:
            player_id = int(candidate["drl_player_id"])
            player = player_index.get(player_id)
            if player is None:
                raise ValueError("player_not_found_in_export")
            issues = validate_candidate(player, candidate)
            if issues:
                raise ValueError("candidate_not_approved:" + ",".join(sorted(set(issues))))
            relative = Path(str(candidate["download_path"]))
            local_file = (root / relative).resolve() if not relative.is_absolute() else relative.resolve()
            if not local_file.is_relative_to(root) or not local_file.is_file():
                raise ValueError("download_file_missing_or_outside_staging")
            details = image_info(local_file)
            formats = {"jpeg": ("image/jpeg", "jpg"), "png": ("image/png", "png"), "webp": ("image/webp", "webp")}
            if details.get("format") not in formats or not details.get("width") or not details.get("height"):
                raise ValueError("image_format_or_dimensions_invalid")
            mime_type, extension = formats[details["format"]]
            file_size = int(details["bytes"])
            if file_size <= 0 or file_size > 10 * 1024 * 1024:
                raise ValueError("image_exceeds_private_bucket_size_limit")
            digest = details["sha256"]
            photo_type = "profile" if candidate.get("media_kind") == "profile_photo" else "action"
            object_path = f"players/{player_id}/{photo_type}/{digest}.{extension}"
            encoded_path = quote(object_path, safe="/")
            _jarvis_request(
                base_url, secret, f"/storage/v1/object/drl-player-media/{encoded_path}",
                "POST", local_file.read_bytes(), mime_type,
                {"x-upsert": "true", "cache-control": "31536000"},
            )
            asset = {
                "drl_player_id": player_id,
                "photo_type": photo_type,
                "object_path": object_path,
                "source_url": candidate["image_url"],
                "rights_status": candidate["rights_status"],
                "rights_evidence_url": candidate["rights_evidence_url"],
                "mime_type": mime_type,
                "file_size_bytes": file_size,
                "image_width": details["width"],
                "image_height": details["height"],
                "checksum_sha256": digest,
            }
            rpc_body = json.dumps({"p_asset": asset}, separators=(",", ":")).encode("utf-8")
            _jarvis_request(
                base_url, secret, "/rest/v1/rpc/drl_register_player_photo_asset",
                "POST", rpc_body, "application/json",
            )
            report.append({
                "drl_player_id": player_id, "photo_type": photo_type,
                "object_path": object_path, "status": "uploaded_and_registered",
                "bytes": file_size, "sha256": digest,
            })
        except Exception as error:
            # Keep diagnostics categorical; never serialize URLs, secrets or response bodies.
            report.append({
                "drl_player_id": candidate.get("drl_player_id"),
                "status": "upload_or_registration_failed",
                "reason": str(error)[:240] if isinstance(error, ValueError) else type(error).__name__,
            })
    return report


def load_candidates(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, dict):
        value = value.get("candidates")
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise SystemExit("--candidates must be a JSON array or an engine manifest containing a candidates array.")
    return value


def load_players(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise SystemExit("--players must be a JSON array of objects.")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--players", required=True, type=Path,
                        help="Private JARVIS export: drl_player_id, squad_id, identity_status")
    parser.add_argument("--candidates", required=True, type=Path,
                        help="Candidate array or photo-discovery manifest")
    parser.add_argument("--output", required=True, type=Path,
                        help="Review or upload report JSON; stored locally in private staging")
    parser.add_argument("--sync-jarvis", action="store_true",
                        help="Upload only downloaded, identity-confirmed and rights-cleared images to private JARVIS storage")
    parser.add_argument("--staging", type=Path,
                        help="Private local image staging directory; required with --sync-jarvis")
    args = parser.parse_args()

    players = load_players(args.players)
    candidates = load_candidates(args.candidates)
    if args.sync_jarvis:
        if not args.staging:
            parser.error("--staging is required with --sync-jarvis")
        report = sync_approved_photos_to_jarvis(players, candidates, args.staging)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        uploaded = sum(row.get("status") == "uploaded_and_registered" for row in report)
        print(f"JARVIS photo sync finished: {uploaded} uploaded and registered; {len(report)-uploaded} failed.")
        return 0 if uploaded == len(report) else 1
    player_index = {}
    for player in players:
        try:
            player_index[int(player["drl_player_id"])] = player
        except (KeyError, TypeError, ValueError):
            continue

    report = []
    seen: set[tuple[int, int, str, str]] = set()
    for candidate in candidates:
        try:
            player_id = int(candidate.get("drl_player_id"))
            season = int(candidate.get("season", SEASON))
        except (TypeError, ValueError):
            report.append({"status": "rejected", "reason": "invalid_player_or_season_id"})
            continue
        player = player_index.get(player_id)
        issues = ["player_not_found_in_player_export"] if player is None else validate_candidate(player, candidate)
        key = (player_id, season, str(candidate.get("media_kind", "action_photo")), str(candidate.get("image_url", "")))
        if key in seen:
            issues.append("duplicate_player_season_media_candidate")
        seen.add(key)
        report.append({
            **candidate,
            "status": "ready_for_private_download" if not issues else "review_required",
            "issues": sorted(set(issues)), "downloaded": bool(candidate.get("download_path")),
            "uploaded": False, "published": False,
        })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    ready = sum(item["status"] == "ready_for_private_download" for item in report)
    print(f"Reviewed {len(report)} candidates; {ready} eligible for private download; {len(report)-ready} require review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
