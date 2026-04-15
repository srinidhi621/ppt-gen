"""Tests for src.v3.planner — deck plan validation and prompt assembly."""

from __future__ import annotations

import pytest
from src.v3.planner import (
    validate_deck_plan,
    ARCHETYPE_VOCABULARY,
    SUPPORTED_ARCHETYPES,
    _build_user_message,
)


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

    def test_invented_archetype_rejected(self):
        plan = _minimal_plan(slides=[_minimal_slide(archetype="invented_type")])
        errors = validate_deck_plan(plan)
        assert any("not in vocabulary" in e or "archetype" in e for e in errors)

    def test_unsupported_archetype_rejected(self):
        """Archetypes in vocabulary but not backed by examples are rejected.

        These fail at the JSON Schema level (enum restriction) before
        semantic checks run, so the error message comes from the schema.
        """
        unsupported = set(ARCHETYPE_VOCABULARY) - SUPPORTED_ARCHETYPES
        for archetype in sorted(unsupported):
            plan = _minimal_plan(slides=[_minimal_slide(archetype=archetype)])
            errors = validate_deck_plan(plan)
            assert errors, f"Unsupported archetype '{archetype}' was not rejected"

    def test_all_supported_archetypes_accepted(self):
        """Each supported archetype with its required fields passes."""
        archetype_extras = {
            "hero_title": {},
            "hero_statement_with_support_columns": {
                "supports": [{"label": "A", "body": "x"}],
            },
            "comparison_split": {
                "cards": [{"title": "Left", "body": "x"}, {"title": "Right", "body": "y"}],
            },
            "content_with_visual": {
                "body": "Some text",
                "visual_intent": {"must_include": ["chart"]},
            },
            "process_flow": {
                "steps": [{"label": "Step 1", "body": "Do it"}],
            },
            "timeline_roadmap": {
                "steps": [{"label": "Phase 1", "body": "Begin"}],
            },
        }
        for archetype in SUPPORTED_ARCHETYPES:
            extras = archetype_extras.get(archetype, {})
            plan = _minimal_plan(slides=[_minimal_slide(archetype=archetype, **extras)])
            errors = validate_deck_plan(plan)
            assert errors == [], f"Supported archetype {archetype} rejected: {errors}"

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
            _minimal_slide(slide_id="s2", archetype="comparison_split",
                           cards=[{"title": "A", "body": "x"}, {"title": "B", "body": "y"}]),
            _minimal_slide(slide_id="s3", archetype="process_flow",
                           steps=[{"label": "S1", "body": "Do"}]),
        ])
        errors = validate_deck_plan(plan)
        assert errors == []

    # ------------------------------------------------------------------
    # Archetype-specific required fields
    # ------------------------------------------------------------------

    def test_process_flow_without_steps_rejected(self):
        plan = _minimal_plan(slides=[_minimal_slide(archetype="process_flow")])
        errors = validate_deck_plan(plan)
        assert any("requires 'steps'" in e for e in errors)

    def test_process_flow_with_steps_passes(self):
        plan = _minimal_plan(slides=[_minimal_slide(
            archetype="process_flow",
            steps=[{"label": "Step 1", "body": "Do it"}],
        )])
        errors = validate_deck_plan(plan)
        assert errors == []

    def test_comparison_split_without_cards_rejected(self):
        plan = _minimal_plan(slides=[_minimal_slide(archetype="comparison_split")])
        errors = validate_deck_plan(plan)
        assert any("requires 'cards'" in e for e in errors)

    def test_hero_statement_without_supports_rejected(self):
        plan = _minimal_plan(slides=[_minimal_slide(
            archetype="hero_statement_with_support_columns"
        )])
        errors = validate_deck_plan(plan)
        assert any("requires 'supports'" in e for e in errors)

    def test_hero_statement_with_supports_passes(self):
        plan = _minimal_plan(slides=[_minimal_slide(
            archetype="hero_statement_with_support_columns",
            supports=[{"label": "A", "body": "x"}],
        )])
        errors = validate_deck_plan(plan)
        assert errors == []

    def test_content_with_visual_without_visual_intent_rejected(self):
        plan = _minimal_plan(slides=[_minimal_slide(
            archetype="content_with_visual",
            body="Some text",
        )])
        errors = validate_deck_plan(plan)
        assert any("requires 'visual_intent'" in e for e in errors)

    def test_content_with_visual_without_body_rejected(self):
        plan = _minimal_plan(slides=[_minimal_slide(
            archetype="content_with_visual",
            visual_intent={"must_include": ["chart"]},
        )])
        errors = validate_deck_plan(plan)
        assert any("requires 'body'" in e for e in errors)

    def test_content_with_visual_complete_passes(self):
        plan = _minimal_plan(slides=[_minimal_slide(
            archetype="content_with_visual",
            body="Some text",
            visual_intent={"must_include": ["chart"]},
        )])
        errors = validate_deck_plan(plan)
        assert errors == []

    def test_timeline_roadmap_without_steps_rejected(self):
        plan = _minimal_plan(slides=[_minimal_slide(archetype="timeline_roadmap")])
        errors = validate_deck_plan(plan)
        assert any("requires 'steps'" in e for e in errors)

    def test_timeline_roadmap_with_steps_passes(self):
        plan = _minimal_plan(slides=[_minimal_slide(
            archetype="timeline_roadmap",
            steps=[{"label": "Phase 1", "body": "Begin"}],
        )])
        errors = validate_deck_plan(plan)
        assert errors == []

    def test_hero_title_needs_no_extra_fields(self):
        """hero_title only requires the globally-required fields."""
        plan = _minimal_plan(slides=[_minimal_slide(archetype="hero_title")])
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

    def test_includes_supported_archetypes_only(self):
        nc = {"title": "Test", "sections": [{"heading": "S1", "body": "x"}], "metadata": {}}
        msg = _build_user_message(nc)
        assert "hero_title" in msg
        assert "process_flow" in msg
        # Unsupported archetypes must NOT appear in the user message
        assert "three_cards" not in msg
        assert "kpi_grid" not in msg
        assert "matrix_grid" not in msg

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
