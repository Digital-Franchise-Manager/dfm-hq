"""Tests for the Classic franchise bank and 21-player squad valuation."""
import unittest
from decimal import Decimal

from backend.dfm.drl.classic.core.bank_engine import ClassicBankEngine, BankTransactionType


class ClassicBankEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = ClassicBankEngine()
        self.account = self.engine.create_account("franchise-a")

    def test_account_starts_with_9_4_million(self):
        self.assertEqual(self.account.available_balance, Decimal("9400000.00"))
        self.assertEqual(self.account.squad_value, Decimal("0.00"))

    def test_purchase_deducts_funds_and_updates_squad_value(self):
        account = self.engine.purchase_player(
            self.account, "player-1", "1250000.00", "tx-1", player_value="1300000.00"
        )
        self.assertEqual(account.available_balance, Decimal("8150000.00"))
        self.assertEqual(account.squad_value, Decimal("1300000.00"))
        self.assertEqual(account.total_expenditure, Decimal("1250000.00"))
        self.assertEqual(len(account.transactions), 1)
        self.assertEqual(account.transactions[0].transaction_type, BankTransactionType.PLAYER_PURCHASE)

    def test_sale_credits_funds_and_removes_player_value(self):
        account = self.engine.purchase_player(self.account, "player-1", 100, "tx-1", 120)
        account = self.engine.sell_player(account, "player-1", 150, "tx-2")
        self.assertEqual(account.available_balance, Decimal("9400050.00"))
        self.assertEqual(account.squad_value, Decimal("0.00"))
        self.assertEqual(account.total_income, Decimal("150.00"))
        self.assertEqual(len(account.transactions), 2)

    def test_prevents_overspending(self):
        with self.assertRaisesRegex(ValueError, "insufficient"):
            self.engine.purchase_player(self.account, "player-1", "9400000.01", "tx-1")

    def test_prevents_duplicate_player_registration(self):
        account = self.engine.purchase_player(self.account, "player-1", 100, "tx-1")
        with self.assertRaisesRegex(ValueError, "already registered"):
            self.engine.purchase_player(account, "player-1", 100, "tx-2")

    def test_prevents_duplicate_transaction_ids(self):
        account = self.engine.purchase_player(self.account, "player-1", 100, "tx-1")
        with self.assertRaisesRegex(ValueError, "duplicate transaction"):
            self.engine.sell_player(account, "player-1", 100, "tx-1")

    def test_rejects_sale_of_unowned_player(self):
        with self.assertRaisesRegex(ValueError, "not registered"):
            self.engine.sell_player(self.account, "missing", 100, "tx-1")

    def test_rejects_fractional_cents_and_non_positive_amounts(self):
        with self.assertRaisesRegex(ValueError, "fractions of a cent"):
            self.engine.purchase_player(self.account, "p1", "10.001", "tx-1")
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            self.engine.purchase_player(self.account, "p1", 0, "tx-2")

    def test_rejects_more_than_21_players(self):
        account = self.account
        for index in range(21):
            account = self.engine.purchase_player(account, f"p{index}", 1, f"tx-{index}")
        with self.assertRaisesRegex(ValueError, "cannot exceed 21"):
            self.engine.purchase_player(account, "p21", 1, "tx-21")

    def test_financial_summary_reports_balance_value_and_squad_slots(self):
        account = self.engine.purchase_player(self.account, "p1", 500, "tx-1", 650)
        summary = self.engine.get_financial_summary(account)
        self.assertEqual(summary["available_balance"], Decimal("9399500.00"))
        self.assertEqual(summary["squad_value"], Decimal("650.00"))
        self.assertEqual(summary["players_registered"], 1)
        self.assertEqual(summary["squad_slots_remaining"], 20)


if __name__ == "__main__":
    unittest.main()
