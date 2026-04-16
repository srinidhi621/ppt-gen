"""Tests for src.v3.pipeline — end-to-end pipeline integration."""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.v3.builder import BuildAttempt, BuildResult
from src.v3.pipeline import generate


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


# ---------------------------------------------------------------------------
# Regression tests for PR #9 review fixes
# ---------------------------------------------------------------------------

class TestPipelineRegressions:
    """Regression tests for pipeline finalization (Fix #3)."""

    @patch("src.v3.pipeline.plan_deck")
    def test_run_summary_written_on_planner_failure(self, mock_plan, tmp_path):
        """Fix #3: run_summary.json must be written even when planner fails."""
        mock_plan.side_effect = RuntimeError("LLM down")

        result = generate(
            "Test",
            client=MagicMock(),
            runs_dir=tmp_path / "runs",
            run_id="fail_plan",
        )

        assert result.success is False
        run_dir = Path(result.run_dir)
        summary_path = run_dir / "run_summary.json"
        assert summary_path.exists(), "run_summary.json missing on planner failure"
        summary = json.loads(summary_path.read_text())
        assert summary["success"] is False
        assert summary["stage"] == "planner"
        assert "Planner failed" in summary["error"]

    @patch("src.v3.pipeline.check_feasibility")
    @patch("src.v3.pipeline.plan_deck")
    def test_run_summary_written_on_feasibility_rejection(self, mock_plan, mock_feasibility, tmp_path):
        """Fix #3: run_summary.json must be written when feasibility rejects."""
        mock_plan.return_value = _mock_deck_plan()
        mock_feasibility.return_value = {
            "passed": False,
            "violations": [{"slide_index": 0, "slide_id": "s1", "archetype": "hero_title", "issues": ["Too many"]}],
        }

        result = generate(
            "Test",
            client=MagicMock(),
            runs_dir=tmp_path / "runs",
            run_id="fail_feas",
        )

        assert result.success is False
        run_dir = Path(result.run_dir)
        summary_path = run_dir / "run_summary.json"
        assert summary_path.exists(), "run_summary.json missing on feasibility rejection"
        summary = json.loads(summary_path.read_text())
        assert summary["success"] is False
        assert summary["stage"] == "feasibility"

    @patch("src.v3.pipeline.build_deck")
    @patch("src.v3.pipeline.check_feasibility")
    @patch("src.v3.pipeline.plan_deck")
    def test_run_summary_has_duration_on_early_exit(self, mock_plan, mock_feasibility, mock_build, tmp_path):
        """Fix #3: duration_s must be set even on early exit paths."""
        mock_plan.side_effect = RuntimeError("fail")

        result = generate(
            "Test",
            client=MagicMock(),
            runs_dir=tmp_path / "runs",
            run_id="dur_test",
        )

        assert result.duration_s >= 0
        summary = json.loads((Path(result.run_dir) / "run_summary.json").read_text())
        assert "duration_s" in summary
        assert summary["stage"] == "planner"

    @patch("src.v3.pipeline.shutil.copy2", side_effect=OSError("disk full"))
    @patch("src.v3.pipeline.build_deck")
    @patch("src.v3.pipeline.check_feasibility")
    @patch("src.v3.pipeline.plan_deck")
    def test_copy_failure_surfaces_as_builder_error(
        self, mock_plan, mock_feasibility, mock_build, mock_copy, tmp_path
    ):
        """If shutil.copy2 fails after a successful build, the pipeline reports failure."""
        mock_plan.return_value = _mock_deck_plan()
        mock_feasibility.return_value = {"passed": True, "violations": []}
        mock_build.return_value = _mock_build_result(
            success=True, pptx_path="/tmp/deck.pptx"
        )

        result = generate(
            "Test",
            client=MagicMock(),
            runs_dir=tmp_path / "runs",
            run_id="copy_fail",
        )

        # The exception is caught by the outer try around Stage 4
        assert result.success is False
        assert "Builder failed" in result.error
        # run_summary.json is still written (finally block)
        summary_path = Path(result.run_dir) / "run_summary.json"
        assert summary_path.exists()

    @patch("src.v3.pipeline.build_deck")
    @patch("src.v3.pipeline.check_feasibility")
    @patch("src.v3.pipeline.plan_deck")
    def test_builder_input_json_persisted(self, mock_plan, mock_feasibility, mock_build, tmp_path):
        """builder_input.json must be written before the build starts (SPEC §8)."""
        mock_plan.return_value = _mock_deck_plan()
        mock_feasibility.return_value = {"passed": True, "violations": []}
        mock_build.return_value = _mock_build_result(success=False)

        result = generate(
            "Test",
            client=MagicMock(),
            runs_dir=tmp_path / "runs",
            run_id="bi_test",
        )

        run_dir = Path(result.run_dir)
        bi_path = run_dir / "builder_input.json"
        assert bi_path.exists(), "builder_input.json must be persisted"
        bi = json.loads(bi_path.read_text())
        assert "deck_plan" in bi
        assert bi["deck_plan"]["deck_id"] == "test-123"

    @patch("src.v3.pipeline.build_deck")
    @patch("src.v3.pipeline.check_feasibility")
    @patch("src.v3.pipeline.plan_deck")
    def test_build_attempts_dir_naming(self, mock_plan, mock_feasibility, mock_build, tmp_path):
        """Builder work_dir should be build_attempts/ (spec artifact naming)."""
        mock_plan.return_value = _mock_deck_plan()
        mock_feasibility.return_value = {"passed": True, "violations": []}
        mock_build.return_value = _mock_build_result(success=False)

        generate(
            "Test",
            client=MagicMock(),
            runs_dir=tmp_path / "runs",
            run_id="dir_test",
        )

        # Verify build_deck was called with build_attempts/ as work_dir
        call_kwargs = mock_build.call_args
        work_dir = call_kwargs.kwargs.get("work_dir") or call_kwargs[1].get("work_dir")
        assert work_dir is not None
        assert work_dir.name == "build_attempts"
