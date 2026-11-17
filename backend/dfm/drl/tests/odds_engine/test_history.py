import unittest

from backend.dfm.drl.core.odds_engine.engine import OddsEngine
from backend.dfm.drl.core.odds_engine.models import (
    ConfidenceTier,
    EvidenceStatus,
    MarketPriceMovement,
    MarketSource,
    MarketType,
)
from backend.dfm.drl.core.odds_engine.services.history import MarketHistoryService


class InMemoryAppendOnlyRepository:
    def __init__(self):
        self.events = {}

    def append_once(self, event: MarketPriceMovement) -> bool:
        if event.idempotency_key in self.events:
            return False
        self.events[event.idempotency_key] = event
        return True

    def list_for_market(self, market_type: str, market_id: str):
        return tuple(
            event for event in self.events.values()
            if event.market_type.value == market_type and event.market_id == market_id
        )


class HistoryTests(unittest.TestCase):
    def test_history_service_is_idempotent(self):
        source_a = MarketSource(
            "v1", "team_news", EvidenceStatus.VERIFIED, ConfidenceTier.VERIFIED, "Initial"
        )
        source_b = MarketSource(
            "v2", "late_mail", EvidenceStatus.VERIFIED, ConfidenceTier.VERIFIED, "Updated"
        )
        engine = OddsEngine()
        before = engine.calculate_head_to_head(
            market_id="m1", home_franchise_id="h", home_franchise_name="Home",
            home_projection=90, away_franchise_id="a", away_franchise_name="Away",
            away_projection=90, source=source_a,
        )
        after = engine.calculate_head_to_head(
            market_id="m1", home_franchise_id="h", home_franchise_name="Home",
            home_projection=110, away_franchise_id="a", away_franchise_name="Away",
            away_projection=90, source=source_b,
        )
        events = engine.create_price_movements(before, after, revision=2)
        repository = InMemoryAppendOnlyRepository()
        service = MarketHistoryService(repository)
        self.assertEqual(service.record(events), 2)
        self.assertEqual(service.record(events), 0)
        self.assertEqual(
            len(service.get_market_history(MarketType.HEAD_TO_HEAD.value, "m1")), 2
        )


if __name__ == "__main__":
    unittest.main()
