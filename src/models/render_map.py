"""RenderMap contracts."""

from __future__ import annotations

from typing import Dict, List

from pydantic import Field

from .base import PptxBaseModel


class RenderMapEntry(PptxBaseModel):
    slide_id: str
    slide_index: int
    field_keys: List[str] = Field(default_factory=list)


class RenderMap(PptxBaseModel):
    entries: Dict[str, RenderMapEntry] = Field(default_factory=dict)
