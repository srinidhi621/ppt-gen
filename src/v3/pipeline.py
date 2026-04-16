"""V3 end-to-end pipeline: user text → PPTX.

Wires together normalize → planner → feasibility → builder → PPTX.
No review loop yet (that's SLICE-012).

Usage::

    from src.v3.pipeline import generate

    result = generate("Create a 5-slide deck about AI strategy...")
    print(result.pptx_path)  # path to the built PPTX

Or with an explicit client::

    from src.v3.llm_client import ResponsesClient
    from src.v3.pipeline import generate

    client = ResponsesClient.from_env()
    result = generate("...", client=client)
"""

from __future__ import annotations

import json
import logging
import shutil
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from src.v3.builder import BuildResult, build_deck
from src.v3.feasibility import check_feasibility
from src.v3.llm_client import ResponsesClient
from src.v3.normalize import normalize
from src.v3.planner import plan_deck

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_RUNS_DIR = _PROJECT_ROOT / "runs"


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class PipelineResult:
    """Result of a full pipeline run."""
    success: bool
    run_id: str = ""
    run_dir: str = ""
    pptx_path: str = ""
    deck_plan: Optional[dict] = None
    normalized_content: Optional[dict] = None
    build_result: Optional[BuildResult] = None
    feasibility: Optional[dict] = None
    scanner_report: Optional[dict] = None
    duration_s: float = 0.0
    error: str = ""
    stage: str = ""  # which stage succeeded or failed


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def generate(
    user_input: str,
    *,
    client: ResponsesClient | None = None,
    run_id: str | None = None,
    runs_dir: Path | None = None,
    max_build_attempts: int = 3,
) -> PipelineResult:
    """Run the full V3 pipeline from user text to PPTX.

    Stages:
    1. Normalize — parse user input
    2. Plan — LLM generates deck plan
    3. Feasibility — check capacity limits
    4. Build — LLM generates code, sandbox executes, scanner validates

    Parameters
    ----------
    user_input : str
        Raw user text describing the desired presentation.
    client : ResponsesClient, optional
        LLM client. Created from env if not provided.
    run_id : str, optional
        Unique run identifier. Generated if not provided.
    runs_dir : Path, optional
        Directory for run artifacts. Defaults to ``runs/``.
    max_build_attempts : int
        Max builder attempts (default 3).

    Returns
    -------
    PipelineResult
        Contains the PPTX path on success, or error details on failure.
    """
    t0 = time.monotonic()
    run_id = run_id or uuid.uuid4().hex[:12]
    runs_dir = runs_dir or _RUNS_DIR
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    result = PipelineResult(
        success=False,
        run_id=run_id,
        run_dir=str(run_dir),
    )

    # Create client if not provided
    if client is None:
        client = ResponsesClient.from_env()

    # ------------------------------------------------------------------
    # Stage 1: Normalize
    # ------------------------------------------------------------------
    logger.info("[%s] Stage 1: Normalize", run_id)
    result.stage = "normalize"
    try:
        normalized = normalize(user_input)
        result.normalized_content = normalized
        _write_artifact(run_dir / "normalized_content.json", normalized)
    except Exception as exc:
        result.error = f"Normalize failed: {exc}"
        result.duration_s = time.monotonic() - t0
        return result

    # ------------------------------------------------------------------
    # Stage 2: Plan
    # ------------------------------------------------------------------
    logger.info("[%s] Stage 2: Plan", run_id)
    result.stage = "planner"
    try:
        deck_plan = plan_deck(client, normalized)
        result.deck_plan = deck_plan
        _write_artifact(run_dir / "deck_plan.json", deck_plan)
    except Exception as exc:
        result.error = f"Planner failed: {exc}"
        result.duration_s = time.monotonic() - t0
        return result

    # ------------------------------------------------------------------
    # Stage 3: Feasibility
    # ------------------------------------------------------------------
    logger.info("[%s] Stage 3: Feasibility", run_id)
    result.stage = "feasibility"
    try:
        feasibility = check_feasibility(deck_plan)
        result.feasibility = feasibility
        _write_artifact(run_dir / "feasibility.json", feasibility)

        if not feasibility["passed"]:
            violations = feasibility.get("violations", [])
            msg = f"Feasibility gate rejected {len(violations)} slide(s)"
            for v in violations:
                msg += f"\n  - slide {v.get('slide_index')}: {v.get('issues', [])}"
            result.error = msg
            result.duration_s = time.monotonic() - t0
            return result
    except Exception as exc:
        result.error = f"Feasibility check failed: {exc}"
        result.duration_s = time.monotonic() - t0
        return result

    # ------------------------------------------------------------------
    # Stage 4: Build
    # ------------------------------------------------------------------
    logger.info("[%s] Stage 4: Build", run_id)
    result.stage = "builder"
    try:
        build_result = build_deck(
            client,
            deck_plan,
            max_attempts=max_build_attempts,
            work_dir=run_dir / "build",
            cleanup=False,  # Keep artifacts for inspection
        )
        result.build_result = build_result

        if build_result.success:
            # Copy PPTX to run root
            src_pptx = Path(build_result.pptx_path)
            dst_pptx = run_dir / "deck.pptx"
            shutil.copy2(src_pptx, dst_pptx)
            result.pptx_path = str(dst_pptx)
            result.success = True

            # Save build code
            (run_dir / "build_deck.py").write_text(
                build_result.code, encoding="utf-8"
            )

            # Save scanner report from last attempt
            last_attempt = build_result.attempts[-1] if build_result.attempts else None
            if last_attempt and last_attempt.scanner_report:
                result.scanner_report = last_attempt.scanner_report
                _write_artifact(
                    run_dir / "geometry_report.json",
                    last_attempt.scanner_report,
                )
        else:
            result.error = build_result.error or "Builder failed"
    except Exception as exc:
        result.error = f"Builder failed: {exc}"
        logger.exception("Builder exception in run %s", run_id)

    result.duration_s = time.monotonic() - t0

    # Write run summary
    _write_artifact(run_dir / "run_summary.json", {
        "run_id": run_id,
        "success": result.success,
        "stage": result.stage,
        "error": result.error,
        "duration_s": round(result.duration_s, 3),
        "pptx_path": result.pptx_path,
        "build_attempts": len(build_result.attempts) if result.build_result else 0,
        "total_input_tokens": build_result.total_input_tokens if result.build_result else 0,
        "total_output_tokens": build_result.total_output_tokens if result.build_result else 0,
    })

    logger.info(
        "[%s] Pipeline %s in %.1fs (stage: %s)",
        run_id,
        "succeeded" if result.success else "failed",
        result.duration_s,
        result.stage,
    )
    return result


def _write_artifact(path: Path, data: dict) -> None:
    """Write a JSON artifact file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
