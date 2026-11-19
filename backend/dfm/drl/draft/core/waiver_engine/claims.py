"""Waiver claim submission and priority-based processing."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from backend.dfm.drl.draft.core.lockout_engine import DraftLockoutEngine, PlayerLockoutContext
from .models import DraftWaiverState, WaiverClaim, WaiverEntryStatus, WaiverSettings
from .priority import priority_rank, rotate_priority


def submit_claim(
    state: DraftWaiverState, settings: WaiverSettings, *,
    claim_id: str, player_id: str, franchise_id: str, drop_player_id: str | None,
    now: datetime,
) -> DraftWaiverState:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    if not claim_id or any(item.claim_id == claim_id for item in state.claims):
        raise ValueError("claim_id must be unique and non-empty")
    if franchise_id not in state.waiver_priority:
        raise ValueError("franchise is not part of this league")
    entry = next((item for item in state.entries if item.player_id == player_id
                  and item.status is WaiverEntryStatus.OPEN), None)
    if entry is None:
        raise ValueError("player is not currently on waivers")
    if now >= entry.clears_at:
        raise ValueError("waiver period has ended; player is a free agent")
    if any(item.player_id == player_id and item.franchise_id == franchise_id for item in state.claims):
        raise ValueError("franchise has already claimed this player")
    if any(item.player_id == player_id and item.claim_id == claim_id for item in state.claims):
        raise ValueError("duplicate claim")
    roster = state.league_state.roster_for(franchise_id)
    if drop_player_id is not None and drop_player_id not in roster.player_ids:
        raise ValueError("a nominated waiver drop must belong to the claiming franchise")
    if len(roster.player_ids) >= state.league_state.roster_size and drop_player_id is None:
        raise ValueError("a full squad must nominate a player to drop for a waiver claim")
    if settings.move_limit_per_franchise is not None and state.moves_for(franchise_id) >= settings.move_limit_per_franchise:
        raise ValueError("franchise waiver/free-agent move limit has been reached")
    claim = WaiverClaim(claim_id, player_id, franchise_id, drop_player_id, now.astimezone(timezone.utc))
    return replace(state, claims=(*state.claims, claim))


def process_waiver_entry(
    state: DraftWaiverState, player_id: str, now: datetime,
    lockout_contexts: dict[str, PlayerLockoutContext],
    round_first_kickoff: datetime,
    settings: WaiverSettings,
    lockout_engine: DraftLockoutEngine | None = None,
) -> DraftWaiverState:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    engine = lockout_engine or DraftLockoutEngine()
    entry = next((item for item in state.entries if item.player_id == player_id
                  and item.status is WaiverEntryStatus.OPEN), None)
    if entry is None:
        raise ValueError("open waiver entry not found")
    if now < entry.clears_at:
        raise ValueError("waiver period has not ended")
    league = state.league_state
    claims = sorted(
        (item for item in state.claims if item.player_id == player_id),
        key=lambda item: priority_rank(state.waiver_priority, item.franchise_id),
    )
    if player_id not in lockout_contexts:
        raise ValueError("lockout context is required for the claimed player")
    # A player whose own match has locked cannot be awarded or moved to free agency.
    engine.assert_player_tradeable(
        player=lockout_contexts[player_id],
        round_first_kickoff=round_first_kickoff,
        now=now,
    )
    winner = None
    for claim in claims:
        roster = league.roster_for(claim.franchise_id)
        if claim.drop_player_id is not None and claim.drop_player_id not in roster.player_ids:
            continue
        if len(roster.player_ids) >= league.roster_size and claim.drop_player_id is None:
            continue
        if settings.move_limit_per_franchise is not None and state.moves_for(claim.franchise_id) >= settings.move_limit_per_franchise:
            continue
        if claim.drop_player_id is not None and claim.drop_player_id not in lockout_contexts:
            raise ValueError("lockout context is required for the nominated drop player")
        try:
            if claim.drop_player_id is not None:
                engine.assert_player_tradeable(player=lockout_contexts[claim.drop_player_id],
                                               round_first_kickoff=round_first_kickoff, now=now)
        except ValueError:
            continue
        winner = claim
        break

    entries = tuple(
        replace(item, status=WaiverEntryStatus.PROCESSED) if item.player_id == player_id else item
        for item in state.entries
    )
    if winner is None:
        updated_league = replace(
            league,
            waiver_player_ids=tuple(item for item in league.waiver_player_ids if item != player_id),
            free_agent_player_ids=tuple(sorted((*league.free_agent_player_ids, player_id))),
        )
        return replace(state, league_state=updated_league, entries=entries)

    roster = league.roster_for(winner.franchise_id)
    updated_rosters = []
    for item in league.rosters:
        if item.franchise_id == winner.franchise_id:
            ids = (set(item.player_ids) - ({winner.drop_player_id} if winner.drop_player_id else set())) | {player_id}
            updated_rosters.append(replace(item, player_ids=tuple(sorted(ids))))
        else:
            updated_rosters.append(item)
    free_agents = set(league.free_agent_player_ids)
    if winner.drop_player_id is not None:
        free_agents.add(winner.drop_player_id)
    updated_league = replace(
        league,
        rosters=tuple(updated_rosters),
        waiver_player_ids=tuple(item for item in league.waiver_player_ids if item != player_id),
        free_agent_player_ids=tuple(sorted(free_agents)),
    )
    priority = rotate_priority(state.waiver_priority, winner.franchise_id)
    counts = dict(state.moves_used)
    counts[winner.franchise_id] = counts.get(winner.franchise_id, 0) + 1
    return replace(state, league_state=updated_league, waiver_priority=priority,
                   entries=entries, moves_used=tuple(sorted(counts.items())))

def cancel_claim(state: DraftWaiverState, claim_id: str, franchise_id: str) -> DraftWaiverState:
    """Allow a coach to withdraw their own claim before waiver processing."""
    claim = next((item for item in state.claims if item.claim_id == claim_id), None)
    if claim is None:
        raise ValueError("waiver claim not found")
    if claim.franchise_id != franchise_id:
        raise ValueError("only the claiming franchise can cancel this claim")
    entry = next((item for item in state.entries if item.player_id == claim.player_id
                  and item.status is WaiverEntryStatus.OPEN), None)
    if entry is None:
        raise ValueError("waiver claim can no longer be cancelled")
    return replace(state, claims=tuple(item for item in state.claims if item.claim_id != claim_id))
