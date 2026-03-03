"""Tests for planner prompt metadata wiring."""

from __future__ import annotations

import unittest

from src.llm.planner import _build_system_prompt


class TestPlannerPromptMetadata(unittest.TestCase):
    def test_system_prompt_includes_component_and_policy_sections(self) -> None:
        layout_catalog = {
            "layouts": [
                {
                    "layout_id": "content_image_light",
                    "fields": [{"field_key": "ph_title"}, {"field_key": "ph_body"}, {"field_key": "ph_image"}],
                    "constraints": {"max_bullets": 5, "max_total_body_chars": 400},
                }
            ]
        }
        vocabulary = {
            "concepts": {
                "integration": {"domains": ["api", "sync"], "preferred": "icon_integration"}
            }
        }
        branded_catalog = {
            "images": {
                "transform_reality": {
                    "theme": "modernization transformation",
                    "paths": {"Teal": "path/to/img.png"},
                }
            }
        }
        component_catalog = {
            "components": [
                {
                    "component_id": "timeline",
                    "purpose": "Chronological milestones",
                    "use_when": ["roadmap"],
                    "max_items": {"events": 8},
                }
            ]
        }
        planner_policy = {
            "asset_diversity": {
                "min_unique_visual_assets_per_10_slides": 6,
                "max_reuse_per_branded_image": 2,
                "max_adjacent_reuse_same_icon_concept": 1,
                "target_visualized_slides_ratio": 0.8,
            },
            "routing_guidance": {"prefer_image_layout_when_cues_present": True},
            "prompt_directives": ["Do not repeat icon concepts."],
        }

        prompt = _build_system_prompt(
            layout_catalog,
            vocabulary,
            branded_catalog,
            component_catalog,
            planner_policy,
        )

        self.assertIn("=== COMPONENT METADATA (visual planning hints) ===", prompt)
        self.assertIn('"component_id": "timeline"', prompt)
        self.assertIn("=== VISUAL PLANNING POLICY ===", prompt)
        self.assertIn("min_unique_visual_assets_per_10_slides", prompt)
        self.assertIn("Do not reuse a branded image more than 2 times", prompt)


if __name__ == "__main__":
    unittest.main()
