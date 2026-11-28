"""Immutable Draft Mode session and selection records."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from backend.dfm.sports.drl.draft.core.draft_order_engine.models import DraftOrderType


class DraftStatus(str, Enum):
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class DraftPick:
    pick_number: int
    round_number: int
    franchise_id: str
    player_id: str


@dataclass(frozen=True, slots=True)
class DraftSession:
    """In-memory draft state; persistence is supplied by an outer service."""

    franchise_order: tuple[str, ...]
    player_pool: tuple[str, ...]
    rounds: int
    draft_type: DraftOrderType
    picks: tuple[DraftPick, ...] = ()
    status: DraftStatus = DraftStatus.READY

    @property
    def total_picks(self) -> int:
        return len(self.franchise_order) * self.rounds

    @property
    def remaining_picks(self) -> int:
        return self.total_picks - len(self.picks)

    @property
    def available_player_ids(self) -> tuple[str, ...]:
        selected = {pick.player_id for pick in self.picks}
        return tuple(player_id for player_id in self.player_pool if player_id not in selected)
