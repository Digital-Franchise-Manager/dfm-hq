from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXTRACTOR = ROOT / "backend" / "dfm" / "drl" / "nrl" / "extractor"
sys.path.insert(0, str(EXTRACTOR))

from photo_manifest import merge_candidates, write_manifest, load_manifest
from photo_sources import official_host, same_official_family, ImagePageParser
from photo_audit import image_info
from player_media import validate_candidate


class PhotoSourceTests(unittest.TestCase):
    def test_accepts_official_nrl_and_fantasy_hosts(self):
        self.assertTrue(official_host("https://www.nrl.com/players/example"))
        self.assertTrue(official_host("https://fantasy.nrl.com/players/1"))

    def test_rejects_non_official_and_insecure_hosts(self):
        self.assertFalse(official_host("https://example.com/player.jpg"))
        self.assertFalse(official_host("http://www.nrl.com/player.jpg"))

    def test_rejects_off_domain_image(self):
        self.assertFalse(same_official_family(
            "https://www.nrl.com/players/example",
            "https://example-cdn.invalid/player.jpg",
        ))

    def test_accepts_same_official_domain_family(self):
        self.assertTrue(same_official_family(
            "https://www.nrl.com/players/example",
            "https://nrl.com/media/player.jpg",
        ))

    def test_parser_collects_open_graph_and_image_tags(self):
        parser = ImagePageParser()
        parser.feed('<meta property="og:image" content="/media/player.jpg"><img src="/media/second.png" alt="Player">')
        self.assertEqual(len(parser.images), 2)


class PhotoManifestTests(unittest.TestCase):
    def test_merge_deduplicates_same_player_kind_and_url(self):
        a = {"drl_player_id": 7, "media_kind": "profile_photo", "image_url": "https://www.nrl.com/a.jpg"}
        b = dict(a, status="downloaded_private")
        self.assertEqual(len(merge_candidates([a], [b])), 1)

    def test_manifest_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "manifest.json"
            write_manifest(path, [{"drl_player_id": 7}], season=2026)
            self.assertEqual(load_manifest(path)["candidates"][0]["drl_player_id"], 7)


class PhotoValidationTests(unittest.TestCase):
    def setUp(self):
        self.player = {"drl_player_id": 7, "squad_id": 500001, "identity_status": "verified"}
        self.candidate = {
            "drl_player_id": 7, "squad_id": 500001, "season": 2026,
            "media_kind": "profile_photo",
            "source_page_url": "https://www.nrl.com/players/example",
            "image_url": "https://www.nrl.com/media/player.jpg",
            "identity_confirmed": True, "profile_photo_confirmed": True,
            "rights_status": "permission_granted",
            "rights_evidence_url": "https://www.nrl.com/terms",
        }

    def test_cleared_profile_candidate_passes(self):
        self.assertEqual(validate_candidate(self.player, self.candidate), [])

    def test_unverified_identity_is_rejected(self):
        player = dict(self.player, identity_status="unresolved")
        self.assertIn("player_identity_not_verified_in_JARVIS", validate_candidate(player, self.candidate))

    def test_action_photo_requires_uniform_and_rights_checks(self):
        candidate = dict(self.candidate, media_kind="action_photo", profile_photo_confirmed=False)
        issues = validate_candidate(self.player, candidate)
        self.assertIn("human_match_action_photo_review_not_confirmed", issues)
        self.assertIn("human_current_club_uniform_review_not_confirmed", issues)

    def test_wrong_player_id_is_rejected(self):
        candidate = dict(self.candidate, drl_player_id=99)
        self.assertIn("candidate_drl_player_id_mismatch", validate_candidate(self.player, candidate))


class ImageAuditTests(unittest.TestCase):
    def test_png_dimensions_are_read(self):
        header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + (640).to_bytes(4, "big") + (480).to_bytes(4, "big")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.png"
            path.write_bytes(header)
            info = image_info(path)
            self.assertEqual(info["format"], "png")
            self.assertEqual(info["width"], 640)
            self.assertEqual(info["height"], 480)


if __name__ == "__main__":
    unittest.main()
