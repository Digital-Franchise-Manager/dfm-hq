"""Immutable contracts for the DRL Classic 21-player squad engine."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping

from backend.dfm.drl.core.player_positions import validate_player_positions


@dataclass(frozen=True, slots=True)
class ClassicPlayer:
    """A registered squad player with a round-specific selected position."""

    player_id: str
    primary_position: str
    secondary_positions: tuple[str, ...] = ()
    selected_position: str | None = None
    fantasy_points: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.player_id, str) or not self.player_id.strip():
            raise ValueError("player_id is required")
        validate_player_positions(
            self.primary_position, self.secondary_positions, require_primary=True
        )
        if self.selected_position is None:
            raise ValueError("selected_position is required for Classic squad players")
        if self.selected_position not in self.eligible_positions:
            raise ValueError("selected_position must be one of the player's eligible positions")
        if not isfinite(self.fantasy_points) or self.fantasy_points < 0:
            raise ValueError("fantasy_points must be a finite non-negative number")

    @property
    def eligible_positions(self) -> tuple[str, ...]:
        return (self.primary_position, *self.secondary_positions)


@dataclass(frozen=True, slots=True)
class ClassicSquadSelection:
    """A 21-player squad: positional XIII, four interchange and four EMGs.

    Emergency assignments map a player in the scoring 17 to the EMG player
    nominated to replace that player if unavailable.
    """

    roster_player_ids: tuple[str, ...]
    starting_xiii: Mapping[str, tuple[str, ...]]
    interchange_player_ids: tuple[str, ...]
    emergency_player_ids: tuple[str, ...]
    emergency_assignments: Mapping[str, str]
    auto_emergency: bool = True


@dataclass(frozen=True, slots=True)
class ClassicReplacement:
    """An emergency substitution made for an unavailable scoring player."""

    position: str
    unavailable_player_id: str
    replacement_player_id: str
    replacement_points: float
    automatic: bool


@dataclass(frozen=True, slots=True)
class ClassicSquadScore:
    """Final Classic round score and positional breakdown."""

    total_points: float
    position_points: Mapping[str, float]
    replacements: tuple[ClassicReplacement, ...]
    unused_emergency_player_ids: tuple[str, ...]
