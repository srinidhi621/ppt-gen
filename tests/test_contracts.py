"""Tests for src.contracts.validator — JSON schema validation."""

import pytest

from src.contracts.validator import validate


# ---------------------------------------------------------------------------
# Geometry report schema
# ---------------------------------------------------------------------------

class TestGeometryReportSchema:
    def test_valid_passing_report(self):
        report = {
            "pass": True,
            "blocking_count": 0,
            "warning_count": 0,
            "findings": [],
        }
        ok, errors = validate(report, "geometry_report")
        assert ok, f"Valid report failed: {errors}"

    def test_valid_failing_report(self):
        report = {
            "pass": False,
            "blocking_count": 1,
            "warning_count": 2,
            "findings": [
                {
                    "check_id": "VH-01",
                    "category": "Color",
                    "check_name": "All fills use palette tokens",
                    "severity": "BLOCKING",
                    "pass": False,
                    "slide_index": 0,
                    "details": "Shape 'Rect 1' has fill #FF0000",
                },
            ],
        }
        ok, errors = validate(report, "geometry_report")
        assert ok, f"Valid report failed: {errors}"

    def test_missing_pass_field(self):
        report = {
            "blocking_count": 0,
            "warning_count": 0,
            "findings": [],
        }
        ok, errors = validate(report, "geometry_report")
        assert not ok
        assert any("pass" in e for e in errors)

    def test_missing_findings(self):
        report = {
            "pass": True,
            "blocking_count": 0,
            "warning_count": 0,
        }
        ok, errors = validate(report, "geometry_report")
        assert not ok

    def test_invalid_severity(self):
        report = {
            "pass": False,
            "blocking_count": 1,
            "warning_count": 0,
            "findings": [
                {
                    "check_id": "VH-01",
                    "category": "Color",
                    "check_name": "test",
                    "severity": "CRITICAL",  # Invalid
                    "pass": False,
                    "slide_index": 0,
                    "details": "test",
                },
            ],
        }
        ok, errors = validate(report, "geometry_report")
        assert not ok

    def test_invalid_check_id_format(self):
        report = {
            "pass": False,
            "blocking_count": 1,
            "warning_count": 0,
            "findings": [
                {
                    "check_id": "INVALID",  # Invalid format
                    "category": "Color",
                    "check_name": "test",
                    "severity": "BLOCKING",
                    "pass": False,
                    "slide_index": 0,
                    "details": "test",
                },
            ],
        }
        ok, errors = validate(report, "geometry_report")
        assert not ok

    def test_extra_fields_rejected(self):
        report = {
            "pass": True,
            "blocking_count": 0,
            "warning_count": 0,
            "findings": [],
            "extra_field": "not allowed",
        }
        ok, errors = validate(report, "geometry_report")
        assert not ok


# ---------------------------------------------------------------------------
# Content fidelity report schema
# ---------------------------------------------------------------------------

class TestContentFidelityReportSchema:
    def test_valid_report(self):
        report = {
            "visible_coverage_score": 0.88,
            "notes_only_fact_count": 1,
            "total_facts": 12,
            "matched_visible_facts": 10,
            "matched_notes_only_facts": ["Q3 revenue grew 14%"],
            "dropped_facts": ["Q3 revenue grew 14%"],
            "hallucinated_specifics": [],
            "placeholder_leaks": [],
            "markdown_leaks": [],
        }
        ok, errors = validate(report, "content_fidelity_report")
        assert ok, f"Valid report failed: {errors}"

    def test_missing_coverage_score(self):
        report = {
            "notes_only_fact_count": 1,
            "total_facts": 12,
            "matched_visible_facts": 10,
            "matched_notes_only_facts": [],
            "dropped_facts": [],
            "hallucinated_specifics": [],
            "placeholder_leaks": [],
            "markdown_leaks": [],
        }
        ok, errors = validate(report, "content_fidelity_report")
        assert not ok

    def test_coverage_score_out_of_range(self):
        report = {
            "visible_coverage_score": 1.5,  # > 1
            "notes_only_fact_count": 0,
            "total_facts": 0,
            "matched_visible_facts": 0,
            "matched_notes_only_facts": [],
            "dropped_facts": [],
            "hallucinated_specifics": [],
            "placeholder_leaks": [],
            "markdown_leaks": [],
        }
        ok, errors = validate(report, "content_fidelity_report")
        assert not ok


# ---------------------------------------------------------------------------
# Deck plan schema
# ---------------------------------------------------------------------------

