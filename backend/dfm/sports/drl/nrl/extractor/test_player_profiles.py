import unittest

from player_profiles import extract_profile


class PlayerProfileExtractionTests(unittest.TestCase):
    def test_maps_official_round_columns_and_leaves_unavailable_stats_null(self):
        html = """
        <html><body>
          <div>Tackle Efficiency 91.5%</div>
          <table>
            <tr><th>Round</th><th>Opponent</th><th>Score</th><th>Position</th>
                <th>Minutes Played</th><th>Tries</th><th>Try Assists</th><th>Points</th>
                <th>Linebreaks</th><th>Tackles Made</th><th>Total Running Metres</th></tr>
            <tr><td>1</td><td>Panthers</td><td>W</td><td>Centre</td><td>80</td>
                <td>2</td><td>1</td><td>8</td><td>1</td><td>24</td><td>155</td></tr>
            <tr><td>2</td><td>Storm</td><td>L</td><td>Centre</td><td>80</td>
                <td>1</td><td>0</td><td>4</td><td>2</td><td>30</td><td>180</td></tr>
          </table>
          <img src="https://www.nrl.com/photo.png" alt="Photo of Test Player" />
        </body></html>
        """
        result = extract_profile(html, "https://www.nrl.com/players/nrl-premiership/test/test-player/",
                                 123456, 2026)
        self.assertEqual(result["stats"]["appearances"], 2)
        self.assertEqual(result["stats"]["tries"], 3)
        self.assertEqual(result["stats"]["try_assists"], 1)
        self.assertEqual(result["stats"]["points"], 12)
        self.assertEqual(result["stats"]["tackles"], 54)
        self.assertEqual(result["stats"]["metres_gained"], 335)
        self.assertEqual(result["stats"]["line_breaks"], 3)
        self.assertEqual(result["stats"]["tackle_efficiency"], 91.5)
        self.assertIsNone(result["stats"]["errors"])
        self.assertIsNone(result["stats"]["penalties_conceded"])
        self.assertEqual(result["media_rights_status"], "pending_review")
        self.assertTrue(result["identity_review_required"])


if __name__ == "__main__":
    unittest.main()
