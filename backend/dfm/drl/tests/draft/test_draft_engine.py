"""Tests for Draft Mode lifecycle and player selection."""
import unittest

from backend.dfm.drl.draft.core.draft_engine import DraftEngine, DraftStatus


class DraftEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = DraftEngine()
        self.session = self.engine.create_draft(
            ("A", "B", "C"), ("p1", "p2", "p3", "p4", "p5", "p6"),
            rounds=2, draft_type="snake",
        )

    def test_creates_ready_draft_and_exposes_first_pick(self):
        self.assertEqual(self.session.status, DraftStatus.READY)
        self.assertEqual(self.session.remaining_picks, 6)
        self.assertEqual(self.engine.get_next_pick(self.session).franchise_id, "A")

    def test_makes_picks_in_snake_order(self):
        session = self.session
        expected = ("A", "B", "C", "C", "B", "A")
        for index, franchise in enumerate(expected):
            session = self.engine.make_pick(session, franchise, f"p{index + 1}")
        self.assertEqual(session.status, DraftStatus.COMPLETED)
        self.assertEqual(session.remaining_picks, 0)
        self.assertIsNone(self.engine.get_next_pick(session))

    def test_rejects_pick_from_wrong_franchise(self):
        with self.assertRaisesRegex(ValueError, "entitled to pick 1"):
            self.engine.make_pick(self.session, "B", "p1")

    def test_prevents_duplicate_player_selection(self):
        session = self.engine.make_pick(self.session, "A", "p1")
        with self.assertRaisesRegex(ValueError, "already been selected"):
            self.engine.make_pick(session, "B", "p1")

    def test_rejects_unknown_franchise_or_player(self):
        with self.assertRaisesRegex(ValueError, "not part"):
            self.engine.make_pick(self.session, "X", "p1")
        with self.assertRaisesRegex(ValueError, "player pool"):
            self.engine.make_pick(self.session, "A", "missing")

    def test_rejects_invalid_player_pool(self):
        with self.assertRaisesRegex(ValueError, "duplicate player"):
            self.engine.create_draft(("A",), ("p1", "p1"), 1, "linear")

    def test_completed_draft_cannot_accept_more_picks(self):
        session = self.session
        for index, franchise in enumerate(("A", "B", "C", "C", "B", "A")):
            session = self.engine.make_pick(session, franchise, f"p{index + 1}")
        with self.assertRaisesRegex(ValueError, "already completed"):
            self.engine.make_pick(session, "A", "p1")


if __name__ == "__main__":
    unittest.main()
