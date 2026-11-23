#!/usr/bin/env python3
"""Extract verifiable NRL season totals from supplied official player-profile URLs.

Input manifest JSON:
[
  {"drl_player_id": 12345, "season": 2026,
   "profile_url": "https://www.nrl.com/players/nrl-premiership/club/player/"}
]

The script never guesses profile URLs or player identities. It writes a reviewable JSON
file; it does not connect to Supabase, upload photographs, or publish media.
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
from urllib.request import Request, urlopen

USER_AGENT = "DFM-DRL-PlayerArchive/1.0 (+https://digitalfranchisemanager.com)"
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
    return re.sub(r"\s+", " ", value).strip()


def as_int(value: str) -> int | None:
    value = clean(value).replace(",", "")
    if not value or value in {"-", "—", "–"}:
        return None
    match = re.fullmatch(r"-?\d+", value)
    return int(value) if match else None


class ProfileParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._cell_tag: str | None = None
        self.images: list[dict[str, str]] = []
        self._capture_image = False
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []
            self._cell_tag = tag
        elif tag == "img":
            src = attr.get("src") or attr.get("data-src")
            alt = clean(attr.get("alt") or "")
            if src and ("player" in alt.lower() or "photo of" in alt.lower()):
                self.images.append({"src": src, "alt": alt})
        elif tag in {"h1", "p", "div", "span"}:
            self._text_parts.append(" ")

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)
        self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(clean(" ".join(self._cell)))
            self._cell = None
            self._cell_tag = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if self._row:
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None


def numeric_column(headers: list[str], aliases: tuple[str, ...]) -> int | None:
    normalized = [clean(h).lower() for h in headers]
    for alias in aliases:
        if alias in normalized:
            return normalized.index(alias)
    return None


def extract_round_table(tables: list[list[list[str]]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    for table in tables:
        header_index = next(
            (i for i, row in enumerate(table)
             if len(row) >= 5 and ROUND_LABELS.issubset({clean(c).lower() for c in row})),
            None,
        )
        if header_index is None:
            continue
        headers = [clean(cell).lower() for cell in table[header_index]]
        columns = {key: numeric_column(headers, aliases) for key, aliases in FIELD_ALIASES.items()}
        appearances = 0
        totals = {key: 0 for key in FIELD_ALIASES}
        seen = {key: False for key in FIELD_ALIASES}
        round_records: list[dict[str, Any]] = []
        for row in table[header_index + 1:]:
            if not row or as_int(row[0]) is None:
                continue
            appearances += 1
            record: dict[str, Any] = {"round": as_int(row[0])}
            for key, index in columns.items():
                value = as_int(row[index]) if index is not None and index < len(row) else None
                record[key] = value
                if value is not None:
                    totals[key] += value
                    seen[key] = True
            round_records.append(record)
        result: dict[str, Any] = {"appearances": appearances}
        for key in FIELD_ALIASES:
            result[key] = totals[key] if seen[key] else None
        return result, round_records
    return {"appearances": None, **{key: None for key in FIELD_ALIASES}}, []


def extract_profile(html: str, profile_url: str, drl_player_id: int, season: int) -> dict[str, Any]:
    parser = ProfileParser()
    parser.feed(html)
    totals, round_records = extract_round_table(parser.tables)
    page_text = clean(" ".join(parser._text_parts))
    efficiency = re.search(r"Tackle\s*Efficiency\s*(\d+(?:\.\d+)?)\s*%", page_text, re.I)
    totals["tackle_efficiency"] = float(efficiency.group(1)) if efficiency else None

    # The inspected NRL profile round table does not include errors or penalties conceded.
    totals["errors"] = None
    totals["penalties_conceded"] = None

    profile_image = next((image for image in parser.images if "photo of" in image["alt"].lower()), None)
    return {
        "season": season,
        "drl_player_id": drl_player_id,
        "source_provider": "nrl.com",
        "source_profile_url": profile_url,
        "stats": totals,
        "rounds": round_records,
        "profile_image_candidate": profile_image,
        "media_rights_status": "pending_review" if profile_image else None,
        "identity_review_required": True,
    }


def fetch(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    with urlopen(request, timeout=25) as response:
        if response.status != 200:
            raise RuntimeError(f"Unexpected HTTP status {response.status}")
        return response.read().decode("utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if not isinstance(manifest, list):
        raise SystemExit("Manifest must be a JSON array.")
    results = []
    for index, item in enumerate(manifest):
        player_id = item.get("drl_player_id")
        season = item.get("season")
        url = item.get("profile_url")
        if not isinstance(player_id, int) or not isinstance(season, int) or not isinstance(url, str):
            print(f"Skipping invalid manifest row {index + 1}", file=sys.stderr)
            continue
        if not url.startswith("https://www.nrl.com/players/"):
            print(f"Skipping non-NRL profile URL for player {player_id}", file=sys.stderr)
            continue
        try:
            html = fetch(url)
            results.append(extract_profile(html, url, player_id, season))
            print(f"Extracted {player_id} ({index + 1}/{len(manifest)})", file=sys.stderr)
        except (HTTPError, URLError, TimeoutError, RuntimeError) as error:
            results.append({
                "season": season, "drl_player_id": player_id,
                "source_provider": "nrl.com", "source_profile_url": url,
                "error": str(error), "stats": None,
                "identity_review_required": True,
            })
        if index + 1 < len(manifest):
            time.sleep(max(0, args.delay))

    args.output.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(results)} review records to {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
