"""Immutable domain models for DRL fantasy-market calculations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class MarketType(str, Enum):
    HEAD_TO_HEAD = "head_to_head"
    PREMIERSHIP = "premiership"
    MAN_OF_THE_MATCH = "man_of_the_match"


class ConfidenceTier(str, Enum):
    RUMOUR = "rumour"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERIFIED = "verified"


class EvidenceStatus(str, Enum):
    RUMOUR = "rumour"
    UNVERIFIED = "unverified"
    CORROBORATED = "corroborated"
    VERIFIED = "verified"


@dataclass(frozen=True, slots=True)
class MarketSource:
    """Provenance attached to every calculation and subsequent price revision."""

    source_id: str
    category: str
    evidence_status: EvidenceStatus
    confidence_tier: ConfidenceTier
    summary: str

    def __post_init__(self) -> None:
        for name in ("source_id", "category", "summary"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be blank")
        if self.evidence_status is EvidenceStatus.RUMOUR:
            if self.confidence_tier is not ConfidenceTier.RUMOUR:
                raise ValueError("Rumour evidence must use the rumour confidence tier")

    @property
    def eligible_for_official_market(self) -> bool:
        """Only verified evidence can produce an official market revision."""
        return (
            self.evidence_status is EvidenceStatus.VERIFIED
            and self.confidence_tier is ConfidenceTier.VERIFIED
        )


@dataclass(frozen=True, slots=True)
class MarketOutcome:
    selection_id: str
    label: str
    probability: float
    decimal_price: float


@dataclass(frozen=True, slots=True)
class MarketCalculation:
    market_type: MarketType
    market_id: str
    outcomes: tuple[MarketOutcome, ...]
    source: MarketSource
    model_version: str
    is_official: bool

    def __post_init__(self) -> None:
        if not self.market_id.strip():
            raise ValueError("market_id must not be blank")
        if not self.model_version.strip():
            raise ValueError("model_version must not be blank")
        if len(self.outcomes) < 2:
            raise ValueError("a market must contain at least two outcomes")
        if any(item.probability <= 0 or item.probability >= 1 for item in self.outcomes):
            raise ValueError("market outcome probabilities must be between zero and one")
        total = sum(item.probability for item in self.outcomes)
        if abs(total - 1.0) > 1e-8:
            raise ValueError("market outcome probabilities must sum to one")
        if self.is_official != self.source.eligible_for_official_market:
            raise ValueError("official status must match verified source provenance")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["market_type"] = self.market_type.value
        payload["source"]["evidence_status"] = self.source.evidence_status.value
        payload["source"]["confidence_tier"] = self.source.confidence_tier.value
        return payload


@dataclass(frozen=True, slots=True)
class MarketPriceMovement:
    """Append-only audit record; one record represents one selection movement."""

    event_id: str
    idempotency_key: str
    market_type: MarketType
    market_id: str
    selection_id: str
    previous_probability: float
    revised_probability: float
    previous_decimal_price: float
    revised_decimal_price: float
    trigger_category: str
    trigger_summary: str
    confidence_tier: ConfidenceTier
    source_id: str
    model_version: str
    revision: int

    def __post_init__(self) -> None:
        if self.revision < 1:
            raise ValueError("revision must be positive")
        if self.confidence_tier is ConfidenceTier.RUMOUR:
            raise ValueError("rumours cannot create official price movement records")
        if not self.idempotency_key or not self.event_id:
            raise ValueError("audit identifiers must not be blank")
