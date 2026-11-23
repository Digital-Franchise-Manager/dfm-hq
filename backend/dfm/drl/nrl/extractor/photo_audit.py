#!/usr/bin/env python3
"""Audit DRL photo manifests and downloaded image files without external libraries."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def image_info(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    info: dict[str, Any] = {
        "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
        "format": "unknown", "width": None, "height": None,
    }
    if data.startswith(b"\xff\xd8\xff"):
        info["format"] = "jpeg"
        offset = 2
        while offset + 9 < len(data):
            if data[offset] != 0xFF:
                offset += 1
                continue
            marker = data[offset + 1]
            offset += 2
            if marker in {0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
                continue
            if offset + 2 > len(data):
                break
            length = int.from_bytes(data[offset:offset + 2], "big")
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF} and offset + 7 < len(data):
                info["height"] = int.from_bytes(data[offset + 3:offset + 5], "big")
                info["width"] = int.from_bytes(data[offset + 5:offset + 7], "big")
                break
            if length < 2:
                break
            offset += length
    elif data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        info.update(format="png", width=int.from_bytes(data[16:20], "big"), height=int.from_bytes(data[20:24], "big"))
    elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        info["format"] = "webp"
        if data[12:16] == b"VP8X" and len(data) >= 30:
            info["width"] = 1 + int.from_bytes(data[24:27], "little")
            info["height"] = 1 + int.from_bytes(data[27:30], "little")
    return info


def audit_manifest(manifest: dict[str, Any], staging: Path) -> dict[str, Any]:
    candidates = manifest.get("candidates", [])
    players = {str(item.get("drl_player_id")) for item in candidates if item.get("drl_player_id") is not None}
    seen_hashes: dict[str, str] = {}
    duplicate_files: list[dict[str, str]] = []
    missing_files: list[dict[str, Any]] = []
    file_errors: list[dict[str, Any]] = []
    downloaded = 0
    for item in candidates:
        relative = item.get("download_path")
        if not relative:
            continue
        path = Path(relative)
        if not path.is_absolute():
            path = staging / path
        if not path.is_file():
            missing_files.append({"drl_player_id": item.get("drl_player_id"), "path": str(path)})
            continue
        downloaded += 1
        try:
            info = image_info(path)
            digest = info["sha256"]
            if digest in seen_hashes:
                duplicate_files.append({"path": str(path), "duplicate_of": seen_hashes[digest]})
            else:
                seen_hashes[digest] = str(path)
            item["audit_image"] = info
            if info["format"] == "unknown" or info["width"] is None or info["height"] is None:
                file_errors.append({"path": str(path), "reason": "unsupported_or_unreadable_image"})
        except OSError as error:
            file_errors.append({"path": str(path), "reason": str(error)})
    statuses: dict[str, int] = {}
    for item in candidates:
        status = str(item.get("status", "unknown"))
        statuses[status] = statuses.get(status, 0) + 1
    return {
        "players_with_candidates": len(players), "candidate_count": len(candidates),
        "downloaded_count": downloaded, "missing_download_files": missing_files,
        "duplicate_files": duplicate_files, "file_errors": file_errors,
        "status_counts": statuses,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--staging", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    report = audit_manifest(manifest, args.staging)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
