"""Canonical rugby league player-position definitions shared by DRL modes.

This module owns position vocabulary and validation only. Classic and Draft
retain independent competition, awards and roster-selection rules.
"""

from __future__ import annotations

from collections.abc import Iterable

POSITIONAL_XIII: tuple[tuple[str, int], ...] = (
    ("WFB", 3),
    ("CTR", 2),
    ("HLF", 2),
    ("EDG", 2),
    ("MID", 3),
    ("HOK", 1),
)

POSITION_CODES: tuple[str, ...] = tuple(code for code, _ in POSITIONAL_XIII)
VALID_POSITION_CODES = frozenset(POSITION_CODES)


def validate_position(position: str, *, field: str = "position") -> None:
    """Reject any position code outside the canonical six-position system."""
    if not isinstance(position, str) or position not in VALID_POSITION_CODES:
        allowed = ", ".join(POSITION_CODES)
        raise ValueError(f"{field} must be one of: {allowed}")


def validate_player_positions(
    primary_position: str = "",
    secondary_positions: Iterable[str] = (),
    *,
    require_primary: bool = False,
) -> None:
    """Validate primary and secondary assignments.

    Empty primary positions remain permitted for legacy award candidates that
    are not used in positional selection. Registration/roster boundaries can
    call this helper with require_primary=True.
    """
    if not isinstance(primary_position, str):
        raise ValueError("primary_position must be a position code string")
    if not primary_position and require_primary:
        raise ValueError("primary_position is required")
    if primary_position:
        validate_position(primary_position, field="primary_position")

    if isinstance(secondary_positions, (str, bytes)):
        raise ValueError("secondary_positions must be an iterable of position codes")
    try:
        secondary = tuple(secondary_positions)
    except TypeError as exc:
        raise ValueError("secondary_positions must be an iterable of position codes") from exc

    if len(secondary) != len(set(secondary)):
        raise ValueError("secondary_positions must not contain duplicates")
    for position in secondary:
        validate_position(position, field="secondary_position")
    if primary_position and primary_position in secondary:
        raise ValueError("primary_position must not also appear in secondary_positions")
