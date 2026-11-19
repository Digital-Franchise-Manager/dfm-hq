"""Independent DRL Classic fantasy points calculation engine."""
from __future__ import annotations

from collections.abc import Iterable

from backend.dfm.drl.core.points_scoring import (
    METRE_DIVISORS,
    STAT_POINTS,
    CaptaincySelection,
    PlayerAvailability,
    PlayerRoundStats,
    ScoringStat,
    validate_round_stats,
)
from .models import ClassicPlayerPoints, ClassicRoundPoints


class ClassicPointsEngine:
    """Calculate Classic points from verified NRL match statistics.

    This is a deterministic, in-memory domain engine. It does not fetch stats,
    persist processed events or share its calculation implementation with Draft.
    """

    mode = "classic"

    @staticmethod
    def _base_points(record: PlayerRoundStats) -> int:
        if record.availability is not PlayerAvailability.PLAYED:
            return 0
        total = 0
        for stat, value in record.statistics.items():
            if stat in METRE_DIVISORS:
                total += int(value) // METRE_DIVISORS[stat]
            else:
                total += STAT_POINTS[stat] * int(value)
        return total

    def score_round(
        self,
        round_id: str,
        player_stats: Iterable[PlayerRoundStats],
        captaincy: CaptaincySelection,
    ) -> ClassicRoundPoints:
        records = tuple(player_stats)
        validate_round_stats(round_id, records, captaincy)
        by_id = {record.player_id: record for record in records}
        captain = by_id[captaincy.captain_player_id]
        vice_multiplier = (
            2
            if captain.availability in (PlayerAvailability.DNP, PlayerAvailability.BYE)
            else 1
        )

        scores = []
        for record in records:
            base_points = self._base_points(record)
            if record.player_id == captaincy.captain_player_id:
                multiplier = 2
            elif record.player_id == captaincy.vice_captain_player_id:
                multiplier = vice_multiplier
            else:
                multiplier = 1
            scores.append(
                ClassicPlayerPoints(
                    player_id=record.player_id,
                    match_id=record.match_id,
                    base_points=base_points,
                    multiplier=multiplier,
                    total_points=base_points * multiplier,
                    availability=record.availability,
                )
            )

        result = tuple(scores)
        return ClassicRoundPoints(
            round_id=round_id,
            player_scores=result,
            total_points=sum(score.total_points for score in result),
        )
