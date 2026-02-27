"""Tests for deterministic composition spec builder."""

from __future__ import annotations

import unittest

from src.compose import build_composition_spec
from src.models.deck_ir import AssetRef, DeckIR, DeckSlide
from src.models.validation import ValidationReport, ValidationViolation


class TestCompositionSpecBuilder(unittest.TestCase):
    def test_builds_structured_composition_with_fit_diagnostics(self) -> None:
        deck_before = DeckIR(
            deck_id="deck_1",
            run_id="run_1",
            template_id="template",
            title="Deck",
            slides=[
                DeckSlide(
                    slide_id="s1",
                    layout_id="one_content_light",
                    fields={
                        "ph_title": "Legacy Modernization",
                        "ph_body": [
                            "First long bullet that should be shortened for fit",
                            "Second long bullet that might move to notes",
                        ],
                    },
                    speaker_notes="Original notes",
                    asset_refs=[
                        AssetRef(
                            asset_type="icon",
                            asset_id="lucide:cloud",
                            target_field_key="ph_image",
                        )
                    ],
                )
            ],
        )

        deck_after = DeckIR(
            deck_id="deck_1",
            run_id="run_1",
            template_id="template",
            title="Deck",
            slides=[
                DeckSlide(
                    slide_id="s1",
                    layout_id="one_content_light",
                    fields={
                        "ph_title": "Legacy Modernization",
                        "ph_body": ["First long bullet that should be shortened for fit"],
                    },
                    speaker_notes=(
                        "Original notes\n\n---\n[REMEDIATION OVERFLOW]\n"
                        "[Overflow from ph_body]: Second long bullet that might move to notes"
                    ),
                    asset_refs=[
                        AssetRef(
                            asset_type="icon",
                            asset_id="lucide:cloud",
                            target_field_key="ph_image",
                        )
                    ],
                )
            ],
        )

        before_report = ValidationReport(
            violations=[
                ValidationViolation(
                    slide_id="s1",
                    layout_id="one_content_light",
                    field_key="ph_body",
                    violation_type="TOO_MANY_BULLETS",
                    severity="BLOCKING",
                ),
                ValidationViolation(
                    slide_id="s1",
                    layout_id="one_content_light",
                    field_key="ph_body",
                    violation_type="BODY_LINE_BUDGET",
                    severity="WARN",
                ),
            ]
        )
        after_report = ValidationReport(violations=[])

        composition = build_composition_spec(
            deck_before=deck_before,
            deck_after=deck_after,
            before_report=before_report,
            after_report=after_report,
            stage="v1",
        )

        self.assertEqual(composition.version, "1.0")
        self.assertEqual(composition.stage, "v1")
        self.assertEqual(len(composition.slides), 1)
        slide = composition.slides[0]
        self.assertEqual(slide.archetype, "content")
        self.assertEqual(slide.fit_diagnostics.before, ["BODY_LINE_BUDGET", "TOO_MANY_BULLETS"])
        self.assertEqual(slide.fit_diagnostics.after, [])
        self.assertGreaterEqual(len(slide.notes_additions), 1)

        body_block = next(block for block in slide.text_blocks if block.field_key == "ph_body")
        self.assertEqual(body_block.overflow_action, "move_to_speaker_notes")
        self.assertIn("- First long bullet", body_block.text)

        self.assertEqual(len(slide.visual_blocks), 1)
        visual = slide.visual_blocks[0]
        self.assertEqual(visual.role, "primary")
        self.assertEqual(visual.placement_mode, "centered_icon")


if __name__ == "__main__":
    unittest.main()
