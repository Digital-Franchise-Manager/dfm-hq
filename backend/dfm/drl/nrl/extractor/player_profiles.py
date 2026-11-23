#!/usr/bin/env python3
"""Discover and extract 2026 NRL player profiles for verified DRL identities.

Input JSON is an export of the existing JARVIS player rows. Each row must include:
  drl_player_id, first_name, last_name, squad_id, position,
  identity_status (the literal value "verified")

The extractor queries the official NRL player directory by squad, then requires a
unique exact match on first name, last name, position and squad. Unverified,
missing, ambiguous and unmatched identities are excluded from extraction.

Output is a reviewable JSON file only. This script does not connect to Supabase,
change JARVIS, upload photographs, or publish media. Image candidates remain
pending rights review.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

NRL_ORIGIN = "https://www.nrl.com"
DIRECTORY_ENDPOINT = f"{NRL_ORIGIN}/players/data"
COMPETITION_ID = 111
SEASON = 2026
USER_AGENT = "DFM-DRL-PlayerArchive/1.1 (+https://digitalfranchisemanager.com)"
SQUAD_IDS = (
    500001, 500002, 500003, 500004, 500005, 500010, 500011, 500012,
    500013, 500014, 500021, 500022, 500023, 500028, 500031, 500032, 500723,
)
FIELD_ALIASES = {
    "tries": ("tries",),
    "try_assists": ("try assists",),
    "points": ("points",),
    "tackles": ("tackles made",),
    "metres_gained": ("total running metres",),
    "line_breaks": ("linebreaks", "line breaks"),
}
ROUND_LABELS = {"round", "opponent", "score", "position", "minutes played"}


def clean(value: str) -> str:
    return re.sub(r"\\s+", " ", value).strip()


def normalized(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def as_int(value: str) -> int | None:
    value = clean(value).replace(",", "")
    if not value or value in {"-", "—", "–"}:
        return None
    return int(value) if re.fullmatch(r"-?\\d+", value) else None


def fetch_bytes(url: str, accept: str) -> bytes:
    if not url.startswith("https://www.nrl.com/"):
        raise ValueError("Refusing to fetch a URL outside www.nrl.com.")
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    with urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"Unexpected HTTP status {response.status}")
        return response.read()


def fetch_json(url: str) -> Any:
    return json.loads(fetch_bytes(url, "application/json").decode("utf-8", errors="replace"))


def collect_directory_profiles(value: Any, found: list[dict[str, Any]]) -> None:
    """Walk the directory response without assuming a fixed wrapper shape."""
    if isinstance(value, dict):
        if all(key in value for key in ("firstName", "lastName", "url")):
            found.append(value)
        for child in value.values():
            if isinstance(child, (dict, list)):
                collect_directory_profiles(child, found)
    elif isinstance(value, list):
        for child in value:
            collect_directory_profiles(child, found)


def discover_squad(squad_id: int, delay: float) -> list[dict[str, Any]]:
    query = urlencode({"competition": COMPETITION_ID, "team": squad_id})
    payload = fetch_json(f"{DIRECTORY_ENDPOINT}?{query}")
    profiles: list[dict[str, Any]] = []
    collect_directory_profiles(payload, profiles)
    unique: dict[str, dict[str, Any]] = {}
    for item in profiles:
        relative = str(item.get("url") or "")
        if not relative:
            continue
        absolute = urljoin(NRL_ORIGIN, relative)
        if not absolute.startswith(f"{NRL_ORIGIN}/players/"):
            continue
        unique[absolute] = {
            "first_name": clean(str(item.get("firstName") or "")),
            "last_name": clean(str(item.get("lastName") or "")),
            "team": clean(str(item.get("teamNickName") or "")),
            "position": clean(str(item.get("position") or "")),
            "profile_url": absolute,
            "image_candidate": item.get("bodyImage"),
            "directory_squad_id": squad_id,
        }
    if delay:
        time.sleep(max(0, delay))
    return list(unique.values())


def match_player(row: dict[str, Any], directory: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    if str(row.get("identity_status", "")).casefold() != "verified":
        return None, "identity_not_verified"
    try:
        squad_id = int(row.get("squad_id"))
    except (TypeError, ValueError):
        return None, "missing_or_invalid_squad_id"
    if squad_id not in SQUAD_IDS:
        return None, "unknown_squad_id"
    first = normalized(row.get("first_name"))
    last = normalized(row.get("last_name"))
    position = normalized(row.get("position"))
    if not first or not last or not position:
        return None, "missing_name_or_position"
    candidates = [
        item for item in directory
        if item["directory_squad_id"] == squad_id
        and normalized(item["first_name"]) == first
        and normalized(item["last_name"]) == last
        and normalized(item["position"]) == position
    ]
    if len(candidates) == 1:
        return candidates[0], "matched"
    if not candidates:
        return None, "no_exact_name_squad_position_match"
    return None, "ambiguous_directory_match"


class ProfileParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self.images: list[dict[str, str]] = []
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []
        elif tag == "img":
            src = attr.get("src") or attr.get("data-src")
            alt = clean(attr.get("alt") or "")
            if src and ("player" in alt.lower() or "photo of" in alt.lower()):
                self.images.append({"src": urljoin(NRL_ORIGIN, src), "alt": alt})

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)
        self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(clean(" ".join(self._cell)))
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if self._row:
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None


def numeric_column(headers: list[str], aliases: tuple[str, ...]) -> int | None:
    normalized_headers = [clean(header).lower() for header in headers]
    for alias in aliases:
        if alias in normalized_headers:
            return normalized_headers.index(alias)
    return None


def extract_round_table(tables: list[list[list[str]]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    for table in tables:
        header_index = next(
            (i for i, row in enumerate(table)
             if len(row) >= 5 and ROUND_LABELS.issubset({clean(cell).lower() for cell in row})),
            None,
        )
        if header_index is None:
            continue
        headers = [clean(cell).lower() for cell in table[header_index]]
        columns = {key: numeric_column(headers, aliases) for key, aliases in FIELD_ALIASES.items()}
        appearances = 0
        totals = {key: 0 for key in FIELD_ALIASES}
        seen = {key: False for key in FIELD_ALIASES}
        rounds: list[dict[str, Any]] = []
        for row in table[header_index + 1:]:
            if not row or as_int(row[0]) is None:
                continue
            appearances += 1
            record: dict[str, Any] = {"round": as_int(row[0])}
            for key, column in columns.items():
                value = as_int(row[column]) if column is not None and column < len(row) else None
                record[key] = value
                if value is not None:
                    totals[key] += value
                    seen[key] = True
            rounds.append(record)
        result: dict[str, Any] = {"appearances": appearances}
        for key in FIELD_ALIASES:
            result[key] = totals[key] if seen[key] else None
        return result, rounds
    return {"appearances": None, **{key: None for key in FIELD_ALIASES}}, []


def extract_profile(profile: dict[str, Any], drl_player_id: int) -> dict[str, Any]:
    html = fetch_bytes(profile["profile_url"], "text/html").decode("utf-8", errors="replace")
    parser = ProfileParser()
    parser.feed(html)
    totals, rounds = extract_round_table(parser.tables)
    page_text = clean(" ".join(parser._text_parts))
    efficiency = re.search(r"Tackle\\s*Efficiency\\s*(\\d+(?:\\.\\d+)?)\\s*%", page_text, re.I)
    totals["tackle_efficiency"] = float(efficiency.group(1)) if efficiency else None
    # Errors and penalties are not included in the inspected profile round table.
    totals["errors"] = None
    totals["penalties_conceded"] = None
    image = next((item for item in parser.images if "photo of" in item["alt"].lower()), None)
    return {
        "season": SEASON,
        "drl_player_id": drl_player_id,
        "source_provider": "nrl.com",
        "source_profile_url": profile["profile_url"],
        "directory_identity": {
            "first_name": profile["first_name"],
            "last_name": profile["last_name"],
            "team": profile["team"],
            "position": profile["position"],
        },
        "stats": totals,
        "rounds": rounds,
        "profile_image_candidate": image,
        "media_rights_status": "pending_review" if image else None,
        "identity_review_required": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--players", required=True, type=Path,
                        help="JSON export of JARVIS player rows")
    parser.add_argument("--output", required=True, type=Path,
                        help="Path for review-only extraction JSON")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Seconds between official NRL requests (default: 1)")
    args = parser.parse_args()

    rows = json.loads(args.players.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise SystemExit("--players must contain a JSON array.")

    squad_ids = sorted({
        int(row["squad_id"]) for row in rows
        if str(row.get("identity_status", "")).casefold() == "verified"
        and str(row.get("squad_id", "")).isdigit()
        and int(row["squad_id"]) in SQUAD_IDS
    })
    directory: dict[int, list[dict[str, Any]]] = {}
    for index, squad_id in enumerate(squad_ids):
        try:
            directory[squad_id] = discover_squad(squad_id, args.delay)
            print(f"Directory squad {squad_id}: {len(directory[squad_id])} profiles", file=sys.stderr)
        except (HTTPError, URLError, TimeoutError, RuntimeError, ValueError) as error:
            print(f"Directory squad {squad_id} failed: {error}", file=sys.stderr)
            directory[squad_id] = []

    results: list[dict[str, Any]] = []
    eligible = [row for row in rows if str(row.get("identity_status", "")).casefold() == "verified"]
    for index, row in enumerate(eligible):
        try:
            player_id = int(row["drl_player_id"])
        except (KeyError, TypeError, ValueError):
            results.append({"status": "skipped", "reason": "missing_or_invalid_drl_player_id"})
            continue
        try:
            squad_id = int(row.get("squad_id"))
        except (TypeError, ValueError):
            squad_id = -1
        profile, reason = match_player(row, directory.get(squad_id, []))
        if profile is None:
            results.append({
                "status": "review_required",
                "reason": reason,
                "drl_player_id": player_id,
            })
            continue
        try:
            record = extract_profile(profile, player_id)
            record["status"] = "extracted_for_review"
            results.append(record)
            print(f"Extracted DRL player {player_id} ({index + 1}/{len(eligible)})", file=sys.stderr)
        except (HTTPError, URLError, TimeoutError, RuntimeError, ValueError) as error:
            results.append({
                "status": "extraction_failed",
                "drl_player_id": player_id,
                "source_profile_url": profile["profile_url"],
                "error": str(error),
            })
        if index + 1 < len(eligible):
            time.sleep(max(0, args.delay))

    args.output.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\\n", encoding="utf-8")
    counts: dict[str, int] = {}
    for item in results:
        key = str(item.get("status", "unknown"))
        counts[key] = counts.get(key, 0) + 1
    print(f"Wrote {len(results)} review records: {counts}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
