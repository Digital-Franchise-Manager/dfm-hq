"""Tests for Draft waivers, priority rotation and free agency."""
import unittest
from datetime import datetime, timedelta, timezone

from backend.dfm.drl.draft.core.lockout_engine import PlayerLockoutContext
from backend.dfm.drl.draft.core.trade_engine import DraftLeagueState, DraftRoster
from backend.dfm.drl.draft.core.waiver_engine import DraftWaiverEngine, WaiverSettings


class DraftWaiverEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = DraftWaiverEngine()
        self.now = datetime(2027, 3, 1, 8, tzinfo=timezone.utc)
        self.kickoff = self.now + timedelta(days=3)
        self.league = DraftLeagueState(
            league_id="league-1", roster_size=3,
            rosters=(
                DraftRoster("A", ("a1", "a2", "a3")),
                DraftRoster("B", ("b1", "b2", "b3")),
                DraftRoster("C", ("c1", "c2", "c3")),
            ),
            free_agent_player_ids=("fa1",),
        )
        self.state = self.engine.create_state(self.league, ("B", "A", "C"))
        self.settings = WaiverSettings(waiver_period=timedelta(hours=24))
        self.contexts = {
            p: PlayerLockoutContext(p, self.kickoff + timedelta(hours=i))
            for i, p in enumerate(("a1", "b1", "c1", "fa1"))
        }

    def drop(self):
        return self.engine.drop_player(
            self.state, self.settings, franchise_id="A", player_id="a1",
            lockout_context=self.contexts["a1"], round_first_kickoff=self.kickoff,
            now=self.now,
        )

    def test_drop_places_player_on_waivers_and_opens_roster_slot(self):
        state = self.drop()
        self.assertNotIn("a1", state.league_state.roster_for("A").player_ids)
        self.assertIn("a1", state.league_state.waiver_player_ids)
        self.assertEqual(state.entries[0].clears_at, self.now + timedelta(hours=24))

    def test_claim_cannot_be_submitted_after_waiver_period(self):
        state = self.drop()
        with self.assertRaisesRegex(ValueError, "waiver period has ended"):
            self.engine.submit_claim(
                state, self.settings, claim_id="claim-1", player_id="a1",
                franchise_id="B", drop_player_id="b1",
                now=self.now + timedelta(hours=24),
            )

    def test_priority_winner_gets_player_and_moves_to_bottom(self):
        state = self.drop()
        state = self.engine.submit_claim(
            state, self.settings, claim_id="claim-b", player_id="a1",
            franchise_id="B", drop_player_id="b1", now=self.now + timedelta(hours=1),
        )
        state = self.engine.submit_claim(
            state, self.settings, claim_id="claim-c", player_id="a1",
            franchise_id="C", drop_player_id="c1", now=self.now + timedelta(hours=2),
        )
        state = self.engine.process_waiver(
            state, "a1", self.now + timedelta(hours=24), self.contexts,
            self.kickoff, self.settings,
        )
        self.assertIn("a1", state.league_state.roster_for("B").player_ids)
        self.assertNotIn("b1", state.league_state.roster_for("B").player_ids)
        self.assertIn("b1", state.league_state.free_agent_player_ids)
        self.assertEqual(state.waiver_priority, ("A", "C", "B"))
        self.assertEqual(state.moves_for("B"), 1)

    def test_claimant_can_cancel_their_own_pending_claim(self):
        state = self.drop()
        state = self.engine.submit_claim(
            state, self.settings, claim_id="claim-b", player_id="a1",
            franchise_id="B", drop_player_id="b1", now=self.now + timedelta(hours=1),
        )
        state = self.engine.cancel_claim(state, "claim-b", "B")
        self.assertEqual(state.claims, ())

    def test_unclaimed_player_becomes_free_agent(self):
        state = self.drop()
        state = self.engine.process_waiver(
            state, "a1", self.now + timedelta(hours=24), self.contexts,
            self.kickoff, self.settings,
        )
        self.assertIn("a1", state.league_state.free_agent_player_ids)
        self.assertNotIn("a1", state.league_state.waiver_player_ids)

    def test_free_agent_add_requires_drop_when_roster_is_full(self):
        with self.assertRaisesRegex(ValueError, "must nominate a player to drop"):
            self.engine.add_free_agent(
                self.state, self.settings, franchise_id="A", player_id="fa1",
                drop_player_id=None, lockout_contexts=self.contexts,
                round_first_kickoff=self.kickoff, now=self.now,
            )

    def test_free_agent_add_swaps_player_atomically(self):
        state = self.engine.add_free_agent(
            self.state, self.settings, franchise_id="A", player_id="fa1",
            drop_player_id="a1", lockout_contexts=self.contexts,
            round_first_kickoff=self.kickoff, now=self.now,
        )
        self.assertEqual(set(state.league_state.roster_for("A").player_ids), {"fa1", "a2", "a3"})
        self.assertIn("a1", state.league_state.free_agent_player_ids)
        self.assertNotIn("fa1", state.league_state.free_agent_player_ids)
        self.assertEqual(state.moves_for("A"), 1)

    def test_open_roster_slot_can_be_filled_without_second_drop(self):
        state = self.drop()
        state = self.engine.add_free_agent(
            state, self.settings, franchise_id="A", player_id="fa1",
            drop_player_id=None, lockout_contexts=self.contexts,
            round_first_kickoff=self.kickoff, now=self.now + timedelta(minutes=1),
        )
        self.assertEqual(set(state.league_state.roster_for("A").player_ids), {"fa1", "a2", "a3"})

    def test_custom_move_limit_is_enforced(self):
        limited = WaiverSettings(move_limit_per_franchise=0)
        with self.assertRaisesRegex(ValueError, "move limit"):
            self.engine.add_free_agent(
                self.state, limited, franchise_id="A", player_id="fa1",
                drop_player_id="a1", lockout_contexts=self.contexts,
                round_first_kickoff=self.kickoff, now=self.now,
            )

    def test_locked_player_cannot_be_added_from_free_agency(self):
        contexts = dict(self.contexts)
        contexts["fa1"] = PlayerLockoutContext("fa1", self.now - timedelta(minutes=1))
        with self.assertRaisesRegex(ValueError, "is locked"):
            self.engine.add_free_agent(
                self.state, self.settings, franchise_id="A", player_id="fa1",
                drop_player_id="a1", lockout_contexts=contexts,
                round_first_kickoff=self.kickoff, now=self.now,
            )


if __name__ == "__main__":
    unittest.main()
