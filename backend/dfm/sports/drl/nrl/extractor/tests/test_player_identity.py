import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import player_identity as identity


def record(player_id, first, last, positions):
    return {
        "id": player_id, "first_name": first, "last_name": last,
        "positions": positions, "squad_id": 500001, "_source_file": "fixture.PDF",
    }


class PlayerIdentityTests(unittest.TestCase):
    def test_connelly_maps_later_id_to_earliest_id(self):
        row = record(507949, "Connelly", "Lemuelu", [3])
        self.assertEqual(identity.resolve(row)[0], 100003377)

    def test_sione_katoas_remain_separate(self):
        winger = record(501240, "Sione", "Katoa", [1])
        hooker = record(503922, "Sione", "Katoa", [6])
        self.assertEqual(identity.resolve(winger)[0], 501240)
        self.assertEqual(identity.resolve(hooker)[0], 503922)

    def test_marzhew_and_leleisiuao_share_confirmed_canonical_identity(self):
        marzhew = record(504325, "Greg", "Marzhew", [6])
        leleisiuao = record(504325, "Greg", "Leleisiuao", [6])
        self.assertEqual(identity.resolve(marzhew)[0], 504325)
        self.assertEqual(identity.resolve(leleisiuao)[0], 504325)

    def test_master_uses_earliest_mapped_season(self):
        seasons = {
            2019: [record(504325, "Greg", "Leleisiuao", [6])],
            2020: [record(100003377, "Connelly", "Lemuelu", [5])],
            2021: [record(504325, "Greg", "Marzhew", [6])],
            2023: [record(507949, "Connelly", "Lemuelu", [3])],
        }
        with tempfile.TemporaryDirectory() as temp:
            summary = identity.build_outputs(seasons, Path(temp))
            with (Path(temp) / "player-master.csv").open(encoding="utf-8") as handle:
                master = {int(row["drl_player_id"]): row for row in csv.DictReader(handle)}
            self.assertEqual(master[100003377]["source_season"], "2020")
            self.assertEqual(master[504325]["source_season"], "2019")
            self.assertEqual(master[504325]["last_name"], "Marzhew")
            self.assertEqual(master[504325]["historical_name_variants"], "Greg Leleisiuao")
            with (Path(temp) / "source-map.csv").open(encoding="utf-8") as handle:
                source_map = list(csv.DictReader(handle))
            greg_rows = [row for row in source_map if row["season_player_id"] == "504325"]
            self.assertEqual({row["drl_player_id"] for row in greg_rows}, {"504325"})
            self.assertEqual(summary["source_map_review_required_rows"], 0)
            self.assertFalse(summary["database_write_performed"])


if __name__ == "__main__":
    unittest.main()
