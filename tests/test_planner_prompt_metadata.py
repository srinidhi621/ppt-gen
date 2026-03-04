"""Tests for planner prompt metadata wiring."""

from __future__ import annotations

import unittest

from src.llm.planner import _build_system_prompt, _build_user_prompt
from src.models.content import ContentModel, ContentSection


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

    def test_user_prompt_includes_planning_guardrails_when_provided(self) -> None:
        content_model = ContentModel(
            doc_id="doc",
            version="1.0",
            source_hash="abc123",
            sections=[
                ContentSection(
                    section_id="exec_summary",
                    title="Executive Summary",
                    bullets=["Point one"],
                    paragraphs=[],
                )
            ],
        )
        prompt = _build_user_prompt(
            content_model=content_model,
            cues_data={"cues": []},
            run_id="run_1",
            deck_id="deck_1",
            template_id="corp_deck_2025",
            planning_context={
                "intent_briefs": [{"section_id": "exec_summary", "bottom_line": "Point one"}],
                "structure_plans": [{"section_id": "exec_summary"}],
            },
        )
        self.assertIn("=== MESSAGE + STRUCTURE + VISUAL GUARDRAILS ===", prompt)
        self.assertIn('"section_id": "exec_summary"', prompt)


if __name__ == "__main__":
    unittest.main()
