import unittest
from datetime import datetime, timedelta, timezone

from backend.dfm.drl.draft.core.lockout_engine import (
    DraftLockoutEngine,
    LockoutReason,
    PlayerLockedError,
    PlayerLockoutContext,
)


class DraftLockoutEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = DraftLockoutEngine()
        self.first_kickoff = datetime(2026, 11, 26, 20, 0, tzinfo=timezone(timedelta(hours=11)))
        self.sunday_kickoff = datetime(2026, 11, 29, 16, 0, tzinfo=timezone(timedelta(hours=11)))

    def test_captain_locks_for_round_from_first_kickoff(self):
        player = PlayerLockoutContext("captain", self.sunday_kickoff, is_captain=True)
        decision = self.engine.evaluate_player(
            player=player,
            round_first_kickoff=self.first_kickoff,
            now=self.first_kickoff,
        )
        self.assertTrue(decision.is_locked)
        self.assertEqual(decision.reason, LockoutReason.CAPTAIN_ROUND)

    def test_vice_captain_locks_for_round_from_first_kickoff(self):
        player = PlayerLockoutContext("vice", self.sunday_kickoff, is_vice_captain=True)
        decision = self.engine.evaluate_player(
            player=player,
            round_first_kickoff=self.first_kickoff,
            now=self.first_kickoff,
        )
        self.assertTrue(decision.is_locked)
        self.assertEqual(decision.reason, LockoutReason.VICE_CAPTAIN_ROUND)

    def test_emergency_bench_player_locks_for_round_from_first_kickoff(self):
        player = PlayerLockoutContext("emergency", self.sunday_kickoff, is_emergency=True)
        decision = self.engine.evaluate_player(
            player=player,
            round_first_kickoff=self.first_kickoff,
            now=self.first_kickoff,
        )
        self.assertTrue(decision.is_locked)
        self.assertEqual(decision.lockout_at, self.first_kickoff)
        self.assertEqual(decision.reason, LockoutReason.EMERGENCY_ROUND)

    def test_ordinary_player_uses_individual_one_hour_deadline(self):
        player = PlayerLockoutContext("ordinary", self.sunday_kickoff)
        cutoff = self.sunday_kickoff - timedelta(hours=1)
        before = self.engine.evaluate_player(
            player=player,
            round_first_kickoff=self.first_kickoff,
            now=cutoff - timedelta(seconds=1),
        )
        at_cutoff = self.engine.evaluate_player(
            player=player,
            round_first_kickoff=self.first_kickoff,
            now=cutoff,
        )
        self.assertFalse(before.is_locked)
        self.assertTrue(at_cutoff.is_locked)
        self.assertEqual(at_cutoff.reason, LockoutReason.INDIVIDUAL_MATCH)

    def test_early_individual_deadline_precedes_emergency_round_lock(self):
        player = PlayerLockoutContext(
            "opening-emergency",
            self.first_kickoff,
            is_emergency=True,
        )
        decision = self.engine.evaluate_player(
            player=player,
            round_first_kickoff=self.first_kickoff,
            now=self.first_kickoff - timedelta(minutes=30),
        )
        self.assertTrue(decision.is_locked)
        self.assertEqual(decision.lockout_at, self.first_kickoff - timedelta(hours=1))
        self.assertEqual(decision.reason, LockoutReason.INDIVIDUAL_MATCH)

    def test_trade_guard_checks_both_outgoing_and_incoming_players(self):
        ordinary = PlayerLockoutContext("ordinary", self.sunday_kickoff)
        locked_emergency = PlayerLockoutContext(
            "emergency",
            self.sunday_kickoff,
            is_emergency=True,
        )
        with self.assertRaises(PlayerLockedError):
            self.engine.assert_trade_allowed(
                outgoing_player=ordinary,
                incoming_player=locked_emergency,
                round_first_kickoff=self.first_kickoff,
                now=self.first_kickoff,
            )

    def test_naive_datetimes_are_rejected(self):
        player = PlayerLockoutContext("naive", datetime(2026, 11, 29, 16, 0))
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            self.engine.evaluate_player(
                player=player,
                round_first_kickoff=self.first_kickoff,
                now=self.first_kickoff,
            )

    def test_player_cannot_be_both_captain_and_vice_captain(self):
        player = PlayerLockoutContext(
            "invalid-role",
            self.sunday_kickoff,
            is_captain=True,
            is_vice_captain=True,
        )
        with self.assertRaisesRegex(ValueError, "both Captain and Vice-Captain"):
            self.engine.evaluate_player(
                player=player,
                round_first_kickoff=self.first_kickoff,
                now=self.first_kickoff,
            )


if __name__ == "__main__":
    unittest.main()
