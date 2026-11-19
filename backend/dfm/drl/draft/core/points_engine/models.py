"""Draft-mode result contracts for fantasy points scoring."""
from dataclasses import dataclass

from backend.dfm.drl.core.points_scoring import PlayerAvailability


@dataclass(frozen=True, slots=True)
class DraftPlayerPoints:
    player_id: str
    match_id: str
    base_points: int
    multiplier: int
    total_points: int
    availability: PlayerAvailability


@dataclass(frozen=True, slots=True)
class DraftRoundPoints:
    round_id: str
    player_scores: tuple[DraftPlayerPoints, ...]
    total_points: int
