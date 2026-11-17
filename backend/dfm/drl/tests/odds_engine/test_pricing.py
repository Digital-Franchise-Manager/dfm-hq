import unittest

from backend.dfm.drl.core.odds_engine.pricing import (
    build_outcomes,
    probability_to_decimal_price,
)


class PricingTests(unittest.TestCase):
    def test_decimal_price_is_fair_inverse_probability(self):
        self.assertEqual(probability_to_decimal_price(0.5), 2.0)
        self.assertEqual(probability_to_decimal_price(0.25), 4.0)

    def test_invalid_probability_is_rejected(self):
        for value in (0.0, 1.0, -0.1, 1.1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                probability_to_decimal_price(value)

    def test_duplicate_selections_are_rejected(self):
        with self.assertRaises(ValueError):
            build_outcomes((("a", "A"), ("a", "A2")), (0.5, 0.5))


if __name__ == "__main__":
    unittest.main()
