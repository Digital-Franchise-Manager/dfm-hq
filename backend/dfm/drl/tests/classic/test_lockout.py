import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from backend.dfm.drl.classic.core.lockout_engine import (
    ClassicLockoutEngine,
    LockoutReason,
    PlayerLockedError,
    PlayerLockoutContext,
)


class ClassicLockoutEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = ClassicLockoutEngine()
        self.first_kickoff = datetime(2026, 11, 26, 20, 0, tzinfo=timezone(timedelta(hours=11)))
        self.sunday_kickoff = datetime(2026, 11, 29, 16, 0, tzinfo=timezone(timedelta(hours=11)))

    def test_captain_locks_at_first_round_kickoff_even_when_playing_sunday(self):
        player = PlayerLockoutContext("captain", self.sunday_kickoff, is_captain=True)
        decision = self.engine.evaluate_player(
            player=player,
            round_first_kickoff=self.first_kickoff,
            now=self.first_kickoff,
        )
        self.assertTrue(decision.is_locked)
        self.assertEqual(decision.lockout_at, self.first_kickoff)
        self.assertEqual(decision.reason, LockoutReason.CAPTAIN_ROUND)

    def test_vice_captain_locks_at_first_round_kickoff(self):
        player = PlayerLockoutContext("vice", self.sunday_kickoff, is_vice_captain=True)
        decision = self.engine.evaluate_player(
            player=player,
            round_first_kickoff=self.first_kickoff,
            now=self.first_kickoff + timedelta(seconds=1),
        )
        self.assertTrue(decision.is_locked)
        self.assertEqual(decision.reason, LockoutReason.VICE_CAPTAIN_ROUND)

    def test_ordinary_player_remains_tradeable_until_one_hour_before_own_match(self):
        player = PlayerLockoutContext("sunday-player", self.sunday_kickoff)
        cutoff = self.sunday_kickoff - timedelta(hours=1)
        before = self.engine.evaluate_player(
            player=player,
            round_first_kickoff=self.first_kickoff,
            now=cutoff - timedelta(microseconds=1),
        )
        at_cutoff = self.engine.evaluate_player(
            player=player,
            round_first_kickoff=self.first_kickoff,
            now=cutoff,
        )
        self.assertFalse(before.is_locked)
        self.assertTrue(at_cutoff.is_locked)
        self.assertEqual(at_cutoff.reason, LockoutReason.INDIVIDUAL_MATCH)

    def test_early_individual_deadline_precedes_round_captaincy_lock(self):
        first_player = PlayerLockoutContext(
            "opening-match-captain",
            self.first_kickoff,
            is_captain=True,
        )
        decision = self.engine.evaluate_player(
            player=first_player,
            round_first_kickoff=self.first_kickoff,
            now=self.first_kickoff - timedelta(minutes=59),
        )
        self.assertTrue(decision.is_locked)
        self.assertEqual(decision.lockout_at, self.first_kickoff - timedelta(hours=1))
        self.assertEqual(decision.reason, LockoutReason.INDIVIDUAL_MATCH)

    def test_locked_out_player_cannot_be_traded_out_or_in(self):
        ordinary = PlayerLockoutContext("ordinary", self.sunday_kickoff)
        locked = PlayerLockoutContext("locked", self.sunday_kickoff)
        with self.assertRaises(PlayerLockedError):
            self.engine.assert_trade_allowed(
                outgoing_player=locked,
                incoming_player=ordinary,
                round_first_kickoff=self.first_kickoff,
                now=self.sunday_kickoff - timedelta(minutes=30),
            )
        with self.assertRaises(PlayerLockedError):
            self.engine.assert_trade_allowed(
                outgoing_player=ordinary,
                incoming_player=locked,
                round_first_kickoff=self.first_kickoff,
                now=self.sunday_kickoff - timedelta(minutes=30),
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


    def test_one_hour_deadline_uses_elapsed_time_across_sydney_dst_transition(self):
        sydney = ZoneInfo("Australia/Sydney")
        first = datetime(2026, 10, 1, 20, 0, tzinfo=sydney)
        # Sydney jumps from 02:00 to 03:00 on this date.
        match = datetime(2026, 10, 4, 3, 30, tzinfo=sydney)
        player = PlayerLockoutContext("dst-player", match)
        decision = self.engine.evaluate_player(
            player=player,
            round_first_kickoff=first,
            now=datetime(2026, 10, 4, 1, 45, tzinfo=sydney),
        )
        local_cutoff = decision.lockout_at.astimezone(sydney)
        self.assertEqual((local_cutoff.hour, local_cutoff.minute), (1, 30))


if __name__ == "__main__":
    unittest.main()
