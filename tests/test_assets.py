"""Tests for asset catalog and matching."""

import tempfile
import unittest
from pathlib import Path

from src.assets import build_asset_catalog, match_asset


class TestAssetMatching(unittest.TestCase):
    def test_match_asset_prefers_token_overlap(self) -> None:
        assets = [
            {"asset_type": "image", "asset_id": "a.png", "tags": ["timeline", "roadmap"], "synonyms": []},
            {"asset_type": "image", "asset_id": "b.png", "tags": ["shield", "security"], "synonyms": []},
        ]
        matched = match_asset(
            "project timeline with milestones",
            assets,
            allowed_types=("image",),
            min_score=1,
        )
        self.assertIsNotNone(matched)
        self.assertEqual(matched["asset_id"], "a.png")

    def test_match_asset_returns_none_when_low_score(self) -> None:
        assets = [
            {"asset_type": "image", "asset_id": "a.png", "tags": ["timeline"], "synonyms": []},
        ]
        matched = match_asset(
            "unrelated cue terms",
            assets,
            allowed_types=("image",),
            min_score=2,
        )
        self.assertIsNone(matched)


class TestBuildAssetCatalog(unittest.TestCase):
    def test_build_asset_catalog_with_minimal_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "icons").mkdir(parents=True)
            (root / "external_assets").mkdir(parents=True)
            (root / "Ascendion Logos").mkdir(parents=True)
            (root / "Icons and Dimensional Keywords").mkdir(parents=True)
            (root / "Ascendion Logos" / "logo.png").write_bytes(b"")
            (root / "Icons and Dimensional Keywords" / "timeline.png").write_bytes(b"")
            (root / "icons" / "icons.json").write_text(
                '{"icons":[{"icon_id":"icon_1","filename":"icon_1.png","tags":[],"synonyms":[]}]}',
                encoding="utf-8",
            )
            (root / "external_assets" / "registry.manifest.json").write_text(
                (
                    '{"icons":[{"id":"tabler:cloud","pack":"tabler","svg_path":"svg/cloud.svg",'
                    '"tags":["cloud"],"categories":["weather"],"aliases":["cloudy"]}]}'
                ),
                encoding="utf-8",
            )

            payload = build_asset_catalog(root)
            self.assertIn("summary", payload)
            self.assertIn("assets", payload)
            self.assertGreaterEqual(payload["summary"]["assets_count"], 3)
            self.assertTrue(
                any(asset["asset_id"] == "tabler:cloud" for asset in payload["assets"])
            )


if __name__ == "__main__":
    unittest.main()
