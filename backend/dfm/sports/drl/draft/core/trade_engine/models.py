"""Immutable contracts for Draft league rosters and coach-to-coach trades."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class TradeStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    REJECTED = "rejected"
    VETOED = "vetoed"
    EXPIRED = "expired"
    COUNTERED = "countered"


class VetoMode(str, Enum):
    DISABLED = "disabled"
    COMMISSIONER = "commissioner"
    LEAGUE_VOTE = "league_vote"


@dataclass(frozen=True, slots=True)
class DraftRoster:
    franchise_id: str
    player_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DraftTradeSettings:
    trade_deadline: datetime | None = None
    review_period: timedelta = timedelta(hours=24)
    veto_mode: VetoMode = VetoMode.COMMISSIONER
    veto_vote_threshold: float = 0.5

    def __post_init__(self) -> None:
        object.__setattr__(self, "veto_mode", VetoMode(self.veto_mode))
        if not isinstance(self.review_period, timedelta):
            raise ValueError("review_period must be a timedelta")
        if self.review_period.total_seconds() < 0:
            raise ValueError("review_period cannot be negative")
        if not 0 < self.veto_vote_threshold <= 1:
            raise ValueError("veto_vote_threshold must be greater than 0 and at most 1")
        if self.trade_deadline is not None and (
            self.trade_deadline.tzinfo is None or self.trade_deadline.utcoffset() is None
        ):
            raise ValueError("trade_deadline must be timezone-aware")


@dataclass(frozen=True, slots=True)
class VetoVote:
    franchise_id: str
    veto: bool
    voted_at: datetime


@dataclass(frozen=True, slots=True)
class TradeProposal:
    proposal_id: str
    proposing_franchise_id: str
    receiving_franchise_id: str
    offered_player_ids: tuple[str, ...]
    requested_player_ids: tuple[str, ...]
    roster_drops: tuple[tuple[str, tuple[str, ...]], ...]
    free_agent_additions: tuple[tuple[str, tuple[str, ...]], ...]
    proposed_at: datetime
    status: TradeStatus = TradeStatus.PROPOSED
    accepted_at: datetime | None = None
    review_until: datetime | None = None
    votes: tuple[VetoVote, ...] = ()
    parent_proposal_id: str | None = None
    countered_by_proposal_id: str | None = None
    invalid_roster_franchise_ids: tuple[str, ...] = ()
    confirmed_invalid_roster_franchise_ids: tuple[str, ...] = ()
    roster_validity_deadline: datetime | None = None


@dataclass(frozen=True, slots=True)
class DraftTradeRecord:
    proposal_id: str
    proposing_franchise_id: str
    receiving_franchise_id: str
    transferred_player_ids: tuple[str, ...]
    completed_at: datetime


@dataclass(frozen=True, slots=True)
class DraftLeagueState:
    """Immutable league ownership state; a persistence adapter must store updates."""

    league_id: str
    roster_size: int
    rosters: tuple[DraftRoster, ...]
    free_agent_player_ids: tuple[str, ...] = ()
    waiver_player_ids: tuple[str, ...] = ()
    proposals: tuple[TradeProposal, ...] = ()
    completed_trades: tuple[DraftTradeRecord, ...] = ()
    minimum_valid_players: int = 17

    def effective_score_for(self, franchise_id: str, raw_score: int | float) -> int | float:
        """A franchise below the minimum squad size scores zero for the round."""
        return raw_score if len(self.roster_for(franchise_id).player_ids) >= self.minimum_valid_players else 0

    def roster_for(self, franchise_id: str) -> DraftRoster:
        for roster in self.rosters:
            if roster.franchise_id == franchise_id:
                return roster
        raise ValueError("franchise is not part of this league")
