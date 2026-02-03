"""DeckIR contracts."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import Field, constr

from .base import PptxBaseModel

NonEmptyStr = constr(min_length=1)
AssetType = Union[Literal["icon"], Literal["image"]]

FieldValue = Union[str, List[str]]


class AssetRef(PptxBaseModel):
    asset_type: AssetType = Field(..., description="icon|image")
    asset_id: NonEmptyStr = Field(..., description="icon_id or image reference")
    target_field_key: Optional[NonEmptyStr] = None


class DeckSlide(PptxBaseModel):
    slide_id: NonEmptyStr
    layout_id: NonEmptyStr
    fields: Dict[str, FieldValue]
    speaker_notes: Optional[Union[str, Dict[str, Any]]] = ""
    asset_refs: List[AssetRef] = Field(default_factory=list)
    constraints_override: Optional[Dict[str, Any]] = None


class DeckIR(PptxBaseModel):
    deck_id: NonEmptyStr
    run_id: NonEmptyStr
    template_id: NonEmptyStr
    title: NonEmptyStr
    subtitle: Optional[NonEmptyStr] = None
    global_constraints: Dict[str, Any] = Field(default_factory=dict)
    slides: List[DeckSlide]
