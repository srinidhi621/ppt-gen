"""PatchSet contracts."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import Field

from .base import PptxBaseModel

PatchType = Literal[
    "REWRITE_FIELD_TEXT",
    "DROP_BULLETS",
    "MOVE_TO_SPEAKER_NOTES",
    "SPLIT_SLIDE",
    "CHANGE_LAYOUT",
    "SWAP_ICON",
]


class Patch(PptxBaseModel):
    patch_type: PatchType
    target_slide_id: Optional[str] = None
    target_field_key: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)


class PatchSet(PptxBaseModel):
    patches: List[Patch] = Field(default_factory=list)
