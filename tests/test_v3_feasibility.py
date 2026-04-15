"""Tests for src.v3.feasibility — capacity gate."""

from __future__ import annotations

import pytest
from src.v3.feasibility import check_feasibility, _count_slide_words, _count_slide_items


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slide(archetype: str = "hero_title", **kwargs) -> dict:
    base = {
        "slide_id": "test",
        "archetype": archetype,
        "purpose": "test",
        "audience_takeaway": "Test takeaway.",
        "headline": "Test headline",
    }
    base.update(kwargs)
    return base


def _plan(*slides) -> dict:
    return {"slides": list(slides)}


# ---------------------------------------------------------------------------
# check_feasibility
# ---------------------------------------------------------------------------

class TestCheckFeasibility:
    def test_minimal_plan_passes(self):
        result = check_feasibility(_plan(_slide("hero_title")))
        assert result["passed"] is True
        assert result["violations"] == []
        assert result["passing_slides"] == [0]

    def test_unknown_archetype_fails(self):
        result = check_feasibility(_plan(_slide("made_up_type")))
        assert result["passed"] is False
        assert len(result["violations"]) == 1
        assert "Unknown archetype" in result["violations"][0]["issues"][0]

    def test_word_count_exceeds_max(self):
        # hero_title max_words = 30
        long_body = " ".join(["word"] * 35)
        slide = _slide("hero_title", body=long_body)
        result = check_feasibility(_plan(slide))
        assert result["passed"] is False
        assert any("Word count" in issue for v in result["violations"] for issue in v["issues"])

    def test_word_count_at_limit_passes(self):
        # hero_title max_words = 30; headline ~ 2 words
        body = " ".join(["word"] * 27)
        slide = _slide("hero_title", body=body)
        result = check_feasibility(_plan(slide))
        assert result["passed"] is True

    def test_mixed_pass_and_fail(self):
        good = _slide("hero_title", slide_id="good")
        bad = _slide("hero_title", slide_id="bad", body=" ".join(["word"] * 40))
        result = check_feasibility(_plan(good, bad))
        assert result["passed"] is False
        assert len(result["violations"]) == 1
        assert result["violations"][0]["slide_id"] == "bad"
        assert result["passing_slides"] == [0]


# ---------------------------------------------------------------------------
# Archetype-specific item counting: hero_title
# ---------------------------------------------------------------------------

class TestHeroTitleItems:
    def test_headline_only(self):
        slide = _slide("hero_title")
        assert _count_slide_items(slide) == 1  # headline only

    def test_headline_and_body(self):
        slide = _slide("hero_title", body="Subhead text")
        assert _count_slide_items(slide) == 2

    def test_three_items_exceeds_max(self):
        # max_items=2, but hero_title only counts headline+body so can't exceed
        slide = _slide("hero_title", body="Sub")
        result = check_feasibility(_plan(slide))
        assert result["passed"] is True


# ---------------------------------------------------------------------------
# Archetype-specific item counting: hero_statement_with_support_columns
# ---------------------------------------------------------------------------

class TestHeroStatementItems:
    def test_supports_count(self):
        slide = _slide("hero_statement_with_support_columns", supports=[
            {"label": "A", "body": "x"},
            {"label": "B", "body": "y"},
            {"label": "C", "body": "z"},
        ])
        assert _count_slide_items(slide) == 3

    def test_four_supports_at_limit(self):
        slide = _slide("hero_statement_with_support_columns", supports=[
            {"label": "A", "body": "x"},
            {"label": "B", "body": "y"},
            {"label": "C", "body": "z"},
            {"label": "D", "body": "w"},
        ])
        result = check_feasibility(_plan(slide))
        assert result["passed"] is True

    def test_five_supports_exceeds_max(self):
        slide = _slide("hero_statement_with_support_columns", supports=[
            {"label": f"S{i}", "body": "x"} for i in range(5)
        ])
        result = check_feasibility(_plan(slide))
        assert result["passed"] is False
        assert any("Item count" in issue for v in result["violations"] for issue in v["issues"])


# ---------------------------------------------------------------------------
# Archetype-specific item counting: comparison_split
# ---------------------------------------------------------------------------

class TestComparisonSplitItems:
    def test_two_cards_with_single_line_bodies(self):
        """2 cards with single-line bodies = 2 items, well under max_items=8."""
        slide = _slide("comparison_split", cards=[
            {"title": "Before", "body": "Old way"},
            {"title": "After", "body": "New way"},
        ])
        assert _count_slide_items(slide) == 2
        result = check_feasibility(_plan(slide))
        assert result["passed"] is True

    def test_multiline_bodies_count_points(self):
        """Comparison points in body lines are counted individually."""
        slide = _slide("comparison_split", cards=[
            {"title": "Before", "body": "Point A\nPoint B\nPoint C"},
            {"title": "After", "body": "Point D\nPoint E\nPoint F"},
        ])
        assert _count_slide_items(slide) == 6

    def test_nine_points_exceeds_max(self):
        """max_items=8: 9 total points should fail."""
        slide = _slide("comparison_split", cards=[
            {"title": "Before", "body": "\n".join([f"Point {i}" for i in range(5)])},
            {"title": "After", "body": "\n".join([f"Point {i}" for i in range(5)])},
        ])
        assert _count_slide_items(slide) == 10
        result = check_feasibility(_plan(slide))
        assert result["passed"] is False


