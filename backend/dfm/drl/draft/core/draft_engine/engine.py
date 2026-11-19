"""Draft lifecycle, pick validation and duplicate-selection prevention."""
from __future__ import annotations

from dataclasses import replace
from collections.abc import Iterable

from backend.dfm.drl.draft.core.draft_order_engine.engine import DraftOrderEngine
from backend.dfm.drl.draft.core.draft_order_engine.models import DraftOrderType
from .models import DraftPick, DraftSession, DraftStatus


class DraftEngine:
    """Pure draft state transitions; no database or HTTP dependencies."""

    @staticmethod
    def create_draft(
        franchise_order: Iterable[str],
        player_pool: Iterable[str],
        rounds: int,
        draft_type: DraftOrderType | str,
    ) -> DraftSession:
        franchises = tuple(franchise_order)
        players = tuple(player_pool)
        if not players:
            raise ValueError("player pool cannot be empty")
        if any(not isinstance(item, str) or not item.strip() for item in players):
            raise ValueError("player IDs must be non-empty strings")
        if len(set(players)) != len(players):
            raise ValueError("player pool cannot contain duplicate player IDs")
        # Generate once here to validate franchise order, round count and type.
        DraftOrderEngine.generate_order(franchises, rounds, draft_type)
        selected_type = DraftOrderType(draft_type)
        return DraftSession(franchises, players, rounds, selected_type)

    def make_pick(
        self,
        session: DraftSession,
        franchise_id: str,
        player_id: str,
    ) -> DraftSession:
        if session.status is DraftStatus.COMPLETED:
            raise ValueError("draft is already completed")
        if session.remaining_picks <= 0:
            raise ValueError("draft has no remaining picks")
        if franchise_id not in session.franchise_order:
            raise ValueError("franchise is not part of this draft")
        if player_id not in session.player_pool:
            raise ValueError("player is not in this draft's player pool")
        if player_id not in session.available_player_ids:
            raise ValueError("player has already been selected")

        next_pick_number = len(session.picks) + 1
        slot = DraftOrderEngine.get_pick(
            session.franchise_order, session.rounds, session.draft_type, next_pick_number
        )
        if franchise_id != slot.franchise_id:
            raise ValueError(
                f"franchise {slot.franchise_id} is entitled to pick {next_pick_number}"
            )

        pick = DraftPick(
            pick_number=slot.pick_number,
            round_number=slot.round_number,
            franchise_id=franchise_id,
            player_id=player_id,
        )
        picks = (*session.picks, pick)
        status = DraftStatus.COMPLETED if len(picks) == session.total_picks else DraftStatus.IN_PROGRESS
        return replace(session, picks=picks, status=status)

    @staticmethod
    def get_next_pick(session: DraftSession):
        if session.remaining_picks <= 0:
            return None
        return DraftOrderEngine.get_pick(
            session.franchise_order,
            session.rounds,
            session.draft_type,
            len(session.picks) + 1,
        )
