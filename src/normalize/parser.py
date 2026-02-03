"""Markdown to ContentModel parser (scaffold)."""

from __future__ import annotations

from pathlib import Path

from ..models.content import ContentModel


def parse_markdown(path: Path) -> ContentModel:
    """Parse Markdown into ContentModel."""
    raise NotImplementedError("Content normalization is not implemented yet")
