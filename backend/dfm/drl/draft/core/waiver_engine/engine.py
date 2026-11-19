"""Draft waiver and free-agency lifecycle."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from backend.dfm.drl.draft.core.lockout_engine import DraftLockoutEngine, PlayerLockoutContext
from backend.dfm.drl.draft.core.trade_engine.models import DraftLeagueState
from .models import DraftWaiverState, WaiverEntry, WaiverEntryStatus, WaiverSettings
from .priority import validate_priority
from .claims import cancel_claim, process_waiver_entry, submit_claim
from .free_agents import add_free_agent


class DraftWaiverEngine:
    """Manage player drops, waiver claims, priority and free-agent acquisition."""

    def __init__(self, lockout_engine: DraftLockoutEngine | None = None) -> None:
        self.lockout_engine = lockout_engine or DraftLockoutEngine()

    @staticmethod
    def create_state(league_state: DraftLeagueState, waiver_priority: tuple[str, ...]) -> DraftWaiverState:
        validate_priority(waiver_priority, tuple(item.franchise_id for item in league_state.rosters))
        return DraftWaiverState(league_state=league_state, waiver_priority=waiver_priority)

    def drop_player(
        self, state: DraftWaiverState, settings: WaiverSettings, *,
        franchise_id: str, player_id: str, lockout_context: PlayerLockoutContext,
        round_first_kickoff: datetime, now: datetime,
    ) -> DraftWaiverState:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        if lockout_context.player_id != player_id:
            raise ValueError("lockout context player does not match dropped player")
        roster = state.league_state.roster_for(franchise_id)
        if player_id not in roster.player_ids:
            raise ValueError("player is not owned by this franchise")
        if any(item.player_id == player_id and item.status is WaiverEntryStatus.OPEN for item in state.entries):
            raise ValueError("player is already on waivers")
        self.lockout_engine.assert_player_tradeable(player=lockout_context,
                                                    round_first_kickoff=round_first_kickoff, now=now)
        updated_rosters = tuple(
            replace(item, player_ids=tuple(pid for pid in item.player_ids if pid != player_id))
            if item.franchise_id == franchise_id else item
            for item in state.league_state.rosters
        )
        # A dropped player temporarily occupies an empty roster slot until a claim resolves.
        league = replace(
            state.league_state, rosters=updated_rosters,
            waiver_player_ids=tuple(sorted((*state.league_state.waiver_player_ids, player_id))),
        )
        entry = WaiverEntry(player_id, franchise_id, now.astimezone(timezone.utc),
                            (now + settings.waiver_period).astimezone(timezone.utc))
        return replace(state, league_state=league, entries=(*state.entries, entry))

    def submit_claim(self, state: DraftWaiverState, settings: WaiverSettings, **kwargs) -> DraftWaiverState:
        return submit_claim(state, settings, **kwargs)

    def cancel_claim(self, state: DraftWaiverState, claim_id: str, franchise_id: str) -> DraftWaiverState:
        return cancel_claim(state, claim_id, franchise_id)

    def process_waiver(
        self, state: DraftWaiverState, player_id: str, now: datetime,
        lockout_contexts: dict[str, PlayerLockoutContext], round_first_kickoff: datetime,
        settings: WaiverSettings,
    ) -> DraftWaiverState:
        return process_waiver_entry(state, player_id, now, lockout_contexts,
                                    round_first_kickoff, settings, self.lockout_engine)

    def add_free_agent(
        self, state: DraftWaiverState, settings: WaiverSettings, **kwargs
    ) -> DraftWaiverState:
        return add_free_agent(state, settings, lockout_engine=self.lockout_engine, **kwargs)
