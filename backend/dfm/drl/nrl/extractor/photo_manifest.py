#!/usr/bin/env python3
"""Portable JSON manifest helpers for DRL player photographs."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

MANIFEST_VERSION = 1


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": MANIFEST_VERSION, "season": 2026, "candidates": []}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("candidates"), list):
        raise ValueError("Manifest must be an object containing a candidates array.")
    return value


def write_manifest(path: Path, candidates: list[dict[str, Any]], season: int = 2026) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": MANIFEST_VERSION, "season": int(season), "candidates": candidates}
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def candidate_key(candidate: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(candidate.get("drl_player_id", "")),
        str(candidate.get("media_kind", "")),
        str(candidate.get("image_url", "")),
    )


def merge_candidates(existing: list[dict[str, Any]], discovered: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = {candidate_key(item): dict(item) for item in existing}
    for item in discovered:
        key = candidate_key(item)
        if key in merged:
            old = merged[key]
            # Refresh review metadata but never erase a previously downloaded local file.
            saved_path = old.get("download_path")
            saved_status = old.get("status")
            old.update(item)
            if saved_path:
                old["download_path"] = saved_path
            if saved_status == "downloaded_private":
                old["status"] = saved_status
        else:
            merged[key] = dict(item)
    return sorted(
        merged.values(),
        key=lambda item: (
            str(item.get("drl_player_id", "")),
            str(item.get("media_kind", "")),
            str(item.get("image_url", "")),
        ),
    )