# ---------------------------------------------------------------------------
# Archetype-specific item counting: quote_callout
# ---------------------------------------------------------------------------

class TestQuoteCalloutItems:
    def test_quote_is_single_item(self):
        """A valid quote_callout always counts as 1 item (the quote itself)."""
        slide = _slide("quote_callout", body="— Albert Einstein")
        assert _count_slide_items(slide) == 1

    def test_quote_passes_feasibility(self):
        """max_items=1: a normal quote_callout should pass."""
        slide = _slide("quote_callout", body="— Attribution")
        result = check_feasibility(_plan(slide))
        assert result["passed"] is True


# ---------------------------------------------------------------------------
# Archetype-specific item counting: kpi_grid
# ---------------------------------------------------------------------------

class TestKpiGridItems:
    def test_four_metrics_passes(self):
        slide = _slide("kpi_grid", metrics=[
            {"value": "14%", "label": "Revenue Growth"},
            {"value": "$2.1M", "label": "ARR"},
            {"value": "98%", "label": "Uptime"},
            {"value": "4.8", "label": "NPS Score"},
        ])
        assert _count_slide_items(slide) == 4
        result = check_feasibility(_plan(slide))
        assert result["passed"] is True

    def test_seven_metrics_exceeds_max(self):
        slide = _slide("kpi_grid", metrics=[
            {"value": str(i), "label": f"Metric {i}"} for i in range(7)
        ])
        assert _count_slide_items(slide) == 7
        result = check_feasibility(_plan(slide))
        assert result["passed"] is False


# ---------------------------------------------------------------------------
# Archetype-specific item counting: process_flow
# ---------------------------------------------------------------------------

class TestProcessFlowItems:
    def test_six_steps_at_limit(self):
        slide = _slide("process_flow", steps=[
            {"label": f"Step {i}", "body": "Do the thing"} for i in range(6)
        ])
        assert _count_slide_items(slide) == 6
        result = check_feasibility(_plan(slide))
        assert result["passed"] is True

    def test_seven_steps_exceeds_max(self):
        slide = _slide("process_flow", steps=[
            {"label": f"Step {i}", "body": "Do the thing"} for i in range(7)
        ])
        result = check_feasibility(_plan(slide))
        assert result["passed"] is False


# ---------------------------------------------------------------------------
# Archetype-specific item counting: content_with_visual
# ---------------------------------------------------------------------------

class TestContentWithVisualItems:
    def test_body_and_visual_counts_two(self):
        slide = _slide("content_with_visual",
                        body="Some text",
                        visual_intent={"must_include": ["chart"]})
        assert _count_slide_items(slide) == 2

    def test_passes_feasibility(self):
        slide = _slide("content_with_visual",
                        body="Some text",
                        visual_intent={"must_include": ["chart"]})
        result = check_feasibility(_plan(slide))
        assert result["passed"] is True


# ---------------------------------------------------------------------------
# Archetype-specific item counting: timeline_roadmap
# ---------------------------------------------------------------------------

class TestTimelineRoadmapItems:
    def test_five_phases_at_limit(self):
        slide = _slide("timeline_roadmap", steps=[
            {"label": f"Phase {i}", "body": "Description"} for i in range(5)
        ])
        assert _count_slide_items(slide) == 5
        result = check_feasibility(_plan(slide))
        assert result["passed"] is True

    def test_six_phases_exceeds_max(self):
        slide = _slide("timeline_roadmap", steps=[
            {"label": f"Phase {i}", "body": "Description"} for i in range(6)
        ])
        result = check_feasibility(_plan(slide))
        assert result["passed"] is False


# ---------------------------------------------------------------------------
# _count_slide_words
# ---------------------------------------------------------------------------

class TestCountSlideWords:
    def test_headline_only(self):
        assert _count_slide_words({"headline": "Three word headline"}) == 3

    def test_multiple_fields(self):
        slide = {"headline": "Two words", "body": "Three more words", "kicker": "One"}
        assert _count_slide_words(slide) == 6

    def test_bullets(self):
        slide = {"headline": "Title", "bullets": ["one two", "three four five"]}
        assert _count_slide_words(slide) == 6  # 1 (Title) + 2 + 3

    def test_cards(self):
        slide = {"headline": "H", "cards": [{"title": "A B", "body": "C D E"}]}
        assert _count_slide_words(slide) == 6  # 1 + 2 + 3

    def test_metrics(self):
        slide = {"headline": "H", "metrics": [{"value": "14%", "label": "Growth Rate"}]}
        assert _count_slide_words(slide) == 4  # 1 + 1 + 2

    def test_steps(self):
        slide = {"headline": "H", "steps": [{"label": "Step One", "body": "Do it"}]}
        assert _count_slide_words(slide) == 5  # 1 + 2 + 2
