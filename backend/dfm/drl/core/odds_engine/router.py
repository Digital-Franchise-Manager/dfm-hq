"""Authenticated FastAPI router factory for the DRL Odds Engine.

The application must inject its own authenticated-principal dependency and engine
provider. There is intentionally no default unauthenticated router or database
client in this module.
"""

from typing import Any, Callable

from .engine import OddsEngine
from .models import ConfidenceTier, EvidenceStatus, MarketSource


def create_router(
    *,
    authorization_dependency: Callable[..., Any],
    engine_dependency: Callable[..., OddsEngine],
):
    """Build routes only when the host supplies mandatory authorization."""
    if authorization_dependency is None or engine_dependency is None:
        raise ValueError("authorization and engine dependencies are required")

    from fastapi import APIRouter, Depends
    from pydantic import BaseModel, Field

    class SourcePayload(BaseModel):
        source_id: str = Field(min_length=1)
        category: str = Field(min_length=1)
        evidence_status: EvidenceStatus
        confidence_tier: ConfidenceTier
        summary: str = Field(min_length=1)

        def to_domain(self) -> MarketSource:
            return MarketSource(
                source_id=self.source_id,
                category=self.category,
                evidence_status=self.evidence_status,
                confidence_tier=self.confidence_tier,
                summary=self.summary,
            )

    class HeadToHeadPayload(BaseModel):
        market_id: str = Field(min_length=1)
        home_franchise_id: str = Field(min_length=1)
        home_franchise_name: str = Field(min_length=1)
        home_projection: float = Field(ge=0, allow_inf_nan=False)
        away_franchise_id: str = Field(min_length=1)
        away_franchise_name: str = Field(min_length=1)
        away_projection: float = Field(ge=0, allow_inf_nan=False)
        source: SourcePayload
        score_margin_scale: float = Field(default=35.0, gt=0, allow_inf_nan=False)

    class PremiershipPayload(BaseModel):
        market_id: str = Field(min_length=1)
        club_power_ratings: dict[str, float]
        club_labels: dict[str, str]
        source: SourcePayload
        temperature: float = Field(default=1.0, gt=0, allow_inf_nan=False)

    class ManOfTheMatchPayload(BaseModel):
        market_id: str = Field(min_length=1)
        player_projected_scores: dict[str, float]
        player_labels: dict[str, str]
        source: SourcePayload
        temperature: float = Field(default=10.0, gt=0, allow_inf_nan=False)

    router = APIRouter(prefix="/api/dfm/drl/odds", tags=["DRL Odds Engine"])

    @router.post("/head-to-head")
    def head_to_head(
        payload: HeadToHeadPayload,
        _principal: Any = Depends(authorization_dependency),
        engine: OddsEngine = Depends(engine_dependency),
    ):
        result = engine.calculate_head_to_head(
            market_id=payload.market_id,
            home_franchise_id=payload.home_franchise_id,
            home_franchise_name=payload.home_franchise_name,
            home_projection=payload.home_projection,
            away_franchise_id=payload.away_franchise_id,
            away_franchise_name=payload.away_franchise_name,
            away_projection=payload.away_projection,
            source=payload.source.to_domain(),
            score_margin_scale=payload.score_margin_scale,
        )
        return result.to_dict()

    @router.post("/premiership")
    def premiership(
        payload: PremiershipPayload,
        _principal: Any = Depends(authorization_dependency),
        engine: OddsEngine = Depends(engine_dependency),
    ):
        result = engine.calculate_premiership(
            market_id=payload.market_id,
            club_power_ratings=payload.club_power_ratings,
            club_labels=payload.club_labels,
            source=payload.source.to_domain(),
            temperature=payload.temperature,
        )
        return result.to_dict()

    @router.post("/man-of-the-match")
    def man_of_the_match(
        payload: ManOfTheMatchPayload,
        _principal: Any = Depends(authorization_dependency),
        engine: OddsEngine = Depends(engine_dependency),
    ):
        result = engine.calculate_man_of_the_match(
            market_id=payload.market_id,
            player_projected_scores=payload.player_projected_scores,
            player_labels=payload.player_labels,
            source=payload.source.to_domain(),
            temperature=payload.temperature,
        )
        return result.to_dict()

    return router
