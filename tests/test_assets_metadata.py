"""Tests for optional planner metadata catalogs."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.assets import (
    load_archetype_message_contracts,
    load_component_catalog,
    load_planner_policy,
    load_visual_primitive_policy,
)


class TestAssetsMetadata(unittest.TestCase):
    def test_load_component_catalog_defaults_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            assets_dir = Path(temp_dir)
            payload = load_component_catalog(assets_dir)
            self.assertEqual(payload["components"], [])
            self.assertEqual(payload["planner_hints"], {})

    def test_load_planner_policy_reads_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            assets_dir = Path(temp_dir)
            catalog_dir = assets_dir / "catalog"
            catalog_dir.mkdir(parents=True, exist_ok=True)
            policy_path = catalog_dir / "planner_policy_v1.json"
            policy_path.write_text(
                json.dumps(
                    {
                        "asset_diversity": {
                            "min_unique_visual_assets_per_10_slides": 9,
                            "max_reuse_per_branded_image": 1,
                            "max_adjacent_reuse_same_icon_concept": 0,
                            "target_visualized_slides_ratio": 0.9,
                        },
                        "routing_guidance": {"force_image_on_section_break": True},
                        "prompt_directives": ["avoid repeated icons"],
                    }
                ),
                encoding="utf-8",
            )

            payload = load_planner_policy(assets_dir)
            self.assertEqual(payload["asset_diversity"]["min_unique_visual_assets_per_10_slides"], 9)
            self.assertEqual(payload["asset_diversity"]["max_reuse_per_branded_image"], 1)
            self.assertEqual(payload["prompt_directives"], ["avoid repeated icons"])

    def test_load_archetype_message_contracts_defaults_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            assets_dir = Path(temp_dir)
            payload = load_archetype_message_contracts(assets_dir)
            self.assertIn("archetypes", payload)
            self.assertEqual(payload["archetypes"][0]["archetype_id"], "general_story")

    def test_load_visual_primitive_policy_reads_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            assets_dir = Path(temp_dir)
            catalog_dir = assets_dir / "catalog"
            catalog_dir.mkdir(parents=True, exist_ok=True)
            policy_path = catalog_dir / "visual_primitive_policy_v1.json"
            policy_path.write_text(
                json.dumps(
                    {
                        "allowed_primitives": ["table", "shape_cluster"],
                        "max_primitives_per_slide": 2,
                        "declutter_rules": ["keep_it_simple"],
                    }
                ),
                encoding="utf-8",
            )
            payload = load_visual_primitive_policy(assets_dir)
            self.assertEqual(payload["allowed_primitives"], ["table", "shape_cluster"])
            self.assertEqual(payload["max_primitives_per_slide"], 2)


if __name__ == "__main__":
    unittest.main()
