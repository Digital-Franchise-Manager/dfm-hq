"""Regression tests for independent DRL Draft fantasy points scoring."""
import unittest

from backend.dfm.sports.drl.core.points_scoring import (
    CaptaincySelection,
    PlayerAvailability,
    PlayerRoundStats,
    ScoringStat as S,
)
from backend.dfm.sports.drl.draft.core.points_engine import DraftPointsEngine


class DraftPointsEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = DraftPointsEngine()

    def test_calculates_stat_points_and_metres(self):
        result = self.engine.score_round("r1", (
            PlayerRoundStats("p1", "m1", {
                S.TRY: 2, S.MISSED_TACKLE: 1, S.TOTAL_METRES: 29,
                S.KICK_METRES: 89, S.TURNOVER: 1, S.FORCED_DROPOUT: 1,
                S.ESCAPE_IN_GOAL: 1,
            }, event_ids=("evt-a", "evt-b")),
            PlayerRoundStats("p2", "m1", {}),
        ), CaptaincySelection("p2", "p1"))
        p1 = result.player_scores[0]
        self.assertEqual(p1.base_points, 26)
        self.assertEqual(p1.total_points, 26)

    def test_captain_doubles_and_vice_is_standby(self):
        result = self.engine.score_round("r1", (
            PlayerRoundStats("captain", "m1", {S.TRY: 1}),
            PlayerRoundStats("vice", "m1", {S.TRY_ASSIST: 1}),
        ), CaptaincySelection("captain", "vice"))
        self.assertEqual([player.total_points for player in result.player_scores], [16, 5])

    def test_vice_doubles_only_when_captain_is_unavailable(self):
        result = self.engine.score_round("r1", (
            PlayerRoundStats("captain", "m1", {}, availability=PlayerAvailability.BYE),
            PlayerRoundStats("vice", "m2", {S.TRY_ASSIST: 1}),
        ), CaptaincySelection("captain", "vice"))
        self.assertEqual(result.player_scores[1].total_points, 10)

    def test_dnp_player_receives_zero_points(self):
        result = self.engine.score_round("r1", (
            PlayerRoundStats("captain", "m1", {}, availability=PlayerAvailability.DNP),
            PlayerRoundStats("vice", "m1", {}),
        ), CaptaincySelection("captain", "vice"))
        self.assertEqual(result.player_scores[0].total_points, 0)

    def test_duplicate_source_event_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate statistical event"):
            self.engine.score_round("r1", (
                PlayerRoundStats("captain", "m1", {}, ("same-event",)),
                PlayerRoundStats("vice", "m1", {}, ("same-event",)),
            ), CaptaincySelection("captain", "vice"))


if __name__ == "__main__":
    unittest.main()
