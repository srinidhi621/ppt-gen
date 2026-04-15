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

    def test_item_count_exceeds_max(self):
        # three_cards max_items = 3
        slide = _slide("three_cards", cards=[
            {"title": "A", "body": "x"},
            {"title": "B", "body": "x"},
            {"title": "C", "body": "x"},
            {"title": "D", "body": "x"},
        ])
        result = check_feasibility(_plan(slide))
        assert result["passed"] is False
        assert any("Item count" in issue for v in result["violations"] for issue in v["issues"])

    def test_item_count_at_limit_passes(self):
        # three_cards max_items = 3
        slide = _slide("three_cards", cards=[
            {"title": "A", "body": "x"},
            {"title": "B", "body": "x"},
            {"title": "C", "body": "x"},
        ])
        result = check_feasibility(_plan(slide))
        assert result["passed"] is True

    def test_kpi_grid_metrics(self):
        # kpi_grid max_items = 6, max_words = 60
        slide = _slide("kpi_grid", metrics=[
            {"value": "14%", "label": "Revenue Growth"},
            {"value": "$2.1M", "label": "ARR"},
            {"value": "98%", "label": "Uptime"},
            {"value": "4.8", "label": "NPS Score"},
        ])
        result = check_feasibility(_plan(slide))
        assert result["passed"] is True

    def test_kpi_grid_too_many_metrics(self):
        # kpi_grid max_items = 6
        slide = _slide("kpi_grid", metrics=[
            {"value": str(i), "label": f"Metric {i}"} for i in range(8)
        ])
        result = check_feasibility(_plan(slide))
        assert result["passed"] is False

    def test_mixed_pass_and_fail(self):
        good = _slide("hero_title", slide_id="good")
        bad = _slide("hero_title", slide_id="bad", body=" ".join(["word"] * 40))
        result = check_feasibility(_plan(good, bad))
        assert result["passed"] is False
        assert len(result["violations"]) == 1
        assert result["violations"][0]["slide_id"] == "bad"
        assert result["passing_slides"] == [0]

    def test_process_flow_steps(self):
        slide = _slide("process_flow", steps=[
            {"label": f"Step {i}", "body": "Do the thing"} for i in range(6)
        ])
        result = check_feasibility(_plan(slide))
        assert result["passed"] is True

    def test_process_flow_too_many_steps(self):
        slide = _slide("process_flow", steps=[
            {"label": f"Step {i}", "body": "Do the thing"} for i in range(8)
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


# ---------------------------------------------------------------------------
# _count_slide_items
# ---------------------------------------------------------------------------

class TestCountSlideItems:
    def test_cards(self):
        slide = {"cards": [{"title": "A", "body": "x"}, {"title": "B", "body": "x"}]}
        assert _count_slide_items(slide) == 2

    def test_metrics(self):
        slide = {"metrics": [{"value": "1", "label": "a"}, {"value": "2", "label": "b"}]}
        assert _count_slide_items(slide) == 2

    def test_no_collections(self):
        slide = {"headline": "H", "body": "B"}
        assert _count_slide_items(slide) == 2

    def test_steps(self):
        slide = {"steps": [{"label": "S1"}, {"label": "S2"}, {"label": "S3"}]}
        assert _count_slide_items(slide) == 3
