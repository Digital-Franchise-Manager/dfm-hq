"""Immutable financial records for a DRL Classic franchise."""
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
