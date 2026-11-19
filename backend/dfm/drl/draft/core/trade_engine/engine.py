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
        confirm_invalid_roster: bool = False,
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
        projected = self._projected_roster_sizes(
            state, proposing_franchise_id, receiving_franchise_id,
            offered_player_ids, requested_player_ids, roster_drops, free_agent_additions,
        )
        invalid = tuple(sorted(fid for fid, size in projected.items() if size < state.minimum_valid_players))
        if proposing_franchise_id in invalid and not confirm_invalid_roster:
            raise ValueError(
                f"confirmation required: this trade leaves your squad with {projected[proposing_franchise_id]} players; "
                f"minimum is {state.minimum_valid_players}"
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
            invalid_roster_franchise_ids=invalid,
            confirmed_invalid_roster_franchise_ids=((proposing_franchise_id,) if proposing_franchise_id in invalid else ()),
            roster_validity_deadline=round_first_kickoff.astimezone(timezone.utc) if invalid else None,
        )
        return replace(state, proposals=(*state.proposals, proposal))

    def accept_trade(
        self, state: DraftLeagueState, proposal_id: str, franchise_id: str,
        settings: DraftTradeSettings, now: datetime,
        confirm_invalid_roster: bool = False,
    ) -> DraftLeagueState:
        self._aware(now, "now")
        proposal = self._proposal(state, proposal_id)
        if proposal.status is not TradeStatus.PROPOSED:
            raise ValueError("trade proposal is not awaiting acceptance")
        if franchise_id != proposal.receiving_franchise_id:
            raise ValueError("only the receiving franchise can accept this proposal")
        if settings.trade_deadline and now >= settings.trade_deadline:
            raise ValueError("Draft trade deadline has passed")
        receiver_size = self._projected_roster_sizes(
            state, proposal.proposing_franchise_id, proposal.receiving_franchise_id,
            proposal.offered_player_ids, proposal.requested_player_ids,
            proposal.roster_drops, proposal.free_agent_additions,
        )[proposal.receiving_franchise_id]
        receiver_invalid = receiver_size < state.minimum_valid_players
        if receiver_invalid and not confirm_invalid_roster:
            raise ValueError(
                f"confirmation required: accepting this trade leaves your squad with {receiver_size} players; "
                f"minimum is {state.minimum_valid_players}"
            )
        invalid = set(proposal.invalid_roster_franchise_ids)
        confirmed = set(proposal.confirmed_invalid_roster_franchise_ids)
        if receiver_invalid:
            invalid.add(franchise_id)
            confirmed.add(franchise_id)
        accepted = replace(
            proposal, status=TradeStatus.ACCEPTED, accepted_at=now.astimezone(timezone.utc),
            review_until=(now + settings.review_period).astimezone(timezone.utc),
            invalid_roster_franchise_ids=tuple(sorted(invalid)),
            confirmed_invalid_roster_franchise_ids=tuple(sorted(confirmed)),
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
        now: datetime, player_lockouts: dict[str, PlayerLockoutContext],
        round_first_kickoff: datetime,
    ) -> DraftLeagueState:
        self._aware(now, "now")
        self._aware(round_first_kickoff, "round_first_kickoff")
        proposal = self._proposal(state, proposal_id)
        if proposal.status is not TradeStatus.ACCEPTED:
            raise ValueError("trade must be accepted before completion")
        if proposal.review_until is None or now < proposal.review_until:
            raise ValueError("trade review period has not ended")
        involved = set(proposal.offered_player_ids + proposal.requested_player_ids)
        for _, ids in proposal.roster_drops + proposal.free_agent_additions:
            involved.update(ids)
        if not involved.issubset(player_lockouts):
            raise ValueError("lockout context is required for every player at trade completion")
        for player_id in sorted(involved):
            self.lockout_engine.assert_player_tradeable(
                player=player_lockouts[player_id], round_first_kickoff=round_first_kickoff, now=now
            )
        if set(proposal.invalid_roster_franchise_ids) - set(proposal.confirmed_invalid_roster_franchise_ids):
            raise ValueError("every franchise warned about an invalid squad must confirm before trade completion")
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

        if len(proposer) > state.roster_size or len(receiver) > state.roster_size:
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

    def counter_offer(
        self, state: DraftLeagueState, settings: DraftTradeSettings, *,
        proposal_id: str, countering_franchise_id: str,
        offered_player_ids: tuple[str, ...], requested_player_ids: tuple[str, ...],
        player_lockouts: dict[str, PlayerLockoutContext],
        round_first_kickoff: datetime, now: datetime,
        roster_drops: tuple[tuple[str, tuple[str, ...]], ...] = (),
        free_agent_additions: tuple[tuple[str, tuple[str, ...]], ...] = (),
        confirm_invalid_roster: bool = False,
    ) -> DraftLeagueState:
        """Replace a pending offer with a linked counter-offer while retaining history."""
        original = self._proposal(state, proposal_id)
        if original.status is not TradeStatus.PROPOSED:
            raise ValueError("only a pending proposal can be countered")
        if countering_franchise_id != original.receiving_franchise_id:
            raise ValueError("only the receiving franchise can counter this proposal")
        countered = replace(original, status=TradeStatus.COUNTERED, countered_by_proposal_id=proposal_id + ":counter")
        state = self._replace_proposal(state, countered)
        next_state = self.propose_trade(
            state, settings, proposal_id=proposal_id + ":counter",
            proposing_franchise_id=original.receiving_franchise_id,
            receiving_franchise_id=original.proposing_franchise_id,
            offered_player_ids=offered_player_ids, requested_player_ids=requested_player_ids,
            player_lockouts=player_lockouts, round_first_kickoff=round_first_kickoff,
            now=now, roster_drops=roster_drops, free_agent_additions=free_agent_additions,
            confirm_invalid_roster=confirm_invalid_roster,
        )
        counter = self._proposal(next_state, proposal_id + ":counter")
        return self._replace_proposal(next_state, replace(counter, parent_proposal_id=proposal_id))

    @staticmethod
    def _projected_roster_sizes(
        state: DraftLeagueState, proposer_id: str, receiver_id: str,
        offered: tuple[str, ...], requested: tuple[str, ...],
        drops: tuple[tuple[str, tuple[str, ...]], ...],
        additions: tuple[tuple[str, tuple[str, ...]], ...],
    ) -> dict[str, int]:
        sizes = {proposer_id: len(state.roster_for(proposer_id).player_ids) - len(offered) + len(requested),
                 receiver_id: len(state.roster_for(receiver_id).player_ids) - len(requested) + len(offered)}
        for franchise_id, ids in drops:
            sizes[franchise_id] -= len(ids)
        for franchise_id, ids in additions:
            sizes[franchise_id] += len(ids)
        return sizes

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
