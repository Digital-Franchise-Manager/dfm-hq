"""Atomic player replacement tests for the Classic Bank Engine."""
import unittest
from decimal import Decimal

from backend.dfm.drl.classic.core.bank_engine import ClassicBankEngine


class ClassicBankTradeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = ClassicBankEngine()
        self.account = self.engine.create_account("franchise-a")
        self.account = self.engine.purchase_player(
            self.account, "player-out", "450000.00", "buy-out", "600000.00"
        )

    def test_replace_player_credits_current_value_and_deducts_incoming_value(self):
        updated = self.engine.replace_player(
            self.account, "player-out", "player-in", "700000.00", "trade-1"
        )
        self.assertEqual(updated.available_balance, Decimal("8850000.00"))
        self.assertEqual(updated.squad_value, Decimal("700000.00"))
        self.assertEqual([item.player_id for item in updated.holdings], ["player-in"])
        self.assertEqual(updated.transactions[-2].amount, Decimal("600000.00"))
        self.assertEqual(updated.transactions[-1].amount, Decimal("700000.00"))

    def test_failed_replacement_does_not_mutate_original_account(self):
        original = self.account
        with self.assertRaisesRegex(ValueError, "insufficient available funds"):
            self.engine.replace_player(
                self.account, "player-out", "player-in", "10000000.00", "trade-2"
            )
        self.assertEqual(self.account, original)

    def test_replacement_rejects_unknown_outgoing_and_duplicate_incoming(self):
        with self.assertRaisesRegex(ValueError, "not registered"):
            self.engine.replace_player(
                self.account, "missing", "player-in", "100.00", "trade-3"
            )
        with self.assertRaisesRegex(ValueError, "already registered"):
            self.engine.replace_player(
                self.account, "player-out", "player-out", "100.00", "trade-4"
            )


if __name__ == "__main__":
    unittest.main()
