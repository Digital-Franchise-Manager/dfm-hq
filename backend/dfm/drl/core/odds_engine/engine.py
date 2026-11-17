"""Public orchestration API for the independent DRL Odds Engine."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from .calculations import (
    calculate_head_to_head_probabilities,
    calculate_man_of_the_match_probabilities,
    calculate_premiership_probabilities,
)
from .models import (
    MarketCalculation,
    MarketPriceMovement,
    MarketSource,
    MarketType,
)
from .pricing import build_outcomes

MODEL_VERSION = "drl-odds-0.1.0"


class OddsEngine:
    """Calculate DRL fantasy-market probabilities without database coupling."""

    model_version = MODEL_VERSION

    def calculate_head_to_head(
        self,
        *,
        market_id: str,
        home_franchise_id: str,
        home_franchise_name: str,
        home_projection: float,
        away_franchise_id: str,
        away_franchise_name: str,
        away_projection: float,
        source: MarketSource,
        score_margin_scale: float = 35.0,
    ) -> MarketCalculation:
        if home_franchise_id == away_franchise_id:
            raise ValueError("a franchise cannot play against itself")
        if home_projection < 0 or away_projection < 0:
            raise ValueError("fantasy score projections cannot be negative")
        probabilities = calculate_head_to_head_probabilities(
            home_projection, away_projection, score_margin_scale
        )
        return MarketCalculation(
            market_type=MarketType.HEAD_TO_HEAD,
            market_id=market_id,
            outcomes=build_outcomes(
                ((home_franchise_id, home_franchise_name), (away_franchise_id, away_franchise_name)),
                probabilities,
            ),
            source=source,
            model_version=self.model_version,
            is_official=source.eligible_for_official_market,
        )

    def calculate_premiership(
        self,
        *,
        market_id: str,
        club_power_ratings: Mapping[str, float],
        club_labels: Mapping[str, str],
        source: MarketSource,
        temperature: float = 1.0,
    ) -> MarketCalculation:
        if set(club_power_ratings) != set(club_labels):
            raise ValueError("club ratings and labels must contain identical club identifiers")
        probabilities = calculate_premiership_probabilities(club_power_ratings, temperature)
        outcomes = build_outcomes(
            tuple((club_id, club_labels[club_id]) for club_id in probabilities),
            tuple(probabilities.values()),
        )
        return MarketCalculation(
            market_type=MarketType.PREMIERSHIP,
            market_id=market_id,
            outcomes=outcomes,
            source=source,
            model_version=self.model_version,
            is_official=source.eligible_for_official_market,
        )

    def calculate_man_of_the_match(
        self,
        *,
        market_id: str,
        player_projected_scores: Mapping[str, float],
        player_labels: Mapping[str, str],
        source: MarketSource,
        temperature: float = 10.0,
    ) -> MarketCalculation:
        if set(player_projected_scores) != set(player_labels):
            raise ValueError("player projections and labels must contain identical player identifiers")
        probabilities = calculate_man_of_the_match_probabilities(
            player_projected_scores, temperature
        )
        outcomes = build_outcomes(
            tuple((player_id, player_labels[player_id]) for player_id in probabilities),
            tuple(probabilities.values()),
        )
        return MarketCalculation(
            market_type=MarketType.MAN_OF_THE_MATCH,
            market_id=market_id,
            outcomes=outcomes,
            source=source,
            model_version=self.model_version,
            is_official=source.eligible_for_official_market,
        )

    @staticmethod
    def create_price_movements(
        previous: MarketCalculation,
        revised: MarketCalculation,
        *,
        revision: int,
    ) -> tuple[MarketPriceMovement, ...]:
        """Create deterministic audit events for verified, official price changes."""
        if previous.market_type is not revised.market_type or previous.market_id != revised.market_id:
            raise ValueError("market history cannot cross market boundaries")
        if not previous.is_official or not revised.is_official:
            raise ValueError("only verified official calculations can move official prices")
        if revision < 2:
            raise ValueError("a movement revision must be at least two")
        previous_by_id = {item.selection_id: item for item in previous.outcomes}
        revised_by_id = {item.selection_id: item for item in revised.outcomes}
        if previous_by_id.keys() != revised_by_id.keys():
            raise ValueError("market selections cannot change within a price revision")

        movements: list[MarketPriceMovement] = []
        source = revised.source
        for selection_id in sorted(previous_by_id):
            old = previous_by_id[selection_id]
            new = revised_by_id[selection_id]
            if (
                abs(old.probability - new.probability) <= 1e-12
                and abs(old.decimal_price - new.decimal_price) <= 1e-12
            ):
                continue
            material = {
                "market_type": revised.market_type.value,
                "market_id": revised.market_id,
                "selection_id": selection_id,
                "revision": revision,
                "source_id": source.source_id,
                "model_version": revised.model_version,
            }
            key = hashlib.sha256(
                json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            movements.append(
                MarketPriceMovement(
                    event_id=key[:24],
                    idempotency_key=key,
                    market_type=revised.market_type,
                    market_id=revised.market_id,
                    selection_id=selection_id,
                    previous_probability=old.probability,
                    revised_probability=new.probability,
                    previous_decimal_price=old.decimal_price,
                    revised_decimal_price=new.decimal_price,
                    trigger_category=source.category,
                    trigger_summary=source.summary,
                    confidence_tier=source.confidence_tier,
                    source_id=source.source_id,
                    model_version=revised.model_version,
                    revision=revision,
                )
            )
        return tuple(movements)
