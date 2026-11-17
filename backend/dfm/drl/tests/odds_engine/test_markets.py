import unittest

from backend.dfm.drl.core.odds_engine.engine import OddsEngine
from backend.dfm.drl.core.odds_engine.models import (
    ConfidenceTier,
    EvidenceStatus,
    MarketSource,
    MarketType,
)


def verified_source(source_id="official-team-list"):
    return MarketSource(
        source_id=source_id,
        category="official_team_news",
        evidence_status=EvidenceStatus.VERIFIED,
        confidence_tier=ConfidenceTier.VERIFIED,
        summary="Verified source supplied by the competition data adapter",
    )


def rumour_source():
    return MarketSource(
        source_id="unconfirmed-social-post",
        category="transfer_rumour",
        evidence_status=EvidenceStatus.RUMOUR,
        confidence_tier=ConfidenceTier.RUMOUR,
        summary="Unconfirmed information; indicative analysis only",
    )


class MarketTests(unittest.TestCase):
    def setUp(self):
        self.engine = OddsEngine()

    def test_head_to_head_probabilities_and_prices(self):
        result = self.engine.calculate_head_to_head(
            market_id="match-1",
            home_franchise_id="home",
            home_franchise_name="Home",
            home_projection=100.0,
            away_franchise_id="away",
            away_franchise_name="Away",
            away_projection=80.0,
            source=verified_source(),
        )
        self.assertIs(result.market_type, MarketType.HEAD_TO_HEAD)
        self.assertTrue(result.is_official)
        self.assertAlmostEqual(sum(x.probability for x in result.outcomes), 1.0)
        self.assertGreater(result.outcomes[0].probability, result.outcomes[1].probability)

    def test_rumour_calculation_is_indicative_not_official(self):
        result = self.engine.calculate_head_to_head(
            market_id="match-2",
            home_franchise_id="home",
            home_franchise_name="Home",
            home_projection=100.0,
            away_franchise_id="away",
            away_franchise_name="Away",
            away_projection=90.0,
            source=rumour_source(),
        )
        self.assertFalse(result.is_official)

    def test_premiership_requires_all_17_clubs(self):
        ratings = {f"club-{index}": float(index) for index in range(17)}
        labels = {club_id: club_id.upper() for club_id in ratings}
        result = self.engine.calculate_premiership(
            market_id="season-2027",
            club_power_ratings=ratings,
            club_labels=labels,
            source=verified_source(),
        )
        self.assertEqual(len(result.outcomes), 17)
        self.assertAlmostEqual(sum(x.probability for x in result.outcomes), 1.0)
        with self.assertRaises(ValueError):
            self.engine.calculate_premiership(
                market_id="incomplete",
                club_power_ratings=dict(list(ratings.items())[:16]),
                club_labels=dict(list(labels.items())[:16]),
                source=verified_source(),
            )

    def test_man_of_the_match_market(self):
        scores = {"p1": 80.0, "p2": 65.0, "p3": 55.0}
        labels = {"p1": "Player One", "p2": "Player Two", "p3": "Player Three"}
        result = self.engine.calculate_man_of_the_match(
            market_id="match-3-motm",
            player_projected_scores=scores,
            player_labels=labels,
            source=verified_source(),
        )
        self.assertEqual(result.market_type, MarketType.MAN_OF_THE_MATCH)
        self.assertAlmostEqual(sum(x.probability for x in result.outcomes), 1.0)

    def test_market_audit_records_only_verified_price_movements(self):
        before = self.engine.calculate_head_to_head(
            market_id="match-4",
            home_franchise_id="home",
            home_franchise_name="Home",
            home_projection=100.0,
            away_franchise_id="away",
            away_franchise_name="Away",
            away_projection=90.0,
            source=verified_source("team-sheet-v1"),
        )
        after = self.engine.calculate_head_to_head(
            market_id="match-4",
            home_franchise_id="home",
            home_franchise_name="Home",
            home_projection=115.0,
            away_franchise_id="away",
            away_franchise_name="Away",
            away_projection=90.0,
            source=verified_source("official-late-mail"),
        )
        events = self.engine.create_price_movements(before, after, revision=2)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].revision, 2)
        self.assertEqual(events[0].confidence_tier, ConfidenceTier.VERIFIED)
        self.assertEqual(
            events,
            self.engine.create_price_movements(before, after, revision=2),
        )

        indicative = self.engine.calculate_head_to_head(
            market_id="match-4",
            home_franchise_id="home",
            home_franchise_name="Home",
            home_projection=130.0,
            away_franchise_id="away",
            away_franchise_name="Away",
            away_projection=90.0,
            source=rumour_source(),
        )
        with self.assertRaises(ValueError):
            self.engine.create_price_movements(before, indicative, revision=3)

    def test_market_selection_set_cannot_change_during_revision(self):
        first = self.engine.calculate_head_to_head(
            market_id="match-5",
            home_franchise_id="home",
            home_franchise_name="Home",
            home_projection=100.0,
            away_franchise_id="away",
            away_franchise_name="Away",
            away_projection=90.0,
            source=verified_source("v1"),
        )
        changed = self.engine.calculate_head_to_head(
            market_id="match-5",
            home_franchise_id="home2",
            home_franchise_name="Home 2",
            home_projection=100.0,
            away_franchise_id="away2",
            away_franchise_name="Away 2",
            away_projection=90.0,
            source=verified_source("v2"),
        )
        with self.assertRaises(ValueError):
            self.engine.create_price_movements(first, changed, revision=2)


if __name__ == "__main__":
    unittest.main()
