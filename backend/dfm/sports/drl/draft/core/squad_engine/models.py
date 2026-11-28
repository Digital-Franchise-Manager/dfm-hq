"""Immutable contracts for Draft squad selection and round scoring."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping
from backend.dfm.sports.drl.core.player_positions import validate_player_positions

@dataclass(frozen=True, slots=True)
class DraftPlayer:
    """A player and their single positional assignment for this round."""
    player_id: str
    primary_position: str
    secondary_positions: tuple[str, ...] = ()
    selected_position: str | None = None
    fantasy_points: float = 0.0

    def __post_init__(self) -> None:
        if not self.player_id or not self.player_id.strip():
            raise ValueError("player_id is required")
        validate_player_positions(self.primary_position, self.secondary_positions, require_primary=True)
        if self.selected_position is not None and self.selected_position not in self.eligible_positions:
            raise ValueError("selected_position must be one of the player's eligible positions")
        if self.fantasy_points < 0:
            raise ValueError("fantasy_points cannot be negative")

    @property
    def eligible_positions(self) -> tuple[str, ...]:
        return (self.primary_position, *self.secondary_positions)

@dataclass(frozen=True, slots=True)
class SquadSelection:
    """A complete round squad: positional XIII, bench and up to four EMGs."""
    roster_player_ids: tuple[str, ...]
    starting_xiii: Mapping[str, tuple[str, ...]]
    bench_player_ids: tuple[str, ...]
    emergency_assignments: Mapping[str, str]
    auto_emergency: bool = True

@dataclass(frozen=True, slots=True)
class Replacement:
    position: str
    unavailable_player_id: str
    replacement_player_id: str
    replacement_points: float
    automatic: bool

@dataclass(frozen=True, slots=True)
class SquadScore:
    total_points: float
    starting_points: Mapping[str, float]
    replacements: tuple[Replacement, ...]
    unused_bench_player_ids: tuple[str, ...]
