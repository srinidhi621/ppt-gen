"""ContentModel contracts."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import Field, constr

from .base import PptxBaseModel

NonEmptyStr = constr(min_length=1)


class ContentSection(PptxBaseModel):
    section_id: NonEmptyStr
    title: NonEmptyStr
    bullets: List[str] = Field(default_factory=list)
    paragraphs: List[str] = Field(default_factory=list)


class ContentCue(PptxBaseModel):
    section_id: NonEmptyStr
    layout_hint: Optional[str] = None
    notes: Optional[str] = None
    icon_hints: List[str] = Field(default_factory=list)
    image_hint: Optional[str] = None
    bullet_index: Optional[int] = None
    paragraph_index: Optional[int] = None


class ContentModel(PptxBaseModel):
    doc_id: NonEmptyStr
    version: NonEmptyStr
    source_hash: NonEmptyStr
    sections: List[ContentSection]
    entities: List[Dict[str, Any]] = Field(default_factory=list)
    metrics: List[Dict[str, Any]] = Field(default_factory=list)
    cues: List[ContentCue] = Field(default_factory=list)
