"""Tests for src.v3.pipeline — end-to-end pipeline integration."""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.v3.builder import BuildAttempt, BuildResult
from src.v3.pipeline import PipelineResult, generate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _mock_deck_plan():
    """A minimal valid deck plan."""
    return {
        "deck_id": "test-123",
        "deck_title": "Test Presentation",
        "style_contract": {
            "tone": "executive_formal",
            "density": "medium",
            "accent_strategy": "monochrome_plus_one",
            "illustrative_richness": "minimal",
        },
        "slides": [
            {
                "slide_id": "s1",
                "archetype": "hero_title",
                "canvas": "header_dark",
                "purpose": "introduce",
                "audience_takeaway": "This is the title",
                "headline": "Test Presentation Title",
            },
        ],
        "metadata": {},
    }


def _mock_build_result(success=True, pptx_path="/tmp/deck.pptx"):
    """A mock BuildResult."""
    return BuildResult(
        success=success,
        code="print('OK')",
        pptx_path=pptx_path if success else "",
        attempts=[
            BuildAttempt(
                attempt=1,
                code="print('OK')",
                syntax_ok=True,
                ast_scan_ok=True,
                exec_success=success,
                scanner_pass=success,
                scanner_report={"blocking_count": 0, "findings": []} if success else None,
            )
        ],
        total_input_tokens=100,
        total_output_tokens=200,
    )


# ---------------------------------------------------------------------------
# Pipeline tests
# ---------------------------------------------------------------------------

class TestPipeline:
    @patch("src.v3.pipeline.build_deck")
    @patch("src.v3.pipeline.check_feasibility")
    @patch("src.v3.pipeline.plan_deck")
    def test_happy_path(self, mock_plan, mock_feasibility, mock_build, tmp_path):
        plan = _mock_deck_plan()
        mock_plan.return_value = plan
        mock_feasibility.return_value = {"passed": True, "violations": []}

        # Create a fake PPTX file for the build result
        pptx_src = tmp_path / "src_deck.pptx"
        pptx_src.write_bytes(b"fake pptx content")
        mock_build.return_value = _mock_build_result(
            success=True, pptx_path=str(pptx_src)
        )

        result = generate(
            "Create a test presentation",
            client=MagicMock(),
            runs_dir=tmp_path / "runs",
        )

        assert result.success is True
        assert result.pptx_path != ""
        assert Path(result.pptx_path).exists()
        assert result.deck_plan is not None
        assert result.stage == "builder"

    @patch("src.v3.pipeline.build_deck")
    @patch("src.v3.pipeline.check_feasibility")
    @patch("src.v3.pipeline.plan_deck")
    def test_writes_run_artifacts(self, mock_plan, mock_feasibility, mock_build, tmp_path):
        plan = _mock_deck_plan()
        mock_plan.return_value = plan
        mock_feasibility.return_value = {"passed": True, "violations": []}

        pptx_src = tmp_path / "src_deck.pptx"
        pptx_src.write_bytes(b"fake pptx")
        mock_build.return_value = _mock_build_result(
            success=True, pptx_path=str(pptx_src)
        )

        result = generate(
            "Test",
            client=MagicMock(),
            runs_dir=tmp_path / "runs",
            run_id="test_run",
        )

        run_dir = Path(result.run_dir)
        assert (run_dir / "normalized_content.json").exists()
        assert (run_dir / "deck_plan.json").exists()
        assert (run_dir / "feasibility.json").exists()
        assert (run_dir / "run_summary.json").exists()
        assert (run_dir / "deck.pptx").exists()
        assert (run_dir / "build_deck.py").exists()

        summary = json.loads((run_dir / "run_summary.json").read_text())
        assert summary["success"] is True
        assert summary["run_id"] == "test_run"

    @patch("src.v3.pipeline.plan_deck")
    def test_planner_failure_stops_pipeline(self, mock_plan, tmp_path):
        mock_plan.side_effect = RuntimeError("LLM down")

        result = generate(
            "Test",
            client=MagicMock(),
            runs_dir=tmp_path / "runs",
        )

        assert result.success is False
        assert result.stage == "planner"
        assert "Planner failed" in result.error

    @patch("src.v3.pipeline.check_feasibility")
    @patch("src.v3.pipeline.plan_deck")
    def test_feasibility_failure_stops_pipeline(self, mock_plan, mock_feasibility, tmp_path):
        mock_plan.return_value = _mock_deck_plan()
        mock_feasibility.return_value = {
            "passed": False,
            "violations": [
                {
                    "slide_index": 0,
                    "slide_id": "s1",
                    "archetype": "hero_title",
                    "issues": ["Too many items: 5 > 2"],
                }
            ],
        }

        result = generate(
            "Test",
            client=MagicMock(),
            runs_dir=tmp_path / "runs",
        )

        assert result.success is False
        assert result.stage == "feasibility"
        assert "rejected" in result.error

    @patch("src.v3.pipeline.build_deck")
    @patch("src.v3.pipeline.check_feasibility")
    @patch("src.v3.pipeline.plan_deck")
    def test_builder_failure(self, mock_plan, mock_feasibility, mock_build, tmp_path):
        mock_plan.return_value = _mock_deck_plan()
        mock_feasibility.return_value = {"passed": True, "violations": []}
        mock_build.return_value = _mock_build_result(success=False)

        result = generate(
            "Test",
            client=MagicMock(),
            runs_dir=tmp_path / "runs",
        )

        assert result.success is False
        assert result.stage == "builder"

    @patch("src.v3.pipeline.build_deck")
    @patch("src.v3.pipeline.check_feasibility")
    @patch("src.v3.pipeline.plan_deck")
    def test_run_id_generated_if_not_provided(self, mock_plan, mock_feasibility, mock_build, tmp_path):
        mock_plan.return_value = _mock_deck_plan()
        mock_feasibility.return_value = {"passed": True, "violations": []}

        pptx_src = tmp_path / "src_deck.pptx"
        pptx_src.write_bytes(b"fake")
        mock_build.return_value = _mock_build_result(
            success=True, pptx_path=str(pptx_src)
        )

        result = generate(
            "Test",
            client=MagicMock(),
            runs_dir=tmp_path / "runs",
        )

        assert result.run_id != ""
        assert len(result.run_id) == 12

    @patch("src.v3.pipeline.build_deck")
    @patch("src.v3.pipeline.check_feasibility")
    @patch("src.v3.pipeline.plan_deck")
    def test_duration_recorded(self, mock_plan, mock_feasibility, mock_build, tmp_path):
        mock_plan.return_value = _mock_deck_plan()
        mock_feasibility.return_value = {"passed": True, "violations": []}

        pptx_src = tmp_path / "src_deck.pptx"
        pptx_src.write_bytes(b"fake")
        mock_build.return_value = _mock_build_result(
            success=True, pptx_path=str(pptx_src)
        )

        result = generate(
            "Test",
            client=MagicMock(),
            runs_dir=tmp_path / "runs",
        )

        assert result.duration_s > 0

    def test_normalize_failure(self, tmp_path):
        """Empty input should still normalize successfully (graceful handling)."""
        with patch("src.v3.pipeline.plan_deck") as mock_plan:
            mock_plan.side_effect = RuntimeError("Plan failed")

            result = generate(
                "",
                client=MagicMock(),
                runs_dir=tmp_path / "runs",
            )

            # Normalize handles empty input; failure comes from planner
            assert result.success is False
            assert result.normalized_content is not None
