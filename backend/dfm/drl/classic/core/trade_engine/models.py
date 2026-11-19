"""Immutable contracts for Classic season trades and trade allowance tracking."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from backend.dfm.drl.classic.core.lockout_engine.models import PlayerLockoutContext


@dataclass(frozen=True, slots=True)
class ClassicTradeRecord:
    trade_id: str
    season_id: str
    round_number: int
    outgoing_player_id: str
    incoming_player_id: str
    outgoing_market_value: Decimal
    incoming_market_value: Decimal
    completed_at: datetime


@dataclass(frozen=True, slots=True)
class ClassicTradeState:
    """Season trade history for one franchise; persistence is owned externally."""

    franchise_id: str
    season_id: str
    trades: tuple[ClassicTradeRecord, ...] = ()

    @property
    def total_trades_used(self) -> int:
        return len(self.trades)

    @property
    def rounds_1_to_19_used(self) -> int:
        return sum(1 for trade in self.trades if trade.round_number <= 19)

    @property
    def round_20_plus_used(self) -> int:
        return sum(1 for trade in self.trades if trade.round_number >= 20)

    def trades_in_round(self, round_number: int) -> int:
        return sum(1 for trade in self.trades if trade.round_number == round_number)


@dataclass(frozen=True, slots=True)
class ClassicTradeRequest:
    """One outgoing-for-incoming player replacement in a specified round."""

    trade_id: str
    season_id: str
    round_number: int
    outgoing_player: PlayerLockoutContext
    incoming_player: PlayerLockoutContext
    incoming_market_value: Decimal
    round_first_kickoff: datetime
    now: datetime | None = None
