import unittest

from backend.dfm.sports.drl.classic.core.squad_engine.engine import ClassicSquadEngine
from backend.dfm.sports.drl.classic.core.squad_engine.models import (
    ClassicPlayer,
    ClassicSquadSelection,
)
from backend.dfm.sports.drl.core.player_positions import POSITIONAL_XIII, POSITION_CODES


def build_squad():
    players = []
    starting_xiii = {}
    roster = []
    for position, count in POSITIONAL_XIII:
        assigned = []
        for index in range(count):
            player_id = f"{position.lower()}-{index}"
            assigned.append(player_id)
            roster.append(player_id)
            players.append(
                ClassicPlayer(player_id, position, selected_position=position, fantasy_points=10)
            )
        starting_xiii[position] = tuple(assigned)

    interchange = []
    for index, position in enumerate(("WFB", "CTR", "MID", "HOK")):
        player_id = f"int-{index}"
        interchange.append(player_id)
        roster.append(player_id)
        players.append(
            ClassicPlayer(player_id, position, selected_position=position, fantasy_points=5)
        )

    emergencies = []
    for index, position in enumerate(("WFB", "CTR", "MID", "HOK")):
        player_id = f"emg-{index}"
        emergencies.append(player_id)
        roster.append(player_id)
        players.append(
            ClassicPlayer(player_id, position, selected_position=position, fantasy_points=3 + index)
        )

    selection = ClassicSquadSelection(
        roster_player_ids=tuple(roster),
        starting_xiii=starting_xiii,
        interchange_player_ids=tuple(interchange),
        emergency_player_ids=tuple(emergencies),
        emergency_assignments={},
    )
    return selection, players


class ClassicSquadEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = ClassicSquadEngine()
        self.selection, self.players = build_squad()

    def test_valid_21_player_squad(self):
        self.engine.validate_squad(self.selection, self.players)

    def test_classic_squad_requires_exactly_21_players(self):
        selection = ClassicSquadSelection(
            roster_player_ids=self.selection.roster_player_ids[:-1],
            starting_xiii=self.selection.starting_xiii,
            interchange_player_ids=self.selection.interchange_player_ids,
            emergency_player_ids=self.selection.emergency_player_ids,
            emergency_assignments={},
        )
        with self.assertRaisesRegex(ValueError, "exactly 21"):
            self.engine.validate_squad(selection, self.players[:-1])

    def test_starting_xiii_must_follow_six_position_allocation(self):
        altered = dict(self.selection.starting_xiii)
        altered["WFB"] = altered["WFB"][:-1]
        selection = ClassicSquadSelection(
            self.selection.roster_player_ids,
            altered,
            self.selection.interchange_player_ids,
            self.selection.emergency_player_ids,
            {},
        )
        with self.assertRaisesRegex(ValueError, "WFB"):
            self.engine.validate_squad(selection, self.players)

    def test_squad_groups_must_be_disjoint_and_complete(self):
        selection = ClassicSquadSelection(
            self.selection.roster_player_ids,
            self.selection.starting_xiii,
            self.selection.interchange_player_ids,
            self.selection.emergency_player_ids[:-1],
            {},
        )
        with self.assertRaisesRegex(ValueError, "exactly four emergency"):
            self.engine.validate_squad(selection, self.players)

    def test_player_selected_position_must_be_eligible(self):
        with self.assertRaisesRegex(ValueError, "eligible positions"):
            ClassicPlayer("bad", "WFB", selected_position="MID")

    def test_scores_starting_xiii_and_all_four_interchange_players(self):
        result = self.engine.score_squad(self.selection, self.players)
        self.assertEqual(result.total_points, 150)
        self.assertEqual(len(result.replacements), 0)
        self.assertEqual(result.unused_emergency_player_ids, self.selection.emergency_player_ids)
        self.assertEqual(set(result.position_points), set(POSITION_CODES))

    def test_manual_emergency_replaces_unavailable_starter(self):
        unavailable_id = self.selection.starting_xiii["WFB"][0]
        emergency_id = self.selection.emergency_player_ids[0]
        selection = ClassicSquadSelection(
            self.selection.roster_player_ids,
            self.selection.starting_xiii,
            self.selection.interchange_player_ids,
            self.selection.emergency_player_ids,
            {unavailable_id: emergency_id},
        )
        result = self.engine.score_squad(selection, self.players, (unavailable_id,))
        self.assertEqual(result.total_points, 143)
        self.assertEqual(result.replacements[0].replacement_player_id, emergency_id)
        self.assertFalse(result.replacements[0].automatic)

    def test_auto_emergency_uses_first_eligible_available_emergency(self):
        unavailable_id = self.selection.interchange_player_ids[0]
        result = self.engine.score_squad(self.selection, self.players, (unavailable_id,))
        self.assertEqual(result.replacements[0].replacement_player_id, self.selection.emergency_player_ids[0])
        self.assertTrue(result.replacements[0].automatic)

    def test_auto_emergency_can_be_disabled(self):
        unavailable_id = self.selection.starting_xiii["WFB"][0]
        selection = ClassicSquadSelection(
            self.selection.roster_player_ids,
            self.selection.starting_xiii,
            self.selection.interchange_player_ids,
            self.selection.emergency_player_ids,
            {},
            auto_emergency=False,
        )
        result = self.engine.score_squad(selection, self.players, (unavailable_id,))
        self.assertEqual(result.total_points, 140)
        self.assertEqual(result.replacements, ())

    def test_emergency_cannot_be_assigned_to_wrong_position(self):
        unavailable_id = self.selection.starting_xiii["WFB"][0]
        wrong_emergency = self.selection.emergency_player_ids[1]
        selection = ClassicSquadSelection(
            self.selection.roster_player_ids,
            self.selection.starting_xiii,
            self.selection.interchange_player_ids,
            self.selection.emergency_player_ids,
            {unavailable_id: wrong_emergency},
        )
        with self.assertRaisesRegex(ValueError, "selected at WFB"):
            self.engine.validate_squad(selection, self.players)

    def test_emergency_player_cannot_be_used_twice(self):
        unavailable_ids = (
            self.selection.starting_xiii["WFB"][0],
            self.selection.interchange_player_ids[0],
        )
        emergency_id = self.selection.emergency_player_ids[0]
        selection = ClassicSquadSelection(
            self.selection.roster_player_ids,
            self.selection.starting_xiii,
            self.selection.interchange_player_ids,
            self.selection.emergency_player_ids,
            {unavailable_ids[0]: emergency_id, unavailable_ids[1]: emergency_id},
        )
        with self.assertRaisesRegex(ValueError, "cannot replace multiple"):
            self.engine.validate_squad(selection, self.players)

    def test_unknown_unavailable_player_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown unavailable"):
            self.engine.score_squad(self.selection, self.players, ("missing",))


if __name__ == "__main__":
    unittest.main()
