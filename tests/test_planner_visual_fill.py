"""Tests for deterministic visual fill and cue-driven relayout."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.llm.planner import _fill_missing_visuals
from src.models.deck_ir import DeckIR, DeckSlide


class TestPlannerVisualFill(unittest.TestCase):
    def _write_layout_catalog(self, path: Path) -> None:
        payload = {
            "layouts": [
                {
                    "layout_id": "title_image_light",
                    "fields": [{"field_key": "ph_title"}, {"field_key": "ph_subtitle"}, {"field_key": "ph_body"}],
                    "constraints": {},
                },
                {
                    "layout_id": "section_break_light",
                    "fields": [{"field_key": "ph_image"}, {"field_key": "ph_title"}],
                    "constraints": {},
                },
                {
                    "layout_id": "two_content_light",
                    "fields": [
                        {"field_key": "ph_title"},
                        {"field_key": "ph_body_left"},
                        {"field_key": "ph_body_right"},
                    ],
                    "constraints": {},
                },
                {
                    "layout_id": "two_content_image_light",
                    "fields": [
                        {"field_key": "ph_title"},
                        {"field_key": "ph_image"},
                        {"field_key": "ph_body_left"},
                        {"field_key": "ph_body_right"},
                    ],
                    "constraints": {},
                },
            ]
        }
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_upgrades_two_content_to_image_layout_and_prefers_image_asset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            layout_dir = root / "assets" / "layout"
            layout_dir.mkdir(parents=True, exist_ok=True)
            catalog_path = layout_dir / "layout_catalog.json"
            self._write_layout_catalog(catalog_path)

            deck = DeckIR(
                deck_id="deck",
                run_id="run",
                template_id="template",
                title="Deck",
                slides=[
                    DeckSlide(
                        slide_id="tier1_xray",
                        layout_id="two_content_light",
                        fields={
                            "ph_title": "Tier 1 - Legacy System X-Ray",
                            "ph_body_left": ["System map", "Entity impact network"],
                            "ph_body_right": ["Ask your legacy system", "Citations by file and line"],
                        },
                        speaker_notes="",
                        asset_refs=[],
                    )
                ],
            )

            cues = {
                "cues": [
                    {
                        "section_id": "tier1_xray",
                        "layout_hint": "two_content_image_light",
                        "icon_hints": ["map", "entity", "network", "chat"],
                        "image_hint": "Composite visual: map + entity impact + chat UI",
                        "notes": "Use a diagram-style visual treatment.",
                    }
                ]
            }
            branded_catalog = {
                "images": {
                    "see_differently": {
                        "theme": "analysis insight perspective",
                        "color_preference": {"light_theme": "Teal"},
                        "paths": {"Teal": "Icons and Dimensional Keywords/See Differently/Pt_SeeDifferently_Teal.png"},
                    }
                }
            }

            _fill_missing_visuals(
                deck,
                catalog_path,
                cues_data=cues,
                vocabulary={"concepts": {}},
                branded_catalog=branded_catalog,
            )

            slide = deck.slides[0]
            self.assertEqual(slide.layout_id, "two_content_image_light")
            self.assertEqual(len(slide.asset_refs), 1)
            self.assertEqual(slide.asset_refs[0].asset_type, "image")
            self.assertEqual(slide.asset_refs[0].target_field_key, "ph_image")

    def test_upgrades_first_title_slide_to_section_break_with_image(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            layout_dir = root / "assets" / "layout"
            layout_dir.mkdir(parents=True, exist_ok=True)
            catalog_path = layout_dir / "layout_catalog.json"
            self._write_layout_catalog(catalog_path)

            deck = DeckIR(
                deck_id="deck",
                run_id="run",
                template_id="template",
                title="Deck",
                slides=[
                    DeckSlide(
                        slide_id="opening",
                        layout_id="title_image_light",
                        fields={
                            "ph_title": "Legacy System X-Ray & Navigator",
                            "ph_subtitle": "Modernization blueprint",
                            "ph_body": "Executive brief",
                        },
                        speaker_notes="",
                        asset_refs=[],
                    )
                ],
            )
            branded_catalog = {
                "images": {
                    "transform_reality": {
                        "theme": "modernization digital transformation",
                        "color_preference": {"light_theme": "Teal"},
                        "paths": {"Teal": "Icons and Dimensional Keywords/Transform Reality/Pt_TransformReality_Teal.png"},
                    }
                }
            }

            _fill_missing_visuals(
                deck,
                catalog_path,
                cues_data={"cues": []},
                vocabulary={"concepts": {}},
                branded_catalog=branded_catalog,
            )

            slide = deck.slides[0]
            self.assertEqual(slide.layout_id, "section_break_light")
            self.assertEqual(set(slide.fields.keys()), {"ph_title"})
            self.assertEqual(len(slide.asset_refs), 1)
            self.assertEqual(slide.asset_refs[0].asset_type, "image")


if __name__ == "__main__":
    unittest.main()
