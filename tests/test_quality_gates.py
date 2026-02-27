"""Tests for deterministic final quality gates."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.models.deck_ir import AssetRef, DeckIR, DeckSlide
from src.models.validation import ValidationReport, ValidationViolation
from src.quality import evaluate_v2_quality_gates, summarize_composition_spec


class TestCompositionSummary(unittest.TestCase):
    def test_summarize_composition_spec(self) -> None:
        spec = {
            "slides": [
                {
                    "visual_blocks": [
                        {
                            "role": "hero",
                            "asset_ref": {"asset_type": "icon", "asset_id": "lucide:map"},
                        },
                        {
                            "role": "secondary",
                            "asset_ref": {"asset_type": "image", "asset_id": "img_1"},
                        },
                    ],
                    "text_blocks": [
                        {"field_key": "ph_body", "overflow_action": "none"},
                        {"field_key": "ph_body", "overflow_action": "move_to_speaker_notes"},
                    ],
                    "notes_additions": ["overflow moved"],
                },
                {"visual_blocks": [], "text_blocks": [], "notes_additions": []},
            ]
        }
        metrics = summarize_composition_spec(spec)
        self.assertEqual(metrics["slides_total"], 2)
        self.assertEqual(metrics["slides_with_visuals"], 1)
        self.assertEqual(metrics["total_visual_blocks"], 2)
        self.assertEqual(metrics["hero_icon_count"], 1)
        self.assertEqual(metrics["text_overflow_actions"], 1)
        self.assertEqual(metrics["slides_with_notes_additions"], 1)


class TestQualityGates(unittest.TestCase):
    def test_quality_gates_pass(self) -> None:
        deck = DeckIR(
            deck_id="d1",
            run_id="r1",
            template_id="t1",
            title="Deck",
            slides=[
                DeckSlide(
                    slide_id="s1",
                    layout_id="content_image_light",
                    fields={"ph_title": "Title", "ph_body": ["One"]},
                    asset_refs=[
                        AssetRef(
                            asset_type="image",
                            asset_id="assets/images/example.png",
                            target_field_key="ph_image",
                        )
                    ],
                )
            ],
        )
        validation_post = ValidationReport(violations=[])
        diagnose = {
            "slides": [
                {
                    "deckir_slide_id": "s1",
                    "actual_images": 1,
                    "text_shapes_by_alt": {"ph_title": {"text_preview": "Title"}},
                }
            ]
        }
        composition = {
            "slides": [
                {
                    "slide_id": "s1",
                    "visual_blocks": [
                        {
                            "role": "primary",
                            "target_field_key": "ph_image",
                            "asset_ref": {"asset_type": "image", "asset_id": "assets/images/example.png"},
                        }
                    ],
                }
            ]
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "run_log.jsonl"
            report = evaluate_v2_quality_gates(
                deck_v2=deck,
                validation_v2_post=validation_post,
                diagnose_report_v2=diagnose,
                composition_spec_v2=composition,
                image_capable_layouts=["content_image_light"],
                run_log_path=log_path,
            )
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(len(report["issues"]), 0)

    def test_quality_gates_fail(self) -> None:
        deck = DeckIR(
            deck_id="d1",
            run_id="r1",
            template_id="t1",
            title="Deck",
            slides=[
                DeckSlide(
                    slide_id="s1",
                    layout_id="content_image_light",
                    fields={"ph_title": "Title", "ph_body": ["**leak**"]},
                    asset_refs=[],
                )
            ],
        )
        validation_post = ValidationReport(
            violations=[
                ValidationViolation(
                    slide_id="s1",
                    layout_id="content_image_light",
                    field_key="ph_body",
                    violation_type="TOTAL_BODY_CHARS",
                    severity="BLOCKING",
                )
            ]
        )
        diagnose = {
            "slides": [
                {
                    "deckir_slide_id": "s1",
                    "actual_images": 0,
                    "text_shapes_by_alt": {"ph_body": {"text_preview": "**leak** text"}},
                }
            ]
        }
        composition = {
            "slides": [
                {
                    "slide_id": "s1",
                    "visual_blocks": [
                        {
                            "role": "hero",
                            "target_field_key": "ph_image",
                            "asset_ref": {"asset_type": "icon", "asset_id": "lucide:map"},
                        }
                    ],
                }
            ]
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "run_log.jsonl"
            report = evaluate_v2_quality_gates(
                deck_v2=deck,
                validation_v2_post=validation_post,
                diagnose_report_v2=diagnose,
                composition_spec_v2=composition,
                image_capable_layouts=["content_image_light"],
                run_log_path=log_path,
            )
        self.assertEqual(report["status"], "FAIL")
        self.assertGreaterEqual(len(report["issues"]), 3)
        self.assertFalse(report["checks"]["no_blocking_overflow"]["pass"])
        self.assertFalse(report["checks"]["visual_coverage_image_layouts"]["pass"])
        self.assertFalse(report["checks"]["no_icon_hero_stretch"]["pass"])
        self.assertFalse(report["checks"]["no_markdown_marker_leak"]["pass"])


if __name__ == "__main__":
    unittest.main()
