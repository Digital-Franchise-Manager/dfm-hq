"""Independent DRL Draft fantasy points calculation engine."""
from __future__ import annotations

from collections.abc import Iterable

from backend.dfm.sports.drl.core.points_scoring import (
    METRE_DIVISORS,
    STAT_POINTS,
    CaptaincySelection,
    PlayerAvailability,
    PlayerRoundStats,
    validate_round_stats,
)
from .models import DraftPlayerPoints, DraftRoundPoints


class DraftPointsEngine:
    """Calculate Draft points from verified NRL match statistics.

    Draft owns this calculation independently of Classic. The engine is
    deterministic and in-memory; source ingestion and persistence are external.
    """

    mode = "draft"

    @staticmethod
    def _base_points(record: PlayerRoundStats) -> int:
        if record.availability is not PlayerAvailability.PLAYED:
            return 0
        points = 0
        for statistic, amount in record.statistics.items():
            if statistic in METRE_DIVISORS:
                points += int(amount) // METRE_DIVISORS[statistic]
            else:
                points += STAT_POINTS[statistic] * int(amount)
        return points

    def score_round(
        self,
        round_id: str,
        player_stats: Iterable[PlayerRoundStats],
        captaincy: CaptaincySelection,
    ) -> DraftRoundPoints:
        records = tuple(player_stats)
        validate_round_stats(round_id, records, captaincy)
        player_by_id = {record.player_id: record for record in records}
        captain_record = player_by_id[captaincy.captain_player_id]
        vice_multiplier = 2 if captain_record.availability in (
            PlayerAvailability.DNP,
            PlayerAvailability.BYE,
        ) else 1

        player_scores = []
        for record in records:
            base_points = self._base_points(record)
            if record.player_id == captaincy.captain_player_id:
                multiplier = 2
            elif record.player_id == captaincy.vice_captain_player_id:
                multiplier = vice_multiplier
            else:
                multiplier = 1
            player_scores.append(
                DraftPlayerPoints(
                    player_id=record.player_id,
                    match_id=record.match_id,
                    base_points=base_points,
                    multiplier=multiplier,
                    total_points=base_points * multiplier,
                    availability=record.availability,
                )
            )

        result = tuple(player_scores)
        return DraftRoundPoints(
            round_id=round_id,
            player_scores=result,
            total_points=sum(player.total_points for player in result),
        )
