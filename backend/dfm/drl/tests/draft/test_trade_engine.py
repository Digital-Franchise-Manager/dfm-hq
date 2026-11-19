"""Tests for Draft coach-to-coach trade lifecycle and veto rules."""
import unittest
from datetime import datetime, timedelta, timezone

from backend.dfm.drl.draft.core.lockout_engine import PlayerLockoutContext
from backend.dfm.drl.draft.core.trade_engine import (
    DraftLeagueState, DraftRoster, DraftTradeEngine, DraftTradeSettings,
    TradeStatus, VetoMode,
)


class DraftTradeEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = DraftTradeEngine()
        self.now = datetime(2027, 3, 1, 8, tzinfo=timezone.utc)
        self.kickoff = self.now + timedelta(days=2)
        self.state = DraftLeagueState(
            league_id="league-1", roster_size=3,
            rosters=(
                DraftRoster("A", ("a1", "a2", "a3")),
                DraftRoster("B", ("b1", "b2", "b3")),
            ),
            free_agent_player_ids=("fa1",),
        )
        self.settings = DraftTradeSettings(review_period=timedelta(hours=1))
        self.contexts = {
            player: PlayerLockoutContext(player, self.kickoff + timedelta(hours=index))
            for index, player in enumerate(("a1", "a3", "b1", "b2", "fa1"))
        }

    def propose(self, state=None, **overrides):
        args = {
            "proposal_id": "trade-1",
            "proposing_franchise_id": "A",
            "receiving_franchise_id": "B",
            "offered_player_ids": ("a1",),
            "requested_player_ids": ("b1", "b2"),
            "player_lockouts": self.contexts,
            "round_first_kickoff": self.kickoff,
            "now": self.now,
            "roster_drops": (("A", ("a3",)),),
            "free_agent_additions": (("B", ("fa1",)),),
        }
        args.update(overrides)
        return self.engine.propose_trade(state or self.state, self.settings, **args)

    def test_multi_player_trade_completes_with_roster_adjustments_atomically(self):
        state = self.propose()
        state = self.engine.accept_trade(state, "trade-1", "B", self.settings, self.now)
        state = self.engine.finalize_trade(
            state, "trade-1", self.settings, self.now + timedelta(hours=1),
            self.contexts, self.kickoff,
        )
        self.assertEqual(state.proposals[0].status, TradeStatus.COMPLETED)
        self.assertEqual(set(state.roster_for("A").player_ids), {"a2", "b1", "b2"})
        self.assertEqual(set(state.roster_for("B").player_ids), {"a1", "b3", "fa1"})
        self.assertEqual(state.free_agent_player_ids, ("a3",))
        self.assertEqual(len(state.completed_trades), 1)

    def test_unequal_trade_requires_explicit_confirmation_and_invalid_squad_scores_zero(self):
        league = DraftLeagueState(
            league_id="league-minimum", roster_size=20, minimum_valid_players=17,
            rosters=(DraftRoster("A", tuple(f"a{i}" for i in range(17))),
                     DraftRoster("B", tuple(f"b{i}" for i in range(17)))),
        )
        contexts = {p: PlayerLockoutContext(p, self.kickoff + timedelta(hours=i))
                    for i, p in enumerate(("a0", "a1", "b0"))}
        args = dict(proposal_id="unequal", proposing_franchise_id="A", receiving_franchise_id="B",
                    offered_player_ids=("a0", "a1"), requested_player_ids=("b0",),
                    player_lockouts=contexts, round_first_kickoff=self.kickoff, now=self.now)
        with self.assertRaisesRegex(ValueError, "confirmation required"):
            self.engine.propose_trade(league, self.settings, **args)
        state = self.engine.propose_trade(league, self.settings, **args, confirm_invalid_roster=True)
        self.assertEqual(state.proposals[0].invalid_roster_franchise_ids, ("A",))
        self.assertEqual(state.proposals[0].confirmed_invalid_roster_franchise_ids, ("A",))
        state = self.engine.accept_trade(state, "unequal", "B", self.settings, self.now)
        state = self.engine.finalize_trade(state, "unequal", self.settings, self.now + timedelta(hours=1), contexts, self.kickoff)
        self.assertEqual(len(state.roster_for("A").player_ids), 16)
        self.assertEqual(state.effective_score_for("A", 125), 0)
        self.assertEqual(state.effective_score_for("B", 125), 125)

    def test_counter_offer_links_history_and_reverses_trading_roles(self):
        state = self.propose()
        state = self.engine.counter_offer(
            state, self.settings, proposal_id="trade-1", countering_franchise_id="B",
            offered_player_ids=("b2",), requested_player_ids=("a3",),
            player_lockouts=self.contexts, round_first_kickoff=self.kickoff, now=self.now,
        )
        original, counter = state.proposals
        self.assertEqual(original.status, TradeStatus.COUNTERED)
        self.assertEqual(counter.parent_proposal_id, "trade-1")
        self.assertEqual(counter.proposing_franchise_id, "B")
        self.assertEqual(counter.receiving_franchise_id, "A")

    def test_only_receiving_franchise_can_accept(self):
        state = self.propose()
        with self.assertRaisesRegex(ValueError, "only the receiving franchise"):
            self.engine.accept_trade(state, "trade-1", "A", self.settings, self.now)

    def test_trade_cannot_finalize_before_review_period_ends(self):
        state = self.propose()
        state = self.engine.accept_trade(state, "trade-1", "B", self.settings, self.now)
        with self.assertRaisesRegex(ValueError, "review period has not ended"):
            self.engine.finalize_trade(state, "trade-1", self.settings, self.now, self.contexts, self.kickoff)

    def test_trade_deadline_blocks_new_proposals(self):
        settings = DraftTradeSettings(trade_deadline=self.now - timedelta(seconds=1))
        with self.assertRaisesRegex(ValueError, "deadline has passed"):
            self.engine.propose_trade(
                self.state, settings, proposal_id="late", proposing_franchise_id="A",
                receiving_franchise_id="B", offered_player_ids=("a1",),
                requested_player_ids=("b1",), player_lockouts=self.contexts,
                round_first_kickoff=self.kickoff, now=self.now,
                roster_drops=(("A", ("a2",)),),
                free_agent_additions=(("B", ("fa1",)),),
            )

    def test_rejects_trade_if_roster_adjustments_would_exceed_squad_size(self):
        with self.assertRaisesRegex(ValueError, "roster adjustments"):
            self.propose(roster_drops=(), free_agent_additions=())

    def test_rejects_player_already_in_pending_trade(self):
        state = self.propose()
        with self.assertRaisesRegex(ValueError, "already involved"):
            self.engine.propose_trade(
                state, self.settings, proposal_id="trade-2",
                proposing_franchise_id="A", receiving_franchise_id="B",
                offered_player_ids=("a1",), requested_player_ids=("b3",),
                player_lockouts=self.contexts, round_first_kickoff=self.kickoff,
                now=self.now,
            )

    def test_locked_player_cannot_be_traded(self):
        locked = dict(self.contexts)
        locked["a1"] = PlayerLockoutContext(
            "a1", self.kickoff + timedelta(hours=2), is_captain=True
        )
        with self.assertRaisesRegex(ValueError, "is locked"):
            self.propose(player_lockouts=locked, now=self.kickoff)

    def test_commissioner_can_veto_accepted_trade(self):
        state = self.propose()
        state = self.engine.accept_trade(state, "trade-1", "B", self.settings, self.now)
        state = self.engine.commissioner_veto(state, "trade-1", "A", ("A",))
        self.assertEqual(state.proposals[0].status, TradeStatus.VETOED)
        with self.assertRaisesRegex(ValueError, "must be accepted"):
            self.engine.finalize_trade(
                state, "trade-1", self.settings, self.now + timedelta(hours=2),
                self.contexts, self.kickoff,
            )

    def test_league_vote_can_veto_trade(self):
        state = DraftLeagueState(
            league_id="league-2", roster_size=2,
            rosters=(
                DraftRoster("A", ("a1", "a2")), DraftRoster("B", ("b1", "b2")),
                DraftRoster("C", ("c1", "c2")), DraftRoster("D", ("d1", "d2")),
            ),
            free_agent_player_ids=("fa1",),
        )
        settings = DraftTradeSettings(
            review_period=timedelta(hours=1), veto_mode=VetoMode.LEAGUE_VOTE,
            veto_vote_threshold=0.5,
        )
        contexts = {
            p: PlayerLockoutContext(p, self.kickoff + timedelta(hours=i))
            for i, p in enumerate(("a1", "b1", "c1", "d1", "fa1"))
        }
        state = self.engine.propose_trade(
            state, settings, proposal_id="vote-trade", proposing_franchise_id="A",
            receiving_franchise_id="B", offered_player_ids=("a1",),
            requested_player_ids=("b1",), player_lockouts=contexts,
            round_first_kickoff=self.kickoff, now=self.now,
        )
        state = self.engine.accept_trade(state, "vote-trade", "B", settings, self.now)
        state = self.engine.vote_to_veto(
            state, "vote-trade", "C", True, settings, self.now + timedelta(minutes=10)
        )
        state = self.engine.finalize_trade(
            state, "vote-trade", settings, self.now + timedelta(hours=1),
            contexts, self.kickoff,
        )
        self.assertEqual(state.proposals[0].status, TradeStatus.VETOED)
        self.assertEqual(state.roster_for("A").player_ids, ("a1", "a2"))


if __name__ == "__main__":
    unittest.main()
