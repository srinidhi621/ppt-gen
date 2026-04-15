"""Schema validator for pipeline handoff payloads.

Usage::

    from src.contracts.validator import validate

    ok, errors = validate(my_report, "geometry_report")
    if not ok:
        print(errors)
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
