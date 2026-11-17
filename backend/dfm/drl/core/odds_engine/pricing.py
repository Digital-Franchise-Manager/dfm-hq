"""Decimal-price conversion and market outcome construction."""

from __future__ import annotations

import math
from collections.abc import Sequence

from .models import MarketOutcome


def probability_to_decimal_price(probability: float) -> float:
    """Convert a fair probability to a fair decimal price (1 / probability)."""
    if not math.isfinite(probability) or not 0 < probability < 1:
        raise ValueError("probability must be finite and strictly between zero and one")
    return round(1.0 / probability, 4)


def build_outcomes(
    selections: Sequence[tuple[str, str]],
    probabilities: Sequence[float],
) -> tuple[MarketOutcome, ...]:
    if len(selections) != len(probabilities) or len(selections) < 2:
        raise ValueError("selections and probabilities must have matching lengths")
    if len({selection_id for selection_id, _ in selections}) != len(selections):
        raise ValueError("selection identifiers must be unique")
    if any(not selection_id.strip() or not label.strip() for selection_id, label in selections):
        raise ValueError("selection identifiers and labels must not be blank")
    total = math.fsum(probabilities)
    if abs(total - 1.0) > 1e-8:
        raise ValueError("probabilities must sum to one")

    return tuple(
        MarketOutcome(
            selection_id=selection_id,
            label=label,
            probability=probability,
            decimal_price=probability_to_decimal_price(probability),
        )
        for (selection_id, label), probability in zip(selections, probabilities, strict=True)
    )
