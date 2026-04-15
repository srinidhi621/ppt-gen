"""Tests for src.v3.planner — deck plan validation and prompt assembly."""

from __future__ import annotations

import pytest
from src.v3.planner import validate_deck_plan, ARCHETYPE_VOCABULARY, _build_user_message


# ---------------------------------------------------------------------------
# validate_deck_plan
# ---------------------------------------------------------------------------

def _minimal_slide(**overrides) -> dict:
    """Build a minimal valid slide dict."""
    slide = {
        "slide_id": "test_slide",
        "archetype": "hero_title",
        "canvas": "header_dark",
        "purpose": "introduce",
        "audience_takeaway": "This is the test takeaway.",
        "headline": "Test headline with a verb",
    }
    slide.update(overrides)
    return slide


def _minimal_plan(**overrides) -> dict:
    """Build a minimal valid deck plan."""
    plan = {
        "slides": [_minimal_slide()],
    }
    plan.update(overrides)
    return plan


class TestValidateDeckPlan:
    def test_valid_minimal_plan(self):
        errors = validate_deck_plan(_minimal_plan())
        assert errors == []

    def test_missing_slides_key(self):
        errors = validate_deck_plan({})
        assert any("slides" in e for e in errors)

    def test_empty_slides_array(self):
        errors = validate_deck_plan({"slides": []})
        assert any("minItems" in e or "slides" in e for e in errors)

    def test_invalid_archetype(self):
        plan = _minimal_plan(slides=[_minimal_slide(archetype="invented_type")])
        errors = validate_deck_plan(plan)
        assert any("not in vocabulary" in e or "archetype" in e for e in errors)

    def test_all_archetypes_accepted(self):
        for archetype in ARCHETYPE_VOCABULARY:
            plan = _minimal_plan(slides=[_minimal_slide(archetype=archetype)])
            errors = validate_deck_plan(plan)
            assert errors == [], f"Archetype {archetype} rejected: {errors}"

    def test_forbidden_field_left(self):
        slide = _minimal_slide()
        slide["left_margin"] = 100
        plan = _minimal_plan(slides=[slide])
        errors = validate_deck_plan(plan)
        assert any("forbidden" in e.lower() for e in errors)

    def test_forbidden_field_hex(self):
        slide = _minimal_slide()
        slide["hex_color"] = "#FF0000"
        plan = _minimal_plan(slides=[slide])
        errors = validate_deck_plan(plan)
        assert any("forbidden" in e.lower() for e in errors)

    def test_forbidden_field_size_pt(self):
        slide = _minimal_slide()
        slide["font_size_pt"] = 12
        plan = _minimal_plan(slides=[slide])
        errors = validate_deck_plan(plan)
        assert any("forbidden" in e.lower() for e in errors)

    def test_missing_purpose(self):
        slide = _minimal_slide(purpose="")
        plan = _minimal_plan(slides=[slide])
        errors = validate_deck_plan(plan)
        assert any("purpose" in e for e in errors)

    def test_missing_audience_takeaway(self):
        slide = _minimal_slide(audience_takeaway="")
        plan = _minimal_plan(slides=[slide])
        errors = validate_deck_plan(plan)
        assert any("audience_takeaway" in e for e in errors)

    def test_missing_headline(self):
        slide = _minimal_slide(headline="")
        plan = _minimal_plan(slides=[slide])
        errors = validate_deck_plan(plan)
        assert any("headline" in e for e in errors)

    def test_multiple_slides_validated(self):
        plan = _minimal_plan(slides=[
            _minimal_slide(slide_id="s1", archetype="hero_title"),
            _minimal_slide(slide_id="s2", archetype="three_cards"),
            _minimal_slide(slide_id="s3", archetype="closing_cta"),
        ])
        errors = validate_deck_plan(plan)
        assert errors == []

    def test_style_contract_accepted(self):
        plan = _minimal_plan(style_contract={
            "tone": "executive_formal",
            "density": "medium",
            "accent_strategy": "monochrome_plus_one",
            "illustrative_richness": "minimal",
        })
        errors = validate_deck_plan(plan)
        assert errors == []


# ---------------------------------------------------------------------------
# _build_user_message
# ---------------------------------------------------------------------------

class TestBuildUserMessage:
    def test_includes_title(self):
        nc = {"title": "Test Deck", "sections": [{"heading": "S1", "body": "content"}], "metadata": {}}
        msg = _build_user_message(nc)
        assert "Test Deck" in msg

    def test_includes_audience(self):
        nc = {"title": "Test", "audience": "Board of Directors",
              "sections": [{"heading": "S1", "body": "content"}], "metadata": {}}
        msg = _build_user_message(nc)
        assert "Board of Directors" in msg

    def test_includes_slide_count_hint(self):
        nc = {"title": "Test", "sections": [{"heading": "S1", "body": "x"}],
              "metadata": {"slide_count_hint": 5}}
        msg = _build_user_message(nc)
        assert "5" in msg

    def test_includes_archetype_list(self):
        nc = {"title": "Test", "sections": [{"heading": "S1", "body": "x"}], "metadata": {}}
        msg = _build_user_message(nc)
        assert "hero_title" in msg
        assert "three_cards" in msg

    def test_includes_section_content(self):
        nc = {"title": "Test", "sections": [{"heading": "Revenue", "body": "Q3 grew 14%"}], "metadata": {}}
        msg = _build_user_message(nc)
        assert "Revenue" in msg
        assert "Q3 grew 14%" in msg

    def test_includes_bullets(self):
        nc = {"title": "Test", "sections": [
            {"heading": "Steps", "body": "", "bullets": ["Step one", "Step two"]}
        ], "metadata": {}}
        msg = _build_user_message(nc)
        assert "- Step one" in msg
        assert "- Step two" in msg
