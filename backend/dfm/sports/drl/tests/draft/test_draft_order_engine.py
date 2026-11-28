"""Tests for commissioner-selectable linear and snake draft order."""
import unittest

from backend.dfm.sports.drl.draft.core.draft_order_engine import DraftOrderEngine, DraftOrderType


class DraftOrderEngineTests(unittest.TestCase):
    def setUp(self):
        self.franchises = ("A", "B", "C", "D")

    def test_linear_order_repeats_each_round(self):
        slots = DraftOrderEngine.generate_order(self.franchises, 3, DraftOrderType.LINEAR)
        self.assertEqual(
            [slot.franchise_id for slot in slots],
            ["A", "B", "C", "D"] * 3,
        )

    def test_snake_order_reverses_each_alternate_round(self):
        slots = DraftOrderEngine.generate_order(self.franchises, 4, "snake")
        self.assertEqual(
            [slot.franchise_id for slot in slots],
            ["A", "B", "C", "D", "D", "C", "B", "A",
             "A", "B", "C", "D", "D", "C", "B", "A"],
        )

    def test_pick_slots_include_overall_and_round_pick_numbers(self):
        slots = DraftOrderEngine.generate_order(self.franchises, 2, "snake")
        self.assertEqual(
            [(s.pick_number, s.round_number, s.pick_in_round, s.franchise_id) for s in slots],
            [(1, 1, 1, "A"), (2, 1, 2, "B"), (3, 1, 3, "C"), (4, 1, 4, "D"),
             (5, 2, 1, "D"), (6, 2, 2, "C"), (7, 2, 3, "B"), (8, 2, 4, "A")],
        )

    def test_rejects_duplicate_franchises(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            DraftOrderEngine.generate_order(("A", "A"), 2, "linear")

    def test_rejects_invalid_type_and_round_count(self):
        with self.assertRaisesRegex(ValueError, "linear.*snake"):
            DraftOrderEngine.generate_order(self.franchises, 2, "auction")
        with self.assertRaisesRegex(ValueError, "positive"):
            DraftOrderEngine.generate_order(self.franchises, 0, "linear")

    def test_rejects_out_of_range_pick_number(self):
        with self.assertRaisesRegex(ValueError, "exceeds"):
            DraftOrderEngine.get_pick(self.franchises, 2, "linear", 9)


if __name__ == "__main__":
    unittest.main()
