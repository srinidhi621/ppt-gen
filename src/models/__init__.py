"""Pydantic models for PPT-Gen contracts."""

from .base import PptxBaseModel
from .config import Config
from .content import ContentModel, ContentSection, ContentCue
from .deck_ir import DeckIR, DeckSlide, AssetRef
from .validation import ValidationReport, ValidationViolation
from .critique import CritiqueReport, CritiqueFinding
from .patch import PatchSet, Patch
from .render_map import RenderMap, RenderMapEntry

__all__ = [
    "Config",
    "PptxBaseModel",
    "ContentModel",
    "ContentSection",
    "ContentCue",
    "DeckIR",
    "DeckSlide",
    "AssetRef",
    "ValidationReport",
    "ValidationViolation",
    "CritiqueReport",
    "CritiqueFinding",
    "PatchSet",
    "Patch",
    "RenderMap",
    "RenderMapEntry",
]
