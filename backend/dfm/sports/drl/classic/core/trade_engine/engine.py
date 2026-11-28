"""Classic-only trade execution, season allowances and round limits."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from backend.dfm.sports.drl.classic.core.bank_engine import BankAccount, ClassicBankEngine
from backend.dfm.sports.drl.classic.core.bank_engine.models import utc_now
from backend.dfm.sports.drl.classic.core.lockout_engine import ClassicLockoutEngine
from .models import ClassicTradeRecord, ClassicTradeRequest, ClassicTradeState


class ClassicTradeEngine:
    """Coordinates Classic trade rules and delegates all money to Bank Engine.

    One outgoing-for-incoming player replacement consumes one trade. The
    Bank Engine remains authoritative for the outgoing player's current
    market value, the incoming price, the franchise balance and the ledger.
    """

    SEASON_TRADE_LIMIT = 44
    ROUNDS_1_TO_19_LIMIT = 36
    ROUND_20_PLUS_LIMIT = 8

    def __init__(
        self,
        bank_engine: ClassicBankEngine | None = None,
        lockout_engine: ClassicLockoutEngine | None = None,
    ) -> None:
        self.bank_engine = bank_engine or ClassicBankEngine()
        self.lockout_engine = lockout_engine or ClassicLockoutEngine()

    @staticmethod
    def round_trade_limit(round_number: int) -> int:
        if isinstance(round_number, bool) or not isinstance(round_number, int) or round_number < 1:
            raise ValueError("round_number must be a positive integer")
        if round_number <= 6:
            return 2
        if round_number <= 12:
            return 3
        return 4

    def _validate_trade_allowance(
        self, state: ClassicTradeState, round_number: int
    ) -> None:
        if state.total_trades_used >= self.SEASON_TRADE_LIMIT:
            raise ValueError("season trade limit of 44 has been reached")
        if state.trades_in_round(round_number) >= self.round_trade_limit(round_number):
            raise ValueError(
                f"round {round_number} trade limit of "
                f"{self.round_trade_limit(round_number)} has been reached"
            )
        if round_number <= 19 and state.rounds_1_to_19_used >= self.ROUNDS_1_TO_19_LIMIT:
            raise ValueError("Rounds 1-19 trade pool of 36 has been exhausted")
        if round_number >= 20 and state.round_20_plus_used >= self.ROUND_20_PLUS_LIMIT:
            raise ValueError("Round 20+ additional trade pool of 8 has been exhausted")

    @staticmethod
    def _validate_request(
        state: ClassicTradeState,
        account: BankAccount,
        request: ClassicTradeRequest,
    ) -> None:
        if not isinstance(request.trade_id, str) or not request.trade_id.strip():
            raise ValueError("trade_id is required")
        if any(trade.trade_id == request.trade_id for trade in state.trades):
            raise ValueError("duplicate trade_id")
        if not isinstance(request.season_id, str) or request.season_id != state.season_id:
            raise ValueError("trade season does not match the franchise trade state")
        if state.franchise_id != account.franchise_id:
            raise ValueError("trade state and bank account franchise IDs do not match")
        if request.outgoing_player.player_id == request.incoming_player.player_id:
            raise ValueError("outgoing and incoming players must be different")
        if isinstance(request.round_number, bool) or not isinstance(request.round_number, int) or request.round_number < 1:
            raise ValueError("round_number must be a positive integer")
        if isinstance(request.incoming_market_value, bool):
            raise ValueError("incoming_market_value must be a positive monetary amount")
        try:
            value = Decimal(str(request.incoming_market_value))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("incoming_market_value must be a valid monetary amount") from exc
        if not value.is_finite() or value <= 0 or value != value.quantize(Decimal("0.01")):
            raise ValueError("incoming_market_value must be positive and accurate to cents")

    def execute_trade(
        self,
        state: ClassicTradeState,
        account: BankAccount,
        request: ClassicTradeRequest,
    ) -> tuple[ClassicTradeState, BankAccount]:
        """Execute one trade atomically and return new immutable state objects.

        If any validation or bank operation fails, neither supplied input
        object is mutated and no updated state is returned.
        """
        self._validate_request(state, account, request)
        self._validate_trade_allowance(state, request.round_number)
        self.lockout_engine.assert_trade_allowed(
            outgoing_player=request.outgoing_player,
            incoming_player=request.incoming_player,
            round_first_kickoff=request.round_first_kickoff,
            now=request.now,
        )

        outgoing_holding = next(
            (
                holding for holding in account.holdings
                if holding.player_id == request.outgoing_player.player_id
            ),
            None,
        )
        if outgoing_holding is None:
            raise ValueError("outgoing player is not registered to this franchise")

        updated_account = self.bank_engine.replace_player(
            account=account,
            outgoing_player_id=request.outgoing_player.player_id,
            incoming_player_id=request.incoming_player.player_id,
            incoming_market_value=request.incoming_market_value,
            trade_id=request.trade_id,
        )
        record = ClassicTradeRecord(
            trade_id=request.trade_id,
            season_id=request.season_id,
            round_number=request.round_number,
            outgoing_player_id=request.outgoing_player.player_id,
            incoming_player_id=request.incoming_player.player_id,
            outgoing_market_value=outgoing_holding.player_value,
            incoming_market_value=Decimal(str(request.incoming_market_value)),
            completed_at=request.now.astimezone(timezone.utc) if request.now else utc_now(),
        )
        updated_state = ClassicTradeState(
            franchise_id=state.franchise_id,
            season_id=state.season_id,
            trades=(*state.trades, record),
        )
        return updated_state, updated_account
