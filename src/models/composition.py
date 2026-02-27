"""CompositionSpec contracts for deterministic slide composition output."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import Field

from .base import PptxBaseModel
from .deck_ir import AssetRef

OverflowAction = Literal[
    "none",
    "drop_bullets",
    "condense",
    "move_to_speaker_notes",
    "split_slide",
    "rewrite",
    "change_layout",
    "unknown",
]
VisualRole = Literal["hero", "primary", "secondary", "accent"]
PlacementMode = Literal["fill", "contain", "centered_icon", "grid"]


class CompositionTextBlock(PptxBaseModel):
    field_key: str
    text: str
    font_size_pt: Optional[float] = None
    line_spacing_pt: Optional[float] = None
    overflow_action: OverflowAction = "none"


class CompositionVisualBlock(PptxBaseModel):
    target_field_key: str
    asset_ref: AssetRef
    role: VisualRole = "primary"
    placement_mode: PlacementMode = "contain"
    size_cap_pct: Optional[float] = None


class CompositionFitDiagnostics(PptxBaseModel):
    before: List[str] = Field(default_factory=list)
    after: List[str] = Field(default_factory=list)
    remediations: List[str] = Field(default_factory=list)


class CompositionSlide(PptxBaseModel):
    slide_id: str
    layout_id: str
    archetype: str
    text_blocks: List[CompositionTextBlock] = Field(default_factory=list)
    visual_blocks: List[CompositionVisualBlock] = Field(default_factory=list)
    notes_additions: List[str] = Field(default_factory=list)
    fit_diagnostics: CompositionFitDiagnostics = Field(
        default_factory=CompositionFitDiagnostics
    )


class CompositionSpec(PptxBaseModel):
    version: str = "1.0"
    stage: str
    slides: List[CompositionSlide] = Field(default_factory=list)
