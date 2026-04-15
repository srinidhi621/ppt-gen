"""Tests for src.v3.normalize."""

from __future__ import annotations

import pytest
from src.v3.normalize import normalize


class TestNormalize:
    def test_empty_input(self):
        result = normalize("")
        assert result["title"] == "Untitled Presentation"
        assert result["metadata"]["word_count"] == 0
        assert len(result["sections"]) == 1

    def test_markdown_with_headings(self):
        text = "# My Deck\n\n## Revenue\n\nQ3 grew 14%.\n\n## Costs\n\nDown 5% YoY."
        result = normalize(text)
        assert result["title"] == "My Deck"
        assert result["metadata"]["source_type"] == "document"
        assert len(result["sections"]) >= 2
        assert any(s["heading"] == "Revenue" for s in result["sections"])

    def test_plain_text_paragraphs(self):
        text = "First topic here.\n\nSecond topic with more detail.\n\nThird topic."
        result = normalize(text)
        assert result["metadata"]["source_type"] == "text"
        assert len(result["sections"]) == 3

    def test_slide_count_hint_extracted(self):
        text = "# Strategy\n\nCreate 5 slides about our growth strategy."
        result = normalize(text)
        assert result["metadata"]["slide_count_hint"] == 5

    def test_audience_extracted(self):
        text = "# Pitch\n\nAudience: Board of Directors\n\nOur revenue grew 14%."
        result = normalize(text)
        assert result["audience"] == "Board of Directors"

    def test_density_extracted(self):
        text = "# Overview\n\nCreate a detailed presentation about AI adoption."
        result = normalize(text)
        assert result["metadata"]["density_preference"] == "high"

    def test_bullets_extracted(self):
        text = "# Plan\n\n## Steps\n\n- Step one\n- Step two\n- Step three"
        result = normalize(text)
        steps_section = [s for s in result["sections"] if s["heading"] == "Steps"]
        assert len(steps_section) == 1
        assert steps_section[0]["bullets"] == ["Step one", "Step two", "Step three"]

    def test_numbered_list_extracted(self):
        text = "# Plan\n\n## Steps\n\n1. First\n2. Second\n3. Third"
        result = normalize(text)
        steps_section = [s for s in result["sections"] if s["heading"] == "Steps"]
        assert len(steps_section) == 1
        assert steps_section[0]["bullets"] == ["First", "Second", "Third"]

    def test_word_count_correct(self):
        text = "one two three four five"
        result = normalize(text)
        assert result["metadata"]["word_count"] == 5

    def test_title_from_first_line(self):
        text = "A short first line\n\nMore content here."
        result = normalize(text)
        assert result["title"] == "A short first line"

    def test_slide_count_hint_ignored_if_too_large(self):
        text = "Create 50 slides about nothing."
        result = normalize(text)
        assert "slide_count_hint" not in result["metadata"]

    def test_low_density_keywords(self):
        text = "Create a brief overview of the project."
        result = normalize(text)
        assert result["metadata"]["density_preference"] == "low"

    def test_sections_have_content(self):
        text = "# Title\n\n## Section A\n\nContent A here.\n\n## Section B\n\nContent B here."
        result = normalize(text)
        for section in result["sections"]:
            if section["heading"] not in ("Title",):
                assert section["body"] or section.get("bullets")

    def test_whitespace_only_treated_as_empty(self):
        result = normalize("   \n\n  \t  ")
        assert result["title"] == "Untitled Presentation"
        assert result["metadata"]["word_count"] == 0
