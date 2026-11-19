"""Classic franchise bank, transfer ledger and 21-player squad valuation."""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal, InvalidOperation
from math import isfinite

from .models import (
    BankAccount,
    BankTransaction,
    BankTransactionType,
    CLASSIC_SQUAD_LIMIT,
    PlayerHolding,
    STARTING_BANK_BALANCE,
    utc_now,
)


def _money(value: Decimal | int | float | str, field: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a positive monetary amount")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be a valid monetary amount") from exc
    if not amount.is_finite() or amount <= 0:
        raise ValueError(f"{field} must be a finite amount greater than zero")
    if amount != amount.quantize(Decimal("0.01")):
        raise ValueError(f"{field} cannot contain fractions of a cent")
    return amount


class ClassicBankEngine:
    """Immutable account transitions; callers persist returned account state."""

    @staticmethod
    def create_account(franchise_id: str) -> BankAccount:
        if not isinstance(franchise_id, str) or not franchise_id.strip():
            raise ValueError("franchise_id is required")
        return BankAccount(
            franchise_id=franchise_id,
            opening_balance=STARTING_BANK_BALANCE,
            available_balance=STARTING_BANK_BALANCE,
        )

    @staticmethod
    def _check_transaction_id(account: BankAccount, transaction_id: str) -> None:
        if not isinstance(transaction_id, str) or not transaction_id.strip():
            raise ValueError("transaction_id is required")
        if any(tx.transaction_id == transaction_id for tx in account.transactions):
            raise ValueError("duplicate transaction_id")

    def purchase_player(
        self,
        account: BankAccount,
        player_id: str,
        purchase_price: Decimal | int | float | str,
        transaction_id: str,
        player_value: Decimal | int | float | str | None = None,
    ) -> BankAccount:
        if not isinstance(player_id, str) or not player_id.strip():
            raise ValueError("player_id is required")
        self._check_transaction_id(account, transaction_id)
        price = _money(purchase_price, "purchase_price")
        value = _money(player_value if player_value is not None else purchase_price, "player_value")
        if any(holding.player_id == player_id for holding in account.holdings):
            raise ValueError("player is already registered to this franchise")
        if len(account.holdings) >= CLASSIC_SQUAD_LIMIT:
            raise ValueError("Classic squad cannot exceed 21 players")
        if price > account.available_balance:
            raise ValueError("insufficient available funds")

        balance_after = account.available_balance - price
        transaction = BankTransaction(
            transaction_id=transaction_id,
            transaction_type=BankTransactionType.PLAYER_PURCHASE,
            player_id=player_id,
            amount=price,
            player_value=value,
            balance_before=account.available_balance,
            balance_after=balance_after,
            occurred_at=utc_now(),
        )
        holding = PlayerHolding(player_id, price, value)
        return replace(
            account,
            available_balance=balance_after,
            holdings=(*account.holdings, holding),
            transactions=(*account.transactions, transaction),
        )

    def sell_player(
        self,
        account: BankAccount,
        player_id: str,
        sale_price: Decimal | int | float | str,
        transaction_id: str,
    ) -> BankAccount:
        if not isinstance(player_id, str) or not player_id.strip():
            raise ValueError("player_id is required")
        self._check_transaction_id(account, transaction_id)
        price = _money(sale_price, "sale_price")
        holding = next((item for item in account.holdings if item.player_id == player_id), None)
        if holding is None:
            raise ValueError("player is not registered to this franchise")

        balance_after = account.available_balance + price
        transaction = BankTransaction(
            transaction_id=transaction_id,
            transaction_type=BankTransactionType.PLAYER_SALE,
            player_id=player_id,
            amount=price,
            player_value=holding.player_value,
            balance_before=account.available_balance,
            balance_after=balance_after,
            occurred_at=utc_now(),
        )
        holdings = tuple(item for item in account.holdings if item.player_id != player_id)
        return replace(
            account,
            available_balance=balance_after,
            holdings=holdings,
            transactions=(*account.transactions, transaction),
        )

    @staticmethod
    def get_financial_summary(account: BankAccount) -> dict[str, Decimal | int]:
        return {
            "available_balance": account.available_balance,
            "squad_value": account.squad_value,
            "total_expenditure": account.total_expenditure,
            "total_income": account.total_income,
            "players_registered": len(account.holdings),
            "squad_slots_remaining": CLASSIC_SQUAD_LIMIT - len(account.holdings),
        }
