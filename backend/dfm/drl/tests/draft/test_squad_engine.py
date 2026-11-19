"""Tests for Draft squad validation and emergency scoring."""
import unittest
from backend.dfm.drl.draft.core.squad_engine import DraftPlayer, SquadEngine, SquadSelection

POSITIONS = {"WFB": 3, "CTR": 2, "HLF": 2, "EDG": 2, "MID": 3, "HOK": 1}

def build_squad(bench_size=4, auto_emergency=True, emergency_assignments=None):
    players, starters, roster, bench = [], {p: [] for p in POSITIONS}, [], []
    for position, count in POSITIONS.items():
        for index in range(count):
            pid = f"{position}-S{index}"
            roster.append(pid)
            starters[position].append(pid)
            players.append(DraftPlayer(pid, position, fantasy_points=50 + index,
                                       selected_position=position))
    for index in range(bench_size):
        position = ("WFB", "CTR", "HLF", "EDG", "MID", "HOK")[index]
        pid = f"BENCH-{index}"
        roster.append(pid)
        bench.append(pid)
        players.append(DraftPlayer(pid, position, fantasy_points=10 + index,
                                   selected_position=position))
    selection = SquadSelection(tuple(roster), {k: tuple(v) for k, v in starters.items()},
                               tuple(bench), emergency_assignments or {}, auto_emergency)
    return selection, tuple(players)

class DraftSquadEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = SquadEngine()

    def test_accepts_standard_17_player_squad(self):
        selection, players = build_squad(4)
        self.engine.validate_squad(selection, players)

    def test_accepts_extended_19_player_squad(self):
        selection, players = build_squad(6)
        self.engine.validate_squad(selection, players)

    def test_rejects_squad_sizes_other_than_17_or_19(self):
        selection, players = build_squad(5)
        with self.assertRaisesRegex(ValueError, "17 or 19"):
            self.engine.validate_squad(selection, players)

    def test_rejects_incorrect_bench_size(self):
        selection, players = build_squad()
        invalid = SquadSelection(selection.roster_player_ids, selection.starting_xiii,
                                 selection.bench_player_ids[:-1], {}, True)
        with self.assertRaisesRegex(ValueError, "bench size"):
            self.engine.validate_squad(invalid, players)

    def test_rejects_missing_or_extra_position_key(self):
        selection, players = build_squad()
        changed = dict(selection.starting_xiii)
        changed.pop("HOK")
        changed["LOCK"] = ()
        invalid = SquadSelection(selection.roster_player_ids, changed,
                                 selection.bench_player_ids, {}, True)
        with self.assertRaisesRegex(ValueError, "all six"):
            self.engine.validate_squad(invalid, players)

    def test_rejects_wrong_positional_starting_count(self):
        selection, players = build_squad()
        changed = dict(selection.starting_xiii)
        changed["MID"] = changed["MID"][:-1]
        invalid = SquadSelection(selection.roster_player_ids, changed,
                                 selection.bench_player_ids, {}, True)
        with self.assertRaisesRegex(ValueError, "MID must contain exactly 3"):
            self.engine.validate_squad(invalid, players)

    def test_rejects_duplicate_starter(self):
        selection, players = build_squad()
        changed = dict(selection.starting_xiii)
        changed["WFB"] = (changed["WFB"][0], changed["WFB"][0], changed["WFB"][2])
        invalid = SquadSelection(selection.roster_player_ids, changed,
                                 selection.bench_player_ids, {}, True)
        with self.assertRaises(ValueError):
            self.engine.validate_squad(invalid, players)

    def test_rejects_player_in_both_starting_and_bench(self):
        selection, players = build_squad()
        bench = list(selection.bench_player_ids)
        bench[0] = selection.starting_xiii["WFB"][0]
        invalid = SquadSelection(selection.roster_player_ids, selection.starting_xiii,
                                 tuple(bench), {}, True)
        with self.assertRaises(ValueError):
            self.engine.validate_squad(invalid, players)

    def test_rejects_roster_player_not_assigned_to_start_or_bench(self):
        selection, players = build_squad()
        invalid = SquadSelection(selection.roster_player_ids[:-1], selection.starting_xiii,
                                 selection.bench_player_ids[:-1], {}, True)
        with self.assertRaises(ValueError):
            self.engine.validate_squad(invalid, players)

    def test_rejects_missing_player_record_and_duplicate_player_record(self):
        selection, players = build_squad()
        with self.assertRaises(ValueError):
            self.engine.validate_squad(selection, players[:-1])
        with self.assertRaisesRegex(ValueError, "unique player_id"):
            self.engine.validate_squad(selection, players + (players[0],))

    def test_rejects_starter_assigned_to_ineligible_position(self):
        selection, players = build_squad()
        changed = list(players)
        changed[0] = DraftPlayer("WFB-S0", "CTR", fantasy_points=50,
                                 selected_position="CTR")
        with self.assertRaises(ValueError):
            self.engine.validate_squad(selection, tuple(changed))

    def test_dpp_player_uses_only_its_selected_round_position(self):
        selection, players = build_squad()
        changed = list(players)
        changed[0] = DraftPlayer("WFB-S0", "WFB", ("CTR",),
                                 selected_position="CTR", fantasy_points=50)
        starters = dict(selection.starting_xiii)
        starters["WFB"] = ("WFB-S1", "WFB-S2", "WFB-S0")
        invalid = SquadSelection(selection.roster_player_ids, starters,
                                 selection.bench_player_ids, {}, True)
        with self.assertRaisesRegex(ValueError, "CTR"):
            self.engine.validate_squad(invalid, tuple(changed))

    def test_rejects_invalid_dpp_selected_position(self):
        with self.assertRaisesRegex(ValueError, "selected_position"):
            DraftPlayer("dpp", "WFB", ("CTR",), selected_position="MID")

    def test_allows_dpp_emergency_in_selected_position(self):
        selection, players = build_squad()
        changed = list(players)
        changed[-1] = DraftPlayer("BENCH-3", "EDG", ("MID",),
                                  selected_position="EDG", fantasy_points=13)
        valid = SquadSelection(selection.roster_player_ids, selection.starting_xiii,
                               selection.bench_player_ids, {"EDG": "BENCH-3"}, True)
        self.engine.validate_squad(valid, tuple(changed))

    def test_rejects_more_than_four_emergency_assignments(self):
        selection, players = build_squad(6)
        emergency = {"WFB": "BENCH-0", "CTR": "BENCH-1", "HLF": "BENCH-2",
                     "EDG": "BENCH-3", "MID": "BENCH-4"}
        invalid = SquadSelection(selection.roster_player_ids, selection.starting_xiii,
                                 selection.bench_player_ids, emergency, True)
        with self.assertRaisesRegex(ValueError, "maximum of four"):
            self.engine.validate_squad(invalid, players)

    def test_rejects_emergency_not_on_bench_or_not_position_eligible(self):
        selection, players = build_squad()
        invalid = SquadSelection(selection.roster_player_ids, selection.starting_xiii,
                                 selection.bench_player_ids,
                                 {"WFB": selection.starting_xiii["WFB"][0]}, True)
        with self.assertRaisesRegex(ValueError, "bench players"):
            self.engine.validate_squad(invalid, players)
        invalid = SquadSelection(selection.roster_player_ids, selection.starting_xiii,
                                 selection.bench_player_ids, {"WFB": "BENCH-1"}, True)
        with self.assertRaises(ValueError):
            self.engine.validate_squad(invalid, players)

    def test_rejects_same_bench_player_assigned_to_multiple_positions(self):
        selection, players = build_squad()
        invalid = SquadSelection(selection.roster_player_ids, selection.starting_xiii,
                                 selection.bench_player_ids,
                                 {"WFB": "BENCH-0", "CTR": "BENCH-0"}, True)
        with self.assertRaisesRegex(ValueError, "multiple emergency positions"):
            self.engine.validate_squad(invalid, players)

    def test_manual_emergency_replaces_dnp_starter(self):
        selection, players = build_squad(emergency_assignments={"WFB": "BENCH-0"})
        score = self.engine.score_squad(selection, players,
                                        (selection.starting_xiii["WFB"][0],))
        self.assertEqual(score.replacements[0].replacement_player_id, "BENCH-0")
        self.assertFalse(score.replacements[0].automatic)

    def test_manual_emergency_replaces_bye_starter(self):
        selection, players = build_squad(emergency_assignments={"CTR": "BENCH-1"})
        score = self.engine.score_squad(selection, players,
                                        (selection.starting_xiii["CTR"][0],))
        self.assertEqual(score.replacements[0].replacement_player_id, "BENCH-1")

    def test_auto_emergency_uses_lowest_scoring_eligible_bench_player(self):
        selection, players = build_squad()
        changed = list(players)
        changed[14] = DraftPlayer("BENCH-1", "WFB", fantasy_points=15,
                                  selected_position="WFB")
        score = self.engine.score_squad(selection, tuple(changed),
                                        (selection.starting_xiii["WFB"][0],))
        self.assertEqual(score.replacements[0].replacement_player_id, "BENCH-0")
        self.assertTrue(score.replacements[0].automatic)

    def test_auto_emergency_off_does_not_auto_select_bench(self):
        selection, players = build_squad(auto_emergency=False)
        score = self.engine.score_squad(selection, players,
                                        (selection.starting_xiii["WFB"][0],))
        self.assertEqual(score.replacements, ())
        self.assertEqual(score.starting_points["WFB"], 50 + 51)

    def test_auto_emergency_skips_unavailable_bench_player(self):
        selection, players = build_squad()
        changed = list(players)
        changed[14] = DraftPlayer("BENCH-1", "WFB", fantasy_points=15,
                                  selected_position="WFB")
        score = self.engine.score_squad(selection, tuple(changed),
                                        (selection.starting_xiii["WFB"][0], "BENCH-0"))
        self.assertEqual(score.replacements[0].replacement_player_id, "BENCH-1")

    def test_bench_player_replaces_at_most_one_unavailable_starter(self):
        selection, players = build_squad(emergency_assignments={"WFB": "BENCH-0"})
        unavailable = selection.starting_xiii["WFB"][:2]
        score = self.engine.score_squad(selection, players, unavailable)
        ids = [replacement.replacement_player_id for replacement in score.replacements]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 2)

    def test_rejects_unknown_unavailable_player(self):
        selection, players = build_squad()
        with self.assertRaisesRegex(ValueError, "unknown unavailable"):
            self.engine.score_squad(selection, players, ("not-a-player",))

    def test_score_is_sum_of_position_totals(self):
        selection, players = build_squad(emergency_assignments={"WFB": "BENCH-0"})
        score = self.engine.score_squad(selection, players,
                                        (selection.starting_xiii["WFB"][0],))
        self.assertEqual(score.total_points, sum(score.starting_points.values()))

    def test_returns_unused_bench_players(self):
        selection, players = build_squad()
        score = self.engine.score_squad(selection, players)
        self.assertEqual(score.unused_bench_player_ids, selection.bench_player_ids)

if __name__ == "__main__":
    unittest.main()
