"""Schema and artifact validators for pipeline handoff payloads.

Usage::

    from src.contracts.validator import validate, validate_sandbox_to_scanner

    ok, errors = validate(my_report, "geometry_report")
    ok, errors = validate_sandbox_to_scanner("/path/to/output.pptx", deck_plan)
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

_SCHEMAS_DIR = Path(__file__).resolve().parent / "schemas"
_schema_cache: dict[str, dict] = {}


def _load_schema(schema_name: str) -> dict:
    """Load and cache a JSON Schema by name."""
    if schema_name not in _schema_cache:
        # Try with and without .schema.json extension
        filename = schema_name
        if not filename.endswith(".schema.json"):
            filename = f"{filename}.schema.json"
        path = _SCHEMAS_DIR / filename
        if not path.exists():
            raise FileNotFoundError(
                f"Schema '{schema_name}' not found at {path}. "
                f"Available: {[f.stem for f in _SCHEMAS_DIR.glob('*.schema.json')]}"
            )
        with open(path) as f:
            _schema_cache[schema_name] = json.load(f)
    return _schema_cache[schema_name]


def validate(payload: dict, schema_name: str) -> tuple[bool, list[str]]:
    """Validate a payload dict against a named JSON schema.

    Args:
        payload: The data dict to validate.
        schema_name: Schema name (e.g., 'geometry_report', 'deck_plan').
            May include or omit the '.schema.json' suffix.

    Returns:
        A tuple of (valid: bool, errors: list[str]).
        If valid is True, errors is empty.
    """
    try:
        schema = _load_schema(schema_name)
    except FileNotFoundError as e:
        return False, [str(e)]

    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(payload), key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append(f"{path}: {error.message}")

    return len(errors) == 0, errors


# ---------------------------------------------------------------------------
# Artifact validators for reachable handoffs
# ---------------------------------------------------------------------------

# Handoffs that are NOT yet wired in the pipeline are recorded here so the
# coverage matrix is honest.  Each will be implemented as its upstream
# pipeline stage lands.
PENDING_HANDOFFS = [
    "normalize_to_planner",      # SLICE-010
    "planner_to_feasibility",    # SLICE-010
    "feasibility_to_builder",    # SLICE-011
    "builder_to_sandbox",        # SLICE-009 (sandbox on separate branch)
    "reviewer_to_repair",        # SLICE-012
    "repair_to_accept",          # SLICE-012
]


def validate_sandbox_to_scanner(
    pptx_path: str | Path,
    deck_plan: dict | None = None,
    exec_report: dict | None = None,
) -> tuple[bool, list[str]]:
    """Validate the Sandbox → Scanner handoff.

    Checks:
    - Output PPTX file exists and is non-empty.
    - The file is a valid PPTX (can be opened by python-pptx).
    - If deck_plan is provided, slide count matches.
    - If exec_report is provided, it passes schema and reports success.
    """
    errors = []
    pptx_path = Path(pptx_path)

    # File existence
    if not pptx_path.exists():
        return False, [f"Output PPTX not found: {pptx_path}"]
    if pptx_path.stat().st_size == 0:
        return False, [f"Output PPTX is empty: {pptx_path}"]

    # Valid PPTX
    try:
        from pptx import Presentation
        prs = Presentation(str(pptx_path))
        slide_count = len(prs.slides)
    except Exception as e:
        return False, [f"Cannot open PPTX: {e}"]

    if slide_count == 0:
        errors.append("PPTX has zero slides")

    # Slide count matches plan
    if deck_plan is not None:
        planned_slides = len(deck_plan.get("slides", []))
        if planned_slides > 0 and slide_count != planned_slides:
            errors.append(
                f"Slide count {slide_count} does not match "
                f"deck_plan ({planned_slides} slides)"
            )

    # Exec report validation
    if exec_report is not None:
        ok, schema_errors = validate(exec_report, "build_exec_report")
        if not ok:
            errors.extend(
                f"exec_report: {e}" for e in schema_errors
            )
        elif not exec_report.get("success"):
            errors.append("exec_report reports failure")

    return len(errors) == 0, errors


def validate_scanner_to_reviewer(
    geometry_report: dict,
    content_fidelity_report: dict | None = None,
) -> tuple[bool, list[str]]:
    """Validate the Scanner/Fidelity → Reviewer handoff.

    Checks:
    - geometry_report passes schema.
    - Zero BLOCKING scanner findings (reviewer should not run on a broken deck).
    - If content_fidelity_report is provided, it passes schema.
    """
    errors = []

    # Schema validation
    ok, schema_errors = validate(geometry_report, "geometry_report")
    if not ok:
        errors.extend(f"geometry_report: {e}" for e in schema_errors)
        return False, errors

    # Zero BLOCKING findings
    blocking = [
        f for f in geometry_report.get("findings", [])
        if f.get("severity") == "BLOCKING"
    ]
    if blocking:
        errors.append(
            f"Scanner has {len(blocking)} BLOCKING finding(s); "
            f"reviewer must not run on a deck with mechanical failures"
        )

    # Content fidelity report
    if content_fidelity_report is not None:
        ok, schema_errors = validate(
            content_fidelity_report, "content_fidelity_report"
        )
        if not ok:
            errors.extend(
                f"content_fidelity_report: {e}" for e in schema_errors
            )

    return len(errors) == 0, errors
