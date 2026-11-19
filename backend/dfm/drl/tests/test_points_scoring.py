"""Tests for the shared DRL custom fantasy scoring rules and input contracts."""
import unittest

from backend.dfm.drl.core.points_scoring import (
    METRE_DIVISORS,
    STAT_CATEGORIES,
    STAT_POINTS,
    CaptaincySelection,
    PlayerAvailability,
    PlayerRoundStats,
    ScoringCategory,
    ScoringStat,
    validate_round_stats,
)


class SharedPointsScoringTests(unittest.TestCase):
    def test_all_scoring_statistics_have_a_category(self):
        self.assertEqual(set(STAT_CATEGORIES), set(ScoringStat))

    def test_all_non_metre_statistics_have_a_point_value(self):
        self.assertEqual(set(STAT_POINTS) | set(METRE_DIVISORS), set(ScoringStat))

    def test_user_defined_stat_categories_are_correct(self):
        self.assertEqual(STAT_CATEGORIES[ScoringStat.TURNOVER], ScoringCategory.ATTACKING)
        self.assertEqual(STAT_CATEGORIES[ScoringStat.FORCED_DROPOUT], ScoringCategory.DEFENSIVE)
        self.assertEqual(STAT_CATEGORIES[ScoringStat.ESCAPE_IN_GOAL], ScoringCategory.ATTACKING)
        self.assertEqual(STAT_CATEGORIES[ScoringStat.ERROR], ScoringCategory.DISCIPLINE)

    def test_scoring_values_match_custom_table(self):
        expected = {
            ScoringStat.TRY: 8, ScoringStat.GOAL: 2, ScoringStat.FIELD_GOAL: 5,
            ScoringStat.TRY_ASSIST: 5, ScoringStat.LINE_BREAK: 4,
            ScoringStat.LINE_BREAK_ASSIST: 2, ScoringStat.TACKLE: 1,
            ScoringStat.TACKLE_BREAK: 2, ScoringStat.MISSED_TACKLE: -2,
            ScoringStat.OFFLOAD_TO_HAND: 4, ScoringStat.OFFLOAD_TO_GROUND: 2,
            ScoringStat.ERROR: -2, ScoringStat.FORTY_TWENTY: 4,
            ScoringStat.TWENTY_FORTY: 4, ScoringStat.PENALTY_CONCEDED: -2,
            ScoringStat.SIX_AGAIN_INFRINGEMENT: -1, ScoringStat.SIN_BIN: -5,
            ScoringStat.SEND_OFF: -10, ScoringStat.TRY_SAVE: 5,
            ScoringStat.KICKS_DEFUSED: 1, ScoringStat.FORCED_DROPOUT: 2,
            ScoringStat.TURNOVER: 4, ScoringStat.ESCAPE_IN_GOAL: 2,
        }
        self.assertEqual(STAT_POINTS, expected)
        self.assertEqual(METRE_DIVISORS, {
            ScoringStat.TOTAL_METRES: 10,
            ScoringStat.KICK_METRES: 30,
        })

    def test_string_stat_keys_are_normalized(self):
        record = PlayerRoundStats("p1", "m1", {"try": 1})
        self.assertEqual(record.statistics, {ScoringStat.TRY: 1})

    def test_unknown_statistic_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown scoring statistic"):
            PlayerRoundStats("p1", "m1", {"made_up_stat": 1})

    def test_negative_or_non_finite_values_are_rejected(self):
        for value in (-1, float("nan"), float("inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    PlayerRoundStats("p1", "m1", {ScoringStat.TRY: value})

    def test_count_statistics_must_be_whole_numbers(self):
        with self.assertRaisesRegex(ValueError, "whole-number"):
            PlayerRoundStats("p1", "m1", {ScoringStat.TRY: 1.5})

    def test_dnp_and_bye_cannot_contain_match_statistics(self):
        with self.assertRaisesRegex(ValueError, "cannot contain"):
            PlayerRoundStats("p1", "m1", {ScoringStat.TRY: 1}, availability=PlayerAvailability.DNP)
        with self.assertRaisesRegex(ValueError, "cannot contain"):
            PlayerRoundStats("p1", "m1", {}, event_ids=("evt-1",), availability=PlayerAvailability.BYE)

    def test_event_ids_must_be_unique(self):
        with self.assertRaisesRegex(ValueError, "unique within"):
            PlayerRoundStats("p1", "m1", {}, event_ids=("evt-1", "evt-1"))

    def test_duplicate_player_rows_and_duplicate_round_events_are_rejected(self):
        captaincy = CaptaincySelection("p1", "p2")
        with self.assertRaisesRegex(ValueError, "one statistics record"):
            validate_round_stats("r1", (
                PlayerRoundStats("p1", "m1", {}),
                PlayerRoundStats("p1", "m2", {}),
                PlayerRoundStats("p2", "m1", {}),
            ), captaincy)
        with self.assertRaisesRegex(ValueError, "duplicate statistical event"):
            validate_round_stats("r1", (
                PlayerRoundStats("p1", "m1", {}, ("event-1",)),
                PlayerRoundStats("p2", "m1", {}, ("event-1",)),
            ), captaincy)

    def test_captain_and_vice_must_be_different(self):
        with self.assertRaisesRegex(ValueError, "different players"):
            CaptaincySelection("p1", "p1")


if __name__ == "__main__":
    unittest.main()
