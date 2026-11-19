"""Veto rules for commissioner review and league voting."""
from __future__ import annotations

from datetime import datetime

from .models import DraftLeagueState, DraftTradeSettings, TradeProposal, TradeStatus, VetoMode, VetoVote


def add_veto_vote(
    state: DraftLeagueState,
    proposal: TradeProposal,
    franchise_id: str,
    veto: bool,
    voted_at: datetime,
    settings: DraftTradeSettings,
) -> TradeProposal:
    if settings.veto_mode is not VetoMode.LEAGUE_VOTE:
        raise ValueError("league voting is not enabled for this league")
    if proposal.status is not TradeStatus.ACCEPTED:
        raise ValueError("only accepted trades can enter the veto vote")
    if franchise_id in (proposal.proposing_franchise_id, proposal.receiving_franchise_id):
        raise ValueError("trading franchises cannot vote on their own trade")
    eligible = {roster.franchise_id for roster in state.rosters} - {
        proposal.proposing_franchise_id, proposal.receiving_franchise_id
    }
    if franchise_id not in eligible:
        raise ValueError("voter is not eligible to vote on this trade")
    if any(vote.franchise_id == franchise_id for vote in proposal.votes):
        raise ValueError("franchise has already voted on this trade")
    if proposal.review_until is None or voted_at > proposal.review_until:
        raise ValueError("trade review period has ended")
    return TradeProposal(
        proposal_id=proposal.proposal_id,
        proposing_franchise_id=proposal.proposing_franchise_id,
        receiving_franchise_id=proposal.receiving_franchise_id,
        offered_player_ids=proposal.offered_player_ids,
        requested_player_ids=proposal.requested_player_ids,
        roster_drops=proposal.roster_drops,
        free_agent_additions=proposal.free_agent_additions,
        proposed_at=proposal.proposed_at,
        status=proposal.status,
        accepted_at=proposal.accepted_at,
        review_until=proposal.review_until,
        votes=(*proposal.votes, VetoVote(franchise_id, veto, voted_at)),
        parent_proposal_id=proposal.parent_proposal_id,
        countered_by_proposal_id=proposal.countered_by_proposal_id,
        invalid_roster_franchise_ids=proposal.invalid_roster_franchise_ids,
        confirmed_invalid_roster_franchise_ids=proposal.confirmed_invalid_roster_franchise_ids,
        roster_validity_deadline=proposal.roster_validity_deadline,
    )


def is_vetoed(state: DraftLeagueState, proposal: TradeProposal, settings: DraftTradeSettings) -> bool:
    if settings.veto_mode is not VetoMode.LEAGUE_VOTE:
        return False
    eligible_count = len(state.rosters) - 2
    if eligible_count <= 0:
        return False
    veto_count = sum(1 for vote in proposal.votes if vote.veto)
    return veto_count / eligible_count >= settings.veto_vote_threshold
