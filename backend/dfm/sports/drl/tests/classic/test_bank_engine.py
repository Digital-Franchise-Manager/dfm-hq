"""Tests for the Classic bank and transparent player-pricing model."""
import unittest
from decimal import Decimal

from backend.dfm.sports.drl.classic.core.bank_engine import (
    ClassicBankEngine, BankTransactionType, PlayerPricingConfig
)
from backend.dfm.sports.drl.core.points_scoring import PlayerAvailability


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

    def test_recent_scores_weight_most_recent_performance(self):
        quote = self.engine.calculate_player_price(
            "p1", [100, 80, 60], current_price=Decimal("400000")
        )
        self.assertEqual(quote.weighted_score, Decimal("86.00"))
        self.assertEqual(quote.break_even_score, Decimal("80.00"))
        self.assertEqual(quote.next_price, Decimal("430000.00"))
        self.assertEqual(quote.price_change, Decimal("30000.00"))

    def test_previous_season_average_is_blended_with_recent_form(self):
        quote = self.engine.calculate_player_price(
            "p1", [100, 80, 60], current_price=400000,
            previous_season_average=40
        )
        self.assertEqual(quote.weighted_score, Decimal("74.50"))

    def test_opening_price_is_used_when_current_price_is_not_yet_set(self):
        quote = self.engine.calculate_player_price(
            "rookie", [50], opening_price=250000
        )
        self.assertEqual(quote.current_price, Decimal("250000.00"))
        self.assertEqual(quote.opening_price, Decimal("250000.00"))

    def test_previous_season_average_can_seed_a_new_price(self):
        quote = self.engine.calculate_player_price(
            "returning-player", [], previous_season_average=60
        )
        self.assertEqual(quote.current_price, Decimal("300000"))
        self.assertEqual(quote.weighted_score, Decimal("60.00"))

    def test_dnp_and_bye_do_not_change_player_price(self):
        for availability in (PlayerAvailability.DNP, PlayerAvailability.BYE):
            quote = self.engine.calculate_player_price(
                "p1", [100, 80, 60], current_price=400000,
                availability=availability
            )
            self.assertEqual(quote.next_price, Decimal("400000.00"))
            self.assertEqual(quote.price_change, Decimal("0.00"))

    def test_price_movement_is_capped_and_rounded_to_configured_increment(self):
        quote = self.engine.calculate_player_price(
            "p1", [300], current_price=400000
        )
        self.assertEqual(quote.next_price, Decimal("460000.00"))

    def test_pricing_rejects_missing_performance_basis(self):
        with self.assertRaisesRegex(ValueError, "recent scores or previous-season"):
            self.engine.calculate_player_price("p1", [], current_price=300000)

    def test_pricing_rejects_invalid_scores_and_prices(self):
        for score in (-1, float("nan"), float("inf"), True):
            with self.subTest(score=score):
                with self.assertRaises(ValueError):
                    self.engine.calculate_player_price("p1", [score], current_price=300000)
        with self.assertRaises(ValueError):
            self.engine.calculate_player_price("p1", [50], current_price=0)

    def test_custom_pricing_parameters_are_applied(self):
        config = PlayerPricingConfig(
            value_per_point=Decimal("4000"),
            recent_score_weights=(Decimal("1"),),
            max_change_fraction=Decimal("0.10"),
            price_floor=Decimal("100000"),
            price_ceiling=Decimal("900000"),
            price_increment=Decimal("100"),
        )
        quote = self.engine.calculate_player_price(
            "p1", [100], current_price=400000, config=config
        )
        self.assertEqual(quote.break_even_score, Decimal("100.00"))
        self.assertEqual(quote.next_price, Decimal("400000.00"))

    def test_market_revaluation_updates_squad_value_without_cash_ledger_entry(self):
        account = self.engine.purchase_player(self.account, "p1", 300000, "tx-1")
        revalued = self.engine.update_player_market_value(account, "p1", 350000)
        self.assertEqual(revalued.squad_value, Decimal("350000.00"))
        self.assertEqual(revalued.available_balance, account.available_balance)
        self.assertEqual(revalued.transactions, account.transactions)
        self.assertEqual(account.squad_value, Decimal("300000.00"))

    def test_market_revaluation_rejects_unowned_player(self):
        with self.assertRaisesRegex(ValueError, "not registered"):
            self.engine.update_player_market_value(self.account, "missing", 100000)


if __name__ == "__main__":
    unittest.main()
