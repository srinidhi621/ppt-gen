"""Model validation tests."""

import unittest

from pydantic import ValidationError

from src.models.content import ContentModel, ContentSection
from src.models.critique import CritiqueFinding, CritiqueReport
from src.models.deck_ir import DeckIR, DeckSlide
from src.models.patch import Patch
from src.models.validation import ValidationReport, ValidationViolation


class TestModels(unittest.TestCase):
    def test_content_model_minimal(self) -> None:
        model = ContentModel(
            doc_id="doc_1",
            version="1.0",
            source_hash="hash",
            sections=[ContentSection(section_id="s1", title="Title")],
        )
        self.assertEqual(model.doc_id, "doc_1")

    def test_content_model_roundtrip_json(self) -> None:
        model = ContentModel(
            doc_id="doc_1",
            version="1.0",
            source_hash="hash",
            sections=[ContentSection(section_id="s1", title="Title")],
        )
        round_tripped = ContentModel.model_validate_json(model.to_json())
        self.assertEqual(round_tripped.model_dump(), model.model_dump())

    def test_deck_ir_minimal(self) -> None:
        deck = DeckIR(
            deck_id="deck_1",
            run_id="run_1",
            template_id="template_1",
            title="Title",
            slides=[
                DeckSlide(
                    slide_id="s1",
                    layout_id="layout_1",
                    fields={"ph_title": "T"},
                    speaker_notes={"notes": "Keep this tight"},
                )
            ],
        )
        self.assertEqual(deck.deck_id, "deck_1")

    def test_validation_report_empty(self) -> None:
        report = ValidationReport(violations=[])
        self.assertEqual(report.violations, [])

    def test_validation_report_rejects_invalid_severity(self) -> None:
        with self.assertRaises(ValidationError):
            ValidationViolation(
                slide_id="s1",
                layout_id="layout_1",
                field_key="ph_body",
                violation_type="TOO_MANY_BULLETS",
                severity="BAD",
            )

    def test_critique_report_rejects_invalid_type(self) -> None:
        with self.assertRaises(ValidationError):
            CritiqueFinding(
                slide_id="s1",
                finding_type="NOT_A_REAL_TYPE",
                severity="S1",
            )

    def test_patch_rejects_invalid_type(self) -> None:
        with self.assertRaises(ValidationError):
            Patch(patch_type="DO_SOMETHING_ELSE")


if __name__ == "__main__":
    unittest.main()
