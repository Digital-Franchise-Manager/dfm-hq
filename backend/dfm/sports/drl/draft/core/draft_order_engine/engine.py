"""Linear and snake draft order generation."""
from __future__ import annotations

from collections.abc import Sequence

from .models import DraftOrderType, DraftPickSlot


class DraftOrderEngine:
    """Generate deterministic pick slots from a commissioner-set order."""

    @staticmethod
    def generate_order(
        franchise_order: Sequence[str],
        rounds: int,
        draft_type: DraftOrderType | str,
    ) -> tuple[DraftPickSlot, ...]:
        franchises = tuple(franchise_order)
        if not franchises:
            raise ValueError("at least one franchise is required")
        if any(not isinstance(item, str) or not item.strip() for item in franchises):
            raise ValueError("franchise IDs must be non-empty strings")
        if len(set(franchises)) != len(franchises):
            raise ValueError("franchise order cannot contain duplicate franchises")
        if isinstance(rounds, bool) or not isinstance(rounds, int) or rounds < 1:
            raise ValueError("rounds must be a positive integer")
        try:
            selected_type = DraftOrderType(draft_type)
        except ValueError as exc:
            raise ValueError("draft_type must be 'linear' or 'snake'") from exc

        slots: list[DraftPickSlot] = []
        overall_pick = 1
        for round_number in range(1, rounds + 1):
            round_order = franchises
            if selected_type is DraftOrderType.SNAKE and round_number % 2 == 0:
                round_order = tuple(reversed(franchises))
            for pick_in_round, franchise_id in enumerate(round_order, start=1):
                slots.append(
                    DraftPickSlot(
                        pick_number=overall_pick,
                        round_number=round_number,
                        pick_in_round=pick_in_round,
                        franchise_id=franchise_id,
                    )
                )
                overall_pick += 1
        return tuple(slots)

    @classmethod
    def get_pick(
        cls,
        franchise_order: Sequence[str],
        rounds: int,
        draft_type: DraftOrderType | str,
        pick_number: int,
    ) -> DraftPickSlot:
        if isinstance(pick_number, bool) or not isinstance(pick_number, int) or pick_number < 1:
            raise ValueError("pick_number must be a positive integer")
        order = cls.generate_order(franchise_order, rounds, draft_type)
        if pick_number > len(order):
            raise ValueError("pick_number exceeds the configured draft")
        return order[pick_number - 1]
