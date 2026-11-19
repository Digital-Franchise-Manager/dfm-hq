"""Classic franchise bank, transfer ledger and 21-player squad valuation."""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal, InvalidOperation

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

    def replace_player(
        self,
        account: BankAccount,
        outgoing_player_id: str,
        incoming_player_id: str,
        incoming_market_value: Decimal | int | float | str,
        trade_id: str,
    ) -> BankAccount:
        """Atomically sell one holding and buy its replacement.

        The outgoing player's authoritative current market value is read from
        the existing holding. That value is credited before the incoming
        player's current market value is deducted. The immutable input account
        is never modified if any validation fails.
        """
        if not isinstance(outgoing_player_id, str) or not outgoing_player_id.strip():
            raise ValueError("outgoing_player_id is required")
        if not isinstance(incoming_player_id, str) or not incoming_player_id.strip():
            raise ValueError("incoming_player_id is required")
        if outgoing_player_id == incoming_player_id:
            raise ValueError("outgoing and incoming players must be different")
        if not isinstance(trade_id, str) or not trade_id.strip():
            raise ValueError("trade_id is required")

        sale_transaction_id = f"{trade_id}:sale"
        purchase_transaction_id = f"{trade_id}:purchase"
        self._check_transaction_id(account, sale_transaction_id)
        self._check_transaction_id(account, purchase_transaction_id)
        incoming_price = _money(incoming_market_value, "incoming_market_value")

        outgoing_holding = next(
            (item for item in account.holdings if item.player_id == outgoing_player_id),
            None,
        )
        if outgoing_holding is None:
            raise ValueError("outgoing player is not registered to this franchise")
        if any(item.player_id == incoming_player_id for item in account.holdings):
            raise ValueError("incoming player is already registered to this franchise")

        sale_value = _money(outgoing_holding.player_value, "outgoing_market_value")
        balance_after_sale = account.available_balance + sale_value
        if incoming_price > balance_after_sale:
            raise ValueError("insufficient available funds")

        balance_after_purchase = balance_after_sale - incoming_price
        sold_at = utc_now()
        sale_transaction = BankTransaction(
            transaction_id=sale_transaction_id,
            transaction_type=BankTransactionType.PLAYER_SALE,
            player_id=outgoing_player_id,
            amount=sale_value,
            player_value=sale_value,
            balance_before=account.available_balance,
            balance_after=balance_after_sale,
            occurred_at=sold_at,
        )
        purchase_transaction = BankTransaction(
            transaction_id=purchase_transaction_id,
            transaction_type=BankTransactionType.PLAYER_PURCHASE,
            player_id=incoming_player_id,
            amount=incoming_price,
            player_value=incoming_price,
            balance_before=balance_after_sale,
            balance_after=balance_after_purchase,
            occurred_at=utc_now(),
        )
        new_holding = PlayerHolding(
            player_id=incoming_player_id,
            acquisition_price=incoming_price,
            player_value=incoming_price,
        )
        updated_holdings = tuple(
            new_holding if item.player_id == outgoing_player_id else item
            for item in account.holdings
        )
        return replace(
            account,
            available_balance=balance_after_purchase,
            holdings=updated_holdings,
            transactions=(
                *account.transactions,
                sale_transaction,
                purchase_transaction,
            ),
        )

    @staticmethod
    def get_financial_summary(account: BankAccount) -> dict[str, Decimal | int]:
        return {
            "available_balance": account.available_balance,
            "squad_value": account.squad_value,
            "team_value": account.team_value,
            "total_expenditure": account.total_expenditure,
            "total_income": account.total_income,
            "players_registered": len(account.holdings),
            "squad_slots_remaining": CLASSIC_SQUAD_LIMIT - len(account.holdings),
        }
