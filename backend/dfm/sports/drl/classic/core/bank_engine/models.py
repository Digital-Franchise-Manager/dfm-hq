"""Immutable financial and player-pricing records for DRL Classic."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

STARTING_BANK_BALANCE = Decimal("9400000.00")
CLASSIC_SQUAD_LIMIT = 21


class BankTransactionType(str, Enum):
    PLAYER_PURCHASE = "player_purchase"
    PLAYER_SALE = "player_sale"


@dataclass(frozen=True, slots=True)
class PlayerHolding:
    player_id: str
    acquisition_price: Decimal
    player_value: Decimal


@dataclass(frozen=True, slots=True)
class PlayerPricingConfig:
    """Public, configurable DRL pricing assumptions; not an NRL formula."""

    value_per_point: Decimal = Decimal("5000")
    recent_score_weights: tuple[Decimal, ...] = (
        Decimal("0.50"), Decimal("0.30"), Decimal("0.20")
    )
    previous_season_weight: Decimal = Decimal("0.25")
    max_change_fraction: Decimal = Decimal("0.15")
    price_floor: Decimal = Decimal("100000")
    price_ceiling: Decimal = Decimal("1000000")
    price_increment: Decimal = Decimal("100")

    def __post_init__(self) -> None:
        if self.value_per_point <= 0:
            raise ValueError("value_per_point must be greater than zero")
        if not self.recent_score_weights or any(weight < 0 for weight in self.recent_score_weights):
            raise ValueError("recent_score_weights must contain non-negative weights")
        if sum(self.recent_score_weights, Decimal("0")) <= 0:
            raise ValueError("recent_score_weights must have a positive total")
        if not Decimal("0") <= self.previous_season_weight <= Decimal("1"):
            raise ValueError("previous_season_weight must be between zero and one")
        if not Decimal("0") <= self.max_change_fraction <= Decimal("1"):
            raise ValueError("max_change_fraction must be between zero and one")
        if self.price_floor <= 0 or self.price_ceiling < self.price_floor:
            raise ValueError("price bounds are invalid")
        if self.price_increment <= 0:
            raise ValueError("price_increment must be greater than zero")


@dataclass(frozen=True, slots=True)
class PlayerPriceAssessment:
    player_id: str
    opening_price: Decimal
    current_price: Decimal
    break_even_score: Decimal
    weighted_score: Decimal
    price_change: Decimal
    next_price: Decimal
    availability: str
    estimate_type: str = "DRL model estimate"


@dataclass(frozen=True, slots=True)
class BankTransaction:
    transaction_id: str
    transaction_type: BankTransactionType
    player_id: str
    amount: Decimal
    player_value: Decimal
    balance_before: Decimal
    balance_after: Decimal
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class BankAccount:
    franchise_id: str
    opening_balance: Decimal = STARTING_BANK_BALANCE
    available_balance: Decimal = STARTING_BANK_BALANCE
    holdings: tuple[PlayerHolding, ...] = ()
    transactions: tuple[BankTransaction, ...] = ()

    @property
    def squad_value(self) -> Decimal:
        return sum((holding.player_value for holding in self.holdings), Decimal("0.00"))

    @property
    def team_value(self) -> Decimal:
        """Current franchise value: available bank cash plus squad market value."""
        return self.available_balance + self.squad_value

    @property
    def total_expenditure(self) -> Decimal:
        return sum(
            (tx.amount for tx in self.transactions
             if tx.transaction_type is BankTransactionType.PLAYER_PURCHASE),
            Decimal("0.00"),
        )

    @property
    def total_income(self) -> Decimal:
        return sum(
            (tx.amount for tx in self.transactions
             if tx.transaction_type is BankTransactionType.PLAYER_SALE),
            Decimal("0.00"),
        )


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
