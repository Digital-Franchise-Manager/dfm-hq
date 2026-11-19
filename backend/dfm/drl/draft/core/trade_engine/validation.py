"""Validation helpers for Draft trade packages and league ownership."""
from __future__ import annotations

from .models import DraftLeagueState, TradeProposal, TradeStatus


def validate_league_state(state: DraftLeagueState) -> None:
    if not state.league_id or not state.league_id.strip():
        raise ValueError("league_id is required")
    if isinstance(state.roster_size, bool) or not isinstance(state.roster_size, int) or state.roster_size < 1:
        raise ValueError("roster_size must be a positive integer")
    if isinstance(state.minimum_valid_players, bool) or not isinstance(state.minimum_valid_players, int) or state.minimum_valid_players < 1:
        raise ValueError("minimum_valid_players must be a positive integer")
    if state.minimum_valid_players > state.roster_size:
        raise ValueError("minimum_valid_players cannot exceed roster_size")
    franchise_ids = [roster.franchise_id for roster in state.rosters]
    if not franchise_ids or len(franchise_ids) != len(set(franchise_ids)):
        raise ValueError("league must contain unique franchise rosters")
    for roster in state.rosters:
        if len(roster.player_ids) > state.roster_size:
            raise ValueError("a franchise roster cannot exceed the configured squad size")
        if len(roster.player_ids) != len(set(roster.player_ids)):
            raise ValueError("a franchise roster cannot contain duplicate players")
    owned = [player for roster in state.rosters for player in roster.player_ids]
    all_unowned = list(state.free_agent_player_ids) + list(state.waiver_player_ids)
    if len(owned + all_unowned) != len(set(owned + all_unowned)):
        raise ValueError("each player must have exactly one league ownership or availability status")


def pending_player_ids(state: DraftLeagueState) -> set[str]:
    involved: set[str] = set()
    for proposal in state.proposals:
        if proposal.status in (TradeStatus.PROPOSED, TradeStatus.ACCEPTED):
            involved.update(proposal.offered_player_ids)
            involved.update(proposal.requested_player_ids)
            for _, ids in proposal.roster_drops + proposal.free_agent_additions:
                involved.update(ids)
    return involved


def validate_package(
    state: DraftLeagueState,
    proposing_franchise_id: str,
    receiving_franchise_id: str,
    offered_player_ids: tuple[str, ...],
    requested_player_ids: tuple[str, ...],
    roster_drops: tuple[tuple[str, tuple[str, ...]], ...],
    free_agent_additions: tuple[tuple[str, tuple[str, ...]], ...],
) -> None:
    validate_league_state(state)
    if proposing_franchise_id == receiving_franchise_id:
        raise ValueError("a franchise cannot trade with itself")
    proposer = state.roster_for(proposing_franchise_id)
    receiver = state.roster_for(receiving_franchise_id)
    if not offered_player_ids or not requested_player_ids:
        raise ValueError("both sides must include at least one traded player")
    if len(set(offered_player_ids + requested_player_ids)) != len(offered_player_ids) + len(requested_player_ids):
        raise ValueError("trade package contains duplicate players")
    if not set(offered_player_ids).issubset(proposer.player_ids):
        raise ValueError("every offered player must belong to the proposing franchise")
    if not set(requested_player_ids).issubset(receiver.player_ids):
        raise ValueError("every requested player must belong to the receiving franchise")

    adjustments: dict[str, tuple[set[str], set[str]]] = {}
    for franchise_id, ids in roster_drops:
        if franchise_id not in (proposing_franchise_id, receiving_franchise_id):
            raise ValueError("roster adjustments may only affect the two trading franchises")
        drops, adds = adjustments.setdefault(franchise_id, (set(), set()))
        if drops.intersection(ids) or len(set(ids)) != len(ids):
            raise ValueError("duplicate roster drop")
        drops.update(ids)
    for franchise_id, ids in free_agent_additions:
        if franchise_id not in (proposing_franchise_id, receiving_franchise_id):
            raise ValueError("roster adjustments may only affect the two trading franchises")
        drops, adds = adjustments.setdefault(franchise_id, (set(), set()))
        if adds.intersection(ids) or len(set(ids)) != len(ids):
            raise ValueError("duplicate free-agent addition")
        adds.update(ids)

    if len({f for f, _ in roster_drops}) != len(roster_drops):
        raise ValueError("roster drops must be grouped once per franchise")
    if len({f for f, _ in free_agent_additions}) != len(free_agent_additions):
        raise ValueError("free-agent additions must be grouped once per franchise")

    all_additions = [player for _, ids in free_agent_additions for player in ids]
    all_drops = [player for _, ids in roster_drops for player in ids]
    if len(all_additions) != len(set(all_additions)):
        raise ValueError("a free agent cannot be added to multiple franchises in one trade")
    if len(all_drops) != len(set(all_drops)):
        raise ValueError("a player cannot be dropped by multiple franchises in one trade")

    for franchise_id, incoming, outgoing in (
        (proposing_franchise_id, requested_player_ids, offered_player_ids),
        (receiving_franchise_id, offered_player_ids, requested_player_ids),
    ):
        roster = state.roster_for(franchise_id)
        drops, adds = adjustments.get(franchise_id, (set(), set()))
        if not drops.issubset(roster.player_ids):
            raise ValueError("a roster adjustment drop must belong to that franchise")
        if drops.intersection(incoming) or drops.intersection(outgoing):
            raise ValueError("a traded player cannot also be listed as a roster drop")
        if not adds.issubset(state.free_agent_player_ids):
            raise ValueError("roster adjustments may only add currently unowned free agents")
        final_size = len(roster.player_ids) - len(outgoing) + len(incoming) - len(drops) + len(adds)
        if final_size < 0 or final_size > state.roster_size:
            raise ValueError("trade and roster adjustments must keep both squads within the configured size")

    reserved = pending_player_ids(state)
    all_involved = set(offered_player_ids + requested_player_ids)
    for _, ids in roster_drops + free_agent_additions:
        all_involved.update(ids)
    if reserved.intersection(all_involved):
        raise ValueError("a player is already involved in another pending trade")
