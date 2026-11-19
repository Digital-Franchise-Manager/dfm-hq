"""Tests for Classic trade allowances, lockouts and bank integration."""
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from backend.dfm.drl.classic.core.bank_engine import ClassicBankEngine
from backend.dfm.drl.classic.core.lockout_engine import PlayerLockoutContext
from backend.dfm.drl.classic.core.trade_engine import (
    ClassicTradeEngine,
    ClassicTradeRecord,
    ClassicTradeRequest,
    ClassicTradeState,
)


class ClassicTradeEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = ClassicTradeEngine()
        self.bank = ClassicBankEngine()
        self.account = self.bank.create_account("franchise-a")
        self.account = self.bank.purchase_player(
            self.account, "outgoing-1", "600000.00", "initial-buy", "600000.00"
        )
        self.state = ClassicTradeState("franchise-a", "season-2027")
        self.round_first_kickoff = datetime(2027, 3, 1, 8, tzinfo=timezone.utc)
        self.now = self.round_first_kickoff - timedelta(days=1)

    def request(self, **overrides):
        values = {
            "trade_id": "trade-1",
            "season_id": "season-2027",
            "round_number": 1,
            "outgoing_player": PlayerLockoutContext(
                "outgoing-1", self.round_first_kickoff + timedelta(hours=4)
            ),
            "incoming_player": PlayerLockoutContext(
                "incoming-1", self.round_first_kickoff + timedelta(hours=5)
            ),
            "incoming_market_value": Decimal("700000.00"),
            "round_first_kickoff": self.round_first_kickoff,
            "now": self.now,
        }
        values.update(overrides)
        return ClassicTradeRequest(**values)

    @staticmethod
    def history(round_numbers):
        now = datetime(2027, 1, 1, tzinfo=timezone.utc)
        return tuple(
            ClassicTradeRecord(
                trade_id=f"existing-{index}",
                season_id="season-2027",
                round_number=round_number,
                outgoing_player_id=f"out-{index}",
                incoming_player_id=f"in-{index}",
                outgoing_market_value=Decimal("100.00"),
                incoming_market_value=Decimal("100.00"),
                completed_at=now,
            )
            for index, round_number in enumerate(round_numbers)
        )

    def test_round_trade_limits(self):
        self.assertEqual(self.engine.round_trade_limit(1), 2)
        self.assertEqual(self.engine.round_trade_limit(6), 2)
        self.assertEqual(self.engine.round_trade_limit(7), 3)
        self.assertEqual(self.engine.round_trade_limit(12), 3)
        self.assertEqual(self.engine.round_trade_limit(13), 4)
        self.assertEqual(self.engine.round_trade_limit(27), 4)

    def test_trade_replaces_player_and_updates_bank_atomically(self):
        state, account = self.engine.execute_trade(self.state, self.account, self.request())
        self.assertEqual(state.total_trades_used, 1)
        self.assertEqual(state.rounds_1_to_19_used, 1)
        self.assertEqual(account.available_balance, Decimal("8700000.00"))
        self.assertEqual(account.squad_value, Decimal("700000.00"))
        self.assertEqual([holding.player_id for holding in account.holdings], ["incoming-1"])
        self.assertEqual(len(account.transactions), 3)
        self.assertEqual(account.transactions[-2].transaction_type.value, "player_sale")
        self.assertEqual(account.transactions[-1].transaction_type.value, "player_purchase")

    def test_trade_uses_current_outgoing_market_value_not_original_cost(self):
        account = self.bank.purchase_player(
            self.bank.create_account("franchise-a"),
            "outgoing-1",
            "400000.00",
            "buy-old",
            "600000.00",
        )
        _, updated = self.engine.execute_trade(self.state, account, self.request())
        self.assertEqual(updated.available_balance, Decimal("8900000.00"))

    def test_round_cap_is_enforced(self):
        state = ClassicTradeState(
            "franchise-a", "season-2027", self.history([1, 1])
        )
        with self.assertRaisesRegex(ValueError, "round 1 trade limit"):
            self.engine.execute_trade(state, self.account, self.request())

    def test_rounds_1_to_19_pool_is_36(self):
        state = ClassicTradeState(
            "franchise-a", "season-2027", self.history([round_no for round_no in range(1, 19) for _ in range(2)])
        )
        self.assertEqual(state.rounds_1_to_19_used, 36)
        with self.assertRaisesRegex(ValueError, "pool of 36"):
            self.engine.execute_trade(state, self.account, self.request())

    def test_round_20_plus_pool_is_eight(self):
        state = ClassicTradeState(
            "franchise-a", "season-2027", self.history([20] * 4 + [21] * 4)
        )
        with self.assertRaisesRegex(ValueError, "additional trade pool of 8"):
            self.engine.execute_trade(
                state, self.account, self.request(round_number=22)
            )

    def test_season_cap_is_enforced(self):
        state = ClassicTradeState(
            "franchise-a",
            "season-2027",
            self.history([round_no for round_no in range(1, 19) for _ in range(2)] + [20] * 8),
        )
        self.assertEqual(state.total_trades_used, 44)
        with self.assertRaisesRegex(ValueError, "season trade limit of 44"):
            self.engine.execute_trade(
                state, self.account, self.request(round_number=22)
            )

    def test_insufficient_bank_funds_reject_trade_without_mutation(self):
        request = self.request(incoming_market_value=Decimal("10000000.00"))
        original_account = self.account
        original_state = self.state
        with self.assertRaisesRegex(ValueError, "insufficient available funds"):
            self.engine.execute_trade(self.state, self.account, request)
        self.assertEqual(self.account, original_account)
        self.assertEqual(self.state, original_state)

    def test_duplicate_trade_id_is_rejected(self):
        state, account = self.engine.execute_trade(self.state, self.account, self.request())
        with self.assertRaisesRegex(ValueError, "duplicate trade_id"):
            self.engine.execute_trade(
                state,
                account,
                self.request(
                    outgoing_player=PlayerLockoutContext(
                        "incoming-1", self.round_first_kickoff + timedelta(hours=4)
                    ),
                    incoming_player=PlayerLockoutContext(
                        "incoming-2", self.round_first_kickoff + timedelta(hours=5)
                    ),
                ),
            )

    def test_locked_outgoing_player_is_rejected(self):
        request = self.request(
            outgoing_player=PlayerLockoutContext(
                "outgoing-1", self.round_first_kickoff + timedelta(minutes=30)
            ),
            now=self.round_first_kickoff,
        )
        with self.assertRaisesRegex(ValueError, "is locked"):
            self.engine.execute_trade(self.state, self.account, request)

    def test_locked_incoming_player_is_rejected(self):
        request = self.request(
            incoming_player=PlayerLockoutContext(
                "incoming-1", self.round_first_kickoff + timedelta(minutes=30)
            ),
            now=self.round_first_kickoff,
        )
        with self.assertRaisesRegex(ValueError, "is locked"):
            self.engine.execute_trade(self.state, self.account, request)

    def test_trade_requires_existing_outgoing_player(self):
        request = self.request(
            outgoing_player=PlayerLockoutContext(
                "missing-player", self.round_first_kickoff + timedelta(hours=4)
            )
        )
        with self.assertRaisesRegex(ValueError, "not registered"):
            self.engine.execute_trade(self.state, self.account, request)

    def test_trade_rejects_mismatched_franchise(self):
        state = ClassicTradeState("another-franchise", "season-2027")
        with self.assertRaisesRegex(ValueError, "franchise IDs"):
            self.engine.execute_trade(state, self.account, self.request())

    def test_invalid_round_number_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "positive integer"):
            self.engine.round_trade_limit(0)


if __name__ == "__main__":
    unittest.main()
