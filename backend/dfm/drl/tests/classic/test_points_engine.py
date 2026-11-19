"""Regression tests for independent DRL Classic fantasy points scoring."""
import unittest

from backend.dfm.drl.classic.core.points_engine import ClassicPointsEngine
from backend.dfm.drl.core.points_scoring import (
    CaptaincySelection,
    PlayerAvailability,
    PlayerRoundStats,
    ScoringStat as S,
)


class ClassicPointsEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = ClassicPointsEngine()

    def test_calculates_all_stat_values_and_metre_rounding(self):
        stats = PlayerRoundStats("p1", "m1", {
            S.TRY: 1, S.GOAL: 2, S.FIELD_GOAL: 1, S.TRY_ASSIST: 1,
            S.LINE_BREAK: 1, S.LINE_BREAK_ASSIST: 1, S.TACKLE: 10,
            S.TACKLE_BREAK: 2, S.MISSED_TACKLE: 1, S.OFFLOAD_TO_HAND: 1,
            S.OFFLOAD_TO_GROUND: 1, S.ERROR: 1, S.FORTY_TWENTY: 1,
            S.TWENTY_FORTY: 1, S.TOTAL_METRES: 19, S.KICK_METRES: 59,
            S.PENALTY_CONCEDED: 1, S.SIX_AGAIN_INFRINGEMENT: 1,
            S.SIN_BIN: 1, S.SEND_OFF: 1, S.TRY_SAVE: 1,
            S.KICKS_DEFUSED: 1, S.FORCED_DROPOUT: 1, S.TURNOVER: 1,
            S.ESCAPE_IN_GOAL: 1,
        }, event_ids=("all-stats-event",))
        result = self.engine.score_round("r1", (
            stats,
            PlayerRoundStats("p2", "m1", {}),
        ), CaptaincySelection("p2", "p1"))
        p1 = next(player for player in result.player_scores if player.player_id == "p1")
        self.assertEqual(p1.base_points, 39)
        self.assertEqual(p1.total_points, 39)
        self.assertEqual(result.total_points, 39)

    def test_captain_scores_double(self):
        result = self.engine.score_round("r1", (
            PlayerRoundStats("captain", "m1", {S.TRY: 1}),
            PlayerRoundStats("vice", "m1", {S.TRY: 1}),
        ), CaptaincySelection("captain", "vice"))
        self.assertEqual([p.total_points for p in result.player_scores], [16, 8])

    def test_vice_only_doubles_when_captain_is_dnp(self):
        result = self.engine.score_round("r1", (
            PlayerRoundStats("captain", "m1", {}, availability=PlayerAvailability.DNP),
            PlayerRoundStats("vice", "m2", {S.TRY: 1}),
        ), CaptaincySelection("captain", "vice"))
        self.assertEqual([p.multiplier for p in result.player_scores], [2, 2])
        self.assertEqual([p.total_points for p in result.player_scores], [0, 16])

    def test_vice_only_doubles_when_captain_has_bye(self):
        result = self.engine.score_round("r1", (
            PlayerRoundStats("captain", "m1", {}, availability=PlayerAvailability.BYE),
            PlayerRoundStats("vice", "m2", {S.TRY: 1}),
        ), CaptaincySelection("captain", "vice"))
        self.assertEqual(result.player_scores[1].total_points, 16)

    def test_vice_does_not_double_if_captain_played_but_scored_zero(self):
        result = self.engine.score_round("r1", (
            PlayerRoundStats("captain", "m1", {}),
            PlayerRoundStats("vice", "m1", {S.TRY: 1}),
        ), CaptaincySelection("captain", "vice"))
        self.assertEqual(result.player_scores[1].multiplier, 1)
        self.assertEqual(result.player_scores[1].total_points, 8)

    def test_negative_points_are_also_doubled_for_captain(self):
        result = self.engine.score_round("r1", (
            PlayerRoundStats("captain", "m1", {S.ERROR: 1}),
            PlayerRoundStats("vice", "m1", {}),
        ), CaptaincySelection("captain", "vice"))
        self.assertEqual(result.player_scores[0].total_points, -4)

    def test_deterministic_recalculation_uses_replacement_stats_snapshot(self):
        original = (PlayerRoundStats("captain", "m1", {S.TRY: 1}),
                    PlayerRoundStats("vice", "m1", {}))
        corrected = (PlayerRoundStats("captain", "m1", {S.TRY: 2}),
                     PlayerRoundStats("vice", "m1", {}))
        captaincy = CaptaincySelection("captain", "vice")
        self.assertEqual(self.engine.score_round("r1", original, captaincy).total_points, 16)
        self.assertEqual(self.engine.score_round("r1", corrected, captaincy).total_points, 32)

    def test_requires_captain_and_vice_records(self):
        with self.assertRaisesRegex(ValueError, "captain must"):
            self.engine.score_round("r1", (PlayerRoundStats("vice", "m1", {}),),
                                    CaptaincySelection("captain", "vice"))


if __name__ == "__main__":
    unittest.main()
