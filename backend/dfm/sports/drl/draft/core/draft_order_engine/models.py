"""Immutable contracts for commissioner-configured draft order."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DraftOrderType(str, Enum):
    """Supported draft order formats."""

    LINEAR = "linear"
    SNAKE = "snake"


@dataclass(frozen=True, slots=True)
class DraftPickSlot:
    """The franchise entitled to make one overall selection."""

    pick_number: int
    round_number: int
    pick_in_round: int
    franchise_id: str
