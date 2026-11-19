"""Immutable contracts for Draft waivers, claims and roster moves."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from backend.dfm.drl.draft.core.trade_engine.models import DraftLeagueState


class WaiverEntryStatus(str, Enum):
    OPEN = "open"
    PROCESSED = "processed"


@dataclass(frozen=True, slots=True)
class WaiverSettings:
    waiver_period: timedelta = timedelta(hours=24)
    move_limit_per_franchise: int | None = None

    def __post_init__(self) -> None:
        if self.waiver_period.total_seconds() < 0:
            raise ValueError("waiver_period cannot be negative")
        if self.move_limit_per_franchise is not None and self.move_limit_per_franchise < 0:
            raise ValueError("move_limit_per_franchise cannot be negative")


@dataclass(frozen=True, slots=True)
class WaiverEntry:
    player_id: str
    dropped_by_franchise_id: str
    dropped_at: datetime
    clears_at: datetime
    status: WaiverEntryStatus = WaiverEntryStatus.OPEN


@dataclass(frozen=True, slots=True)
class WaiverClaim:
    claim_id: str
    player_id: str
    franchise_id: str
    drop_player_id: str
    submitted_at: datetime


@dataclass(frozen=True, slots=True)
class DraftWaiverState:
    league_state: DraftLeagueState
    waiver_priority: tuple[str, ...]
    entries: tuple[WaiverEntry, ...] = ()
    claims: tuple[WaiverClaim, ...] = ()
    moves_used: tuple[tuple[str, int], ...] = ()

    def moves_for(self, franchise_id: str) -> int:
        return dict(self.moves_used).get(franchise_id, 0)
