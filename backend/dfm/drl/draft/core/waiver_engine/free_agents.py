"""First-come, first-served Draft free-agent moves."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from backend.dfm.drl.draft.core.lockout_engine import DraftLockoutEngine, PlayerLockoutContext
from .models import DraftWaiverState, WaiverSettings


def add_free_agent(
    state: DraftWaiverState, settings: WaiverSettings, *,
    franchise_id: str, player_id: str, drop_player_id: str,
    lockout_contexts: dict[str, PlayerLockoutContext],
    round_first_kickoff: datetime, now: datetime,
    lockout_engine: DraftLockoutEngine | None = None,
) -> DraftWaiverState:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    if player_id not in state.league_state.free_agent_player_ids:
        raise ValueError("player is not an available free agent")
    if settings.move_limit_per_franchise is not None and state.moves_for(franchise_id) >= settings.move_limit_per_franchise:
        raise ValueError("franchise waiver/free-agent move limit has been reached")
    roster = state.league_state.roster_for(franchise_id)
    if drop_player_id not in roster.player_ids:
        raise ValueError("a free-agent acquisition must nominate a current roster player to drop")
    if player_id not in lockout_contexts or drop_player_id not in lockout_contexts:
        raise ValueError("lockout contexts are required for the acquired and dropped players")
    engine = lockout_engine or DraftLockoutEngine()
    engine.assert_player_tradeable(player=lockout_contexts[player_id],
                                   round_first_kickoff=round_first_kickoff, now=now)
    engine.assert_player_tradeable(player=lockout_contexts[drop_player_id],
                                   round_first_kickoff=round_first_kickoff, now=now)
    updated_rosters = []
    for item in state.league_state.rosters:
        if item.franchise_id == franchise_id:
            ids = (set(item.player_ids) - {drop_player_id}) | {player_id}
            updated_rosters.append(replace(item, player_ids=tuple(sorted(ids))))
        else:
            updated_rosters.append(item)
    league = replace(
        state.league_state, rosters=tuple(updated_rosters),
        free_agent_player_ids=tuple(sorted(
            (set(state.league_state.free_agent_player_ids) - {player_id}) | {drop_player_id}
        )),
    )
    counts = dict(state.moves_used)
    counts[franchise_id] = counts.get(franchise_id, 0) + 1
    return replace(state, league_state=league, moves_used=tuple(sorted(counts.items())))
