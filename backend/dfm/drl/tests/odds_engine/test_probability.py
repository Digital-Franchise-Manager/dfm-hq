import math
import unittest

from backend.dfm.drl.core.odds_engine.probability import (
    logistic_probability,
    softmax,
)


class ProbabilityTests(unittest.TestCase):
    def test_softmax_is_normalised_for_large_values(self):
        result = softmax((100000.0, 100001.0, 99999.0))
        self.assertAlmostEqual(math.fsum(result), 1.0, places=12)
        self.assertTrue(all(0 < item < 1 for item in result))

    def test_softmax_is_invariant_to_constant_offset(self):
        left = softmax((1.0, 2.0, 3.0))
        right = softmax((1001.0, 1002.0, 1003.0))
        for a, b in zip(left, right):
            self.assertAlmostEqual(a, b, places=12)

    def test_logistic_is_stable_for_extreme_margins(self):
        self.assertGreater(logistic_probability(1e6, 35.0), 0.999999)
        self.assertLess(logistic_probability(-1e6, 35.0), 0.000001)

    def test_invalid_temperature_and_scale_are_rejected(self):
        with self.assertRaises(ValueError):
            softmax((1.0, 2.0), 0)
        with self.assertRaises(ValueError):
            logistic_probability(1.0, -1)


if __name__ == "__main__":
    unittest.main()
