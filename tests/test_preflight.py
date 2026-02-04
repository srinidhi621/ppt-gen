"""Preflight validation tests."""

import unittest
from pathlib import Path

from src.config import load_config
from src.models.deck_ir import DeckIR, DeckSlide
from src.validate.preflight import (
    _count_bullets,
    _count_chars,
    _estimate_lines,
    _max_words_in_bullet,
    _shorten_bullet,
    _truncate_text,
    validate_and_remediate,
)


class TestPreflightHelpers(unittest.TestCase):
    def test_count_chars_string(self) -> None:
        self.assertEqual(_count_chars("Hello World"), 11)

    def test_count_chars_list(self) -> None:
        self.assertEqual(_count_chars(["One", "Two", "Three"]), 11)

    def test_count_bullets_string(self) -> None:
        self.assertEqual(_count_bullets("Single"), 1)

    def test_count_bullets_list(self) -> None:
        self.assertEqual(_count_bullets(["A", "B", "C"]), 3)

    def test_count_bullets_empty(self) -> None:
        self.assertEqual(_count_bullets(""), 0)
        self.assertEqual(_count_bullets([]), 0)

    def test_max_words_in_bullet_string(self) -> None:
        self.assertEqual(_max_words_in_bullet("Hello World"), 2)

    def test_max_words_in_bullet_list(self) -> None:
        self.assertEqual(_max_words_in_bullet(["One two", "One two three four"]), 4)

    def test_estimate_lines(self) -> None:
        # 100 chars with 50 chars per line = 2 lines
        self.assertEqual(_estimate_lines("x" * 100, 50), 2)
        # 51 chars with 50 chars per line = 2 lines (ceiling)
        self.assertEqual(_estimate_lines("x" * 51, 50), 2)

    def test_truncate_text(self) -> None:
        result = _truncate_text("Hello World Test", 12)
        self.assertTrue(result.endswith("..."))
        self.assertLessEqual(len(result), 12)

    def test_truncate_text_short(self) -> None:
        result = _truncate_text("Short", 10)
        self.assertEqual(result, "Short")

    def test_shorten_bullet(self) -> None:
        result = _shorten_bullet("One two three four five six", 3)
        self.assertEqual(result, "One two three...")

    def test_shorten_bullet_already_short(self) -> None:
        result = _shorten_bullet("One two", 5)
        self.assertEqual(result, "One two")


class TestPreflightValidation(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config()
        self.catalog_path = Path(self.config.layout_catalog_path)

    def test_validate_no_violations(self) -> None:
        deck = DeckIR(
            deck_id="test",
            run_id="test_run",
            template_id="template",
            title="Title",
            slides=[
                DeckSlide(
                    slide_id="s1",
                    layout_id="one_content_light",
                    fields={"ph_title": "Short Title", "ph_body": ["Bullet one", "Bullet two"]},
                )
            ],
        )
        remediated, report = validate_and_remediate(deck, self.catalog_path)
        # May have some warnings but no blocking violations
        blocking = [v for v in report.violations if v.severity == "BLOCKING"]
        self.assertEqual(len(blocking), 0)

    def test_validate_too_many_bullets(self) -> None:
        deck = DeckIR(
            deck_id="test",
            run_id="test_run",
            template_id="template",
            title="Title",
            slides=[
                DeckSlide(
                    slide_id="s1",
                    layout_id="one_content_light",  # max_bullets=7
                    fields={
                        "ph_title": "Title",
                        "ph_body": ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10"],
                    },
                )
            ],
        )
        remediated, report = validate_and_remediate(deck, self.catalog_path)
        
        # Should have TOO_MANY_BULLETS violation
        bullet_violations = [v for v in report.violations if v.violation_type == "TOO_MANY_BULLETS"]
        self.assertGreater(len(bullet_violations), 0)
        
        # Remediated deck should have trimmed bullets
        body = remediated.slides[0].fields["ph_body"]
        self.assertIsInstance(body, list)
        self.assertLessEqual(len(body), 7)

    def test_validate_title_too_long(self) -> None:
        long_title = "A" * 150  # Exceeds max_title_chars=100
        deck = DeckIR(
            deck_id="test",
            run_id="test_run",
            template_id="template",
            title="Deck",
            slides=[
                DeckSlide(
                    slide_id="s1",
                    layout_id="one_content_light",
                    fields={"ph_title": long_title, "ph_body": ["Simple bullet"]},
                )
            ],
        )
        remediated, report = validate_and_remediate(deck, self.catalog_path)
        
        # Should have TITLE_TOO_LONG violation
        title_violations = [v for v in report.violations if v.violation_type == "TITLE_TOO_LONG"]
        self.assertGreater(len(title_violations), 0)
        
        # Remediated title should be truncated
        new_title = str(remediated.slides[0].fields["ph_title"])
        self.assertLess(len(new_title), len(long_title))

    def test_remediation_moves_to_notes(self) -> None:
        deck = DeckIR(
            deck_id="test",
            run_id="test_run",
            template_id="template",
            title="Title",
            slides=[
                DeckSlide(
                    slide_id="s1",
                    layout_id="one_content_light",
                    fields={
                        "ph_title": "Title",
                        "ph_body": ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9"],
                    },
                    speaker_notes="Original notes",
                )
            ],
        )
        remediated, report = validate_and_remediate(deck, self.catalog_path)
        
        # Speaker notes should contain overflow
        notes = str(remediated.slides[0].speaker_notes)
        self.assertIn("REMEDIATION OVERFLOW", notes)
        self.assertIn("Original notes", notes)

    def test_remediation_truncates_single_bullet_list(self) -> None:
        long_bullet = "A" * 900
        deck = DeckIR(
            deck_id="test",
            run_id="test_run",
            template_id="template",
            title="Title",
            slides=[
                DeckSlide(
                    slide_id="s1",
                    layout_id="one_content_light",
                    fields={"ph_title": "Title", "ph_body": [long_bullet]},
                    speaker_notes="Notes",
                )
            ],
        )
        remediated, report = validate_and_remediate(deck, self.catalog_path)
        body = remediated.slides[0].fields["ph_body"]
        self.assertIsInstance(body, list)
        self.assertEqual(len(body), 1)
        self.assertLessEqual(len(str(body[0])), 700)
        notes = str(remediated.slides[0].speaker_notes)
        self.assertIn("REMEDIATION OVERFLOW", notes)
        self.assertIn("Full text from ph_body", notes)

    def test_unknown_layout_flags_violation(self) -> None:
        deck = DeckIR(
            deck_id="test",
            run_id="test_run",
            template_id="template",
            title="Title",
            slides=[
                DeckSlide(
                    slide_id="s1",
                    layout_id="nonexistent_layout",
                    fields={"ph_title": "Title"},
                )
            ],
        )
        remediated, report = validate_and_remediate(deck, self.catalog_path)
        
        # Should flag unknown layout as blocking
        blocking = [v for v in report.violations if v.severity == "BLOCKING"]
        self.assertGreater(len(blocking), 0)


if __name__ == "__main__":
    unittest.main()
