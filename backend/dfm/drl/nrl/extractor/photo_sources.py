#!/usr/bin/env python3
"""Permitted public image-source adapters for the DRL NRL photo workflow."""
from __future__ import annotations

import json
import re
import time
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

NRL_ORIGIN = "https://www.nrl.com"
DIRECTORY_ENDPOINT = f"{NRL_ORIGIN}/players/data"
COMPETITION_ID = 111
USER_AGENT = "DFM-DRL-PhotoArchive/1.0 (+https://digitalfranchisemanager.com)"
MAX_PAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_BYTES = 12 * 1024 * 1024
SQUAD_IDS = {
    500001, 500002, 500003, 500004, 500005, 500010, 500011, 500012,
    500013, 500014, 500021, 500022, 500023, 500028, 500031, 500032, 500723,
}
OFFICIAL_HOSTS = {
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
CLUB_HOSTS = OFFICIAL_HOSTS - {"nrl.com", "www.nrl.com", "fantasy.nrl.com"}
FAMILY_ROOTS = (
    "nrl.com", "broncos.com.au", "raiders.com.au", "canberraraiders.com.au",
    "bulldogs.com.au", "cowboys.com.au", "dolphinsnrl.com.au", "manlyseaeagles.com.au",
    "melbournestorm.com.au", "newcastleknights.com.au", "parraeels.com.au",
    "panthers.com.au", "rabbitohs.com.au", "dragons.com.au", "titans.com.au",
    "warriors.kiwi", "weststigers.com.au", "sharks.com.au",
)


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalized(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", clean(value).casefold())


def safe_https_url(value: Any) -> bool:
    if not isinstance(value, str) or len(value) > 2048:
        return False
    parsed = urlparse(value)
    try:
        port_ok = parsed.port in (None, 443)
    except ValueError:
        return False
    return (
        parsed.scheme == "https" and bool(parsed.hostname)
        and parsed.username is None and parsed.password is None and port_ok
    )


def official_host(value: Any) -> bool:
    if not safe_https_url(value):
        return False
    return (urlparse(str(value)).hostname or "").lower() in OFFICIAL_HOSTS


def same_official_family(page_url: str, image_url: str) -> bool:
    if not official_host(page_url) or not official_host(image_url):
        return False
    page_host = (urlparse(page_url).hostname or "").lower()
    image_host = (urlparse(image_url).hostname or "").lower()

    def family(host: str) -> str | None:
        return next(
            (root for root in FAMILY_ROOTS if host == root or host.endswith("." + root)),
            None,
        )

    return family(page_host) is not None and family(page_host) == family(image_host)


def fetch_bytes(url: str, accept: str, max_bytes: int = MAX_PAGE_BYTES) -> tuple[bytes, str, str]:
    if not official_host(url):
        raise ValueError("Refusing to fetch a URL outside the approved official-source allow-list.")
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    with urlopen(request, timeout=25) as response:
        final_url = response.geturl()
        if not official_host(final_url):
            raise ValueError("Refusing an off-domain redirect from an approved source.")
        if response.status != 200:
            raise RuntimeError(f"Unexpected HTTP status {response.status}")
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError("Source response exceeds the configured size limit.")
        return data, final_url, response.headers.get("Content-Type", "")


class ImagePageParser(HTMLParser):
    """Collect image references and JSON-LD image values without executing scripts."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.images: list[dict[str, str]] = []
        self._script_type = ""
        self._script_parts: list[str] = []
        self.json_ld: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key.lower(): value or "" for key, value in attrs}
        if tag == "script":
            self._script_type = attr.get("type", "").lower()
            self._script_parts = []
        if tag == "meta" and attr.get("property", "").lower() in {"og:image", "og:image:url"}:
            self._add(attr.get("content", ""), attr.get("alt", ""))
        if tag == "meta" and attr.get("name", "").lower() == "twitter:image":
            self._add(attr.get("content", ""), attr.get("alt", ""))
        if tag == "link" and "image_src" in attr.get("rel", "").lower():
            self._add(attr.get("href", ""), "")
        if tag == "img":
            self._add(attr.get("src") or attr.get("data-src") or attr.get("data-original"), attr.get("alt", ""))
            for entry in attr.get("srcset", "").split(","):
                self._add(entry.strip().split(" ")[0] if entry.strip() else "", attr.get("alt", ""))

    def _add(self, src: str | None, alt: str) -> None:
        if src:
            self.images.append({"src": src.strip(), "alt": clean(alt)})

    def handle_data(self, data: str) -> None:
        if self._script_type == "application/ld+json":
            self._script_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            if self._script_type == "application/ld+json":
                self.json_ld.append("".join(self._script_parts))
            self._script_type = ""
            self._script_parts = []


def _json_images(value: Any, found: list[str]) -> None:
    if isinstance(value, dict):
        image = value.get("image")
        if isinstance(image, str):
            found.append(image)
        elif isinstance(image, list):
            found.extend(item for item in image if isinstance(item, str))
        elif isinstance(image, dict) and isinstance(image.get("url"), str):
            found.append(image["url"])
        for child in value.values():
            if isinstance(child, (dict, list)):
                _json_images(child, found)
    elif isinstance(value, list):
        for child in value:
            _json_images(child, found)


def discover_page_images(page_url: str, media_kind: str, player: dict[str, Any]) -> list[dict[str, Any]]:
    if not official_host(page_url):
        return []
    body, final_url, _ = fetch_bytes(page_url, "text/html,application/xhtml+xml")
    parser = ImagePageParser()
    parser.feed(body.decode("utf-8", errors="replace"))
    raw = list(parser.images)
    json_images: list[str] = []
    for script in parser.json_ld:
        try:
            _json_images(json.loads(script), json_images)
        except (json.JSONDecodeError, TypeError):
            continue
    raw.extend({"src": value, "alt": ""} for value in json_images)
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw:
        image_url = urljoin(final_url, item["src"])
        if image_url in seen or not same_official_family(final_url, image_url):
            continue
        seen.add(image_url)
        results.append({
            "drl_player_id": player.get("drl_player_id"),
            "season": int(player.get("season", 2026)),
            "squad_id": player.get("squad_id"),
            "current_club_name": player.get("current_club_name"),
            "media_kind": media_kind,
            "source_provider": urlparse(final_url).hostname,
            "source_page_url": final_url,
            "image_url": image_url,
            "alt_text": item.get("alt") or None,
            "photographer_credit": player.get("photographer_credit"),
            "rights_status": player.get("rights_status", "pending_review"),
            "rights_evidence_url": player.get("rights_evidence_url"),
            "identity_confirmed": player.get("identity_confirmed") is True,
            "profile_photo_confirmed": player.get("profile_photo_confirmed") is True,
            "action_photo_confirmed": player.get("action_photo_confirmed") is True,
            "current_uniform_confirmed": player.get("current_uniform_confirmed") is True,
            "current_club_verified": player.get("current_club_verified") is True,
            "current_club_source_url": player.get("current_club_source_url"),
        })
    return results


def discover_nrl_directory_profile(
    player: dict[str, Any],
    delay: float = 1.0,
    directory_cache: dict[int, list[dict[str, Any]]] | None = None,
) -> dict[str, Any] | None:
    """Resolve a verified player to a unique exact NRL directory profile.

    A per-squad cache prevents one directory request per player in a squad.
    """
    if str(player.get("identity_status", "")).casefold() != "verified":
        return None
    try:
        squad_id = int(player["squad_id"])
    except (KeyError, TypeError, ValueError):
        return None
    if squad_id not in SQUAD_IDS:
        return None
    first, last = normalized(player.get("first_name")), normalized(player.get("last_name"))
    if not first or not last:
        return None
    cache = directory_cache if directory_cache is not None else {}
    if squad_id not in cache:
        query = urlencode({"competition": COMPETITION_ID, "team": squad_id})
        payload, _, _ = fetch_bytes(f"{DIRECTORY_ENDPOINT}?{query}", "application/json")
        data = json.loads(payload.decode("utf-8", errors="replace"))
        found: list[dict[str, Any]] = []

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                if all(key in value for key in ("firstName", "lastName", "url")):
                    found.append(value)
                for child in value.values():
                    if isinstance(child, (dict, list)):
                        walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(data)
        cache[squad_id] = found
        if delay:
            time.sleep(max(0, delay))
    matches = [
        item for item in cache[squad_id]
        if normalized(item.get("firstName")) == first
        and normalized(item.get("lastName")) == last
    ]
    if len(matches) != 1:
        return None
    profile_url = urljoin(NRL_ORIGIN, str(matches[0].get("url", "")))
    if not profile_url.startswith(NRL_ORIGIN + "/players/"):
        return None
    image = matches[0].get("bodyImage")
    return {
        "profile_url": profile_url,
        "image_url": urljoin(NRL_ORIGIN, image) if isinstance(image, str) else None,
        "first_name": clean(matches[0].get("firstName")),
        "last_name": clean(matches[0].get("lastName")),
        "squad_id": squad_id,
    }


class NRLFantasySource:
    """Reads supplied NRL Fantasy player pages; does not guess undocumented APIs."""
    name = "nrl_fantasy"

    def discover(self, player: dict[str, Any]) -> list[dict[str, Any]]:
        urls = player.get("fantasy_profile_url") or []
        if isinstance(urls, str):
            urls = [urls]
        if not isinstance(urls, list):
            return []
        results: list[dict[str, Any]] = []
        for url in urls:
            if official_host(url) and (urlparse(url).hostname or "").lower() == "fantasy.nrl.com":
                results.extend(discover_page_images(url, "profile_photo", player))
        return results


class OfficialNRLSource:
    name = "official_nrl"

    def __init__(self) -> None:
        self.directory_cache: dict[int, list[dict[str, Any]]] = {}

    def discover(self, player: dict[str, Any], delay: float = 1.0) -> list[dict[str, Any]]:
        profile_url = player.get("nrl_profile_url")
        image_url = player.get("nrl_profile_image_url")
        if not profile_url:
            match = discover_nrl_directory_profile(
                player, delay=delay, directory_cache=self.directory_cache
            )
            if match:
                profile_url = match["profile_url"]
                image_url = image_url or match.get("image_url")
        results: list[dict[str, Any]] = []
        if profile_url and official_host(profile_url) and (urlparse(profile_url).hostname or "").lower() in {"nrl.com", "www.nrl.com"}:
            results.extend(discover_page_images(profile_url, "profile_photo", player))
        if image_url and profile_url and same_official_family(profile_url, image_url):
            results.append({
                "drl_player_id": player.get("drl_player_id"),
                "season": int(player.get("season", 2026)),
                "squad_id": player.get("squad_id"),
                "current_club_name": player.get("current_club_name"),
                "media_kind": "profile_photo",
                "source_provider": "nrl.com",
                "source_page_url": profile_url,
                "image_url": image_url,
                "alt_text": f"NRL profile photograph of {clean(player.get('first_name'))} {clean(player.get('last_name'))}",
                "rights_status": player.get("rights_status", "pending_review"),
                "rights_evidence_url": player.get("rights_evidence_url"),
                "identity_confirmed": player.get("identity_confirmed") is True,
                "profile_photo_confirmed": player.get("profile_photo_confirmed") is True,
                "action_photo_confirmed": False,
                "current_uniform_confirmed": False,
                "current_club_verified": player.get("current_club_verified") is True,
                "current_club_source_url": player.get("current_club_source_url"),
            })
        return results


class ClubActionSource:
    name = "official_club_action"

    def discover(self, player: dict[str, Any]) -> list[dict[str, Any]]:
        urls = player.get("action_photo_pages") or []
        if isinstance(urls, str):
            urls = [urls]
        if not isinstance(urls, list):
            return []
        results: list[dict[str, Any]] = []
        for url in urls:
            if official_host(url) and (urlparse(url).hostname or "").lower() in CLUB_HOSTS:
                results.extend(discover_page_images(url, "action_photo", player))
        return results


def download_image(image_url: str, source_page_url: str, destination) -> dict[str, Any]:
    """Download an eligible image to private local staging after URL and size checks."""
    from pathlib import Path
    if not same_official_family(source_page_url, image_url):
        raise ValueError("Image URL must remain within the approved source's official domain family.")
    body, final_url, content_type = fetch_bytes(
        image_url, "image/webp,image/png,image/jpeg", MAX_IMAGE_BYTES
    )
    if not same_official_family(source_page_url, final_url):
        raise ValueError("Refusing an off-domain image redirect.")
    signatures = {
        "image/jpeg": body.startswith(b"\xff\xd8\xff"),
        "image/png": body.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": body.startswith(b"RIFF") and body[8:12] == b"WEBP",
    }
    detected = next((kind for kind, valid in signatures.items() if valid), None)
    declared = content_type.split(";", 1)[0].strip().lower()
    if detected is None or declared not in {detected, "application/octet-stream"}:
        raise ValueError("Downloaded content is not a supported JPEG, PNG or WebP image.")
    suffix = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[detected]
    path = Path(destination).with_suffix(suffix)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return {"path": str(path), "bytes": len(body), "content_type": detected, "source_url": final_url}
