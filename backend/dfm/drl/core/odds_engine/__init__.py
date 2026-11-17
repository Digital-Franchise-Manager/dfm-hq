"""Independent DRL Odds Engine.

This package owns DRL fantasy-market probability and decimal-price calculations.
It is deliberately independent of Newsroom, Match Centre and the fantasy scoring
engine. Consumers integrate through the public service boundary.
"""

from .engine import OddsEngine
from .models import (
    ConfidenceTier,
    EvidenceStatus,
    MarketCalculation,
    MarketOutcome,
    MarketSource,
    MarketType,
)

__all__ = [
    "ConfidenceTier",
    "EvidenceStatus",
    "MarketCalculation",
    "MarketOutcome",
    "MarketSource",
    "MarketType",
    "OddsEngine",
]
