"""Append-only market history service with an injected persistence boundary."""

from __future__ import annotations

from typing import Protocol

from ..models import MarketPriceMovement


class MarketHistoryRepository(Protocol):
    """Persistence adapter contract; implementations must be append-only."""

    def append_once(self, event: MarketPriceMovement) -> bool:
        """Persist once by idempotency key; return False for an existing event."""
        ...

    def list_for_market(self, market_type: str, market_id: str) -> tuple[MarketPriceMovement, ...]:
        """Return audit events in revision order."""
        ...


class MarketHistoryService:
    """Coordinates immutable price movement records without owning a database."""

    def __init__(self, repository: MarketHistoryRepository) -> None:
        self._repository = repository

    def record(self, events: tuple[MarketPriceMovement, ...]) -> int:
        """Append events once and return the number newly stored."""
        stored = 0
        for event in events:
            if self._repository.append_once(event):
                stored += 1
        return stored

    def get_market_history(
        self, market_type: str, market_id: str
    ) -> tuple[MarketPriceMovement, ...]:
        if not market_type.strip() or not market_id.strip():
            raise ValueError("market type and market id must not be blank")
        return self._repository.list_for_market(market_type, market_id)
