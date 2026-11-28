"""Shared DRL fantasy scoring vocabulary and immutable input contracts.

The Classic and Draft calculation engines remain independent. This module
contains only the scoring rules, data contracts and input validation shared
by both modes; it does not calculate fantasy scores or persist results.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Mapping


class ScoringCategory(str, Enum):
    ATTACKING = "attacking"
    DEFENSIVE = "defensive"
    DISCIPLINE = "discipline"


class ScoringStat(str, Enum):
    TRY = "try"
    GOAL = "goal"
    FIELD_GOAL = "field_goal"
    TRY_ASSIST = "try_assist"
    LINE_BREAK = "line_break"
    LINE_BREAK_ASSIST = "line_break_assist"
    TACKLE = "tackle"
    TACKLE_BREAK = "tackle_break"
    MISSED_TACKLE = "missed_tackle"
    OFFLOAD_TO_HAND = "offload_to_hand"
    OFFLOAD_TO_GROUND = "offload_to_ground"
    ERROR = "error"
    FORTY_TWENTY = "forty_twenty"
    TWENTY_FORTY = "twenty_forty"
    TOTAL_METRES = "total_metres"
    KICK_METRES = "kick_metres"
    PENALTY_CONCEDED = "penalty_conceded"
    SIX_AGAIN_INFRINGEMENT = "six_again_infringement"
    SIN_BIN = "sin_bin"
    SEND_OFF = "send_off"
    TRY_SAVE = "try_save"
    KICKS_DEFUSED = "kicks_defused"
    FORCED_DROPOUT = "forced_dropout"
    TURNOVER = "turnover"
    ESCAPE_IN_GOAL = "escape_in_goal"


STAT_CATEGORIES = {
    ScoringStat.TRY: ScoringCategory.ATTACKING,
    ScoringStat.GOAL: ScoringCategory.ATTACKING,
    ScoringStat.FIELD_GOAL: ScoringCategory.ATTACKING,
    ScoringStat.TRY_ASSIST: ScoringCategory.ATTACKING,
    ScoringStat.LINE_BREAK: ScoringCategory.ATTACKING,
    ScoringStat.LINE_BREAK_ASSIST: ScoringCategory.ATTACKING,
    ScoringStat.TACKLE: ScoringCategory.DEFENSIVE,
    ScoringStat.TACKLE_BREAK: ScoringCategory.ATTACKING,
    ScoringStat.MISSED_TACKLE: ScoringCategory.DEFENSIVE,
    ScoringStat.OFFLOAD_TO_HAND: ScoringCategory.ATTACKING,
    ScoringStat.OFFLOAD_TO_GROUND: ScoringCategory.ATTACKING,
    ScoringStat.ERROR: ScoringCategory.DISCIPLINE,
    ScoringStat.FORTY_TWENTY: ScoringCategory.ATTACKING,
    ScoringStat.TWENTY_FORTY: ScoringCategory.ATTACKING,
    ScoringStat.TOTAL_METRES: ScoringCategory.ATTACKING,
    ScoringStat.KICK_METRES: ScoringCategory.ATTACKING,
    ScoringStat.PENALTY_CONCEDED: ScoringCategory.DISCIPLINE,
    ScoringStat.SIX_AGAIN_INFRINGEMENT: ScoringCategory.DISCIPLINE,
    ScoringStat.SIN_BIN: ScoringCategory.DISCIPLINE,
    ScoringStat.SEND_OFF: ScoringCategory.DISCIPLINE,
    ScoringStat.TRY_SAVE: ScoringCategory.DEFENSIVE,
    ScoringStat.KICKS_DEFUSED: ScoringCategory.DEFENSIVE,
    ScoringStat.FORCED_DROPOUT: ScoringCategory.DEFENSIVE,
    ScoringStat.TURNOVER: ScoringCategory.ATTACKING,
    ScoringStat.ESCAPE_IN_GOAL: ScoringCategory.ATTACKING,
}

# Per-occurrence values. Metre statistics are calculated using METRE_DIVISORS.
STAT_POINTS = {
    ScoringStat.TRY: 8,
    ScoringStat.GOAL: 2,
    ScoringStat.FIELD_GOAL: 5,
    ScoringStat.TRY_ASSIST: 5,
    ScoringStat.LINE_BREAK: 4,
    ScoringStat.LINE_BREAK_ASSIST: 2,
    ScoringStat.TACKLE: 1,
    ScoringStat.TACKLE_BREAK: 2,
    ScoringStat.MISSED_TACKLE: -2,
    ScoringStat.OFFLOAD_TO_HAND: 4,
    ScoringStat.OFFLOAD_TO_GROUND: 2,
    ScoringStat.ERROR: -2,
    ScoringStat.FORTY_TWENTY: 4,
    ScoringStat.TWENTY_FORTY: 4,
    ScoringStat.PENALTY_CONCEDED: -2,
    ScoringStat.SIX_AGAIN_INFRINGEMENT: -1,
    ScoringStat.SIN_BIN: -5,
    ScoringStat.SEND_OFF: -10,
    ScoringStat.TRY_SAVE: 5,
    ScoringStat.KICKS_DEFUSED: 1,
    ScoringStat.FORCED_DROPOUT: 2,
    ScoringStat.TURNOVER: 4,
    ScoringStat.ESCAPE_IN_GOAL: 2,
}
METRE_DIVISORS = {
    ScoringStat.TOTAL_METRES: 10,
    ScoringStat.KICK_METRES: 30,
}
COUNT_STATS = frozenset(ScoringStat) - frozenset(METRE_DIVISORS)


class PlayerAvailability(str, Enum):
    PLAYED = "played"
    DNP = "dnp"
    BYE = "bye"


@dataclass(frozen=True, slots=True)
class PlayerRoundStats:
    """Verified statistics for one player in one NRL match within a DRL round.

    statistics accepts ScoringStat keys or their string values. event_ids are
    source-stat event identifiers used to reject duplicate events in a round.
    Corrected source data should be submitted as a replacement snapshot and
    recalculated; the calculation engines deliberately hold no persistent state.
    """
    player_id: str
    match_id: str
    statistics: Mapping[ScoringStat | str, int | float]
    event_ids: tuple[str, ...] = ()
    availability: PlayerAvailability = PlayerAvailability.PLAYED

    def __post_init__(self) -> None:
        if not isinstance(self.player_id, str) or not self.player_id.strip():
            raise ValueError("player_id is required")
        if not isinstance(self.match_id, str) or not self.match_id.strip():
            raise ValueError("match_id is required")
        try:
            availability = PlayerAvailability(self.availability)
        except ValueError as exc:
            raise ValueError("availability must be played, dnp or bye") from exc
        object.__setattr__(self, "availability", availability)

        normalized = {}
        for raw_stat, raw_value in dict(self.statistics).items():
            try:
                stat = raw_stat if isinstance(raw_stat, ScoringStat) else ScoringStat(raw_stat)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"unknown scoring statistic: {raw_stat}") from exc
            if stat in normalized:
                raise ValueError(f"duplicate statistic: {stat.value}")
            if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
                raise ValueError(f"{stat.value} must be numeric")
            if not isfinite(raw_value) or raw_value < 0:
                raise ValueError(f"{stat.value} must be finite and non-negative")
            if stat in COUNT_STATS and int(raw_value) != raw_value:
                raise ValueError(f"{stat.value} must be a whole-number count")
            normalized[stat] = raw_value

        event_ids = tuple(self.event_ids)
        if any(not isinstance(event_id, str) or not event_id.strip() for event_id in event_ids):
            raise ValueError("event_ids must contain non-empty strings")
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("event_ids must be unique within a player record")
        if availability is not PlayerAvailability.PLAYED:
            if any(normalized.values()) or event_ids:
                raise ValueError("DNP and bye records cannot contain match statistics or event IDs")
        object.__setattr__(self, "statistics", normalized)
        object.__setattr__(self, "event_ids", event_ids)


@dataclass(frozen=True, slots=True)
class CaptaincySelection:
    """The round's nominated captain and vice-captain."""
    captain_player_id: str
    vice_captain_player_id: str

    def __post_init__(self) -> None:
        if not self.captain_player_id or not self.captain_player_id.strip():
            raise ValueError("captain_player_id is required")
        if not self.vice_captain_player_id or not self.vice_captain_player_id.strip():
            raise ValueError("vice_captain_player_id is required")
        if self.captain_player_id == self.vice_captain_player_id:
            raise ValueError("captain and vice-captain must be different players")


def validate_round_stats(
    round_id: str,
    player_stats: tuple[PlayerRoundStats, ...],
    captaincy: CaptaincySelection,
) -> None:
    """Validate unique player rows, source events and captaincy membership."""
    if not isinstance(round_id, str) or not round_id.strip():
        raise ValueError("round_id is required")
    if not player_stats:
        raise ValueError("at least one player statistics record is required")

    player_ids = [record.player_id for record in player_stats]
    if len(player_ids) != len(set(player_ids)):
        raise ValueError("each player may have only one statistics record per round")
    by_id = {record.player_id: record for record in player_stats}
    if captaincy.captain_player_id not in by_id:
        raise ValueError("captain must have a player statistics or availability record")
    if captaincy.vice_captain_player_id not in by_id:
        raise ValueError("vice-captain must have a player statistics or availability record")

    seen_events = set()
    for record in player_stats:
        for event_id in record.event_ids:
            if event_id in seen_events:
                raise ValueError(f"duplicate statistical event ID in round: {event_id}")
            seen_events.add(event_id)
