"""Draft coach-to-coach trade proposals, review, veto and atomic completion."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

from backend.dfm.drl.draft.core.lockout_engine import DraftLockoutEngine, PlayerLockoutContext
from .models import (
    DraftLeagueState, DraftTradeRecord, DraftTradeSettings, TradeProposal, TradeStatus, VetoMode
)
from .validation import validate_package, validate_league_state
from .veto_system import add_veto_vote, is_vetoed


class DraftTradeEngine:
    """Pure immutable Draft trade transitions; persistence belongs to the service layer."""

    def __init__(self, lockout_engine: DraftLockoutEngine | None = None) -> None:
        self.lockout_engine = lockout_engine or DraftLockoutEngine()

    @staticmethod
    def _aware(value: datetime, name: str) -> None:
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{name} must be timezone-aware")

    def propose_trade(
        self,
        state: DraftLeagueState,
        settings: DraftTradeSettings,
        *,
        proposal_id: str,
        proposing_franchise_id: str,
        receiving_franchise_id: str,
        offered_player_ids: tuple[str, ...],
        requested_player_ids: tuple[str, ...],
        player_lockouts: dict[str, PlayerLockoutContext],
        round_first_kickoff: datetime,
        now: datetime,
        roster_drops: tuple[tuple[str, tuple[str, ...]], ...] = (),
        free_agent_additions: tuple[tuple[str, tuple[str, ...]], ...] = (),
    ) -> DraftLeagueState:
        self._aware(now, "now")
        self._aware(round_first_kickoff, "round_first_kickoff")
        if not proposal_id or not proposal_id.strip():
            raise ValueError("proposal_id is required")
        if any(item.proposal_id == proposal_id for item in state.proposals):
            raise ValueError("duplicate proposal_id")
        if settings.trade_deadline and now >= settings.trade_deadline:
            raise ValueError("Draft trade deadline has passed")
        validate_package(state, proposing_franchise_id, receiving_franchise_id,
                         offered_player_ids, requested_player_ids, roster_drops, free_agent_additions)
        involved = set(offered_player_ids + requested_player_ids)
        for _, ids in roster_drops + free_agent_additions:
            involved.update(ids)
        if not involved.issubset(player_lockouts):
            raise ValueError("lockout context is required for every player in the trade and roster adjustments")
        for player_id in sorted(involved):
            self.lockout_engine.assert_player_tradeable(
                player=player_lockouts[player_id],
                round_first_kickoff=round_first_kickoff,
                now=now,
            )
        proposal = TradeProposal(
            proposal_id=proposal_id,
            proposing_franchise_id=proposing_franchise_id,
            receiving_franchise_id=receiving_franchise_id,
            offered_player_ids=tuple(offered_player_ids),
            requested_player_ids=tuple(requested_player_ids),
            roster_drops=tuple(roster_drops),
            free_agent_additions=tuple(free_agent_additions),
            proposed_at=now.astimezone(timezone.utc),
        )
        return replace(state, proposals=(*state.proposals, proposal))

    def accept_trade(
        self, state: DraftLeagueState, proposal_id: str, franchise_id: str,
        settings: DraftTradeSettings, now: datetime,
    ) -> DraftLeagueState:
        self._aware(now, "now")
        proposal = self._proposal(state, proposal_id)
        if proposal.status is not TradeStatus.PROPOSED:
            raise ValueError("trade proposal is not awaiting acceptance")
        if franchise_id != proposal.receiving_franchise_id:
            raise ValueError("only the receiving franchise can accept this proposal")
        if settings.trade_deadline and now >= settings.trade_deadline:
            raise ValueError("Draft trade deadline has passed")
        accepted = replace(
            proposal, status=TradeStatus.ACCEPTED, accepted_at=now.astimezone(timezone.utc),
            review_until=(now + settings.review_period).astimezone(timezone.utc),
        )
        return self._replace_proposal(state, accepted)

    def reject_trade(self, state: DraftLeagueState, proposal_id: str, franchise_id: str) -> DraftLeagueState:
        proposal = self._proposal(state, proposal_id)
        if proposal.status is not TradeStatus.PROPOSED:
            raise ValueError("trade proposal is not awaiting a response")
        if franchise_id != proposal.receiving_franchise_id:
            raise ValueError("only the receiving franchise can reject this proposal")
        return self._replace_proposal(state, replace(proposal, status=TradeStatus.REJECTED))

    def vote_to_veto(
        self, state: DraftLeagueState, proposal_id: str, franchise_id: str,
        veto: bool, settings: DraftTradeSettings, now: datetime,
    ) -> DraftLeagueState:
        self._aware(now, "now")
        proposal = self._proposal(state, proposal_id)
        updated = add_veto_vote(state, proposal, franchise_id, veto, now, settings)
        return self._replace_proposal(state, updated)

    def commissioner_veto(
        self, state: DraftLeagueState, proposal_id: str, commissioner_franchise_id: str,
        commissioner_franchise_ids: tuple[str, ...],
    ) -> DraftLeagueState:
        proposal = self._proposal(state, proposal_id)
        if commissioner_franchise_id not in commissioner_franchise_ids:
            raise ValueError("only an authorised league commissioner can veto this trade")
        if proposal.status is not TradeStatus.ACCEPTED:
            raise ValueError("only accepted trades can be vetoed")
        return self._replace_proposal(state, replace(proposal, status=TradeStatus.VETOED))

    def finalize_trade(
        self, state: DraftLeagueState, proposal_id: str, settings: DraftTradeSettings,
        now: datetime,
    ) -> DraftLeagueState:
        self._aware(now, "now")
        proposal = self._proposal(state, proposal_id)
        if proposal.status is not TradeStatus.ACCEPTED:
            raise ValueError("trade must be accepted before completion")
        if proposal.review_until is None or now < proposal.review_until:
            raise ValueError("trade review period has not ended")
        if is_vetoed(state, proposal, settings):
            return self._replace_proposal(state, replace(proposal, status=TradeStatus.VETOED))

        proposer = set(state.roster_for(proposal.proposing_franchise_id).player_ids)
        receiver = set(state.roster_for(proposal.receiving_franchise_id).player_ids)
        proposer.difference_update(proposal.offered_player_ids)
        proposer.update(proposal.requested_player_ids)
        receiver.difference_update(proposal.requested_player_ids)
        receiver.update(proposal.offered_player_ids)
        for franchise_id, ids in proposal.roster_drops:
            target = proposer if franchise_id == proposal.proposing_franchise_id else receiver
            target.difference_update(ids)
        for franchise_id, ids in proposal.free_agent_additions:
            target = proposer if franchise_id == proposal.proposing_franchise_id else receiver
            target.update(ids)

        if len(proposer) != state.roster_size or len(receiver) != state.roster_size:
            raise ValueError("trade roster adjustments no longer satisfy configured squad size")
        free_agents = set(state.free_agent_player_ids)
        additions = {player for _, ids in proposal.free_agent_additions for player in ids}
        if not additions.issubset(free_agents):
            raise ValueError("a proposed free-agent addition is no longer available")
        drops = {player for _, ids in proposal.roster_drops for player in ids}
        free_agents.difference_update(additions)
        free_agents.update(drops)

        rosters = []
        for roster in state.rosters:
            if roster.franchise_id == proposal.proposing_franchise_id:
                rosters.append(replace(roster, player_ids=tuple(sorted(proposer))))
            elif roster.franchise_id == proposal.receiving_franchise_id:
                rosters.append(replace(roster, player_ids=tuple(sorted(receiver))))
            else:
                rosters.append(roster)
        record = DraftTradeRecord(
            proposal_id=proposal.proposal_id,
            proposing_franchise_id=proposal.proposing_franchise_id,
            receiving_franchise_id=proposal.receiving_franchise_id,
            transferred_player_ids=tuple(sorted(proposal.offered_player_ids + proposal.requested_player_ids)),
            completed_at=now.astimezone(timezone.utc),
        )
        completed = replace(proposal, status=TradeStatus.COMPLETED)
        updated = self._replace_proposal(replace(
            state, rosters=tuple(rosters), free_agent_player_ids=tuple(sorted(free_agents)),
            completed_trades=(*state.completed_trades, record),
        ), completed)
        validate_league_state(updated)
        return updated

    @staticmethod
    def _proposal(state: DraftLeagueState, proposal_id: str) -> TradeProposal:
        for proposal in state.proposals:
            if proposal.proposal_id == proposal_id:
                return proposal
        raise ValueError("trade proposal not found")

    @staticmethod
    def _replace_proposal(state: DraftLeagueState, proposal: TradeProposal) -> DraftLeagueState:
        return replace(state, proposals=tuple(
            proposal if item.proposal_id == proposal.proposal_id else item
            for item in state.proposals
        ))
