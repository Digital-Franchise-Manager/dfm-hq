"""Tests for the shared DRL six-position vocabulary and mode integration."""

import unittest

from backend.dfm.drl.core.player_positions import (
    POSITIONAL_XIII, POSITION_CODES, validate_player_positions, validate_position,
)
from backend.dfm.drl.classic.core.awards_engine.models import PlayerCandidate as ClassicPlayerCandidate
from backend.dfm.drl.draft.core.awards_engine.models import PlayerCandidate as DraftPlayerCandidate


class SharedPlayerPositionTests(unittest.TestCase):
    def test_canonical_six_positions_and_positional_xiii(self):
        self.assertEqual(POSITIONAL_XIII, (
            ("WFB", 3), ("CTR", 2), ("HLF", 2), ("EDG", 2), ("MID", 3), ("HOK", 1),
        ))
        self.assertEqual(POSITION_CODES, ("WFB", "CTR", "HLF", "EDG", "MID", "HOK"))
        self.assertEqual(sum(slots for _, slots in POSITIONAL_XIII), 13)

    def test_all_six_position_codes_are_accepted(self):
        for position in POSITION_CODES:
            with self.subTest(position=position):
                validate_position(position)

    def test_unknown_and_malformed_codes_are_rejected(self):
        for position in ("FB", "LOCK", "wfb", " WFB", "", None):
            with self.subTest(position=position):
                with self.assertRaises(ValueError):
                    validate_position(position)

    def test_primary_and_secondary_positions_are_validated(self):
        validate_player_positions("WFB", ("CTR", "HLF"))
        with self.assertRaises(ValueError):
            validate_player_positions("LOCK", ())
        with self.assertRaises(ValueError):
            validate_player_positions("WFB", ("LOCK",))

    def test_duplicate_or_overlapping_secondary_positions_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_player_positions("WFB", ("CTR", "CTR"))
        with self.assertRaises(ValueError):
            validate_player_positions("WFB", ("WFB",))

    def test_primary_position_can_be_required_at_roster_boundary(self):
        validate_player_positions("HOK", (), require_primary=True)
        with self.assertRaises(ValueError):
            validate_player_positions("", (), require_primary=True)

    def test_classic_and_draft_candidates_use_shared_validation(self):
        for candidate_type in (ClassicPlayerCandidate, DraftPlayerCandidate):
            with self.subTest(candidate_type=candidate_type.__module__):
                candidate_type("p1", "Player One", 10, "f1", "c1", "WFB", ("CTR",))
                with self.assertRaises(ValueError):
                    candidate_type("p2", "Player Two", 10, "f1", "c1", "LOCK", ())


if __name__ == "__main__":
    unittest.main()