class TestDeckPlanSchema:
    def test_valid_deck_plan(self):
        plan = {
            "deck_title": "Q3 Review",
            "archetype": "report",
            "slides": [
                {
                    "slide_type": "title_slide",
                    "title": "Q3 Business Review",
                    "body": "Company performance overview",
                },
                {
                    "slide_type": "metrics",
                    "title": "Key Metrics",
                    "metrics": [
                        {"value": "14%", "label": "Revenue Growth"},
                    ],
                },
            ],
        }
        ok, errors = validate(plan, "deck_plan")
        assert ok, f"Valid plan failed: {errors}"

    def test_missing_slides(self):
        plan = {"deck_title": "Test"}
        ok, errors = validate(plan, "deck_plan")
        assert not ok

    def test_empty_slides(self):
        plan = {"slides": []}
        ok, errors = validate(plan, "deck_plan")
        assert not ok

    def test_slide_missing_title(self):
        plan = {
            "slides": [
                {"slide_type": "title_slide"},
            ],
        }
        ok, errors = validate(plan, "deck_plan")
        assert not ok


# ---------------------------------------------------------------------------
# Normalized content schema
# ---------------------------------------------------------------------------

class TestNormalizedContentSchema:
    def test_valid_content(self):
        content = {
            "title": "Q3 Review",
            "sections": [
                {"heading": "Overview", "body": "Q3 was strong"},
            ],
        }
        ok, errors = validate(content, "normalized_content")
        assert ok, f"Valid content failed: {errors}"

    def test_missing_title(self):
        content = {
            "sections": [
                {"heading": "Overview", "body": "Q3 was strong"},
            ],
        }
        ok, errors = validate(content, "normalized_content")
        assert not ok

    def test_empty_title(self):
        content = {
            "title": "",
            "sections": [
                {"heading": "Overview", "body": "Q3 was strong"},
            ],
        }
        ok, errors = validate(content, "normalized_content")
        assert not ok

    def test_missing_sections(self):
        content = {"title": "Test"}
        ok, errors = validate(content, "normalized_content")
        assert not ok


# ---------------------------------------------------------------------------
# Review feedback schema
# ---------------------------------------------------------------------------

class TestReviewFeedbackSchema:
    def test_valid_feedback(self):
        feedback = {
            "overall_score": 8.5,
            "pass": True,
            "issues": [],
            "strengths": ["Clear layout", "Good use of color"],
            "summary": "Well-designed deck",
        }
        ok, errors = validate(feedback, "review_feedback")
        assert ok, f"Valid feedback failed: {errors}"

    def test_missing_overall_score(self):
        feedback = {
            "issues": [],
        }
        ok, errors = validate(feedback, "review_feedback")
        assert not ok

    def test_score_out_of_range(self):
        feedback = {
            "overall_score": 11,  # > 10
            "issues": [],
        }
        ok, errors = validate(feedback, "review_feedback")
        assert not ok

    def test_valid_issue(self):
        feedback = {
            "overall_score": 6.0,
            "issues": [
                {
                    "slide_index": 2,
                    "severity": "major",
                    "description": "Title too long",
                    "category": "content",
                    "suggested_fix": "Shorten to < 8 words",
                },
            ],
        }
        ok, errors = validate(feedback, "review_feedback")
        assert ok, f"Valid feedback failed: {errors}"


# ---------------------------------------------------------------------------
# Build exec report schema
# ---------------------------------------------------------------------------

class TestBuildExecReportSchema:
    def test_valid_report(self):
        report = {
            "success": True,
            "slides_built": 5,
            "pptx_path": "/tmp/output.pptx",
            "errors": [],
            "warnings": [],
            "build_time_seconds": 2.34,
        }
        ok, errors = validate(report, "build_exec_report")
        assert ok, f"Valid report failed: {errors}"

    def test_missing_success(self):
        report = {
            "slides_built": 5,
            "pptx_path": "/tmp/output.pptx",
        }
        ok, errors = validate(report, "build_exec_report")
        assert not ok

    def test_missing_pptx_path(self):
        report = {
            "success": True,
            "slides_built": 5,
        }
        ok, errors = validate(report, "build_exec_report")
        assert not ok


# ---------------------------------------------------------------------------
# Validator edge cases
# ---------------------------------------------------------------------------

class TestValidatorEdgeCases:
    def test_unknown_schema(self):
        ok, errors = validate({}, "nonexistent_schema")
        assert not ok
        assert len(errors) > 0

    def test_schema_name_with_extension(self):
        """Can use full filename as schema name."""
        report = {
            "pass": True,
            "blocking_count": 0,
            "warning_count": 0,
            "findings": [],
        }
        ok, errors = validate(report, "geometry_report.schema.json")
        assert ok, f"Valid report with extension failed: {errors}"
