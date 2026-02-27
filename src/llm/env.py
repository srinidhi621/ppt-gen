"""Minimal .env loader for local development."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict


def load_dotenv(dotenv_path: Path) -> Dict[str, str]:
    """Load KEY=VALUE lines from .env into process env if missing.

    Existing environment variables win over .env values.
    """
    loaded: Dict[str, str] = {}
    if not dotenv_path.exists():
        return loaded

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = _strip_quotes(value.strip())
        if not key:
            continue
        if key not in os.environ:
            os.environ[key] = value
        loaded[key] = os.environ.get(key, value)
    return loaded


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and (
        (value[0] == "'" and value[-1] == "'")
        or (value[0] == '"' and value[-1] == '"')
    ):
        return value[1:-1]
    return value
